"""
행렬 곱셈 지수(omega) 탐색 스켈리톤.

목표: N x N 행렬 곱을, b x b 블록을 m번의 (스칼라/블록) 곱셈으로 계산하는
"bilinear algorithm"을 찾아서 유효 지수 omega_eff = log(m) / log(b) 를
2.0 에 최대한 가깝게 낮추는 것.

핵심 아이디어 (Strassen 1969 와 동일한 틀):
- b x b 블록 행렬 곱 C = A @ B 를, A/B 블록들의 선형결합 m개를 곱하고
  (M_1..M_m), 그 곱들의 선형결합으로 C의 각 블록을 복원하는 형태로 쓴다.
- 이 스킴이 "맞다"는 것은 수식이 아니라, 무작위 행렬로 직접 검산해서 확인한다
  (기호적으로 증명하는 대신, 통계적으로 강하게 신뢰 - 여러 seed로 반복 검증).
- b, m 을 정의하는 계수 텐서만 스스로 수정(self-modify)하면 되도록 구조를 분리했다.
  SE 에이전트는 SCHEME 딕셔너리만 고치면 된다. 나머지 실행/검증 로직은 건드릴 필요 없다.

스킴 표현:
  SCHEME = {
      "b": b,                     # 블록 크기 (예: 2 -> 2x2 블록)
      "m": m,                     # 사용하는 곱셈 개수 (예: Strassen은 7)
      "A_coeffs": [ (i,j,coeff), ... 총 m개 리스트의 리스트 ],
      "B_coeffs": [ ... ],
      "C_coeffs": [ ... ],
  }
  더 정확히는 아래 make_strassen_2x2() 예시를 참고.
"""

import itertools
import numpy as np


def make_strassen_2x2():
    """기준선(baseline): 표준 Strassen 2x2 스킴. b=2, m=7 -> omega=log2(7)=2.807.

    A, B 를 2x2 블록으로 나눴을 때:
      A = [[A11,A12],[A21,A22]], B = [[B11,B12],[B21,B22]]
    M1..M7 (Strassen 1969):
      M1=(A11+A22)(B11+B22)
      M2=(A21+A22)B11
      M3=A11(B12-B22)
      M4=A22(B21-B11)
      M5=(A11+A12)B22
      M6=(A21-A11)(B11+B12)
      M7=(A12-A22)(B21+B22)
    C11=M1+M4-M5+M7
    C12=M3+M5
    C21=M2+M4
    C22=M1-M2+M3+M6
    """
    b = 2
    A_coeffs = [
        {(0, 0): 1, (1, 1): 1},   # A11+A22
        {(1, 0): 1, (1, 1): 1},   # A21+A22
        {(0, 0): 1},              # A11
        {(1, 1): 1},              # A22
        {(0, 0): 1, (0, 1): 1},   # A11+A12
        {(1, 0): 1, (0, 0): -1},  # A21-A11
        {(0, 1): 1, (1, 1): -1},  # A12-A22
    ]
    B_coeffs = [
        {(0, 0): 1, (1, 1): 1},
        {(0, 0): 1},
        {(0, 1): 1, (1, 1): -1},
        {(1, 0): 1, (0, 0): -1},
        {(1, 1): 1},
        {(0, 0): 1, (0, 1): 1},
        {(1, 0): 1, (1, 1): 1},
    ]
    C_coeffs = [
        {(0, 0): [(0, 1), (3, 1), (4, -1), (6, 1)]},
        {(0, 1): [(2, 1), (4, 1)]},
        {(1, 0): [(1, 1), (3, 1)]},
        {(1, 1): [(0, 1), (1, -1), (2, 1), (5, 1)]},
    ]
    return {"b": b, "m": 7, "A_coeffs": A_coeffs, "B_coeffs": B_coeffs, "C_coeffs": C_coeffs}


# ---------------------------------------------------------------------------
# SE 에이전트가 여기를 고쳐서 m 을 7보다 줄인 새 스킴을 시도한다.
# 처음에는 baseline 그대로 둔다 - 자가 수정 루프가 이 값을 변형해 나간다.
SCHEME = make_strassen_2x2()
# ---------------------------------------------------------------------------


def _block_slices(n, b):
    step = n // b
    return [slice(k * step, (k + 1) * step) for k in range(b)]


def scheme_multiply(A, B, scheme):
    """scheme 을 이용해 재귀적으로 A @ B 를 계산 (b^k 크기 정사각행렬 전용)."""
    n = A.shape[0]
    b = scheme["b"]
    if n == b:
        return _apply_scheme_base(A, B, scheme)
    if n % b != 0:
        raise ValueError(f"size {n} not divisible by block size {b}")

    sl = _block_slices(n, b)
    Ablk = [[A[sl[i], sl[j]] for j in range(b)] for i in range(b)]
    Bblk = [[B[sl[i], sl[j]] for j in range(b)] for i in range(b)]

    M = []
    for k in range(scheme["m"]):
        Ak = sum(c * Ablk[i][j] for (i, j), c in scheme["A_coeffs"][k].items())
        Bk = sum(c * Bblk[i][j] for (i, j), c in scheme["B_coeffs"][k].items())
        M.append(scheme_multiply(Ak, Bk, scheme))

    step = n // b
    C = np.zeros_like(A)
    for (i, j), terms in [(pos, terms) for entry in scheme["C_coeffs"] for pos, terms in entry.items()]:
        acc = np.zeros((step, step), dtype=A.dtype)
        for k, c in terms:
            acc = acc + c * M[k]
        C[sl[i], sl[j]] = acc
    return C


def _apply_scheme_base(A, B, scheme):
    """블록 크기 b 그 자체에서는 재귀를 멈추고 scheme 을 한 번만 적용한다."""
    b = scheme["b"]
    M = []
    for k in range(scheme["m"]):
        Ak = sum(c * A[i, j] for (i, j), c in scheme["A_coeffs"][k].items())
        Bk = sum(c * B[i, j] for (i, j), c in scheme["B_coeffs"][k].items())
        M.append(Ak * Bk)

    C = np.zeros_like(A)
    for entry in scheme["C_coeffs"]:
        for (i, j), terms in entry.items():
            C[i, j] = sum(c * M[k] for k, c in terms)
    return C


def effective_omega(scheme):
    """omega_eff = log(m) / log(b). 2.0 이 이론 하한, 낮을수록 좋다."""
    import math
    return math.log(scheme["m"]) / math.log(scheme["b"])


def verify_scheme(scheme, sizes=(2, 4, 8), trials=20, seed=0):
    """무작위 행렬로 scheme_multiply 결과를 numpy 표준 곱과 비교해서 검산한다.

    scheme["b"]^k 형태의 정사각행렬 크기들에 대해 시도. 모두 통과해야 True.
    """
    rng = np.random.default_rng(seed)
    b = scheme["b"]
    for size in sizes:
        if size % b != 0 and size != 1:
            continue
        for _ in range(trials):
            A = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
            B = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
            expected = A @ B
            got = scheme_multiply(A, B, scheme)
            if not np.allclose(expected, got, atol=1e-6):
                return False, f"mismatch at size={size}"
    return True, "ok"


if __name__ == "__main__":
    ok, msg = verify_scheme(SCHEME)
    print(f"verify: {ok} ({msg})")
    print(f"b={SCHEME['b']} m={SCHEME['m']} omega_eff={effective_omega(SCHEME):.6f}")
