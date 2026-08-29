"""
자가 수정 루프: searcher(ALS 탐색기)가 낸 후보를 '신뢰된' verifier 로 검증하고,
정직한 결과를 logs/history.jsonl 에 누적한다. 성공하면 searcher 를 다음 사다리 단으로 올린다.

- 판정은 언제나 verifier.py(신뢰·보호)가 한다. searcher 는 판정에 개입하지 못한다.
- searcher._als_residual 은 참고용으로 로그에만 남긴다(verifier 는 무시).
- 개선(더 낮은 omega)이면 best/ 에 스킴을 저장한다.

CLAUDE.md 규칙에 따라 백그라운드로 오래 돌릴 때는 setsid+nohup 패턴을 쓸 것.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

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


def _best_omega():
    meta = BEST_DIR / "meta.json"
    if not meta.exists():
        return math.inf
    try:
        return json.loads(meta.read_text())["omega_eff"]
    except Exception:
        return math.inf


def _save_best(scheme, omega, ts):
    BEST_DIR.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in scheme.items() if not k.startswith("_")}
    (BEST_DIR / "scheme.py").write_text(
        "# verifier 로 검증된 최고 기록 스킴. 자동 생성물.\nSCHEME = " + repr(clean) + "\n",
        encoding="utf-8")
    (BEST_DIR / "meta.json").write_text(
        json.dumps({"omega_eff": omega, "b": scheme["b"], "m": scheme["m"], "ts": ts}, indent=2))


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

    record = {"ts": ts, "b": b, "m": m, "als_residual": resid}
    if ok:
        omega = verifier.effective_omega(scheme)
        record["omega_eff"] = omega
        record["status"] = "VERIFIED"
        if omega < _best_omega() - 1e-9:
            _save_best(scheme, omega, ts)
            record["status"] = "NEW_BEST"
        searcher.record(True)  # 다음(더 어려운) 단으로.
    else:
        record["status"] = "REJECTED"
        record["reason"] = msg
        searcher.record(False)

    _append_log(record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--sleep", type=float, default=0.0)
    args = parser.parse_args()
    for i in range(args.iterations):
        rec = run_once()
        print(json.dumps(rec, ensure_ascii=False))
        if i + 1 < args.iterations and args.sleep > 0:
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
