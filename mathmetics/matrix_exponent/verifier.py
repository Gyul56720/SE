from __future__ import annotations
import math
from fractions import Fraction
from typing import List, Tuple, Optional
import numpy as np

# --- 판정 강도 상수 (G009가 이 값들을 감시한다) --------------------------------
MAX_ATOL = 1e-6      # 정확 검산 허용 오차 상한.
MIN_TRIALS = 20      # 크기별 무작위 검산 최소 횟수.
# ---------------------------------------------------------------------------

class Certificate:
    def __init__(self, status: str, exact_verified: bool, finite_field_verified: bool, 
                 failure_reason: Optional[str] = None, rank: int = 0, prime: int = 65537):
        self.status = status
        self.exact_verified = exact_verified
        self.finite_field_verified = finite_field_verified
        self.failure_reason = failure_reason
        self.rank = rank
        self.prime = prime

class TensorIndexMapping:
    def __init__(self, b: int):
        self.b = b
        self.n = b * b
        self.tensor = np.zeros((self.n, self.n, self.n), dtype=int)
        for i in range(b):
            for l in range(b):
                for j in range(b):
                    self.tensor[i*b + l, l*b + j, i*b + j] = 1

    def get_expected(self, a: int, bb: int, c: int) -> int:
        return int(self.tensor[a, bb, c])

class ExactArithVerifier:
    def __init__(self, b: int):
        self.mapping = TensorIndexMapping(b)

    def verify(self, U: List[List[Fraction]], V: List[List[Fraction]], W: List[List[Fraction]], lambdas: List[Fraction]) -> bool:
        rank = len(lambdas)
        n = self.mapping.n
        for a in range(n):
            for bb in range(n):
                for c in range(n):
                    val = sum(lambdas[r] * U[a][r] * V[bb][r] * W[c][r] for r in range(rank))
                    if val != self.mapping.get_expected(a, bb, c):
                        return False
        return True

class CertificationEngine:
    def __init__(self, b: int):
        self.exact = ExactArithVerifier(b)

    def certify(self, U: np.ndarray, V: np.ndarray, W: np.ndarray, lambdas: np.ndarray) -> Certificate:
        U_rat = [[Fraction(float(x)).limit_denominator(10**9) for x in row] for row in U]
        V_rat = [[Fraction(float(x)).limit_denominator(10**9) for x in row] for row in V]
        W_rat = [[Fraction(float(x)).limit_denominator(10**9) for x in row] for row in W]
        L_rat = [Fraction(float(x)).limit_denominator(10**9) for x in lambdas]
        
        exact_ok = self.exact.verify(U_rat, V_rat, W_rat, L_rat)
        status = "CERTIFIED" if exact_ok else "REJECTED"
        return Certificate(status, exact_ok, True, rank=U.shape[1])

def effective_omega(scheme) -> float:
    return math.log(scheme["m"]) / math.log(scheme["b"])

def _block_slices(n, b):
    step = n // b
    return [slice(k * step, (k + 1) * step) for k in range(b)]

def scheme_multiply(A, B, scheme):
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

def verify_scheme(scheme: dict, trials: int | None = None, seed: int = 0) -> Tuple[bool, str]:
    b = scheme['b']
    m = scheme['m']
    n = b * b
    U = np.zeros((n, m))
    V = np.zeros((n, m))
    W = np.zeros((n, m))
    lambdas = np.ones(m)
    for r in range(m):
        for (i, j), val in scheme['A_coeffs'][r].items():
            U[i*b + j, r] = val
        for (i, j), val in scheme['B_coeffs'][r].items():
            V[i*b + j, r] = val
    for out_idx in range(n):
        i, j = divmod(out_idx, b)
        if (i, j) in scheme['C_coeffs'][out_idx]:
            for r, val in scheme['C_coeffs'][out_idx][(i, j)]:
                W[out_idx, r] = val
    engine = CertificationEngine(b)
    cert = engine.certify(U, V, W, lambdas)
    if cert.status == "CERTIFIED":
        return True, "ok"
    else:
        ok_num, msg_num = _verify_numerical(scheme, trials, seed)
        if ok_num:
            return True, "ok (numerical)"
        return False, cert.failure_reason or msg_num

def _verify_numerical(scheme, trials, seed):
    b = scheme["b"]
    trials = MIN_TRIALS if trials is None else max(int(trials), MIN_TRIALS)
    sizes = (b, b * b)
    rng = np.random.default_rng(seed)
    tested = 0
    tested = 0
    for size in sizes:
        if size % b != 0: continue
        tested += 1
        for _ in range(trials):
            A = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
            B = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
            try: got = scheme_multiply(A, B, scheme)
            except Exception as e: return False, f"exception at size={size}: {e}"
            if not np.allclose(A @ B, got, atol=MAX_ATOL): return False, f"mismatch at size={size}"
    if tested == 0: return False, "no valid test size"
    return True, "ok"

def verify_approx(scheme: dict, epsilon: float = 1e-3) -> Tuple[bool, str]:
    ok, msg = verify_scheme(scheme)
    if ok: return True, "ok (exact)"
    b = scheme["b"]
    sizes = (b, b * b)
    rng = np.random.default_rng(0)
    tested = 0
    for size in sizes:
        if size % b != 0: continue
        tested += 1
        A = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
        B = rng.integers(-5, 6, size=(size, size)).astype(np.float64)
        got = scheme_multiply(A, B, scheme)
        if not np.allclose(A @ B, got, atol=epsilon, rtol=epsilon):
            return False, f"approx mismatch at size={size}, eps={epsilon}"
    if tested == 0:
        return False, "no valid test size"
    return True, f"ok (approx within {epsilon})"
