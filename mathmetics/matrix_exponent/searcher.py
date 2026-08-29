"""
Matrix multiplication tensor decomposition searcher via CP-ALS (Alternating Least Squares)
combined with Perturbation & Warm-Start Refinement to escape local minima for tighter ranks (m=22, m=21),
while strictly preserving pure ALS for b=2 (m=7) to satisfy G010 capability ratchet.

Verifier is NEVER modified.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"

# 미해결 난제 사다리: b=3에서 m=23 정복 후 m=22, m=21 도전
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


def cp_als(T, m, iters=2000, seed=0, tol=1e-12, init_U=None, init_V=None, init_W=None, noise_scale=0.0):
    """랭크 m CP-ALS with optional warm-start and perturbation. (U, V, W, 상대잔차) 반환."""
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    
    if init_U is not None and init_V is not None and init_W is not None:
        U = init_U + rng.normal(0, noise_scale, init_U.shape)
        V = init_V + rng.normal(0, noise_scale, init_V.shape)
        W = init_W + rng.normal(0, noise_scale, init_W.shape)
    else:
        U = rng.standard_normal((n, m))
        V = rng.standard_normal((n, m))
        W = rng.standard_normal((n, m))
        
    normT = np.linalg.norm(T)
    res = 1.0
    
    for it in range(iters):
        U = _unfold(T, 0) @ _kr(V, W) @ np.linalg.pinv((V.T @ V) * (W.T @ W))
        V = _unfold(T, 1) @ _kr(U, W) @ np.linalg.pinv((U.T @ U) * (W.T @ W))
        W = _unfold(T, 2) @ _kr(U, V) @ np.linalg.pinv((U.T @ U) * (V.T @ V))
        
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
        
        T = matmul_tensor(b)
        
        if b == 2:
            # G010 래칫 보존을 위한 순수 ALS (b=2 m=7은 기존 방식 그대로 확실하게 도달)
            restarts = 20
            iters = 1500
            best = None
            for r in range(restarts):
                U, V, W, res = cp_als(T, m, iters=iters, seed=attempt * 100 + r)
                if best is None or res < best[0]:
                    best = (res, U, V, W)
                if res < 1e-11:
                    break
            res, U, V, W = best
        else:
            # b=3 (m=23, m=22 등 난제): Multi-stage Perturbation & Warm-Start 최적화 기법 적용
            restarts = 10
            iters = 2000
            best = None
            best_U, best_V, best_W = None, None, None
            
            for r in range(restarts):
                # 1단계: 기본 ALS 탐색
                U, V, W, res = cp_als(T, m, iters=iters, seed=attempt * 1000 + r * 31)
                if best is None or res < best:
                    best = res
                    best_U, best_V, best_W = U, V, W
                if res < 1e-11:
                    break
            
            # 2단계: 최선의 로컬 미니마 지점을 기반으로 미세 섭동(Perturbation)을 준 후 재최적화 (Escape local minima)
            if best_U is not None and best > 1e-6:
                for p_idx, noise in enumerate([1e-3, 5e-4, 1e-4]):
                    U_ref, V_ref, W_ref, res_ref = cp_als(
                        T, m, iters=2000, seed=attempt * 2000 + p_idx,
                        init_U=best_U, init_V=best_V, init_W=best_W, noise_scale=noise
                    )
                    if res_ref < best:
                        best = res_ref
                        best_U, best_V, best_W = U_ref, V_ref, W_ref
                    if best < 1e-11:
                        break
                        
            U, V, W, res = best_U, best_V, best_W, best

        self.state["attempt"] = attempt + 1
        self._save()
        
        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_als_residual"] = res  # 참고용
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
