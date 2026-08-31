"""
[새로운 지적 패러다임] 이산 대수 트리 탐색 및 점프(Jump) 프로젝트 실행기
"""
from __future__ import annotations
import numpy as np
import json
import time
from pathlib import Path
from jump_searcher import jump_search, matmul_tensor

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "jump_project_results.json"

TARGETS = [(2, 7), (3, 23), (3, 22)]

def run_project(seeds_per_target=5, iters=5000):
    print("=== [새로운 지적 패러다임 IJP] 프로젝트 실행 시작 ===")
    results = []
    
    for b, m in TARGETS:
        print(f"\n>> Target: b={b}, m={m} 탐색 중...")
        T = matmul_tensor(b)
        best_target_res = float("inf")
        start_t = time.time()
        
        for seed in range(seeds_per_target):
            _, _, _, res = jump_search(T, m, iters=iters, seed=seed)
            if res < best_target_res:
                best_target_res = res
            print(f"   [Seed {seed}] 잔차: {res:.6f} (현재 타겟 최선: {best_target_res:.6f})")
            
        elapsed = time.time() - start_t
        results.append({
            "b": b,
            "m": m,
            "best_residual": best_target_res,
            "elapsed_sec": round(elapsed, 2)
        })
        
    LOG_PATH.write_text(json.dumps(results, indent=2))
    print("\n=== 프로젝트 실행 완료. 결과 저장: jump_project_results.json ===")
    return results

if __name__ == "__main__":
    run_project()
