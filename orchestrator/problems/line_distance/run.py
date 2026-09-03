"""오케스트레이터에게 두 직선 최단거리 문제를 풀린다 -- 첫 실적을 재는 시험.

왜 이 문제인가. 오케스트레이터는 지금까지 검증된 결과가 **0건**이다. 압축에서 나온 것은
전부 사전지식이나 닫힌 형태에서 나왔지 탐색이 만든 것이 아니다. 그러니 어려운 문제를
주기 전에 **가장 단순한 최적화 문제 하나를 실제로 푸는지**부터 봐야 한다.

이 문제가 시험대로 좋은 이유:
  · 목적함수가 볼록 이차형식이라 국소최소 = 전역최소. 판정에 애매함이 없다
  · 채점에 LLM 이 한 방울도 안 들어간다 -- 내적 두 개면 최소점인지 확인된다
  · **검증이 푸는 것보다 압도적으로 싸다.** 심판이 답을 몰라도 답을 확인한다
  · 퇴화한 경우(평행/일치)가 섞여 있어 "일반해만 되는" 풀이를 거른다

역할 분담이 이 시험의 요점이다:
  사람/도구 : 문제를 세우고 심판을 만든다 (이 파일과 verify.py)
  오케스트레이터 : 푼다 (plan.json 과 노드 코드를 스스로 쓴다)
  심판       : 채택을 정한다 (verify.py, LLM 없음)

verify.py 에는 풀이법이 들어 있지 않다. repair_node 가 노드에 verifier 를 읽기 전용으로
보여주므로, 심판이 답을 담고 있으면 이 시험이 통째로 무의미해진다. 회귀 검사
(tests/test_line_distance_verifier.py)가 그것도 확인한다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "orchestrator"))

RUNS = REPO / "orchestrator" / "runs"

PROBLEM = '''3차원 공간의 두 직선 사이의 최단거리를 구하라.

직선은 매개변수로 주어진다:

    r1(t) = p1 + t * v1        (t 는 실수)
    r2(s) = p2 + s * v2        (s 는 실수)

각 case 마다 다음 최적화 문제를 풀어라:

    minimize   || r1(t) - r2(s) ||        (t, s 에 대하여)

즉 두 직선 위의 점 하나씩을 골라 그 거리를 가장 작게 만드는 (t, s) 와 그때의 거리를
구하는 것이다.

[입력] 아래 파일에 case 들이 들어 있다. 각 case 는 p1, v1, p2, v2 (각각 길이 3인 실수
리스트)를 갖는다.

    {cases_path}

파일 내용:
```json
{cases_json}
```

[출력] 최종 노드의 solve 는 다음 형태를 반환하라:

    {{"cases": [{{"id": "<case id>", "t": <실수>, "s": <실수>, "distance": <실수>}}, ...]}}

모든 case 를 포함해야 한다. id 는 입력의 id 를 그대로 쓴다.

[주의해야 할 입력] case 에는 다음이 섞여 있다. 일반적인 경우만 다루는 풀이는 떨어진다.
  · 꼬인 위치의 두 직선 (일반)
  · 만나는 두 직선 (거리 0)
  · **평행한 두 직선** -- 최소점이 무한히 많다
  · **완전히 같은 직선** -- 방향벡터가 서로 상수배이고 거리 0
  · 방향벡터 크기가 서로 크게 다른 경우
  · 거의 평행한 경우 (수치적으로 불안정)
평행/일치인 경우에는 최소점 중 **아무거나** 하나를 내면 된다. 유일해를 요구하지 않는다.

[채점] 채점은 네가 아니라 밖에 있는 심판이 한다. 심판은 LLM 을 쓰지 않는다. 각 case 에
대해 다음을 확인한다:
  · 보고한 distance 가 실제 || r1(t) - r2(s) || 와 같은가
  · 그 (t, s) 가 정말 최소점인가
  · 근처에 더 작은 값이 없는가 (무작위 섭동)
어떤 방법으로 구했는지는 보지 않는다. 최소점이기만 하면 된다.

[제약] numpy 와 표준 라이브러리만 쓴다. 외부 최적화 라이브러리(scipy 등)는 없다.
'''


def _plant_verifier(run_dir: Path) -> str:
    """런 디렉토리에 외부 심판을 깔고 상대 경로를 돌려준다.

    LLM 이 쓴 채점표를 버리고 밖에서 만든 심판을 넣는다. 압축에서 코덱 심판을 주입한 것과
    같은 수다 -- plan_schema 의 verifier 가 경로 문자열이라 가능하다."""
    vdir = run_dir / "verifiers"
    vdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "verify.py", vdir / "line_check.py")
    shutil.copy2(HERE / "cases.json", vdir / "cases.json")
    return "verifiers/line_check.py#check"


def _inject(run_dir: Path, verifier_rel: str) -> dict:
    """계획의 **최종 노드** verifier 를 주입 심판으로 갈아끼운다."""
    path = run_dir / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    before = None
    for node in plan["nodes"]:
        if node["id"] == plan["final"]:
            before = node.get("verifier")
            node["verifier"] = verifier_rel
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"final": plan["final"], "replaced": before, "with": verifier_rel,
            "n_nodes": len(plan["nodes"])}


def _print_failures(res: dict, limit: int = 6) -> None:
    """심판이 남긴 기각 사유를 그대로 보여준다. 잘라내면 되먹임의 재료가 사라진다.

    node_status 의 "failed" 세 글자만 찍던 시절에는, 심판이 만든 진단이 파일 안에서
    사라졌다 -- 무엇이 틀렸는지 모르면 다음 수를 정할 수 없다."""
    fails = res.get("failures") or []
    if not fails:
        return
    print(f"\n심판이 남긴 기각 사유 (마지막 {min(limit, len(fails))}건 / 전체 {len(fails)}건):")
    for f in fails[-limit:]:
        print(f"  [{f['plan']}] {f['node']} -- {f['kind']}")
        for line in str(f["message"]).split(" | "):
            print(f"      {line}")


def main() -> int:
    ap = argparse.ArgumentParser(description="오케스트레이터에게 직선거리 문제를 풀린다")
    ap.add_argument("--max-repair-rounds", type=int, default=3)
    ap.add_argument("--node-timeout", type=float, default=120.0)
    ap.add_argument("--run-dir", default=None, help="기존 런을 이어서 돌린다")
    a = ap.parse_args()

    import planner
    import solve as orch_solve

    cases_path = HERE / "cases.json"
    cases_json = cases_path.read_text(encoding="utf-8")

    rel = "verifiers/line_check.py#check"
    if a.run_dir:
        run_dir = Path(a.run_dir).resolve()
        print(f"기존 런을 이어서 돈다: {run_dir}")
    else:
        run_dir = RUNS / time.strftime("linedist-%Y%m%d-%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        problem = PROBLEM.format(cases_path=cases_path, cases_json=cases_json)
        (run_dir / "problem.txt").write_text(problem, encoding="utf-8")

        print(f"런 디렉토리: {run_dir}")
        print("계획을 세운다 ...")
        plan_res = planner.make_plan(problem, str(run_dir))
        if plan_res.get("status") != "planned":
            print(f"계획 실패: {plan_res}")
            return 1

        assert _plant_verifier(run_dir) == rel
        info = _inject(run_dir, rel)
        print(f"계획: 노드 {info['n_nodes']}개, 최종 노드 '{info['final']}'")
        print(f"심판 주입: {info['replaced']} -> {info['with']}")

    print("실행/검증/수리 루프를 돈다 ...")
    # 재계획이 plan.json 을 새로 쓰면서 주입 심판을 지운다. 경로를 넘겨 매번 다시 꽂는다.
    res = orch_solve.drive(str(run_dir), max_repair_rounds=a.max_repair_rounds,
                           node_timeout=a.node_timeout, final_verifier=rel)

    print(f"\n결과: {res.get('status')}  (라운드 {res.get('rounds')}, "
          f"재계획 {res.get('replans')})")
    if res.get("status") == "solved":
        final = res.get("final_result") or {}
        sys.path.insert(0, str(HERE))
        import verify as _v
        ok, why = _v.check(final, {})
        if not ok:
            print(f"\n!! solved 라는데 우리 심판으로 다시 재면 통과가 아니다: {why[:200]}")
            print("   재계획이 주입 심판을 지웠을 때 나오는 모습이다.")
            return 1
        print("\n오케스트레이터가 낸 답:")
        for row in final.get("cases", []):
            print(f"  {str(row.get('id')):11} t={float(row['t']):12.6f}  "
                  f"s={float(row['s']):12.6f}  거리={float(row['distance']):12.6f}")
        print("\n심판이 통과시켰다 -- 오케스트레이터의 첫 검증된 결과다.")
    else:
        print(f"이유: {res.get('reason')}")
        print(f"기록: {json.dumps(res.get('log', []), ensure_ascii=False)[:600]}")
        _print_failures(res)
    (run_dir / "result.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0 if res.get("status") == "solved" else 1


if __name__ == "__main__":
    sys.exit(main())
