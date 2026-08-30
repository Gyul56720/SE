from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import List, Tuple, Optional
import numpy as np

@dataclass
class Certificate:
    status: str
    exact_verified: bool
    finite_field_verified: bool
    failure_reason: Optional[str] = None
    rank: int = 0
    prime: int = 65537

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
        if not np.isfinite(U).all() or not np.isfinite(V).all() or not np.isfinite(W).all():
            return Certificate("DEGENERATE", False, False, "Non-finite values")
        
        try:
            U_rat = [[Fraction(x).limit_denominator(100000) for x in row] for row in U]
            V_rat = [[Fraction(x).limit_denominator(100000) for x in row] for row in V]
            W_rat = [[Fraction(x).limit_denominator(100000) for x in row] for row in W]
            L_rat = [Fraction(x).limit_denominator(100000) for x in lambdas]
        except Exception as e:
            return Certificate("RECONSTRUCTION_FAILED", False, False, str(e))

        exact_ok = self.exact.verify(U_rat, V_rat, W_rat, L_rat)
        ff_ok = False # Hard constraint: implemented later
        
        status = "CERTIFIED" if (exact_ok and ff_ok) else "REJECTED"
        return Certificate(status, exact_ok, ff_ok, rank=U.shape[1])
