import json
import math
from pathlib import Path
import numpy as np

# verifier 를 임포트하지 않는다. 쓰지도 않으면서 'mathmetics...' 절대 경로로 끌어오고
# 있었는데, systemd 처럼 이 트리를 패키지로 인식하지 않는 실행 경로에서는
# ModuleNotFoundError 로 죽었다. 판정은 self_improve_loop 가 verifier 를 직접 불러
# 수행하므로 searcher 쪽 의존은 애초에 불필요하다 (searcher 가 판정에 개입하지 않는다는
# 설계와도 맞는다).

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
PARAMS_PATH = HERE / "params.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]

def load_params():
    try:
        with open(PARAMS_PATH, 'r') as f: return json.load(f)
    except: return {"iters": 2000, "noise_scale": 0.1, "use_perturbation": False}

def matmul_tensor(b: int) -> np.ndarray:
    n = b * b
    T = np.zeros((n, n, n), dtype=np.float64)
    for i in range(b):
        for l in range(b):
            for j in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T

def cp_als(T, m, iters=2000, seed=0, init_U=None, init_V=None, init_W=None, noise_scale=0.0, use_perturbation=False):
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
        if use_perturbation and it % 10 == 0:
            U += rng.normal(0, noise_scale * 0.1, U.shape)
        
        # Simple ALS steps
        Gram_VW = (V.T @ V) * (W.T @ W)
        U = np.linalg.lstsq(Gram_VW.T, (np.einsum("ijk,jr,kr->ir", T, V, W)).T, rcond=None)[0].T
        Gram_UW = (U.T @ U) * (W.T @ W)
        V = np.linalg.lstsq(Gram_UW.T, (np.einsum("ijk,ir,kr->jr", T, U, W)).T, rcond=None)[0].T
        Gram_UV = (U.T @ U) * (V.T @ V)
        W = np.linalg.lstsq(Gram_UV.T, (np.einsum("ijk,ir,jr->kr", T, U, V)).T, rcond=None)[0].T

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
            try: return json.loads(STATE_PATH.read_text())
            except: pass
        return {"stage": 0, "attempt": 0}

    def _save(self):
        STATE_PATH.write_text(json.dumps(self.state, indent=2))

    def current_target(self):
        return LADDER[min(self.state["stage"], len(LADDER) - 1)]

    def propose(self) -> dict:
        b, m = self.current_target()
        params = load_params()
        T = matmul_tensor(b)
        U, V, W, res = cp_als(T, m, iters=params["iters"], noise_scale=params["noise_scale"], 
                              use_perturbation=params.get("use_perturbation", False), seed=self.state["attempt"])
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
