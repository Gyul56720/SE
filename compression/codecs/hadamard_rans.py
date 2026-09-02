"""아다마르 회전 + 블록 양자화 + rANS 엔트로피 부호화.

hadamard_int 와 양자화까지 같고, 코드를 균일길이로 담는 대신 엔트로피 부호화한다.

왜 이득이 있나(실측): 회전 후 가중치는 사실상 가우시안이다(미분 엔트로피가 같은 분산
가우시안과 0.001 bits 차이). 그러면 양자화 코드도 가운데 레벨이 훨씬 자주 쓰이는데,
균일길이 코드는 256개 레벨 모두에 8비트를 준다. 실제 코드 엔트로피는 log2(L) 보다
**0.57 bits 낮고**, 그 차이가 그대로 낭비다.

이 이득은 오차를 건드리지 않는다 -- 같은 코드를 더 짧게 담을 뿐이라 복원 결과가 비트
단위로 동일하다. 두 축 중 압축력만 움직이는, 드물게 공짜에 가까운 개선이다.

blob 에 빈도표를 실어야 한다(256 x 2바이트 = 512바이트). 큰 텐서에서는 무시할 수준이지만
(4864x896 에서 0.001 bits) 작은 텐서에서는 비싸다(7168 원소면 0.57 bits -- 아끼는 만큼을
그대로 되뱉는다). 실제 Qwen2.5-0.5B 의 가장 작은 대상은 k/v_proj 의 128x896 = 114688 로
0.036 bits 라 문제가 없지만, 합성 벤치의 작은 텐서에서는 이득이 상쇄되어 보일 수 있다.

회전과 양자화의 근거는 hadamard_int.py 의 주석을 보라. 여기서는 담는 방식만 다르다.
"""
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import rans  # noqa: E402

BITS = 8
MAX_GROUP = 1024
MAX_HBLOCK = 128
MAGIC = b"HE"
N_SYM = 1 << BITS


def _pow2_divisor(n, cap):
    d = 1
    while d * 2 <= cap and n % (d * 2) == 0:
        d *= 2
    return d


def _divisor(n, cap):
    for g in range(min(cap, n), 0, -1):
        if n % g == 0:
            return g
    return 1


def _hadamard(n):
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


def encode(W):
    W = np.ascontiguousarray(W, dtype=np.float32)
    rows, cols = W.shape
    g = _divisor(cols, MAX_GROUP)
    qmax = (1 << (BITS - 1)) - 1

    R = (W @ _rotation(cols)).reshape(rows, -1, g)
    scale = (np.abs(R).max(2, keepdims=True) / qmax).astype(np.float16)
    sf = scale.astype(np.float32)
    sf[sf == 0] = 1.0
    q = np.round(R / sf).clip(-qmax, qmax).astype(np.int64)

    sym = (q + qmax).ravel()                       # 부호 있는 값을 0.. 로 옮긴다
    freq = rans.build_table(sym, N_SYM)
    return (struct.pack("<2sBBII", MAGIC, BITS, 0, rows, cols)
            + freq.astype("<u2").tobytes()
            + scale.tobytes()
            + rans.encode(sym, freq))


def decode(blob):
    magic, bits, _, rows, cols = struct.unpack("<2sBBII", blob[:12])
    if magic != MAGIC:
        raise ValueError("blob 형식이 아니다")
    n_sym = 1 << bits
    qmax = (1 << (bits - 1)) - 1
    g = _divisor(cols, MAX_GROUP)
    nblk = cols // g

    off = 12
    freq = np.frombuffer(blob[off:off + n_sym * 2], dtype="<u2").astype(np.int64)
    off += n_sym * 2
    n_scale = rows * nblk
    scale = np.frombuffer(blob[off:off + n_scale * 2],
                          dtype=np.float16).reshape(rows, nblk, 1).astype(np.float32)
    off += n_scale * 2

    sym = rans.decode(blob[off:], rows * cols, freq)
    q = (sym.astype(np.float32) - qmax).reshape(rows, nblk, g)
    R = (q * scale).reshape(rows, cols)
    return np.ascontiguousarray(R @ _rotation(cols).T, dtype=np.float32)
