"""
자가 수정(self-modification) 루프: skeleton.py 의 SCHEME 을 반복적으로 백업하고,
검증하고, 개선(더 작은 omega_eff)됐을 때만 채택하는 감시자(watchdog) 스크립트.

이 스크립트 자체는 "생각"하지 않는다 - SCHEME 을 실제로 고치는 건 SE 에이전트
(Claude Code 세션, 아래 prompt.txt 참고) 몫이다. 이 루프는:
  1. 현재 skeleton.py 를 스냅샷/백업한다.
  2. verify_scheme() 으로 정확성부터 확인한다 (안 맞으면 즉시 이전 버전으로 롤백).
  3. 맞으면 omega_eff 를 계산해서, 이전 최고 기록보다 작을 때만 best/ 에 보관한다.
  4. 진행 기록을 logs/history.jsonl 에 append 한다.

CLAUDE.md 규칙에 따라, discord 봇 세션에서 이 스크립트를 몇 분 이상 도는
백그라운드 작업으로 띄울 때는 반드시:

    mkdir -p /home/ubuntu/SE/logs
    setsid nohup python3 mathmetics/matrix_exponent/self_improve_loop.py \
        --iterations 50 > /home/ubuntu/SE/logs/matrix_exponent.log 2>&1 < /dev/null &
    disown
    echo "PID: $!"

로 실행하고, ps -p <PID> 로 살아있는지 확인한 뒤에만 사용자에게 보고할 것.
"""

import argparse
import importlib
import json
import math
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKELETON_PATH = HERE / "skeleton.py"
BEST_DIR = HERE / "best"
LOG_PATH = HERE / "logs" / "history.jsonl"


def _load_skeleton():
    if "skeleton" in sys.modules:
        del sys.modules["skeleton"]
    sys.path.insert(0, str(HERE))
    import skeleton  # type: ignore
    importlib.reload(skeleton)
    return skeleton


def _append_log(record: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _best_omega():
    if not (BEST_DIR / "meta.json").exists():
        return math.inf
    return json.loads((BEST_DIR / "meta.json").read_text())["omega_eff"]


def run_once(prev_good_snapshot: Path):
    ts = time.time()
    try:
        mod = _load_skeleton()
    except Exception as e:
        return {"ts": ts, "status": "IMPORT_ERROR", "error": str(e)}

    try:
        ok, msg = mod.verify_scheme(mod.SCHEME)
    except Exception as e:
        ok, msg = False, f"exception during verify: {e}"

    if not ok:
        # 롤백: 마지막으로 검증 통과했던 skeleton.py 로 되돌린다.
        shutil.copy(prev_good_snapshot, SKELETON_PATH)
        return {"ts": ts, "status": "REJECTED_ROLLBACK", "reason": msg}

    omega = mod.effective_omega(mod.SCHEME)
    record = {
        "ts": ts,
        "status": "VERIFIED",
        "b": mod.SCHEME["b"],
        "m": mod.SCHEME["m"],
        "omega_eff": omega,
    }

    best = _best_omega()
    if omega < best - 1e-9:
        BEST_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(SKELETON_PATH, BEST_DIR / "skeleton.py")
        (BEST_DIR / "meta.json").write_text(
            json.dumps({"omega_eff": omega, "b": mod.SCHEME["b"], "m": mod.SCHEME["m"], "ts": ts}, indent=2)
        )
        record["status"] = "NEW_BEST"

    # 이번 스냅샷을 다음 롤백 기준점으로 갱신.
    shutil.copy(SKELETON_PATH, prev_good_snapshot)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1,
                         help="몇 번 체크할지. SE 에이전트가 SCHEME 을 고칠 시간을 "
                              "벌기 위해 --sleep 과 함께 쓴다.")
    parser.add_argument("--sleep", type=float, default=0.0,
                         help="각 iteration 사이 대기 초(sec). 에이전트가 파일을 "
                              "고칠 시간을 줄 때 사용.")
    args = parser.parse_args()

    prev_good = HERE / "_last_good_skeleton.py"
    if not prev_good.exists():
        shutil.copy(SKELETON_PATH, prev_good)

    for i in range(args.iterations):
        record = run_once(prev_good)
        _append_log(record)
        print(json.dumps(record, ensure_ascii=False))
        if i + 1 < args.iterations and args.sleep > 0:
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
