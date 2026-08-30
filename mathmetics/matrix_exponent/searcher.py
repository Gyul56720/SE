import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]


def matmul_tensor(b: int) -> np.ndarray:
    """b x b 행렬곱을 3차 텐서 T[i*b+l, l*b+j, i*b+j] = 1 로 구성."""
    n = b * b
    T = np.zeros((n, n, n), dtype=np.float64)
    for i in range(b):
        for l in range(b):
            for j in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T


def _unfold(T: np.ndarray, mode: int) -> np.ndarray:
    return np.moveaxis(T, mode, 0).reshape(T.shape[mode], -1)


def _kr(P: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """Khatri-Rao product (column-wise Kronecker product)."""
    return (P[:, None, :] * Q[None, :, :]).reshape(-1, P.shape[1])


def cp_als(
    T: np.ndarray,
    m: int,
    iters: int = 2000,
    seed: int = 0,
    init_U: np.ndarray | None = None,
    init_V: np.ndarray | None = None,
    init_W: np.ndarray | None = None,
    noise_scale: float = 0.0,
    tol: float = 1e-12,
):
    """CP-ALS (Alternating Least Squares)로 행렬곱 텐서의 rank-m bilinear 분해 최적화."""
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
        # Update U
        V_V = V.T @ V
        W_W = W.T @ W
        Gram_VW = V_V * W_W
        U = _unfold(T, 0) @ _kr(V, W) @ np.linalg.pinv(Gram_VW)

        # Update V
        U_U = U.T @ U
        Gram_UW = U_U * W_W
        V = _unfold(T, 1) @ _kr(U, W) @ np.linalg.pinv(Gram_UW)

        # Update W
        Gram_UV = U_U * (V.T @ V)
        W = _unfold(T, 2) @ _kr(U, V) @ np.linalg.pinv(Gram_UV)

        if it % 50 == 0 or it == iters - 1:
            R = np.einsum("ir,jr,kr->ijk", U, V, W)
            res = float(np.linalg.norm(R - T) / normT)
            if res < tol:
                break

    return U, V, W, res


def factors_to_scheme(U: np.ndarray, V: np.ndarray, W: np.ndarray, b: int, m: int) -> dict:
    """(U, V, W) 요소를 verifier.py 규격의 scheme dict로 변환."""
    A = [{(i, j): float(U[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    B = [{(i, j): float(V[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    C = [
        {(i, j): [(k, float(W[i * b + j, k])) for k in range(m)]}
        for i in range(b)
        for j in range(b)
    ]
    return {"b": b, "m": m, "A_coeffs": A, "B_coeffs": B, "C_coeffs": C}


class Searcher:
    """사다리(LADDER) 상태를 저장하면서 CP-ALS 및 warm-start 섭동으로 b, m 분해 탐색."""

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
            # b=2 m=7 (Strassen 기준): G010 래칫 안전성을 위해 기본 CP-ALS 다중 리스타트
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
            # b=3 난제 (m=23, 22, 21): 2-stage ALS + Perturbation 탐색
            restarts = 10
            iters = 2000
            best_res = float("inf")
            best_U, best_V, best_W = None, None, None

            for r in range(restarts):
                U, V, W, res = cp_als(T, m, iters=iters, seed=attempt * 1000 + r * 31)
                if res < best_res:
                    best_res = res
                    best_U, best_V, best_W = U, V, W
                if res < 1e-11:
                    break

            if best_U is not None and best_res > 1e-6:
                for p_idx, noise in enumerate([1e-3, 5e-4, 1e-4]):
                    U_ref, V_ref, W_ref, res_ref = cp_als(
                        T,
                        m,
                        iters=2000,
                        seed=attempt * 2000 + p_idx,
                        init_U=best_U,
                        init_V=best_V,
                        init_W=best_W,
                        noise_scale=noise,
                    )
                    if res_ref < best_res:
                        best_res = res_ref
                        best_U, best_V, best_W = U_ref, V_ref, W_ref
                    if best_res < 1e-11:
                        break

            U, V, W, res = best_U, best_V, best_W, best_res

        self.state["attempt"] = attempt + 1
        self._save()

        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_als_residual"] = res
        return scheme

    def record(self, ok: bool):
        if ok and self.state["stage"] < len(LADDER) - 1:
            self.state["stage"] += 1
            self.state["attempt"] = 0
            self._save()


def propose() -> dict:
    return Searcher().propose()
