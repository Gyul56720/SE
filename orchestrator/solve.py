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
                   노드마다 실행 시간 예산이 걸려(--node-timeout) 무한 루프도 유계 실패가 된다.
  b. 노드 수리    : 실패한 노드의 solve 만 실패 사유를 보고 다시 쓴다(planner.repair_node).
                   노드당 max_node_repairs 회까지. verifier 는 절대 다시 쓰지 않는다.
  c. 계획 재수립  : 수리로 안 되면 DAG 자체가 틀린 것이므로 통째로 다시 세운다
                   (planner.replan). max_replans 회까지. 이전 시도는 attempts/attemptN/ 에 보존.
  d. 포기         : 여기까지 와서도 미완이면 status="incomplete" 로 사실대로 반환한다.

한도 기본값은 라운드 30 / 노드당 수리 20 / 재계획 10 이다. 이 값들은 **끈기**를 정하지 시간을
정하지 않는다 -- 전체 벽시계 상한은 없고, 걸려 있는 시간 예산은 노드 하나짜리(ORCH_NODE_TIMEOUT,
solve 와 verify 에 각각)뿐이다. 최악의 경우 몇 시간을 돈다. 밖에서 `timeout` 으로 감싸거나
GEMINI_TIMEOUT/GEMINI_MAX_CANDIDATES 로 LLM 대기를 조이는 것이 실질적인 상한이다.

라운드마다 런 디렉토리의 rounds.jsonl 에 JSON 한 줄이 append 된다(start / round* / end).
반환값의 log 와 같은 내용이지만 **돌고 있는 중에도** 보이고 런이 죽어도 남는다:

    tail -f runs/<디렉토리>/rounds.jsonl

플래너가 엉뚱한 계획을 내도 노드 verifier 가 통과 안 시키면 채택되지 않는다.
런이 도중에 죽어도 같은 런 디렉토리로 다시 실행하면 verified 노드는 건너뛰고 재개하며,
수리 횟수도 plan.json 의 attempts 에 남아 있어 이어서 센다(같은 수리를 무한 반복하지 않는다):

    python3 orchestrator/solve.py --resume runs/<디렉토리>
"""
from __future__ import annotations

import argparse
import json
import shutil
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


class _NoPool(RuntimeError):
    """쓸 수 있는 LLM 후보가 하나도 없다(키 미설정). 장애가 아니라 설정 문제라 따로 구분한다."""


def _now() -> str:
    """사람이 읽는 시각. ts(epoch) 와 같이 남긴다 -- 로그를 눈으로 볼 때 epoch 는 못 읽는다."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def drive(run_dir: str, max_repair_rounds: int = 30, max_node_repairs: int = 20,
          max_replans: int = 10, pool=None, node_timeout: float = None) -> dict:
    """plan.json 이 있는 런을 목표 달성까지 몰아붙인다: 실행 -> 검증 -> 실패면 수리/재계획 -> 재실행.

    반환 dict 의 status 는 "solved" 이거나 "incomplete" 다. incomplete 면 왜 멈췄는지
    reason 에 남긴다(수리 한도 소진 / 재계획 한도 소진 / 계획 무효). 루프 전체 기록은 log 에.
    LLM 풀은 실제로 수리가 필요할 때만 만든다 -- 한 번에 풀리는 런은 API 키 없이도 돈다.

    **라운드마다 rounds.jsonl 에 한 줄씩 append 한다.** log 는 반환값에만 들어 있어서 런이
    도중에 죽으면 통째로 사라진다 -- 한도를 30/20/10 으로 올린 뒤에는 그 런이 몇 시간짜리라
    "어디까지 갔는지"를 끝나야만 알 수 있다는 것이 실질적인 문제가 된다. 파일에 흘려두면
    돌고 있는 중에도 tail 로 따라갈 수 있고, 죽어도 거기까지는 남는다."""
    run_dir = Path(run_dir).resolve()
    log: list = []
    replans = 0
    reason = "수리 라운드 한도 소진"
    solved: dict = None
    rounds_path = run_dir / "rounds.jsonl"

    def record(rec: dict) -> None:
        """JSON 한 줄을 append 한다. 기록이 실패해도 런은 계속된다 -- 기록은 관측이지 목적이
        아니다. 매번 열고 닫아서 프로세스가 죽어도 직전 줄까지는 디스크에 남는다."""
        try:
            with rounds_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        except Exception as e:                                # noqa: BLE001
            print(f"[solve] rounds.jsonl 기록 실패: {type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)

    def finish(result: dict) -> dict:
        record({"event": "end", "ts": time.time(), "at": _now(),
                "status": result.get("status"), "rounds": result.get("rounds"),
                "replans": result.get("replans"), "reason": result.get("reason")})
        return result

    # --resume 으로 이어 돌리면 라운드 번호가 1 부터 다시 시작한다. start 줄이 그 경계를
    # 표시한다 -- 없으면 한 파일 안의 "라운드 1" 두 개를 구분할 방법이 없다.
    record({"event": "start", "ts": time.time(), "at": _now(),
            "limits": {"max_repair_rounds": max_repair_rounds,
                       "max_node_repairs": max_node_repairs,
                       "max_replans": max_replans,
                       "node_timeout": node_timeout if node_timeout is not None
                       else orchestrator.NODE_TIMEOUT}})

    def get_pool():
        nonlocal pool
        if pool is None:
            pool = llm_pool.build_pool()
        return pool

    def ask(fn, *a, **kw):
        """수리/재계획 LLM 호출. 실패해도 traceback 으로 죽지 않는다 -- 런은 파일에 그대로
        남아 있으므로, 키를 넣거나 쿼터가 풀린 뒤 --resume 으로 이어서 돌리면 된다."""
        if not get_pool():
            raise _NoPool("LLM 후보 풀이 비었다 -- GEMINI_API_KEY(또는 _FALLBACK) 를 설정하라")
        return fn(*a, pool=pool, **kw)

    for round_i in range(1, max_repair_rounds + 2):
        # entry 는 아래에서 계속 채워지므로 기록은 라운드가 **끝날 때** 한 번 한다.
        # try/finally 로 감싸는 이유: solved 의 return 과 다섯 갈래 break 가 전부 이 지점을
        # 지나가게 하려는 것이다. 갈래마다 record 를 부르면 언젠가 하나를 빠뜨린다.
        t0 = time.time()
        entry = {"event": "round", "round": round_i, "ts": t0, "at": _now()}
        log.append(entry)
        try:
            res = orchestrator.run_plan(str(run_dir), node_timeout=node_timeout)
            entry["run_status"] = res.get("status")
            entry["node_status"] = res.get("node_status")

            if res.get("status") == "solved":
                entry["action"] = "solved"
                solved = {"status": "solved", "run_dir": str(run_dir), "rounds": round_i,
                          "replans": replans, "final": res.get("final"),
                          "final_result": res.get("final_result"), "log": log}
                break

            if round_i > max_repair_rounds:
                entry["action"] = "none (마지막 라운드는 확인만)"
                break  # 마지막 라운드는 수리 결과를 확인만 하고 끝낸다.

            # --- 무엇을 고칠 것인가 ---
            if res.get("status") == "invalid_plan":
                failed, plan = [], None      # 계획 자체가 무효 -> 바로 재계획으로.
            else:
                plan = Plan.load(run_dir / "plan.json")
                failed = [nid for nid, st in res.get("node_status", {}).items()
                          if st == "failed"]

            repairable = [nid for nid in failed
                          if planner.repair_count(plan.node(nid)) < max_node_repairs]
            entry["failed"] = failed
            entry["repairable"] = repairable
            entry["replans_so_far"] = replans

            try:
                if repairable:
                    entry["action"] = "repair"
                    entry["repairs"] = [ask(planner.repair_node, str(run_dir), nid)
                                        for nid in repairable]
                    # 수리안이 전부 반려되면 다음 라운드는 같은 코드를 또 돌릴 뿐이다.
                    if all(r.get("status") == "repair_rejected" for r in entry["repairs"]):
                        if replans < max_replans:
                            entry["action"] = "repair_rejected -> replan"
                            entry["replan"] = ask(planner.replan, str(run_dir))
                            replans += 1
                        else:
                            reason = "수리안이 모두 반려됐고 재계획 한도도 소진"
                            break
                elif replans < max_replans:
                    entry["action"] = "replan"
                    entry["replan"] = ask(planner.replan, str(run_dir))
                    replans += 1
                    if entry["replan"].get("status") != "planned":
                        reason = "재계획이 유효한 DAG 를 내지 못했다"
                        break
                else:
                    reason = ("노드 수리 한도 소진 후 재계획 한도까지 소진" if failed
                              else "진전 없음: 고칠 수 있는 실패 노드가 없다")
                    break
            except _NoPool as e:
                entry["error"] = str(e)
                reason = str(e)
                break
            except Exception as e:  # 쿼터 소진·파싱 실패 등. 런은 남으므로 --resume 으로 재개.
                entry["error"] = f"{type(e).__name__}: {e}"
                reason = (f"수리/재계획 LLM 호출이 실패했다 ({type(e).__name__}: {e}) -- "
                          f"런은 그대로 남아 있으니 --resume 으로 이어서 돌릴 수 있다")
                break
        finally:
            entry["seconds"] = round(time.time() - t0, 3)
            entry["replans_after"] = replans
            record(entry)

    if solved is not None:
        return finish(solved)
    return finish({"status": "incomplete", "run_dir": str(run_dir), "reason": reason,
                   "rounds": len(log), "replans": replans, "log": log})


def solve(problem: str, max_repair_rounds: int = 30, max_node_repairs: int = 20,
          max_replans: int = 10, pool=None, node_timeout: float = None,
          run_dir: str = None) -> dict:
    # run_dir 를 받는 이유: 호출자(Discord 도구 등)가 런을 백그라운드로 띄우고 **곧바로**
    # 어디를 봐야 하는지 알아야 한다. 타임스탬프를 여기서만 정하면 호출자는 "가장 최근
    # 디렉토리"를 추측할 수밖에 없고, 동시에 두 런이 뜨면 그 추측이 틀린다.
    run_dir = Path(run_dir).resolve() if run_dir else RUNS / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        plan_res = planner.make_plan(problem, str(run_dir), pool=pool)
    except Exception as e:
        # 최초 계획부터 실패(키 미설정·쿼터 소진·JSON 파싱 실패 등). 아무것도 안 쓰인 빈 런
        # 디렉토리는 치운다 -- 키 하나 빠졌을 때 runs/ 가 빈 디렉토리로 뒤덮이지 않게.
        # 파일이 조금이라도 쓰였으면 남긴다(무엇이 쓰였는지가 진단 근거다).
        if not (run_dir / "plan.json").exists() and not list(run_dir.rglob("*.*")):
            shutil.rmtree(run_dir, ignore_errors=True)
        return {"stage": "planning", "status": "planning_failed", "run_dir": str(run_dir),
                "error": f"{type(e).__name__}: {e}"}
    if plan_res.get("status") != "planned":
        return {"stage": "planning", **plan_res}
    run_res = drive(str(run_dir), max_repair_rounds=max_repair_rounds,
                    max_node_repairs=max_node_repairs, max_replans=max_replans, pool=pool,
                    node_timeout=node_timeout)
    return {"stage": "done", "run_dir": str(run_dir), "plan": plan_res, "run": run_res}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("problem", nargs="?", help="풀 문제 설명")
    parser.add_argument("--resume", metavar="RUN_DIR", help="기존 런 디렉토리를 이어서 실행")
    parser.add_argument("--run-dir", metavar="RUN_DIR", default=None,
                        help="새 런을 여기에 만든다(기본: runs/<타임스탬프>). 백그라운드로 "
                             "띄우는 호출자가 런 위치를 미리 알아야 할 때 쓴다")
    parser.add_argument("--max-repair-rounds", type=int, default=30,
                        help="실행-수리 라운드 상한 (기본 30, 실제 실행은 +1 회)")
    parser.add_argument("--max-node-repairs", type=int, default=20,
                        help="노드 하나당 수리 시도 상한 (기본 20, 넘으면 재계획으로 승격)")
    parser.add_argument("--max-replans", type=int, default=10,
                        help="계획 전체 재수립 상한 (기본 10)")
    parser.add_argument("--node-timeout", type=float, default=None,
                        help=f"노드 하나당 실행 시간 예산(초). 0 이하면 무제한 "
                             f"(기본 {orchestrator.NODE_TIMEOUT:g})")
    args = parser.parse_args()
    kw = dict(max_repair_rounds=args.max_repair_rounds,
              max_node_repairs=args.max_node_repairs, max_replans=args.max_replans,
              node_timeout=args.node_timeout)
    if args.resume:
        result = drive(args.resume, **kw)
    elif args.problem:
        result = solve(args.problem, run_dir=args.run_dir, **kw)
    else:
        parser.error("문제 문자열 또는 --resume RUN_DIR 중 하나가 필요하다")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
