"""
Jump Searcher v2: 이산 격자 기반 대수적 점프 및 메타히리스틱 탐색기 (IJP-DT)
"""

from __future__ import annotations
import numpy as np
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARAMS_PATH = HERE / "params.json"
STATE_PATH = HERE / "jump_state.json"

GRID_VALUES = [-1.0, -0.5, 0.0, 0.5, 1.0]

def load_params():
    try:
        with open(PARAMS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"iters": 2000}

def matmul_tensor(b: int) -> np.ndarray:
    n = b * b
    T = np.zeros((n, n, n))
    for i in range(b):
        for j in range(b):
            for l in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T

def jump_search(T: np.ndarray, m: int, iters: int = 2000, seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    
    # 초기 격자 상태 (정규화된 실수 최적화 결과에 격자 투영 대신 순수 격자 샘플링)
    U = rng.choice(GRID_VALUES, size=(n, m))
    V = rng.choice(GRID_VALUES, size=(n, m))
    W = rng.choice(GRID_VALUES, size=(n, m))
    
    best_U, best_V, best_W = U.copy(), V.copy(), W.copy()
    best_res = float("inf")
    
    for it in range(iters):
        # 무작위 격자 주변 탐색 (Random Mutation / Simulated Annealing style jump)
        factor_idx = rng.integers(0, 3)
        target_mat = [U, V, W][factor_idx]
        
        r_idx = rng.integers(0, target_mat.shape[0])
        c_idx = rng.integers(0, target_mat.shape[1])
        old_val = target_mat[r_idx, c_idx]
        new_val = rng.choice(GRID_VALUES)
        target_mat[r_idx, c_idx] = new_val
        
        R = np.einsum("ir,jr,kr->ijk", U, V, W)
        res = float(np.linalg.norm(T - R))
        
        if res < best_res:
            best_res = res
            best_U, best_V, best_W = U.copy(), V.copy(), W.copy()
        else:
            # 롤백
            target_mat[r_idx, c_idx] = old_val
            
        if best_res < 1e-6:
            break
            
    return best_U, best_V, best_W, best_res

class JumpSearcher:
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

    def current_target(self) -> tuple[int, int]:
        return (2, 7)  # 우선 b=2 m=7(스트라센) 검증부터 시작

    def propose(self) -> dict:
        b, m = self.current_target()
        params = load_params()
        T = matmul_tensor(b)
        U, V, W, res = jump_search(T, m, iters=params.get("iters", 2000), seed=self.state["attempt"])
        
        from searcher import factors_to_scheme
        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_jump_residual"] = res
        self.state["attempt"] += 1
        self._save()
        return scheme

if __name__ == "__main__":
    js = JumpSearcher()
    scheme = js.propose()
    print("Jump Search v2 proposed residual:", scheme.get("_jump_residual"))
