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



def _force_verifier(run_dir: Path, final_verifier: str) -> bool:
    """최종 노드의 verifier 를 주입 심판으로 **다시** 못박는다. 바뀌었으면 True.

    **재계획이 심판을 지운다.** planner.replan 은 make_plan 을 다시 불러 plan.json 을
    통째로 새로 쓰므로, 밖에서 꽂아둔 심판이 사라지고 LLM 이 쓴 채점표가 그 자리에
    들어앉는다. 실측(2026-09-03, tensorrank --budget mm333=26): 라운드 4 / 재계획 1 로
    "solved" 가 떴는데, 그 답을 우리 심판으로 다시 재보니 세 case 전부 "답 없음"이었다.
    **주입이 풀린 채로 LLM 이 제 답에 스스로 합격을 준 것이다.**

    그래서 주입을 한 번 하는 것으로 끝내면 안 된다. 계획이 새로 써질 때마다 다시 꽂는다."""
    path = run_dir / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for node in plan["nodes"]:
        if node["id"] == plan["final"] and node.get("verifier") != final_verifier:
            node["verifier"] = final_verifier
            changed = True
    if changed:
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


INJECTED = "injected_verifier.json"


def injected_verifier(run_dir: Path) -> str | None:
    """런에 적혀 있는 주입 심판 경로. 호출자가 안 넘겨도 여기서 찾는다.

    **주입 정보가 호출자 메모리에만 있으면 재개 경로에서 사라진다.** 실측
    (2026-09-03, tensorrank-130156): problems/tensor_rank/run.py 로 시작한 런을
    나중에 `solve.py --resume` 으로 이어 돌렸는데, 그 경로는 final_verifier 를 모르므로
    재주입을 하지 않았다. 재계획이 한 번 더 돌면서 LLM 이 쓴 채점표
    (components/search_decomposition_verify.py)가 최종 노드에 그대로 남았다.

    그래서 주입을 런 디렉토리에 파일로 남긴다. 어느 경로로 재개해도 심판이 따라온다."""
    path = Path(run_dir) / INJECTED
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("final_verifier") or None
    except (json.JSONDecodeError, OSError):
        return None


def remember_verifier(run_dir: Path, final_verifier: str) -> None:
    """주입 심판을 런에 적어둔다. 재개하는 쪽이 무엇이든 이것을 읽는다."""
    (Path(run_dir) / INJECTED).write_text(
        json.dumps({"final_verifier": final_verifier}, ensure_ascii=False),
        encoding="utf-8")


def failure_reasons(run_dir) -> list:
    """심판이 남긴 기각 사유를 시간순으로 모은다. 재계획 전 시도(attempts/attemptN)도 포함한다.

    **사유는 이미 기록되고 있었는데 아무도 읽지 않았다.** orchestrator 는 노드가 떨어질
    때마다 node.attempts 에 {"rejected": msg} 를 남긴다. 그런데 drive 는 node_status
    ("failed") 만 돌려줬고, run.py 는 그것만 찍었다. 그래서 화면에는 "failed" 세 글자만
    남고, 심판이 애써 만든 진단 -- 틀린 칸 수, 상쇄 질량, 격자 이탈, 예산 초과 -- 이
    전부 파일 안에서 사라졌다.

    실측(2026-09-03, tensorrank --budget mm333=26): 수리 2회 + 재계획 1회를 돌고
    incomplete 로 끝났는데, **무엇이 틀렸는지 화면에 한 글자도 없었다.** 피드백 루프의
    재료가 곧 이 사유이므로, 사람이 못 보면 다음 수를 정할 수 없다."""
    run_dir = Path(run_dir)
    out = []
    plans = sorted(run_dir.glob("attempts/attempt*/plan.json")) + [run_dir / "plan.json"]
    for path in plans:
        if not path.is_file():
            continue
        try:
            plan = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        where = path.parent.name if path.parent != run_dir else "현재"
        for node in plan.get("nodes", []):
            for att in node.get("attempts", []):
                msg = att.get("rejected") or att.get("error")
                if msg:
                    out.append({"plan": where, "node": node.get("id"),
                                "kind": "기각" if att.get("rejected") else "오류",
                                "message": str(msg)})
    return out


def drive(run_dir: str, max_repair_rounds: int = 300, max_node_repairs: int = 200,
          max_replans: int = 100, pool=None, node_timeout: float = None,
          final_verifier: str = None) -> dict:
    """plan.json 이 있는 런을 목표 달성까지 몰아붙인다: 실행 -> 검증 -> 실패면 수리/재계획 -> 재실행.

    반환 dict 의 status 는 "solved" 이거나 "incomplete" 다. incomplete 면 왜 멈췄는지
    reason 에 남긴다(수리 한도 소진 / 재계획 한도 소진 / 계획 무효). 루프 전체 기록은 log 에.
    LLM 풀은 실제로 수리가 필요할 때만 만든다 -- 한 번에 풀리는 런은 API 키 없이도 돈다."""
    run_dir = Path(run_dir).resolve()
    log: list = []
    replans = 0
    reason = "수리 라운드 한도 소진"
    # 호출자가 안 넘겼으면 런에 적힌 것을 쓴다. 재개 경로가 심판을 잃지 않게 하는 자리다.
    if final_verifier is None:
        final_verifier = injected_verifier(run_dir)
        if final_verifier:
            log.append({"verifier_from_run": final_verifier})
    elif final_verifier:
        remember_verifier(run_dir, final_verifier)

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

    def reinject(where: str) -> None:
        """계획이 새로 써진 직후마다 심판을 다시 꽂는다."""
        if final_verifier and (run_dir / "plan.json").is_file():
            if _force_verifier(run_dir, final_verifier):
                log.append({"reinjected_verifier": final_verifier, "after": where})

    reinject("start")
    for round_i in range(1, max_repair_rounds + 2):
        res = orchestrator.run_plan(str(run_dir), node_timeout=node_timeout)
        entry = {"round": round_i, "run_status": res.get("status"),
                 "node_status": res.get("node_status")}
        log.append(entry)

        if res.get("status") == "solved":
            return {"status": "solved", "run_dir": str(run_dir), "rounds": round_i,
                    "replans": replans, "final": res.get("final"),
                    "final_result": res.get("final_result"), "log": log,
                    "failures": failure_reasons(run_dir)}

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
                        reinject(f"replan#{replans}")
                    else:
                        reason = "수리안이 모두 반려됐고 재계획 한도도 소진"
                        break
            elif replans < max_replans:
                entry["action"] = "replan"
                entry["replan"] = ask(planner.replan, str(run_dir))
                replans += 1
                reinject(f"replan#{replans}")
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
        except Exception as e:   # 쿼터 소진·파싱 실패 등. 런은 남으므로 --resume 으로 재개 가능.
            entry["error"] = f"{type(e).__name__}: {e}"
            reason = (f"수리/재계획 LLM 호출이 실패했다 ({type(e).__name__}: {e}) -- "
                      f"런은 그대로 남아 있으니 --resume 으로 이어서 돌릴 수 있다")
            break

    return {"status": "incomplete", "run_dir": str(run_dir), "reason": reason,
            "rounds": len(log), "replans": replans, "log": log,
            "failures": failure_reasons(run_dir)}


def solve(problem: str, max_repair_rounds: int = 300, max_node_repairs: int = 200,
          max_replans: int = 100, pool=None, node_timeout: float = None,
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
    parser.add_argument("--max-repair-rounds", type=int, default=300,
                        help="실행-수리 라운드 상한 (기본 300)")
    parser.add_argument("--max-node-repairs", type=int, default=200,
                        help="노드 하나당 수리 시도 상한 (기본 200, 넘으면 재계획으로 승격)")
    parser.add_argument("--max-replans", type=int, default=100,
                        help="계획 전체 재수립 상한 (기본 100)")
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
