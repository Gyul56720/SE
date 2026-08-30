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
    """최근 5회 연속 실패 여부 확인"""
    if not LOG_PATH.exists(): return False
    failures = []
    with LOG_PATH.open("r") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("status") == "REJECTED":
                failures.append(True)
            else:
                failures = []
    return len(failures) >= 5

def run_once():
    ts = time.time()
    verifier = _load("_me_verifier", HERE / "verifier.py")
    searcher_mod = _load("_me_searcher", HERE / "searcher.py")
    searcher = searcher_mod.Searcher()

    b, m = searcher.current_target()
    scheme = searcher.propose()
    resid = scheme.get("_als_residual")
    try:
        ok, msg = verifier.verify_scheme(scheme)
    except Exception as e:
        ok, msg = False, f"verifier exception: {e}"

    if check_stagnation():
        print("Stagnation detected! Automatically tuning parameters...")
        update_params(iters=3000, noise_scale=0.05)
        print("Parameters updated.")

    record = {"ts": ts, "b": b, "m": m, "als_residual": resid, "status": "VERIFIED" if ok else "REJECTED"}
    if not ok: record["reason"] = msg
    
    searcher.record(ok)
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
