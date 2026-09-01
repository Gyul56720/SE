"""
end-to-end 진입점: 문제 문자열 하나로 플래너 -> 오케스트레이터 -> (실패 시) 재계획 루프를 돈다.

Discord(SE)에서 쓰기 쉽게 만든 얇은 래퍼다. 사람이 "이 문제 orchestrator로 풀어라" 하면
SE 가 아래를 실행하면 된다:

    python3 orchestrator/solve.py "<문제 설명>"

동작:
  1. runs/<타임스탬프>/ 런 디렉토리를 만든다.
  2. planner.make_plan 으로 문제를 DAG(plan.json + components/*.py)로 분해한다
     (모든 LLM 호출은 llm_pool 로 나가 Gemini 쿼터/모델 자동전환을 견딘다).
  3. drive(): orchestrator.run_plan 으로 DAG 를 실행/검증하고, 미완이면 실패 노드의 사유를
     플래너에 되먹여 수리한 뒤 다시 실행한다. 이 루프가 닫혀 있어야 목적지향 에이전트다.
  4. 결과 요약(JSON)을 출력한다. 산출물은 전부 런 디렉토리에 파일로 남아 git 으로 복원 가능.

루프의 단계 (아래로 갈수록 비싸다 -- 싼 것부터 쓴다):
  a. 재실행       : 노드 verifier 가 판정한다. 통과한 노드는 건너뛴다(오케스트레이터).
  b. 노드 수리    : 실패한 노드의 solve 만 실패 사유를 보고 다시 쓴다(planner.repair_node).
                   노드당 max_node_repairs 회까지. verifier 는 절대 다시 쓰지 않는다.
  c. 계획 재수립  : 수리로 안 되면 DAG 자체가 틀린 것이므로 통째로 다시 세운다
                   (planner.replan). max_replans 회까지. 이전 시도는 attempts/attemptN/ 에 보존.
  d. 포기         : 여기까지 와서도 미완이면 status="incomplete" 로 사실대로 반환한다.

플래너가 엉뚱한 계획을 내도 노드 verifier 가 통과 안 시키면 채택되지 않는다.
런이 도중에 죽어도 같은 런 디렉토리로 다시 실행하면 verified 노드는 건너뛰고 재개하며,
수리 횟수도 plan.json 의 attempts 에 남아 있어 이어서 센다(같은 수리를 무한 반복하지 않는다):

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
import llm_pool  # noqa: E402
from plan_schema import Plan  # noqa: E402

RUNS = HERE / "runs"


def drive(run_dir: str, max_repair_rounds: int = 3, max_node_repairs: int = 2,
          max_replans: int = 1, pool=None) -> dict:
    """plan.json 이 있는 런을 목표 달성까지 몰아붙인다: 실행 -> 검증 -> 실패면 수리/재계획 -> 재실행.

    반환 dict 의 status 는 "solved" 이거나 "incomplete" 다. incomplete 면 왜 멈췄는지
    reason 에 남긴다(수리 한도 소진 / 재계획 한도 소진 / 계획 무효). 루프 전체 기록은 log 에.
    LLM 풀은 실제로 수리가 필요할 때만 만든다 -- 한 번에 풀리는 런은 API 키 없이도 돈다."""
    run_dir = Path(run_dir).resolve()
    log: list = []
    replans = 0
    reason = "수리 라운드 한도 소진"

    def get_pool():
        nonlocal pool
        if pool is None:
            pool = llm_pool.build_pool()
        return pool

    for round_i in range(1, max_repair_rounds + 2):
        res = orchestrator.run_plan(str(run_dir))
        entry = {"round": round_i, "run_status": res.get("status"),
                 "node_status": res.get("node_status")}
        log.append(entry)

        if res.get("status") == "solved":
            return {"status": "solved", "run_dir": str(run_dir), "rounds": round_i,
                    "replans": replans, "final": res.get("final"),
                    "final_result": res.get("final_result"), "log": log}

        if round_i > max_repair_rounds:
            break  # 마지막 라운드는 수리 결과를 확인만 하고 끝낸다.

        # --- 무엇을 고칠 것인가 ---
        if res.get("status") == "invalid_plan":
            failed, plan = [], None      # 계획 자체가 무효 -> 바로 재계획으로.
        else:
            plan = Plan.load(run_dir / "plan.json")
            failed = [nid for nid, st in res.get("node_status", {}).items() if st == "failed"]

        repairable = [nid for nid in failed
                      if planner.repair_count(plan.node(nid)) < max_node_repairs]

        if repairable:
            entry["action"] = "repair"
            entry["repairs"] = [planner.repair_node(str(run_dir), nid, pool=get_pool())
                                for nid in repairable]
            # 수리안이 전부 형식 검사에서 반려되면 다음 라운드는 같은 코드를 또 돌릴 뿐이다.
            if all(r.get("status") == "repair_rejected" for r in entry["repairs"]):
                if replans < max_replans:
                    entry["action"] = "repair_rejected -> replan"
                    entry["replan"] = planner.replan(str(run_dir), pool=get_pool())
                    replans += 1
                else:
                    reason = "수리안이 모두 반려됐고 재계획 한도도 소진"
                    break
        elif replans < max_replans:
            entry["action"] = "replan"
            entry["replan"] = planner.replan(str(run_dir), pool=get_pool())
            replans += 1
            if entry["replan"].get("status") != "planned":
                reason = "재계획이 유효한 DAG 를 내지 못했다"
                break
        else:
            reason = ("노드 수리 한도 소진 후 재계획 한도까지 소진" if failed
                      else "진전 없음: 고칠 수 있는 실패 노드가 없다")
            break

    return {"status": "incomplete", "run_dir": str(run_dir), "reason": reason,
            "replans": replans, "log": log}


def solve(problem: str, max_repair_rounds: int = 3, max_node_repairs: int = 2,
          max_replans: int = 1, pool=None) -> dict:
    run_dir = RUNS / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    plan_res = planner.make_plan(problem, str(run_dir), pool=pool)
    if plan_res.get("status") != "planned":
        return {"stage": "planning", **plan_res}
    run_res = drive(str(run_dir), max_repair_rounds=max_repair_rounds,
                    max_node_repairs=max_node_repairs, max_replans=max_replans, pool=pool)
    return {"stage": "done", "run_dir": str(run_dir), "plan": plan_res, "run": run_res}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("problem", nargs="?", help="풀 문제 설명")
    parser.add_argument("--resume", metavar="RUN_DIR", help="기존 런 디렉토리를 이어서 실행")
    parser.add_argument("--max-repair-rounds", type=int, default=3,
                        help="실행-수리 라운드 상한 (기본 3)")
    parser.add_argument("--max-node-repairs", type=int, default=2,
                        help="노드 하나당 수리 시도 상한 (기본 2, 넘으면 재계획으로 승격)")
    parser.add_argument("--max-replans", type=int, default=1,
                        help="계획 전체 재수립 상한 (기본 1)")
    args = parser.parse_args()
    kw = dict(max_repair_rounds=args.max_repair_rounds,
              max_node_repairs=args.max_node_repairs, max_replans=args.max_replans)
    if args.resume:
        result = drive(args.resume, **kw)
    elif args.problem:
        result = solve(args.problem, **kw)
    else:
        parser.error("문제 문자열 또는 --resume RUN_DIR 중 하나가 필요하다")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
