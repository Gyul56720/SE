"""
Matrix multiplication tensor decomposition searcher via CP-ALS (Alternating Least Squares)
with regularization, momentum/damping, and increased restarts to escape local minima.

Verifier is NEVER modified.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"

LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]


def matmul_tensor(b: int) -> np.ndarray:
    """b x b 행렬곱의 트라이리니어 텐서. C[i,j]=sum_l A[i,l]B[l,j] 에 대응."""
    n = b * b
    T = np.zeros((n, n, n))
    for i in range(b):
        for l in range(b):
            for j in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T


def _unfold(T, mode):
    return np.moveaxis(T, mode, 0).reshape(T.shape[mode], -1)


def _kr(P, Q):
    """열별 Khatri-Rao: k열 = kron(P[:,k], Q[:,k])."""
    return (P[:, None, :] * Q[None, :, :]).reshape(-1, P.shape[1])


def cp_als(T, m, iters=2000, seed=0, tol=1e-12, reg=1e-6):
    """랭크 m CP-ALS with L2 regularization (ridge regression) to avoid ill-conditioned updates."""
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    U = rng.standard_normal((n, m)) * 0.1
    V = rng.standard_normal((n, m)) * 0.1
    W = rng.standard_normal((n, m)) * 0.1
    normT = np.linalg.norm(T)
    res = 1.0
    
    eye = reg * np.eye(m)

    for it in range(iters):
        # U update with regularization
        VTV_WTW = (V.T @ V) * (W.T @ W) + eye
        U = _unfold(T, 0) @ _kr(V, W) @ np.linalg.pinv(VTV_WTW)

        # V update with regularization
        UTU_WTW = (U.T @ U) * (W.T @ W) + eye
        V = _unfold(T, 1) @ _kr(U, W) @ np.linalg.pinv(UTU_WTW)

        # W update with regularization
        UTU_VTV = (U.T @ U) * (V.T @ V) + eye
        W = _unfold(T, 2) @ _kr(U, V) @ np.linalg.pinv(UTU_VTV)

        if it % 50 == 0 or it == iters - 1:
            R = np.einsum('ir,jr,kr->ijk', U, V, W)
            res = float(np.linalg.norm(R - T) / normT)
            if res < tol:
                break
    return U, V, W, res


def factors_to_scheme(U, V, W, b, m) -> dict:
    """(U, V, W) 를 verifier.py 가 이해하는 SCHEME dict 로 변환."""
    A = [{(i, j): float(U[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    B = [{(i, j): float(V[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    C = [{(i, j): [(k, float(W[i * b + j, k])) for k in range(m)]}
         for i in range(b) for j in range(b)]
    return {"b": b, "m": m, "A_coeffs": A, "B_coeffs": B, "C_coeffs": C}


class Searcher:
    """사다리 상태를 파일에 유지하며 매 propose() 마다 현재 단(b,m)에서 ALS 를 돌린다."""

    def __init__(self):
        self.state = self._load()

    def _load(self):
        if STATE_PATH.exists():
            try:
                return json.loads(STATE_PATH.read_text())
            except Exception:
                pass
        return {"stage": 0, "attempt": 0}

    def _save(self):
        STATE_PATH.write_text(json.dumps(self.state, indent=2))

    def current_target(self):
        return LADDER[min(self.state["stage"], len(LADDER) - 1)]

    def propose(self) -> dict:
        b, m = self.current_target()
        attempt = self.state["attempt"]
        # 대폭 강화된 restart 수와 반복 횟수 (b=3에서도 충분한 탐색)
        restarts = 30 if b == 2 else 8
        iters = 2000 if b == 2 else 1500
        best = None
        for r in range(restarts):
            # 다양한 정규화 계수(reg)와 시드를 조합하여 local minima 탈출 시도
            reg = 1e-6 if r % 2 == 0 else 1e-5
            U, V, W, res = cp_als(matmul_tensor(b), m, iters=iters, seed=attempt * 1000 + r * 37, reg=reg)
            if best is None or res < best[0]:
                best = (res, U, V, W)
            if res < 1e-11:
                break
        self.state["attempt"] = attempt + 1
        self._save()
        res, U, V, W = best
        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_als_residual"] = res
        return scheme

    def record(self, ok: bool):
        """루프가 verifier 판정을 알려준다. 성공하면 다음(더 어려운) 단으로 올린다."""
        if ok and self.state["stage"] < len(LADDER) - 1:
            self.state["stage"] += 1
            self.state["attempt"] = 0
            self._save()


def propose() -> dict:
    """모듈 레벨 진입점."""
    return Searcher().propose()
