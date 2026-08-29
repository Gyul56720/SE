"""
[신뢰·보호] 행렬곱 스킴의 정확성과 비용을 판정하는 유일한 근거.

이 파일은 자가 수정 실험의 '심판'이다. searcher 는 어떤 방법(ALS, 강화학습, 유전
알고리즘, SE가 고안한 신종 방법 등)으로든 자유롭게 후보 스킴을 만들어도 되지만, 그 결과가
'맞는지' 그리고 '더 나은지'는 오직 이 파일이 정한다. 그래서 이 파일은 searcher 와 분리돼
있고, gates/G009 가 판정 강도(정확 검산·최소 시행·오차 상한)가 약화되지 않도록 커밋 경로에서
강제한다. searcher 를 아무리 고쳐도 이 심판을 조작할 수 없어야, "SE가 정말로 더 나은
알고리즘을 찾았다"는 결과를 신뢰할 수 있다.

절대 하지 말 것 (G009가 막는다):
  - MAX_ATOL 을 키워서(느슨한 근사를 정확으로 위장) 통과시키기
  - MIN_TRIALS 를 줄여서 검산을 대충 하기
  - 검산을 건너뛰고(vacuous) 성공을 반환하기 (G008도 막는다)
  - 틀린 스킴을 통과시키기

정답의 정의(계약): b x b 블록 행렬곱 C=A@B 를, A/B 블록들의 선형결합 m개의 곱(M_1..M_m)과
그 곱들의 선형결합으로 C의 각 블록을 복원하는 '정확한 bilinear 분해'. 비용 지표는
omega_eff = log(m)/log(b) (낮을수록 좋음). 이 계약 자체를 넓히려면(예: 근사/border rank
허용) 이 파일을 '의도적·신뢰된 변경'으로 확장해야 하며, searcher 가 몰래 넓혀선 안 된다.
"""
from __future__ import annotations

import math

import numpy as np

# --- 판정 강도 상수 (G009가 이 값들을 감시한다) --------------------------------
MAX_ATOL = 1e-6      # 정확 검산 허용 오차 상한. 이보다 크면 근사를 정답으로 위장하는 것.
MIN_TRIALS = 20      # 크기별 무작위 검산 최소 횟수.
# ---------------------------------------------------------------------------


def effective_omega(scheme) -> float:
    """omega_eff = log(m)/log(b). 2.0 이 이론 하한, 낮을수록 좋다."""
    return math.log(scheme["m"]) / math.log(scheme["b"])


def _block_slices(n, b):
    step = n // b
    return [slice(k * step, (k + 1) * step) for k in range(b)]


def scheme_multiply(A, B, scheme):
    """scheme 으로 A @ B 를 재귀 계산 (b^k 크기 정사각행렬 전용)."""
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
    for entry in scheme["C_coeffs"]:
        for (i, j), terms in entry.items():
            acc = np.zeros((step, step), dtype=A.dtype)
            for k, c in terms:
                acc = acc + c * M[k]
            C[sl[i], sl[j]] = acc
    return C


def _apply_scheme_base(A, B, scheme):
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


def _validate_structure(scheme) -> str:
    """스킴이 계약(형식)을 지키는지. 문제 있으면 사유 문자열, 없으면 빈 문자열."""
    if not isinstance(scheme, dict):
        return "scheme 이 dict 가 아니다"
    for key in ("b", "m", "A_coeffs", "B_coeffs", "C_coeffs"):
        if key not in scheme:
            return f"필수 키 '{key}' 누락"
    b, m = scheme["b"], scheme["m"]
    if not isinstance(b, int) or b < 2:
        return f"b 는 2 이상의 정수여야 한다 (b={b!r})"
    if not isinstance(m, int) or m < 1:
        return f"m 은 1 이상의 정수여야 한다 (m={m!r})"
    for name in ("A_coeffs", "B_coeffs"):
        if len(scheme[name]) != m:
            return f"{name} 의 길이({len(scheme[name])})가 m({m})과 다르다"
    return ""


def verify_scheme(scheme, trials: int | None = None, seed: int = 0):
    """무작위 정수 행렬로 scheme_multiply 결과를 numpy 표준 곱과 정확 비교한다.

    - 검산 크기는 스킴의 b 로부터 자동 결정한다: (b, b^2). 항상 b 로 나눠지므로
      "크기가 안 맞아 전부 건너뛰어 검산 0회로 통과"하는 일이 구조적으로 불가능하다.
    - 허용 오차는 MAX_ATOL, 크기별 시행 횟수는 max(주어진 trials, MIN_TRIALS).
    - 실제로 검산한 크기가 하나도 없으면(should not happen) fail-closed 로 실패.
    반환: (ok: bool, msg: str).
    """
    err = _validate_structure(scheme)
    if err:
        return False, f"invalid scheme: {err}"

    b = scheme["b"]
    trials = MIN_TRIALS if trials is None else max(int(trials), MIN_TRIALS)
    sizes = (b, b * b)
    rng = np.random.default_rng(seed)

    tested = 0
    for size in sizes:
        if size % b != 0:
            continue
        tested += 1
        for _ in range(trials):
            A = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
            B = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
            try:
                got = scheme_multiply(A, B, scheme)
            except Exception as e:
                return False, f"exception at size={size}: {e}"
            if not np.allclose(A @ B, got, atol=MAX_ATOL):
                return False, f"mismatch at size={size}"

    if tested == 0:
        return False, "no valid test size (fail-closed)"
    return True, "ok"
