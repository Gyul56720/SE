import json
import math
from pathlib import Path
import numpy as np
from mathmetics.matrix_exponent.verifier import verify_scheme

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
PARAMS_PATH = HERE / "params.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]

def load_params():
    try:
        with open(PARAMS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"iters": 2000, "noise_scale": 0.1}

def _kr(A, B):
    return np.einsum("ir,jr->ijr", A, B).reshape(-1, A.shape[1])

def _unfold(T, mode):
    return np.transpose(T, [mode] + [i for i in range(T.ndim) if i != mode]).reshape(T.shape[mode], -1)

def matmul_tensor(b: int) -> np.ndarray:
    n = b * b
    T = np.zeros((n, n, n), dtype=np.float64)
    for i in range(b):
        for l in range(b):
            for j in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T

def cp_als(T, m, iters=2000, seed=0, init_U=None, init_V=None, init_W=None, noise_scale=0.0):
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    U = init_U if init_U is not None else rng.normal(0, 1, (n, m))
    V = init_V if init_V is not None else rng.normal(0, 1, (n, m))
    W = init_W if init_W is not None else rng.normal(0, 1, (n, m))
    
    if noise_scale > 0:
        U += rng.normal(0, noise_scale, U.shape)
        V += rng.normal(0, noise_scale, V.shape)
        W += rng.normal(0, noise_scale, W.shape)

    normT = np.linalg.norm(T)
    tol = 1e-12

    for it in range(iters):
        Gram_VW = (V.T @ V) * (W.T @ W)
        U = _unfold(T, 0) @ _kr(V, W) @ np.linalg.pinv(Gram_VW)
        Gram_UW = (U.T @ U) * (W.T @ W)
        V = _unfold(T, 1) @ _kr(U, W) @ np.linalg.pinv(Gram_UW)
        Gram_UV = (U.T @ U) * (V.T @ V)
        W = _unfold(T, 2) @ _kr(U, V) @ np.linalg.pinv(Gram_UV)

        if it % 50 == 0 or it == iters - 1:
            R = np.einsum("ir,jr,kr->ijk", U, V, W)
            res = float(np.linalg.norm(R - T) / normT)
            if res < tol:
                break
    return U, V, W, res

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
        attempt = self.state["attempt"]
        params = load_params()
        
        T = matmul_tensor(b)
        U, V, W, res = cp_als(T, m, iters=params["iters"], noise_scale=params["noise_scale"], seed=attempt)
        
        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_als_residual"] = res
        self.state["attempt"] = attempt + 1
        self._save()
        return scheme

    def record(self, ok: bool):
        if ok and self.state["stage"] < len(LADDER) - 1:
            self.state["stage"] += 1
            self.state["attempt"] = 0
            self._save()

def propose() -> dict:
    return Searcher().propose()
