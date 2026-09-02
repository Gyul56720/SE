"""아다마르 회전 + 블록 균일 양자화.

핵심은 양자화 전에 가중치를 직교 회전시키는 것이다. H 가 직교면

    W' = quantize(W·H)·Hᵀ = (W·H + E)·Hᵀ = W + E·Hᵀ,   ‖E·Hᵀ‖_F = ‖E‖_F

이라 되돌리는 과정에서 오차가 커지지 않는다. 그런데 W·H 는 W 보다 양자화하기 훨씬 쉽다.
블록 max-abs 양자화의 스텝은 Δ = 2·max|w| / (2^b - 2) 이고, 블록 안 최댓값 하나가 그
블록 전체의 오차를 정한다. 실제 가중치는 채널마다 소수의 큰 값이 나머지의 해상도를
잡아먹는데(행별 max/std 가 8 을 넘는다), 회전이 값을 섞어 그 봉우리를 없앤다.

**H 는 blob 에 담기지 않는다.** n 하나로 결정되는 상수이기 때문이다 -- decode 가 같은
n 에서 같은 H 를 다시 만든다. 같은 크기의 서로 다른 두 행렬이 똑같은 H 를 받으므로
H 를 통해 W 의 정보가 새어나갈 수 없다. 학습된 회전은 이와 달리 W 에 의존하므로 반드시
저장해야 하고, n=896 이면 16·896² = 12.8M 비트가 든다.

실제 차원은 2의 거듭제곱이 아니다(896 = 2^7·7, 4864 = 2^8·19). 실베스터 아다마르는
2^k 에서만 나오므로, n 을 나누는 가장 큰 2의 거듭제곱 크기로 **블록 대각** 아다마르를
쓴다. 블록 안에서만 섞이지만 실측상 손해가 거의 없다 -- 섞는 폭 128 은 전체 회전과
동등하고, 32 까지 내려가도 이득의 대부분이 남는다.
"""
import struct

import numpy as np

# 코드 하나의 비트 수. 6 이 아니라 7 인 이유(실측): 6 비트에서는 회전이 오차를 int8 과
# 거의 같은 자리까지만 끌어내려 두 축 래칫을 안정적으로 못 넘는다 -- design 셋에서
# 0.02538 vs int8 0.02475 로 지고 holdout 에서 0.02457 vs 0.02595 로 이긴다. 어느 텐서가
# 어느 split 에 떨어졌느냐로 승패가 갈리는 마진은 챔피언 자격이 아니다. 7 비트에서는
# 양쪽 split 모두 오차가 int8 의 절반(0.0124 vs 0.0248)이면서 비트는 7.16 < 8.14 다.
BITS = 7
MAX_GROUP = 128           # 스케일 하나가 덮는 최대 원소 수
MAX_HBLOCK = 128          # 아다마르 블록의 최대 크기
MAGIC = b"HR"


def _pow2_divisor(n, cap):
    """n 을 나누는 가장 큰 2의 거듭제곱 (cap 이하). 224 -> 32, 304 -> 16, 896 -> 128."""
    d = 1
    while d * 2 <= cap and n % (d * 2) == 0:
        d *= 2
    return d


def _divisor(n, cap):
    """n 을 나누는 가장 큰 수 (cap 이하). 그룹 크기를 정한다."""
    for g in range(min(cap, n), 0, -1):
        if n % g == 0:
            return g
    return 1


def _hadamard(n):
    """실베스터 재귀. H·Hᵀ = I 인 ±1/√n 행렬."""
    H = np.ones((1, 1), dtype=np.float32)
    while H.shape[0] < n:
        H = np.block([[H, H], [H, -H]])
    return H / np.sqrt(n, dtype=np.float32)


def _rotation(n):
    """n 에서만 결정되는 블록 대각 아다마르. blob 에 담지 않는 이유가 이것이다."""
    b = _pow2_divisor(n, MAX_HBLOCK)
    Hb = _hadamard(b)
    H = np.zeros((n, n), dtype=np.float32)
    for i in range(n // b):
        H[i * b:(i + 1) * b, i * b:(i + 1) * b] = Hb
    return H


def _pack(codes, bits):
    """0..2^bits-1 정수를 비트 단위로 이어붙인다. 바이트 경계에 낭비를 두지 않는다."""
    sh = np.arange(bits - 1, -1, -1, dtype=np.uint8)
    return np.packbits(((codes[:, None] >> sh) & 1).astype(np.uint8).ravel()).tobytes()


def _unpack(raw, count, bits):
    flat = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))[:count * bits]
    sh = np.arange(bits - 1, -1, -1, dtype=np.uint16)
    return (flat.reshape(count, bits).astype(np.uint16) << sh).sum(1)


def encode(W):
    W = np.ascontiguousarray(W, dtype=np.float32)
    rows, cols = W.shape
    g = _divisor(cols, MAX_GROUP)
    qmax = (1 << (BITS - 1)) - 1

    R = (W @ _rotation(cols)).reshape(rows, -1, g)
    scale = (np.abs(R).max(2, keepdims=True) / qmax).astype(np.float16)
    sf = scale.astype(np.float32)
    sf[sf == 0] = 1.0
    q = np.round(R / sf).clip(-qmax, qmax).astype(np.int16)

    codes = (q + qmax).astype(np.uint16).ravel()          # 부호 있는 값을 0.. 로 옮긴다
    return (struct.pack("<2sBBII", MAGIC, BITS, 0, rows, cols)
            + scale.tobytes() + _pack(codes, BITS))


def decode(blob):
    magic, bits, _, rows, cols = struct.unpack("<2sBBII", blob[:12])
    if magic != MAGIC:
        raise ValueError("blob 형식이 아니다")
    g = _divisor(cols, MAX_GROUP)
    nblk = cols // g
    qmax = (1 << (bits - 1)) - 1

    n_scale = rows * nblk
    off = 12 + n_scale * 2
    scale = np.frombuffer(blob[12:off], dtype=np.float16).reshape(rows, nblk, 1).astype(np.float32)
    codes = _unpack(blob[off:], rows * cols, bits).astype(np.float32)

    R = (codes.reshape(rows, nblk, g) - qmax) * scale
    return np.ascontiguousarray(R.reshape(rows, cols) @ _rotation(cols).T, dtype=np.float32)
