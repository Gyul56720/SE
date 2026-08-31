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
POLISH_ENTER = 1e-2
POLISH_ITERS = 100000
LIFT_ENTER = 5e-2
LIFT_ROUNDS = 50
DAMP0 = 1e-3
ANNEAL_FRAC = 0.5


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


def _balance(U, V, W):
    nu = np.linalg.norm(U, axis=0)
    nv = np.linalg.norm(V, axis=0)
    nw = np.linalg.norm(W, axis=0)
    prod = nu * nv * nw
    live = prod > 1e-300
    s = np.ones_like(prod)
    s[live] = np.cbrt(prod[live])

    def rescale(A, norms):
        out = A.copy()
        out[:, live] = A[:, live] / (norms[live] + 1e-308) * s[live]
        return out

    return rescale(U, nu), rescale(V, nv), rescale(W, nw)


def _levenberg_marquardt_polish(T, U, V, W, normT, max_iters=5000, tol=TOL):
    m = U.shape[1]
    n = U.shape[0]
    
    x = np.concatenate([U.ravel(), V.ravel(), W.ravel()])
    best_x = x.copy()
    
    res = _residual(T, U, V, W, normT)
    best_res = res
    
    lam = 1e-3
    
    for it in range(max_iters):
        if res < tol:
            break
            
        U_c = x[0:n*m].reshape(n, m)
        V_c = x[n*m:2*n*m].reshape(n, m)
        W_c = x[2*n*m:].reshape(n, m)
        
        R = np.einsum("ir,jr,kr->ijk", U_c, V_c, W_c) - T
        curr_res = float(np.linalg.norm(R) / normT)
        
        if curr_res < best_res:
            best_res = curr_res
            best_x = x.copy()
            if curr_res < tol:
                break
                
        gU = np.einsum("ijk,jr,kr->ir", R, V_c, W_c)
        gV = np.einsum("ijk,ir,kr->jr", R, U_c, W_c)
        gW = np.einsum("ijk,ir,jr->kr", R, U_c, V_c)
        
        GU = (V_c.T @ V_c) * (W_c.T @ W_c)
        GV = (U_c.T @ U_c) * (W_c.T @ W_c)
        GW = (U_c.T @ U_c) * (V_c.T @ V_c)
        
        try:
            dU = np.linalg.solve(GU + lam * np.eye(m), gU.T).T
            dV = np.linalg.solve(GV + lam * np.eye(m), gV.T).T
            dW = np.linalg.solve(GW + lam * np.eye(m), gW.T).T
            dx = np.concatenate([dU.ravel(), dV.ravel(), dW.ravel()])
        except np.linalg.LinAlgError:
            lam *= 10.0
            continue
            
        x_new = x - dx
        U_new = x_new[0:n*m].reshape(n, m)
        V_new = x_new[n*m:2*n*m].reshape(n, m)
        W_new = x_new[2*n*m:].reshape(n, m)
        
        res_new = _residual(T, U_new, V_new, W_new, normT)
        
        if res_new < curr_res:
            x = x_new
            res = res_new
            lam = max(lam / 3.0, 1e-12)
        else:
            lam = min(lam * 10.0, 1e10)
            
    U_opt = best_x[0:n*m].reshape(n, m)
    V_opt = best_x[n*m:2*n*m].reshape(n, m)
    W_opt = best_x[2*n*m:].reshape(n, m)
    return U_opt, V_opt, W_opt, best_res


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

                if mode == 0:
                    U = X
                elif mode == 1:
                    V = X
                else:
                    W = X

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
            
            if res < tol:
                break
                
            if it > 0 and it % 60 == 0 and res > 1e-2 and use_perturbation and rng is not None:
                scale = noise_scale * (res + 1e-8)
                U += rng.normal(0, scale, U.shape)
                V += rng.normal(0, scale, V.shape)
                W += rng.normal(0, scale, W.shape)

    return best


def cp_als(T, m, iters=2000, seed=0, init_U=None, init_V=None, init_W=None,
           noise_scale=0.0, use_perturbation=False, polish=True):
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    
    U = rng.normal(0, 1, (n, m)) if init_U is None else np.array(init_U, dtype=np.float64)
    V = rng.normal(0, 1, (n, m)) if init_V is None else np.array(init_V, dtype=np.float64)
    W = rng.normal(0, 1, (n, m)) if init_W is None else np.array(init_W, dtype=np.float64)

    normT = np.linalg.norm(T)
    U, V, W, res = _als_sweep(T, U, V, W, iters, rng=rng, normT=normT,
                              noise_scale=noise_scale, use_perturbation=use_perturbation)

    if polish and TOL <= res < POLISH_ENTER:
        U, V, W, res = _als_sweep(T, U, V, W, POLISH_ITERS, damp0=0.0, normT=normT)
        if TOL <= res < 5e-3:
            U, V, W, res = _levenberg_marquardt_polish(T, U, V, W, normT)
    return U, V, W, res


def _lift(T, U, V, W, res, normT, iters):
    best = (U.copy(), V.copy(), W.copy(), res)

    for r in range(LIFT_ROUNDS):
        U0, V0, W0, res0 = best
        Ub, Vb, Wb = _balance(U0, V0, W0)
        thresh = 0.05 * (r + 1) / LIFT_ROUNDS

        frozen = []
        any_frozen = False
        for A in (Ub, Vb, Wb):
            d = np.abs(A[..., None] - DISCRETE_GRID[None, None, :])
            idx = np.argmin(d, axis=-1)
            nearest = DISCRETE_GRID[idx]
            mask = np.min(d, axis=-1) <= thresh
            frozen.append((mask, nearest))
            any_frozen = any_frozen or bool(mask.any())
        
        if not any_frozen:
            continue

        Uc, Vc, Wc = Ub.copy(), Vb.copy(), Wb.copy()
        for arr, (mask, val) in zip((Uc, Vc, Wc), frozen):
            arr[mask] = val[mask]

        Uc, Vc, Wc, resc = _als_sweep(T, Uc, Vc, Wc, iters, damp0=1e-14,
                                      frozen=frozen, normT=normT)
        if math.isfinite(resc) and resc < best[3]:
            best = (Uc, Vc, Wc, resc)
            if resc < TOL:
                break
    return best


def factors_to_scheme(U: np.ndarray, V: np.ndarray, W: np.ndarray, b: int, m: int) -> dict:
    A = [{(i, j): float(U[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    B = [{(i, j): float(V[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    C = [
        {(i, j): [(k, float(W[i * b + j, k])) for k in range(m)]}
        for i in range(b)
        for j in range(b)
    ]
    return {"b": b, "m": m, "A_coeffs": A, "B_coeffs": B, "C_coeffs": C}


class Searcher:
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
        params = load_params()
        budget = int(params.get("iters", 8000))
        noise = float(params.get("noise_scale", 0.12))
        perturb = bool(params.get("use_perturbation", True))

        T = matmul_tensor(b)
        normT = np.linalg.norm(T)

        per_restart = max(1500, budget // 5)
        restarts = max(1, budget // per_restart)

        base_seed = int(self.state["attempt"]) * 73856 + int(b * 1000 + m)
        best = None
        
        for r in range(restarts):
            U, V, W, res = cp_als(T, m, iters=per_restart, seed=base_seed + r * 101,
                                  noise_scale=noise, use_perturbation=perturb)
            
            if res < LIFT_ENTER:
                U, V, W, res = _lift(T, U, V, W, res, normT, per_restart)
            
            if best is None or res < best[3]:
                best = (U, V, W, res)
            
            if best[3] < TOL:
                break

        U, V, W, res = best
        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_als_residual"] = res
        self.state["attempt"] += 1
        self._save()
        return scheme

    def record(self, ok: bool):
        if ok and self.state["stage"] < len(LADDER) - 1:
            self.state["stage"] += 1
            self.state["attempt"] = 0
            self._save()


def propose() -> dict:
    return Searcher().propose()