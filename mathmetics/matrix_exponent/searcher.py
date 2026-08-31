"""
행렬곱 텐서의 정확 CP 분해를 찾는 개선된 탐색기.
"""

import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
PARAMS_PATH = HERE / "params.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]

DISCRETE_GRID = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])

TOL = 1e-13
POLISH_ENTER = 5e-2
LIFT_ENTER = 1e-1
LIFT_ROUNDS = 120
DAMP0 = 5e-3
ANNEAL_FRAC = 0.65


def load_params():
    defaults = {"iters": 8000, "noise_scale": 0.12, "use_perturbation": True}
    try:
        if PARAMS_PATH.exists():
            with open(PARAMS_PATH, "r") as f:
                defaults.update(json.load(f))
    except Exception:
        pass
    return defaults


def matmul_tensor(b: int) -> np.ndarray:
    n = b * b
    T = np.zeros((n, n, n), dtype=np.float64)
    for i in range(b):
        for l in range(b):
            for j in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T


def _residual(T, U, V, W, normT):
    R = np.einsum("ir,jr,kr->ijk", U, V, W)
    return float(np.linalg.norm(R - T) / normT)


def _als_sweep(T, U, V, W, iters, damp0=DAMP0, anneal_frac=ANNEAL_FRAC,
               frozen=None, tol=TOL, normT=None, rng=None, noise_scale=0.0,
               use_perturbation=False):
    if normT is None:
        normT = np.linalg.norm(T)
    
    anneal_end = max(1, int(iters * anneal_frac))
    res = _residual(T, U, V, W, normT)
    best = (U.copy(), V.copy(), W.copy(), res)

    U_prev, V_prev, W_prev = U.copy(), V.copy(), W.copy()
    alpha = 1.0
    
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for it in range(iters):
            if it < anneal_end:
                lam = damp0 * (1.0 - it / anneal_end) ** 2
            else:
                lam = 0.0

            U_old, V_old, W_old = U.copy(), V.copy(), W.copy()

            for mode in range(3):
                if mode == 0:
                    G = (V.T @ V) * (W.T @ W)
                    RHS = np.einsum("ijk,jr,kr->ir", T, V, W)
                elif mode == 1:
                    G = (U.T @ U) * (W.T @ W)
                    RHS = np.einsum("ijk,ir,kr->jr", T, U, W)
                else:
                    G = (U.T @ U) * (V.T @ V)
                    RHS = np.einsum("ijk,ir,jr->kr", T, U, V)

                A = G + lam * np.eye(G.shape[0])
                try:
                    X = np.linalg.solve(A, RHS.T).T
                except np.linalg.LinAlgError:
                    X = np.linalg.lstsq(A.T, RHS.T, rcond=None)[0].T

                if mode == 0: U = X
                elif mode == 1: V = X
                else: W = X

                if frozen is not None:
                    for arr, (mask, val) in zip((U, V, W), frozen):
                        if mask is not None and mask.any():
                            arr[mask] = val[mask]

            if it > 0:
                U_extrap = U + (alpha - 1.0) * (U - U_prev)
                V_extrap = V + (alpha - 1.0) * (V - V_prev)
                W_extrap = W + (alpha - 1.0) * (W - W_prev)
                
                res_new = _residual(T, U_extrap, V_extrap, W_extrap, normT)
                if res_new < res:
                    U, V, W, res = U_extrap, V_extrap, W_extrap, res_new
                    alpha = min(alpha * 1.25, 1.99)
                else:
                    res = _residual(T, U, V, W, normT)
                    alpha = 1.0
            else:
                res = _residual(T, U, V, W, normT)

            U_prev, V_prev, W_prev = U_old, V_old, W_old

            if res < best[3]:
                best = (U.copy(), V.copy(), W.copy(), res)
            
            if res < tol: break
                
            if it > 0 and it % 60 == 0 and res > 1e-3 and use_perturbation and rng is not None:
                scale = noise_scale * (res + 1e-8)
                U += rng.normal(0, scale, U.shape)
                V += rng.normal(0, scale, V.shape)
                W += rng.normal(0, scale, W.shape)

    return best


def cp_als(T, m, iters=2000, seed=0, init_U=None, init_V=None, init_W=None,
           noise_scale=0.0, use_perturbation=False, polish=True):
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    U = rng.normal(0, 1, (n, m)) if init_U is None else init_U
    V = rng.normal(0, 1, (n, m)) if init_V is None else init_V
    W = rng.normal(0, 1, (n, m)) if init_W is None else init_W
    normT = np.linalg.norm(T)
    return _als_sweep(T, U, V, W, iters, rng=rng, normT=normT, noise_scale=noise_scale, use_perturbation=use_perturbation)


def _lift(T, U, V, W, res, normT, iters):
    best = (U, V, W, res)
    for r in range(LIFT_ROUNDS):
        U0, V0, W0, res0 = best
        thresh = 0.05 * (r + 1) / LIFT_ROUNDS
        frozen = []
        for A in (U0, V0, W0):
            d = np.abs(A[..., None] - DISCRETE_GRID[None, None, :])
            mask = np.min(d, axis=-1) <= thresh
            frozen.append((mask, DISCRETE_GRID[np.argmin(d, axis=-1)]))
        
        Uc, Vc, Wc = [A.copy() for A in [U0, V0, W0]]
        for arr, (mask, val) in zip((Uc, Vc, Wc), frozen):
            arr[mask] = val[mask]

        Uc, Vc, Wc, resc = _als_sweep(T, Uc, Vc, Wc, iters // 2, damp0=1e-12, frozen=frozen, normT=normT)
        if resc < best[3]:
            best = (Uc, Vc, Wc, resc)
    return best


def factors_to_scheme(U: np.ndarray, V: np.ndarray, W: np.ndarray, b: int, m: int) -> dict:
    return {"b": b, "m": m, "A_coeffs": [{(i, j): float(U[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)], "B_coeffs": [{(i, j): float(V[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)], "C_coeffs": [{(i, j): [(k, float(W[i * b + j, k])) for k in range(m)]} for i in range(b) for j in range(b)]}


class Searcher:
    def __init__(self):
        if STATE_PATH.exists():
            self.state = json.loads(STATE_PATH.read_text())
        else: self.state = {"stage": 0, "attempt": 0}

    def _save(self): STATE_PATH.write_text(json.dumps(self.state, indent=2))

    def propose(self) -> dict:
        b, m = LADDER[min(self.state["stage"], len(LADDER) - 1)]
        T = matmul_tensor(b)
        best = None
        for r in range(10):
            U, V, W, res = cp_als(T, m, iters=3000, seed=self.state["attempt"] * 999 + r)
            if res < LIFT_ENTER:
                U, V, W, res = _lift(T, U, V, W, res, np.linalg.norm(T), 2000)
            if best is None or res < best[3]: best = (U, V, W, res)
            if res < 1e-10: break
        self.state["attempt"] += 1
        self._save()
        scheme = factors_to_scheme(best[0], best[1], best[2], b, m)
        scheme["_als_residual"] = best[3]
        return scheme

    def record(self, ok: bool):
        if ok and self.state["stage"] < len(LADDER) - 1:
            self.state["stage"] += 1
            self.state["attempt"] = 0
            self._save()

def propose() -> dict: return Searcher().propose()