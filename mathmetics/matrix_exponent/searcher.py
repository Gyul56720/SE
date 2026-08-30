from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from verifier import CertificationEngine, Certificate

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]

def matmul_tensor(b: int) -> np.ndarray:
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
    return (P[:, None, :] * Q[None, :, :]).reshape(-1, P.shape[1])

def cp_als(T, m, iters=2000, seed=0, init_U=None, init_V=None, init_W=None, noise_scale=0.0):
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    if init_U is not None:
        U, V, W = init_U + rng.normal(0, noise_scale, init_U.shape), \
                  init_V + rng.normal(0, noise_scale, init_V.shape), \
                  init_W + rng.normal(0, noise_scale, init_W.shape)
    else:
        U, V, W = rng.standard_normal((n, m)), rng.standard_normal((n, m)), rng.standard_normal((n, m))
    
    lambdas = np.ones(m)
    for it in range(iters):
        for M in [U, V, W]:
            # Simple ALS update
            pass # (Logic simplified for brevity)
    return U, V, W, lambdas, 0.0

class Searcher:
    def __init__(self):
        self.state = self._load()
        self.engine = CertificationEngine(self.current_target()[0])

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
        U, V, W, lambdas, res = cp_als(matmul_tensor(b), m, seed=self.state["attempt"])
        self.state["attempt"] += 1
        self._save()
        return {"U": U.tolist(), "V": V.tolist(), "W": W.tolist(), "lambdas": lambdas.tolist()}

    def record(self, certificate: Certificate):
        if certificate.status == "CERTIFIED":
            if self.state["stage"] < len(LADDER) - 1:
                self.state["stage"] += 1
                self.state["attempt"] = 0
                self._save()

def propose() -> dict:
    return Searcher().propose()
