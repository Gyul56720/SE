"""
플래너 되먹임 루프의 red-green 증명 -- "검증 실패가 계획으로 돌아가는가"를 실측 런으로 증명한다.

RED 의 근거는 합성이 아니라 저장소에 커밋돼 있는 실제 실패 런이다:
  orchestrator/runs/20260829-224043 -- factor / sub_equations 는 verified 인데 최종 노드
  crt_combine 이 `solve: 7`(KeyError) 로 죽어 있다. 결과가 JSON 으로 왕복하며 dict 키 7 이
  "7" 이 된 것뿐이라, solutions_mod[str(p1)] 한 곳이면 끝나는 버그다. 그런데 예전 구조에는
  실패 사유를 플래너로 되돌리는 경로가 없어서, 재개해도 같은 코드를 그대로 다시 돌렸고
  attempts 에 똑같은 `solve: 7` 이 두 번 쌓인 채 런이 영구히 미완으로 남았다.

이 파일이 매번 다시 증명하는 것:
  1. RED   -- 그 런을 그대로 다시 돌리면(수리 없이) 여전히 incomplete 이고 같은 예외가 난다.
  2. GREEN -- drive() 는 실패 사유와 선행 노드의 실제 값을 프롬프트에 담아 수리를 요청하고,
              고쳐진 코드로 재실행해 verifier 를 통과시킨다(solved).
  3. 승격  -- 노드 수리가 한도까지 실패하면 계획 전체 재수립으로 올라가고, 이전 plan/결과는
              attempts/attemptN/ 으로 보존된다(덮어쓰지 않는다).
  4. 안전  -- 문법이 깨졌거나 def solve 가 없는 수리안은 채택되지 않는다(파일 불변).
              verifier 파일은 어떤 경로로도 다시 쓰이지 않는다.

LLM 은 호출하지 않는다. llm_pool.call 을 가짜로 갈아끼워, "무엇을 프롬프트에 넣었는가"와
"응답을 어떻게 채택/반려하는가"만 검증한다(네트워크·쿼터 없이 매번 같은 결과).

실행: python3 tests/test_planner_repair.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ORCH = REPO / "orchestrator"
sys.path.insert(0, str(ORCH))

import llm_pool  # noqa: E402
import planner  # noqa: E402
import solve as solve_mod  # noqa: E402
from plan_schema import Plan  # noqa: E402

FIXTURE = ORCH / "runs" / "20260829-224043"   # 실측 실패 런 (커밋돼 있다)
FAILED_NODE = "crt_combine"

# 수리안: JSON 왕복으로 문자열이 된 키를 str(p1) 로 꺼낸다.
FIXED_SOLVE = '''def solve(inputs):
    N = inputs["factor"]["N"]
    p1, p2 = inputs["factor"]["factors"]
    sm = inputs["sub_equations"]["solutions_mod"]
    sols1, sols2 = sm[str(p1)], sm[str(p2)]
    inv = pow(p1, -1, p2)
    out = {(a1 + p1 * ((a2 - a1) * inv % p2)) % N for a1 in sols1 for a2 in sols2}
    return {"solutions": sorted(out)}
'''

BRUTE_SOLVE = ('def solve(inputs):\n'
               '    return {"solutions": sorted(x for x in range(91) if (x * x - 16) % 91 == 0)}\n')
BRUTE_CHECK = ('def check(output, inputs):\n'
               '    s = output["solutions"]\n'
               '    if len(s) != 4:\n'
               '        return False, f"해가 4개가 아니다: {len(s)}"\n'
               '    return all((x * x - 16) % 91 == 0 for x in s), ""\n')


class FakeLLM:
    """llm_pool.call 대체품. 프롬프트를 모으고, 정해둔 응답을 순서대로 돌려준다."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts: list[str] = []

    def __call__(self, pool, prompt, pool_id="planner"):
        self.prompts.append(prompt)
        reply = self.replies.pop(0) if self.replies else ""
        return (reply(prompt) if callable(reply) else reply), "fake:model"


def _with_fake(fake, fn):
    real = llm_pool.call
    llm_pool.call = fake
    try:
        return fn()
    finally:
        llm_pool.call = real


def _fixture_copy(tmp: str) -> Path:
    dest = Path(tmp) / "run"
    shutil.copytree(FIXTURE, dest)
    return dest


def _node(run_dir: Path, nid: str = FAILED_NODE):
    return Plan.load(run_dir / "plan.json").node(nid)


def _check(failures: list, cond: bool, label: str, detail: str = ""):
    print(f"    {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(f"{label}{': ' + detail if detail else ''}")


def test_red_without_repair(failures: list):
    """RED: 되먹임 없이 그냥 재실행하면 실측 런은 여전히 같은 예외로 미완이다."""
    print("[RED] 수리 없이 재실행 (max_repair_rounds=0)")
    with tempfile.TemporaryDirectory() as tmp:
        run = _fixture_copy(tmp)
        fake = FakeLLM([])   # 호출되면 안 된다
        res = _with_fake(fake, lambda: solve_mod.drive(str(run), max_repair_rounds=0,
                                                       max_replans=0, pool=["fake"]))
        node = _node(run)
        last = node.attempts[-1]
        _check(failures, res["status"] == "incomplete", "미완으로 끝난다", json.dumps(res.get("status")))
        _check(failures, node.status == "failed", "최종 노드가 failed 로 남는다", node.status)
        _check(failures, "solve: 7" in str(last), "같은 KeyError 가 그대로 재현된다", str(last))
        _check(failures, not fake.prompts, "수리 없이는 LLM 을 부르지 않는다")


def test_green_repair_loop(failures: list):
    """GREEN: 실패 사유를 되먹여 수리하면 같은 런이 목표를 달성한다."""
    print("[GREEN] 되먹임 수리 루프")
    with tempfile.TemporaryDirectory() as tmp:
        run = _fixture_copy(tmp)
        fake = FakeLLM(["```python\n" + FIXED_SOLVE + "```"])   # 코드펜스도 벗겨져야 한다
        res = _with_fake(fake, lambda: solve_mod.drive(str(run), max_repair_rounds=3,
                                                       pool=["fake"]))
        sols = (res.get("final_result") or {}).get("solutions", [])
        _check(failures, res["status"] == "solved", "목표 달성(solved)", res.get("reason", ""))
        _check(failures, res.get("rounds") == 2, "2라운드에 끝난다(실행->수리->실행)",
               str(res.get("rounds")))
        _check(failures, sorted(sols) == sorted(x for x in range(91) if (x * x - 16) % 91 == 0),
               "최종 결과가 x^2=16 (mod 91) 의 해 4개다", str(sols))
        _check(failures, _node(run).status == "verified", "노드가 verified 로 확정된다")

        # 되먹임의 내용물 -- 이게 없으면 수리는 그냥 재생성이다.
        p = fake.prompts[0] if fake.prompts else ""
        _check(failures, len(fake.prompts) == 1, "수리 호출은 한 번", str(len(fake.prompts)))
        _check(failures, "solve: 7" in p, "프롬프트에 실패 사유가 들어간다")
        _check(failures, '"solutions_mod"' in p and '"7"' in p,
               "선행 노드가 실제로 넘긴 값(문자열 키)이 들어간다")
        _check(failures, "def check(output, inputs)" in p, "채점 기준(verifier)이 들어간다")
        _check(failures, "고칠 수 없다" in p, "verifier 는 읽기 전용이라고 못박는다")

        # verifier 는 어떤 경로로도 다시 쓰이지 않는다.
        vpath = _node(run).verifier
        _check(failures, (run / vpath).read_text() == (FIXTURE / vpath).read_text(),
               "verifier 파일은 그대로다")


def test_escalation_to_replan(failures: list):
    """승격: 노드 수리가 한도까지 실패하면 계획 전체를 다시 세우고, 이전 시도는 보존된다."""
    print("[승격] 수리 한도 소진 -> 재계획")
    broken = (FIXTURE / "components" / f"{FAILED_NODE}.py").read_text()  # 고쳐지지 않은 원본
    replan_json = json.dumps({
        "nodes": [{"id": "brute", "goal": "전수 탐색으로 직접 푼다", "deps": [],
                   "component_code": BRUTE_SOLVE, "verifier_code": BRUTE_CHECK}],
        "final": "brute"}, ensure_ascii=False)

    with tempfile.TemporaryDirectory() as tmp:
        run = _fixture_copy(tmp)
        fake = FakeLLM([broken, broken, replan_json])
        res = _with_fake(fake, lambda: solve_mod.drive(str(run), max_repair_rounds=4,
                                                       max_node_repairs=2, max_replans=1,
                                                       pool=["fake"]))
        arch = run / "attempts" / "attempt1"
        _check(failures, res["status"] == "solved", "재계획 뒤 목표 달성", res.get("reason", ""))
        _check(failures, res.get("replans") == 1, "재계획은 한 번", str(res.get("replans")))
        _check(failures, len(fake.prompts) == 3, "수리 2회 뒤 재계획 1회", str(len(fake.prompts)))
        _check(failures, (arch / "plan.json").exists() and (arch / "results").exists(),
               "이전 plan/결과가 attempts/attempt1 에 보존된다")
        _check(failures, not (run / "results" / f"{FAILED_NODE}.json").exists(),
               "옛 결과가 새 계획에 섞이지 않는다")
        _check(failures, "verifier 거부" in fake.prompts[-1] or "예외" in fake.prompts[-1],
               "재계획 프롬프트가 이전 실패 기록을 담는다")
        _check(failures, "solve: 7" in fake.prompts[-1], "재계획 프롬프트에 실제 실패 사유가 있다")


def test_bad_repair_rejected(failures: list):
    """안전: 깨진 수리안은 채택되지 않는다 -- 그나마 돌던 코드를 지우면 재개 기반이 무너진다."""
    print("[안전] 형식 검사에 걸리는 수리안 반려")
    cases = [("문법 오류", "def solve(inputs:\n    return {"),
             ("solve 미정의", "def helper(x):\n    return x\n"),
             ("빈 응답", "   ")]
    with tempfile.TemporaryDirectory() as tmp:
        for label, reply in cases:
            run = _fixture_copy(Path(tmp) / label.replace(" ", "_"))
            before = (run / f"components/{FAILED_NODE}.py").read_text()
            fake = FakeLLM([reply])
            out = _with_fake(fake, lambda: planner.repair_node(str(run), FAILED_NODE,
                                                               pool=["fake"]))
            after = (run / f"components/{FAILED_NODE}.py").read_text()
            node = _node(run)
            _check(failures, out["status"] == "repair_rejected", f"{label}: 반려된다",
                   json.dumps(out, ensure_ascii=False))
            _check(failures, before == after, f"{label}: 기존 코드가 덮어써지지 않는다")
            _check(failures, node.status == "failed", f"{label}: status 가 pending 으로 풀리지 않는다")
            _check(failures, planner.repair_count(node) == 0, f"{label}: 수리 횟수로 세지 않는다")


def main() -> int:
    failures: list[str] = []
    for t in (test_red_without_repair, test_green_repair_loop,
              test_escalation_to_replan, test_bad_repair_rejected):
        t(failures)
    if failures:
        print("\n=== 실패 ===")
        for f in failures:
            print(" -", f)
        return 1
    print("\n플래너 되먹임 루프가 실측 런에서 red-green 을 통과했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
