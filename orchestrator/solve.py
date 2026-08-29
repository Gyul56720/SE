"""
end-to-end 진입점: 문제 문자열 하나로 플래너 -> 오케스트레이터를 한 번에 돌린다.

Discord(SE)에서 쓰기 쉽게 만든 얇은 래퍼다. 사람이 "이 문제 orchestrator로 풀어라" 하면
SE 가 아래를 실행하면 된다:

    python3 orchestrator/solve.py "<문제 설명>"

동작:
  1. runs/<타임스탬프>/ 런 디렉토리를 만든다.
  2. planner.make_plan 으로 문제를 DAG(plan.json + components/*.py)로 분해한다
     (모든 LLM 호출은 llm_pool 로 나가 Gemini 쿼터/모델 자동전환을 견딘다).
  3. orchestrator.run_plan 으로 DAG 를 실행/검증한다(노드별 신뢰 verifier).
  4. 결과 요약(JSON)을 출력한다. 산출물은 전부 런 디렉토리에 파일로 남아 git 으로 복원 가능.

플래너가 엉뚱한 계획을 내도 노드 verifier 가 통과 안 시키면 채택되지 않는다.
런이 도중에 죽어도 같은 런 디렉토리로 다시 실행하면 verified 노드는 건너뛰고 재개한다:

    python3 orchestrator/solve.py --resume runs/<디렉토리>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import planner  # noqa: E402
import orchestrator  # noqa: E402

RUNS = HERE / "runs"


def solve(problem: str) -> dict:
    run_dir = RUNS / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    plan_res = planner.make_plan(problem, str(run_dir))
    if plan_res.get("status") != "planned":
        return {"stage": "planning", **plan_res}
    run_res = orchestrator.run_plan(str(run_dir))
    return {"stage": "done", "run_dir": str(run_dir), "plan": plan_res, "run": run_res}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("problem", nargs="?", help="풀 문제 설명")
    parser.add_argument("--resume", metavar="RUN_DIR", help="기존 런 디렉토리를 이어서 실행")
    args = parser.parse_args()
    if args.resume:
        result = orchestrator.run_plan(args.resume)
    elif args.problem:
        result = solve(args.problem)
    else:
        parser.error("문제 문자열 또는 --resume RUN_DIR 중 하나가 필요하다")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
