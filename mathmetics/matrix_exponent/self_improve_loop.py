import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from .optimizer import update_params

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "logs" / "history.jsonl"
BEST_DIR = HERE / "best"

def _load(name, path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _append_log(record):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def check_stagnation():
    if not LOG_PATH.exists(): return False
    failures = []
    with LOG_PATH.open("r") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("status") == "REJECTED": failures.append(True)
            else: failures = []
    return len(failures) >= 5

def run_once():
    ts = time.time()
    verifier = _load("_me_verifier", HERE / "verifier.py")
    searcher_mod = _load("_me_searcher", HERE / "searcher.py")
    searcher = searcher_mod.Searcher()

    b, m = searcher.current_target()
    scheme = searcher.propose()
    resid = scheme.get("_als_residual")
    
    # 1. Tier 2: 근사 검증 (성공 시 루프 전진, 그러나 최종 성공은 아님)
    ok_approx, msg_approx = verifier.verify_approx(scheme, epsilon=1e-3)
    # 2. Tier 1: 정확 검증 (최종 성공)
    ok_exact, msg_exact = verifier.verify_scheme(scheme)

    status = "REJECTED"
    if ok_exact:
        status = "VERIFIED_EXACT"
    elif ok_approx:
        status = "VERIFIED_APPROX"
        print(f"Approximation achieved! Refining precision for next iteration...")
        update_params(iters=4000, noise_scale=0.01) # 더 정밀하게 탐색
    elif check_stagnation():
        print("Stagnation detected! Increasing search budget...")
        update_params(iters=5000, noise_scale=0.05)

    record = {"ts": ts, "b": b, "m": m, "als_residual": resid, "status": status, "reason": msg_exact if not ok_exact else "ok"}
    searcher.record(ok_exact) # 정확한 해일 때만 타겟 랭크 전진
    _append_log(record)
    return record

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()
    for _ in range(args.iterations):
        print(json.dumps(run_once()))

if __name__ == "__main__":
    main()
