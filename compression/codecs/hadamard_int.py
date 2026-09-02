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

# 실제 Qwen2.5-0.5B 가중치로 재보정한 값(실측). 예전 값(BITS=7, MAX_GROUP=128)은 실제
# 가중치에서 **떨어진다** -- VM 에서 7.125 bits / 오차 0.01310 대 int8 의 8.036 / 0.00913.
#
# 원인 둘:
#  1) 실제 가중치에는 극적인 행 내 outlier 가 없다. per-row max-abs int8 오차가 0.00918 로
#     같은 폭의 순수 가우시안(0.00778)보다 18% 높은 정도다. 그래서 회전이 벌어주는 것이
#     1.2~1.3배뿐이다(잘못 보정된 합성에서는 3배로 보였다). 1비트를 줄이면 오차가 2배가
#     되므로 int7 은 회수가 안 된다.
#  2) 그룹이 잘면 스케일이 비싸다. 128 상한이면 896 폭에서 fp16 스케일이 0.143 bits 인데,
#     int8 기준선의 행별 fp32 스케일은 0.036 bits 다 -- 우리가 0.107 을 더 내고 있었다.
#     가중치가 거의 가우시안이라 잔 그룹이 사주는 것도 별로 없다.
#
# 지금 값으로 재보정 합성에서 8.068 bits / 오차 0.00699 대 int8 8.143 / 0.00908 -- 두 축
# 통과. 다만 **비트 마진이 0.9% 로 얇다**(실제 896 폭에서는 0.2%). 쓸 만한 마진은 엔트로피
# 부호화에서 나온다: 코드 엔트로피가 log2(L) 보다 0.57 bits 낮아서 7.50 bits 가 된다
# (비트 7.9% 감소, 오차 23% 감소). 아직 구현하지 않았다.
BITS = 8
MAX_GROUP = 1024          # 스케일 하나가 덮는 최대 원소 수
MAX_HBLOCK = 128          # 아다마르 블록의 최대 크기 (섞는 폭)
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
