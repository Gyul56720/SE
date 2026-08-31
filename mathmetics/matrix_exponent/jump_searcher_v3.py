"""
Jump Searcher v3 (Long Run): IJP-DT
이산 격자 상에서의 지속적 탐색 및 대수적 점프 프로젝트.
"""

import numpy as np
import time
import os

def matmul_tensor(b: int) -> np.ndarray:
    n = b * b
    T = np.zeros((n, n, n))
    for i in range(b):
        for j in range(b):
            for l in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T

GRID_VALUES = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])

def run_session(b=3, m=22, max_steps=1000000, jump_interval=5000):
    seed = int(time.time() * 1000) % 2**32
    rng = np.random.default_rng(seed)
    n = b * b
    T = matmul_tensor(b)
    
    U = rng.choice(GRID_VALUES, size=(n, m))
    V = rng.choice(GRID_VALUES, size=(n, m))
    W = rng.choice(GRID_VALUES, size=(n, m))
    
    best_res = np.linalg.norm(T - np.einsum("ir,jr,kr->ijk", U, V, W))
    
    print(f"[{time.ctime()}] Seed {seed} started. Initial Res: {best_res:.6f}")
    
    for i in range(max_steps):
        # Hill climb
        mat_idx = rng.integers(0, 3)
        target = [U, V, W][mat_idx]
        r, c = rng.integers(0, n), rng.integers(0, m)
        old_val = target[r, c]
        new_val = rng.choice(GRID_VALUES)
        if old_val == new_val: continue
        
        target[r, c] = new_val
        res = np.linalg.norm(T - np.einsum("ir,jr,kr->ijk", U, V, W))
        
        if res < best_res:
            best_res = res
            if res < 1e-9:
                print(f"!!! SOLUTION FOUND at Step {i} !!!")
                return True, best_res
        else:
            target[r, c] = old_val
            
        # Structural Jump
        if (i + 1) % jump_interval == 0:
            # Jump: Randomly replace 2 columns to escape local minima
            for _ in range(2):
                col = rng.integers(0, m)
                U[:, col] = rng.choice(GRID_VALUES, size=n)
                V[:, col] = rng.choice(GRID_VALUES, size=n)
                W[:, col] = rng.choice(GRID_VALUES, size=n)
            best_res = np.linalg.norm(T - np.einsum("ir,jr,kr->ijk", U, V, W))
            print(f"[{time.ctime()}] Step {i+1}: Jumped. Current Best Res: {best_res:.6f}")

    return False, best_res

if __name__ == "__main__":
    print("=== Intellectual Jump Paradigm (IJP) Project Active ===")
    while True:
        found, res = run_session(b=3, m=22, max_steps=2000000)
        if found:
            break
        print(f"[{time.ctime()}] Session ended. Global Best was {res:.6f}. Restarting...")
