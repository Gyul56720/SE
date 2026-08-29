"""
자가 수정 루프: searcher.propose() 가 내놓은 후보를, '신뢰된' verifier 로 독립 검증하고,
더 낮은 omega_eff 일 때만 best 로 채택하는 감시자(watchdog).

핵심 분리 (이 실험이 신뢰 가능한 이유):
  - searcher.py 는 SE 가 자유롭게 바꾼다 (ALS든 신종 방법이든). 이 루프는 매 iteration
    마다 그걸 새로 reload 해서 propose() 를 부른다 -- 즉 '코드 자가 수정'을 실제로 반영한다.
  - 판정은 언제나 verifier.py(신뢰·보호)가 한다. searcher 가 무엇을 하든 심판은 못 바꾼다.
  - searcher.py 가 import 조차 안 되거나(문법 오류 등) propose() 가 틀린 스킴을 내면,
    마지막으로 성공했던 searcher.py 로 자동 롤백한다 -- 프레임워크가 죽지 않게.

이 루프 자신은 "생각"하지 않는다. 개선 방법을 찾는 건 searcher(=SE) 몫이다.

CLAUDE.md 규칙에 따라 백그라운드로 오래 돌릴 때:
    mkdir -p /home/ubuntu/SE/logs
    setsid nohup python3 mathmetics/matrix_exponent/self_improve_loop.py \
        --iterations 50 --sleep 5 > /home/ubuntu/SE/logs/matrix_exponent.log 2>&1 < /dev/null &
    disown
    echo "PID: $!"
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import math
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEARCHER_PATH = HERE / "searcher.py"
LAST_GOOD_SEARCHER = HERE / "_last_good_searcher.py"
BEST_DIR = HERE / "best"
LOG_PATH = HERE / "logs" / "history.jsonl"


def _load_module(name: str, path: Path):
    """이름 충돌 없이 파일을 매번 새로 로드한다 (자가 수정을 반영하기 위해)."""
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_verifier():
    # verifier 는 신뢰된 심판 -- 항상 디스크의 현재 버전을 그대로 쓴다.
    return _load_module("_me_verifier", HERE / "verifier.py")


def _append_log(record: dict):
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
    # 튜플 키를 쓰는 dict 이므로 repr 로 저장한다 (유효한 파이썬 리터럴).
    (BEST_DIR / "scheme.py").write_text(
        "# verifier 로 검증된 최고 기록 스킴. 자동 생성물.\nSCHEME = " + repr(scheme) + "\n",
        encoding="utf-8",
    )
    (BEST_DIR / "meta.json").write_text(
        json.dumps({"omega_eff": omega, "b": scheme["b"], "m": scheme["m"], "ts": ts}, indent=2)
    )


def run_once():
    ts = time.time()
    verifier = _load_verifier()

    # 1) searcher 를 새로 로드 (SE의 코드 자가 수정을 반영). 깨졌으면 롤백.
    try:
        searcher = _load_module("_me_searcher", SEARCHER_PATH)
    except Exception as e:
        if LAST_GOOD_SEARCHER.exists():
            shutil.copy(LAST_GOOD_SEARCHER, SEARCHER_PATH)
        return {"ts": ts, "status": "SEARCHER_IMPORT_ERROR_ROLLBACK", "error": str(e)}

    if not hasattr(searcher, "propose") or not callable(searcher.propose):
        if LAST_GOOD_SEARCHER.exists():
            shutil.copy(LAST_GOOD_SEARCHER, SEARCHER_PATH)
        return {"ts": ts, "status": "SEARCHER_NO_PROPOSE_ROLLBACK"}

    # 2) 후보를 받는다.
    try:
        scheme = searcher.propose()
    except Exception as e:
        if LAST_GOOD_SEARCHER.exists():
            shutil.copy(LAST_GOOD_SEARCHER, SEARCHER_PATH)
        return {"ts": ts, "status": "PROPOSE_ERROR_ROLLBACK", "error": str(e)}

    # 3) '신뢰된' 심판으로 검증.
    try:
        ok, msg = verifier.verify_scheme(scheme)
    except Exception as e:
        ok, msg = False, f"verifier exception: {e}"

    if not ok:
        if LAST_GOOD_SEARCHER.exists():
            shutil.copy(LAST_GOOD_SEARCHER, SEARCHER_PATH)
        return {"ts": ts, "status": "REJECTED_ROLLBACK", "reason": msg}

    # 4) 통과: 이 searcher 를 다음 롤백 기준점으로 저장하고, 개선이면 best 갱신.
    shutil.copy(SEARCHER_PATH, LAST_GOOD_SEARCHER)
    omega = verifier.effective_omega(scheme)
    record = {"ts": ts, "status": "VERIFIED", "b": scheme["b"], "m": scheme["m"], "omega_eff": omega}
    if omega < _best_omega() - 1e-9:
        _save_best(scheme, omega, ts)
        record["status"] = "NEW_BEST"
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="iteration 사이 대기(초). SE가 searcher.py 를 고칠 시간을 준다.")
    args = parser.parse_args()

    if not LAST_GOOD_SEARCHER.exists():
        shutil.copy(SEARCHER_PATH, LAST_GOOD_SEARCHER)

    for i in range(args.iterations):
        record = run_once()
        _append_log(record)
        print(json.dumps(record, ensure_ascii=False))
        if i + 1 < args.iterations and args.sleep > 0:
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
