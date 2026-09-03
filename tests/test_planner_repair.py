"""
플래너 되먹임 루프의 red-green 증명 -- "검증 실패가 계획으로 돌아가는가"를 실측 런으로 증명한다.

RED 의 근거는 합성이 아니라 실제 실패 런이다 -- orchestrator/runs/20260829-224043 을 그대로
얼려 tests/fixtures/failed_crt_run/ 에 둔다: factor / sub_equations 는 verified 인데 최종 노드
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
  5. 예산  -- 무한 루프를 도는 노드가 실제로 끊기고, 그 사유가 attempts 를 거쳐 수리 프롬프트에
              실려 더 빠른 코드로 교체된다. 예산이 없으면 hang 이라 attempts 에 아무것도 남지
              않고 되먹임 루프 자체가 조용히 멈춘다 -- '느림'이 수리 대상이 되는지의 증명이다.
  6. 계획   -- 계획 자체가 깨졌을 때(파싱 불가·구조 오류)도 사유를 되먹여 다시 세운다. 이게
              없으면 계획 단계만 되먹임 없는 한 번뿐인 관문으로 남는다(실측: 벤치 h3).
              실패한 시도의 코드 조각이 런 디렉토리에 남지 않는지도 함께 본다.

왜 살아있는 런이 아니라 얼린 사본인가: runs/20260829-224043 은 `solve.py --resume` 이 실제로
수리해서 verified 로 바꿔버리는 대상이다. 그 디렉토리를 픽스처로 쓰면, 에이전트가 자기 일을
제대로 해내는 순간 RED 근거가 사라져 테스트가 깨진다(테스트가 관측 대상을 관측 행위로 바꾸는
꼴이다). 그래서 실패 상태 그대로를 별도 경로에 고정해 두고, 살아있는 런은 자유롭게 수리·커밋
되게 둔다.

LLM 은 호출하지 않는다. llm_pool.call 을 가짜로 갈아끼워, "무엇을 프롬프트에 넣었는가"와
"응답을 어떻게 채택/반려하는가"만 검증한다(네트워크·쿼터 없이 매번 같은 결과).

실행: python3 tests/test_planner_repair.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ORCH = REPO / "orchestrator"
sys.path.insert(0, str(ORCH))

import llm_pool  # noqa: E402
import orchestrator  # noqa: E402
import planner  # noqa: E402
import solve as solve_mod  # noqa: E402
from plan_schema import Plan, Node  # noqa: E402

FIXTURE = REPO / "tests" / "fixtures" / "failed_crt_run"   # 실측 실패 런을 얼린 사본
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

# 예산 테스트용: 절대 끝나지 않는 solve 와, 그것을 대체할 즉답 solve.
HANGING_SOLVE = 'def solve(inputs):\n    n = 0\n    while True:\n        n += 1\n'
FAST_SOLVE = 'def solve(inputs):\n    return {"n": 42}\n'
BUDGET_CHECK = ('def check(output, inputs):\n'
                '    return output.get("n") == 42, f"n={output.get(\'n\')}"\n')

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


def _make_budget_run(tmp: str) -> Path:
    """무한 루프를 도는 노드 하나짜리 런을 만든다."""
    run = Path(tmp) / "budget_run"
    (run / "components").mkdir(parents=True)
    (run / "components" / "spin.py").write_text(HANGING_SOLVE, encoding="utf-8")
    (run / "components" / "spin_verify.py").write_text(BUDGET_CHECK, encoding="utf-8")
    Plan(problem="42 를 내라", final="spin",
         nodes=[Node(id="spin", goal="42 를 반환한다", deps=[],
                     component="components/spin.py", verifier="components/spin_verify.py")]
         ).save(run / "plan.json")
    return run


def test_time_budget_makes_slowness_repairable(failures: list):
    """예산: 무한 루프가 유계 실패로 바뀌고, 그 사유가 되먹임을 타고 수리로 이어진다."""
    print("[예산] 무한 루프 노드가 끊기고 수리된다")
    if not orchestrator.budget_enforceable():
        print("    SKIP 이 환경에서는 SIGALRM 을 걸 수 없다(POSIX 메인 스레드 아님)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        run = _make_budget_run(tmp)
        fake = FakeLLM([FAST_SOLVE])
        t0 = time.time()
        res = _with_fake(fake, lambda: solve_mod.drive(str(run), max_repair_rounds=3,
                                                       node_timeout=0.5, pool=["fake"]))
        elapsed = time.time() - t0

        node = Plan.load(run / "plan.json").node("spin")
        timeout_msgs = [a.get("error", "") for a in node.attempts if "예산" in str(a.get("error", ""))]
        p = fake.prompts[0] if fake.prompts else ""
        _check(failures, res["status"] == "solved", "예산 초과 노드가 수리 후 통과", res.get("reason", ""))
        _check(failures, elapsed < 30, f"무한 루프가 실제로 끊긴다({elapsed:.1f}초 만에 종료)")
        _check(failures, timeout_msgs, "예산 초과가 attempts 에 사유로 남는다", str(node.attempts))
        _check(failures, "예산" in p and "초과" in p, "그 사유가 수리 프롬프트에 실린다")
        _check(failures, (run / "results" / "spin.json").exists(), "교체된 코드의 결과가 저장된다")


def test_budget_off_is_explicit(failures: list):
    """예산 0 이하는 '무제한'이다 -- 끄는 경로가 조용히 걸려 있지 않은지 확인."""
    print("[예산] 0 이하면 예산을 걸지 않는다")
    with orchestrator.time_budget(0) as armed:
        _check(failures, armed is False, "0 이면 타이머를 걸지 않는다")
    if orchestrator.budget_enforceable():
        with orchestrator.time_budget(5) as armed:
            _check(failures, armed is True, "양수면 타이머를 건다")


def test_planning_retries_on_broken_plan(failures: list):
    """계획: 깨진 계획도 사유를 되먹여 다시 세운다 -- 계획 단계만 개루프로 남지 않게."""
    print("[계획] 파싱 불가 -> 구조 오류 -> 정상, 3번째에 성공")
    good = json.dumps({"nodes": [{"id": "brute", "goal": "직접 푼다", "deps": [],
                                  "component_code": BRUTE_SOLVE, "verifier_code": BRUTE_CHECK}],
                       "final": "brute"}, ensure_ascii=False)
    dangling = json.dumps({"nodes": [{"id": "a", "goal": "", "deps": ["없는노드"],
                                      "component_code": BRUTE_SOLVE,
                                      "verifier_code": BRUTE_CHECK}],
                           "final": "b"}, ensure_ascii=False)
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "plan_retry"
        fake = FakeLLM(["여기 계획입니다: (JSON 아님)", dangling, good])
        out = _with_fake(fake, lambda: planner.make_plan("x^2=4 를 풀어라", str(run),
                                                         pool=["fake"], attempts=3))
        comp = sorted(f.name for f in (run / "components").glob("*.py"))
        _check(failures, out["status"] == "planned", "3번째 시도에서 계획 성립",
               json.dumps(out, ensure_ascii=False)[:200])
        _check(failures, out.get("planning_attempts") == 3, "시도 횟수가 3으로 기록된다",
               str(out.get("planning_attempts")))
        _check(failures, len(fake.prompts) == 3, "LLM 을 3번 부른다", str(len(fake.prompts)))
        _check(failures, "계획으로 읽을 수 없었다" in fake.prompts[1],
               "2번째 프롬프트에 파싱 실패 사유가 실린다")
        _check(failures, "구조 오류" in fake.prompts[2] and "없는노드" in fake.prompts[2],
               "3번째 프롬프트에 구조 오류(미정의 의존)가 실린다")
        _check(failures, comp == ["brute.py", "brute_verify.py"],
               "실패한 시도의 코드 조각이 남지 않는다", str(comp))

    print("[계획] 끝까지 실패하면 사유를 모아 invalid_plan 으로 끝낸다")
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "plan_fail"
        fake = FakeLLM(["아님", "아님", "아님"])
        out = _with_fake(fake, lambda: planner.make_plan("문제", str(run), pool=["fake"],
                                                         attempts=3))
        _check(failures, out["status"] == "invalid_plan", "invalid_plan 으로 끝난다")
        _check(failures, len(out.get("errors", [])) == 3, "시도별 사유가 모두 남는다",
               str(out.get("errors")))
        _check(failures, not list((run / "components").glob("*.py")),
               "아무 파일도 쓰이지 않는다")



def test_llm_pool_reads_dotenv(failures: list) -> None:
    """CLI 로 돌 때도 .env 의 키를 찾는가.

    실측으로 걸린 함정이다: 키는 .env 에 있고 Discord 봇은 systemd 의 EnvironmentFile 로
    그것을 받는데, SSH 셸에서 `python3 ...` 로 직접 돌리면 .env 가 안 실려 후보 풀이 비고
    "빈 후보 풀" 만 보인다. **키가 없는 것처럼 보이지만 실은 있다.**

    서비스로 돌 때와 손으로 돌 때가 달라지는 것이 함정의 정체이므로 둘을 맞춘다.
    이미 있는 환경변수는 절대 덮지 않는다 -- systemd 로 들어온 값이 우선이어야 한다.

    탐색 자리를 갈아끼우고 잰다. 처음에는 cwd 만 옮기고 쟀는데, 그러면 **저장소 루트에
    .env 가 없는 기계에서만 통과하는 시험**이 된다 -- 컨테이너에서는 초록이었고 VM
    에서는 빨강이었다. VM 에는 진짜 .env 가 있어서 임시 .env 가 읽히지도 않았고,
    풀에는 진짜 키가 들어와 있었다. 시험이 기계를 타면 시험이 아니다."""
    import os
    import shutil
    import tempfile

    print("\n[.env] CLI 실행에서도 키를 찾는가")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    # **두 키를 다 치워야 한다.** build_pool 은 GEMINI_API_KEY 와 GEMINI_API_KEY_FALLBACK
    # 을 둘 다 읽는다. 처음에는 앞의 것만 치우고 쟀는데, VM 처럼 FALLBACK 이 환경에 있는
    # 기계에서는 풀이 2개가 되어 떨어졌다 -- 컨테이너에는 FALLBACK 이 없어서 초록이었다.
    # **또 "내 기계에 없는 것"을 전제한 시험이었다.** 같은 병으로 두 번 걸렸다.
    KEYS = ("GEMINI_API_KEY", "GEMINI_API_KEY_FALLBACK")
    saved = {k: os.environ.pop(k, None) for k in KEYS}
    tmp = Path(tempfile.mkdtemp(prefix="dotenv_test_"))
    real_cands = llm_pool._dotenv_candidates
    try:
        (tmp / ".env").write_text("GEMINI_API_KEY=from-dotenv-file\n", encoding="utf-8")
        llm_pool._dotenv_candidates = lambda: [tmp / ".env"]
        pool = llm_pool.build_pool(models=["m"], llm_factory=lambda m, k: (m, k))
        ok(len(pool) == 1 and pool[0][1][1] == "from-dotenv-file",
           ".env 의 키로 후보 풀을 만든다")

        os.environ["GEMINI_API_KEY"] = "from-environment"
        pool = llm_pool.build_pool(models=["m"], llm_factory=lambda m, k: (m, k))
        ok(bool(pool) and pool[0][1][1] == "from-environment",
           ".env 가 이미 있는 환경변수를 덮지 않는다 (systemd 값 우선)")

        # FALLBACK 도 후보가 되는가. VM 이 실제로 두 키를 쓰고 있으므로 이것도 재야 한다.
        os.environ["GEMINI_API_KEY_FALLBACK"] = "second-key"
        pool = llm_pool.build_pool(models=["m"], llm_factory=lambda m, k: (m, k))
        ok(len(pool) == 2 and {c[1][1] for c in pool} == {"from-environment", "second-key"},
           f"두 키가 모두 후보가 된다: {[c[1][1] for c in pool]}")
        os.environ.pop("GEMINI_API_KEY_FALLBACK", None)

        # 여러 자리를 다 훑되 앞자리가 이긴다 -- 뒤에 있는 파일이 앞을 덮으면 안 된다.
        os.environ.pop("GEMINI_API_KEY", None)
        tmp2 = Path(tempfile.mkdtemp(prefix="dotenv_test2_"))
        try:
            (tmp2 / ".env").write_text("GEMINI_API_KEY=second-file\n", encoding="utf-8")
            llm_pool._dotenv_candidates = lambda: [tmp / ".env", tmp2 / ".env"]
            pool = llm_pool.build_pool(models=["m"], llm_factory=lambda m, k: (m, k))
            ok(bool(pool) and pool[0][1][1] == "from-dotenv-file",
               "앞자리 .env 가 이긴다 (뒤 파일이 덮지 않는다)")
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        llm_pool._dotenv_candidates = real_cands
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)


def test_llm_pool_waits_out_transient_outage(failures: list) -> None:
    """풀 한 바퀴가 통째로 503 이면 **기다렸다가 다시 도는가.**

    실측으로 걸린 실패다(2026-09-03). 수요 급증에 Gemini 가 키와 모델을 가리지 않고 503
    UNAVAILABLE 을 던져 후보 12개가 몇 초 만에 전부 탔고, 그대로 RuntimeError 로 죽었다.
    남은 26개를 더 시도했어도 같은 벽이었다 -- **필요한 것은 다음 후보가 아니라 시간이다.**

    그리고 그 반대도 지켜야 한다: 전부 쿼터 소진(429)이면 기다려도 안 풀린다(일일 한도는
    날짜로 풀린다). 그때 백오프를 도는 것은 그냥 낭비다. 두 경우가 갈리는지 본다."""
    print("\n[llm_pool] 일시장애에서 스윕 재시도")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    class Stub:                      # quota_tracker 를 건드리지 않는다
        def is_dead(self, *_): return False
        def remaining(self, *_): return 100
        def get_pinned(self, *_): return None
        def record_success(self, *_): pass
        def set_pinned(self, *_): pass
        def record_exhausted(self, *_): pass
        def mark_dead(self, *_): pass

    class Flaky:
        """정해둔 횟수만큼 503 을 던지고 그 뒤에는 성공한다."""
        def __init__(self, fails, err="503 UNAVAILABLE high demand"):
            self.left, self.err = fails, err
        def invoke(self, _prompt):
            if self.left > 0:
                self.left -= 1
                raise RuntimeError(self.err)
            return "돌아왔다"

    waited: list = []
    real_qt, llm_pool.quota_tracker = llm_pool.quota_tracker, Stub()
    try:
        # 후보 2개가 각각 첫 한 번은 503. 스윕 1 은 통째로 실패(2회 시도),
        # 스윕 2 의 첫 후보에서 성공해야 한다 -- 기다림은 정확히 한 번.
        pool = [("k:a", Flaky(1)), ("k:b", Flaky(1))]
        text, label = llm_pool.call(pool, "p", verbose=False, sweeps=3,
                                    sleep=waited.append)
        ok(text == "돌아왔다", f"두 번째 스윕에서 성공한다 (얻은 것: {text!r})")
        ok(len(waited) == 1, f"스윕 사이에 정확히 한 번 기다린다: {waited}")
        ok(waited and waited[0] >= 1.0, f"기다린 시간이 0 이 아니다: {waited}")

        # 쿼터 소진만 있으면 기다리지 않고 즉시 포기해야 한다.
        waited.clear()
        pool = [("k:a", Flaky(99, "429 RESOURCE_EXHAUSTED")),
                ("k:b", Flaky(99, "429 RESOURCE_EXHAUSTED"))]
        try:
            llm_pool.call(pool, "p", verbose=False, sweeps=3, sleep=waited.append)
            ok(False, "쿼터 소진인데 성공했다고 한다")
        except RuntimeError as e:
            ok("429" in str(e), f"마지막 오류를 사유에 남긴다: {str(e)[:60]}")
        ok(not waited, f"쿼터 소진에서는 기다리지 않는다 (기다림: {waited})")

        # 계속 503 이면 스윕을 다 쓰고 죽되, 업스트림 과부하라고 말해야 한다.
        waited.clear()
        pool = [("k:a", Flaky(99))]
        try:
            llm_pool.call(pool, "p", verbose=False, sweeps=3, sleep=waited.append)
            ok(False, "계속 503 인데 성공했다고 한다")
        except RuntimeError as e:
            ok("업스트림 과부하" in str(e),
               f"코드로 못 푸는 실패임을 밝힌다: {str(e)[-120:]}")
        ok(len(waited) == 2, f"스윕 3회면 사이에 2번 기다린다: {waited}")
        ok(waited == sorted(waited) and waited[1] > waited[0],
           f"백오프가 늘어나야 한다: {waited}")
    finally:
        llm_pool.quota_tracker = real_qt


def test_llm_pool_budgets_time_per_sweep(failures: list) -> None:
    """느린 실패(504)가 스윕 하나에 시간을 다 쓰지 못하게 막는가.

    실측으로 걸린 실패다(2026-09-03, 두 번째 런). 504 DEADLINE_EXCEEDED 는 후보 하나가
    TIMEOUT(60s)을 통째로 먹는다. 12후보 스윕 하나가 720s 를 삼켰고, 전체 상한 900s 가
    스윕 2 중간에 끊겨 **스윕 3, 4 는 돌지도 못했다.** 백오프를 넣어놓고 백오프에 쓸
    시간을 남기지 않은 것이다.

    과부하 구간에서 값이 있는 것은 다음 후보가 아니라 기다림이다. 그러니 한 스윕이
    DEADLINE/스윕수 를 넘기면 남은 후보를 버리고 백오프로 넘어가야 한다."""
    print("\n[llm_pool] 스윕별 시간 예산")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    class Stub:
        def is_dead(self, *_): return False
        def remaining(self, *_): return 100
        def get_pinned(self, *_): return None
        def record_success(self, *_): pass
        def set_pinned(self, *_): pass
        def record_exhausted(self, *_): pass
        def mark_dead(self, *_): pass

    now = [0.0]                       # 가짜 시계. 실제로 기다리지 않는다
    COST = 60.0                       # 504 하나가 먹는 시간

    class Slow:
        def invoke(self, _p):
            now[0] += COST
            raise RuntimeError("504 DEADLINE_EXCEEDED")

    def fake_sleep(sec):
        now[0] += sec

    real_qt, llm_pool.quota_tracker = llm_pool.quota_tracker, Stub()
    real_dl, llm_pool.DEADLINE = llm_pool.DEADLINE, 900.0
    # 스윕 예산은 max(DEADLINE/스윕수, TIMEOUT x 2) 라 TIMEOUT 도 같이 고정해야 한다.
    # 안 그러면 실제 TIMEOUT(240s) 이 바닥을 480s 로 밀어올려 이 계산이 달라진다.
    real_to, llm_pool.TIMEOUT = llm_pool.TIMEOUT, COST
    try:
        pool = [(f"k:m{i}", Slow()) for i in range(12)]
        waited: list = []

        def sleep(sec):
            waited.append(sec)
            fake_sleep(sec)

        try:
            llm_pool.call(pool, "p", verbose=False, sweeps=4, sleep=sleep,
                          clock=lambda: now[0])
            ok(False, "전부 504 인데 성공했다고 한다")
        except RuntimeError as e:
            ok("504" in str(e), f"마지막 오류를 남긴다: {str(e)[:50]}")

        # 스윕 예산 900/4 = 225s. 후보 하나가 60s 이므로 스윕당 4개까지 태우고 끊긴다.
        ok(len(waited) == 3,
           f"스윕 4회면 사이에 3번 기다려야 한다 (한 스윕이 다 먹으면 못 기다린다): {waited}")
        ok(now[0] <= 900.0 + COST,
           f"전체 상한 900s 를 크게 넘기지 않는다: {now[0]:.0f}s")
        print(f"    [실측] 가짜 시계 {now[0]:.0f}s 동안 스윕 4회, 백오프 {waited}")
    finally:
        llm_pool.quota_tracker = real_qt
        llm_pool.DEADLINE = real_dl
        llm_pool.TIMEOUT = real_to


def test_llm_pool_splits_rpm_from_daily_quota(failures: list) -> None:
    """429 를 **분당 한도와 일일 한도로 가르는가.**

    실측으로 걸린 실패다(2026-09-03). 장부에 count=15000(=일일 한도)이 박힌 후보가 8개
    있었는데, 사용자는 그날 LLM 을 부른 적이 없다고 했고 **그 말이 맞았다.** 하루치를 쓴
    것이 아니라 1분치를 쓴 것을 우리가 하루치로 적은 것이다.

    오케스트레이터는 후보 12~38개를 몇 초 안에 몰아 때린다. 분당 한도에 걸리기 딱 좋은
    모양이다. 그런데 llm_pool 은 429 를 전부 record_exhausted 로 확정 기록해서, 60초면
    풀릴 후보를 자정까지 봉인했다. quota_tracker 의 주석이 정확히 이 함정을 경고하고
    있었고 bot_tools 는 이미 가르고 있었는데 orchestrator 쪽만 안 갈랐다."""
    print("\n[llm_pool] 429 분당/일일 구분")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    RPM = ("429 RESOURCE_EXHAUSTED quota_metric: generate_content_free_tier_requests, "
           "quota_id: GenerateRequestsPerMinutePerProjectPerModel")
    RPD = "429 RESOURCE_EXHAUSTED quota_id: GenerateRequestsPerDayPerProjectPerModel"

    ok(llm_pool._is_quota(Exception(RPM)) and llm_pool._is_rpm(Exception(RPM)),
       "분당 한도를 분당으로 읽는다")
    ok(llm_pool._is_quota(Exception(RPD)) and not llm_pool._is_rpm(Exception(RPD)),
       "일일 한도를 일일로 읽는다")
    ok(not llm_pool._is_rpm(Exception("503 UNAVAILABLE")), "503 은 쿼터가 아니다")

    calls = {"rpm": [], "daily": []}

    class Stub:
        def is_dead(self, *_): return False
        def remaining(self, *_): return 100
        def get_pinned(self, *_): return None
        def record_success(self, *_): pass
        def set_pinned(self, *_): pass
        def record_exhausted(self, label, *_): calls["daily"].append(label)
        def record_rpm_cooldown(self, label, *_): calls["rpm"].append(label)
        def mark_dead(self, *_): pass

    class Boom:
        def __init__(self, msg): self.msg = msg
        def invoke(self, _p): raise RuntimeError(self.msg)

    real, llm_pool.quota_tracker = llm_pool.quota_tracker, Stub()
    try:
        pool = [("k:rpm", Boom(RPM)), ("k:rpd", Boom(RPD))]
        try:
            llm_pool.call(pool, "p", verbose=False, sweeps=1, sleep=lambda _: None)
        except RuntimeError:
            pass
        ok(calls["rpm"] == ["k:rpm"],
           f"분당 한도는 60초 쿨다운으로만 적는다: {calls['rpm']}")
        ok(calls["daily"] == ["k:rpd"],
           f"일일 한도만 자정까지 봉인한다: {calls['daily']}")
    finally:
        llm_pool.quota_tracker = real


def test_llm_pool_resolves_allowlist_not_guesses(failures: list) -> None:
    """쓸 모델을 **사람이 고른 목록으로 못 박되, id 는 짐작하지 않는가.**

    두 가지를 동시에 지켜야 한다.

    ① 목록을 줄인다. ListModels 는 40개 넘게 준다. 전부 후보로 삼으면 계획 호출 한 번에
       수십 개를 몇 초 안에 몰아 때려 **분당 한도를 스스로 긁는다** -- 오늘 장부에 잘못
       박힌 소진 표시 8개가 그렇게 생겼다. TTS/임베딩처럼 generateContent 가 안 되는
       것까지 섞여 400/404 도 만든다.

    ② id 를 짐작하지 않는다. 'Gemini 3.6 Flash' 가 'gemini-3.6-flash' 일 것이라는 짐작은
       짐작일 뿐이고, 틀리면 404 가 나는데 그 404 가 다시 '구글이 이상하다'로 읽힌다.
       ListModels 가 id 와 displayName 을 같이 주므로 대조하면 짐작이 필요 없다.

    그리고 접두사로 맞추면 안 된다 -- 'gemini35flash' 는 'gemini35flashlite' 의 접두사라,
    Flash 를 고르려다 Flash Lite 를 집는다."""
    print("\n[llm_pool] 허용 목록을 실제 id 로 푼다")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    LIVE = [("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite"),
            ("gemini-3.5-flash", "Gemini 3.5 Flash"),
            ("gemini-3.6-flash", "Gemini 3.6 Flash"),
            ("gemma-4-26b-it", "Gemma 4 26B"),
            ("gemini-2.5-flash-tts", "Gemini 2.5 Flash TTS"),
            ("some-other-model", "Some Other Model")]
    allow = ["Gemini 3.6 Flash", "Gemini 3.5 Flash", "Gemini 3.5 Flash Lite", "Gemma 4 26B",
             "Gemini 9.9 Flash"]                      # 마지막 하나는 이 키에 없다

    got = llm_pool.resolve_models("k", allow=allow, lister=lambda _k: LIVE)
    ok(got == ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
               "gemma-4-26b-it"],
       f"허용 목록 순서대로 실제 id 만 나온다: {got}")
    ok("gemini-2.5-flash-tts" not in got and "some-other-model" not in got,
       "목록 밖 모델(TTS 등)은 들어오지 않는다")
    ok(got[1] == "gemini-3.5-flash",
       "'Gemini 3.5 Flash' 가 Flash Lite 를 집지 않는다 (접두사 비교 금지)")

    # 조회가 실패해도 지난번에 풀린 것을 쓴다 -- 503 중에 풀이 비면 그것이 또 다른 고장이다.
    def boom(_k):
        raise RuntimeError("503 UNAVAILABLE")
    cached = llm_pool.resolve_models("k", allow=allow, lister=boom)
    ok(cached == got, f"조회 실패 시 캐시를 쓴다: {cached}")

    ok(llm_pool._norm("Gemini 3.5 Flash") == llm_pool._norm("gemini-3.5-flash"),
       "표시이름과 id 가 같은 자리로 정규화된다")
    ok(llm_pool._norm("Gemini 3.5 Flash") != llm_pool._norm("Gemini 3.5 Flash Lite"),
       "Flash 와 Flash Lite 는 다른 것으로 읽힌다")


def test_llm_pool_timeout_fits_measured_latency(failures: list) -> None:
    """긴 프롬프트가 실제로 걸리는 시간보다 마감이 넉넉한가.

    **로그를 뒤덮던 504 중 상당수는 우리가 만든 것이었다.** 실측(probe_gemini,
    2026-09-03), 텐서랭크 문제 기술서 4692자를 태웠을 때:

        gemini-3.1-flash-lite   HTTP 200    5.45s
        gemini-3.5-flash        HTTP 200  145.55s

    그런데 TIMEOUT 이 60초였다. 마감을 60초로 주면 구글은 그 마감이 지난 시점에
    504 DEADLINE_EXCEEDED 를 돌려준다. 우리는 그것을 일시장애로 세고 백오프까지
    돌았다. 짧은 프롬프트는 1~3초에 오므로 이 함정은 문제가 커진 뒤에야 드러난다.

    그리고 스윕 예산이 TIMEOUT 보다 작으면 스윕마다 한 후보도 제대로 못 태운다."""
    print("\n[llm_pool] 마감이 실측 지연을 담는가")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    MEASURED = 145.55                      # gemini-3.5-flash, 4692자
    ok(llm_pool.TIMEOUT > MEASURED,
       f"마감 {llm_pool.TIMEOUT:.0f}s 가 실측 {MEASURED}s 보다 커야 한다")
    ok(llm_pool.TIMEOUT >= MEASURED * 1.5,
       f"여유가 1.5배는 있어야 한다 (지금 {llm_pool.TIMEOUT / MEASURED:.2f}배)")

    per_sweep = max(llm_pool.DEADLINE / llm_pool.SWEEPS,
                    llm_pool.TIMEOUT * llm_pool.MIN_SWEEP_BUDGET_FACTOR)
    ok(per_sweep >= llm_pool.TIMEOUT * 2,
       f"스윕 예산 {per_sweep:.0f}s 는 후보 두 개는 태울 수 있어야 한다 "
       f"(TIMEOUT {llm_pool.TIMEOUT:.0f}s)")

    # 허용 목록 순서가 이름 규칙(_model_rank)을 이기는가.
    # flash-lite 가 flash 보다 26배 빨랐다 -- 이름으로는 알 수 없는 것이다.
    class Stub:
        def is_dead(self, *_): return False
        def remaining(self, *_): return 100
        def get_pinned(self, *_): return None

    real, llm_pool.quota_tracker = llm_pool.quota_tracker, Stub()
    try:
        allow = llm_pool._allow_list()
        if allow:
            first, second = llm_pool._norm(allow[0]), llm_pool._norm(allow[1])
            pool = [(f"k:{second}", "B"), (f"k:{first}", "A")]
            ranked = [lb for lb, _ in llm_pool._ranked(pool, "t")]
            ok(llm_pool._norm(ranked[0].split(":", 1)[1]) == first,
               f"허용 목록 첫 줄이 먼저 온다: {ranked}")
    finally:
        llm_pool.quota_tracker = real


def test_replan_does_not_erase_injected_verifier(failures: list) -> None:
    """**재계획이 주입 심판을 지우지 못하게 막는가.** 이 세션에서 가장 큰 구멍이었다.

    실측(2026-09-03, tensorrank --budget mm333=26). 라운드 4 / 재계획 1 로 "solved" 가
    떴는데, 그 답을 밖에서 만든 심판으로 다시 재보니 세 case 전부 "답 없음"이었다.

    원인. run.py 는 최초 계획의 최종 노드에 심판을 한 번 꽂는다. 그런데 planner.replan 은
    make_plan 을 다시 불러 plan.json 을 **통째로 새로 쓴다.** 꽂아둔 심판이 사라지고
    LLM 이 쓴 채점표가 그 자리에 들어앉는다. 그 다음부터는 LLM 이 제 답에 스스로 합격을
    주고, drive 는 그것을 "solved" 로 돌려준다.

    검증 비대칭이니 심판 분리니 하는 것이 전부 여기서 무너진다 -- 심판이 후보와 같은
    곳에서 나온 순간 아무것도 재고 있지 않다. 그래서 주입은 한 번이 아니라 **계획이 새로
    써질 때마다** 해야 한다."""
    print("\n[안전] 재계획이 주입 심판을 지우지 못한다")
    import solve as orch_solve

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        run = Path(td)
        INJECT = "verifiers/outside.py#check"
        # LLM 이 새로 쓴 계획: 최종 노드 심판이 제 것으로 바뀌어 있다.
        (run / "plan.json").write_text(json.dumps({
            "problem": "p", "final": "b",
            "nodes": [{"id": "a", "verifier": "inline:whatever"},
                      {"id": "b", "verifier": "components/llm_scoring.py#check"}]
        }, ensure_ascii=False), encoding="utf-8")

        changed = orch_solve._force_verifier(run, INJECT)
        plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
        final = next(n for n in plan["nodes"] if n["id"] == "b")
        other = next(n for n in plan["nodes"] if n["id"] == "a")
        ok(changed, "바뀌었음을 보고한다 (조용히 넘어가면 로그에 안 남는다)")
        ok(final["verifier"] == INJECT,
           f"최종 노드 심판이 주입본으로 되돌아온다: {final['verifier']}")
        ok(other["verifier"] == "inline:whatever",
           "최종 노드가 아닌 노드는 건드리지 않는다")
        ok(not orch_solve._force_verifier(run, INJECT),
           "이미 꽂혀 있으면 다시 쓰지 않는다 (멱등)")

        # drive 가 시작 시점에도 다시 꽂는가 -- 이어서 돌리는 런(--run-dir)이 이 경로다.
        (run / "plan.json").write_text(json.dumps({
            "problem": "p", "final": "b",
            "nodes": [{"id": "b", "verifier": "components/llm_scoring.py#check"}]
        }, ensure_ascii=False), encoding="utf-8")
        real = orch_solve.orchestrator.run_plan
        orch_solve.orchestrator.run_plan = lambda *a, **kw: {"status": "invalid_plan"}
        try:
            orch_solve.drive(str(run), max_repair_rounds=0, max_replans=0,
                             final_verifier=INJECT)
        finally:
            orch_solve.orchestrator.run_plan = real
        plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
        ok(plan["nodes"][0]["verifier"] == INJECT,
           f"drive 가 시작 시점에 다시 꽂는다: {plan['nodes'][0]['verifier']}")


def test_failure_reasons_surface(failures: list) -> None:
    """심판의 기각 사유가 **화면까지 올라오는가.** 되먹임의 재료가 그것이다.

    실측(2026-09-03, tensorrank --budget mm333=26). 수리 2회 + 재계획 1회를 돌고
    incomplete 로 끝났는데 화면에는 node_status 의 "failed" 세 글자뿐이었다. 심판은
    틀린 칸 수, 상쇄 질량(국소최소 신호), 격자 이탈, 예산 초과를 전부 만들어 두었고
    orchestrator 도 node.attempts 에 성실히 적고 있었다 -- **아무도 읽지 않았을 뿐이다.**

    무엇이 틀렸는지 모르면 다음 예산을 얼마로 걸지, 문제 기술서를 어떻게 고칠지
    정할 수 없다. 그리고 재계획 전 시도(attempts/attemptN)까지 봐야 흐름이 보인다."""
    print("\n[진단] 기각 사유가 결과까지 올라온다")
    import solve as orch_solve
    import tempfile

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    def plan_with(node_id, atts):
        return {"problem": "p", "final": node_id,
                "nodes": [{"id": node_id, "verifier": "v.py#check", "attempts": atts}]}

    with tempfile.TemporaryDirectory() as td:
        run = Path(td)
        (run / "attempts" / "attempt1").mkdir(parents=True)
        (run / "attempts" / "attempt1" / "plan.json").write_text(json.dumps(
            plan_with("old_node", [{"rejected": "case mm333: 4 칸이 틀렸다"}])),
            encoding="utf-8")
        (run / "plan.json").write_text(json.dumps(
            plan_with("new_node", [{"error": "solve: KeyError('u')"},
                                   {"rejected": "case w_state: 격자 이탈 -- |성분| 최대 100"}])),
            encoding="utf-8")

        got = orch_solve.failure_reasons(run)
        ok(len(got) == 3, f"세 건이 다 모인다 (재계획 전 것 포함): {len(got)}")
        ok(got[0]["plan"] == "attempt1" and got[0]["node"] == "old_node",
           f"재계획 전 시도가 먼저 온다: {got[0]}")
        ok(got[-1]["kind"] == "기각" and "격자" in got[-1]["message"],
           f"마지막이 최신 기각이다: {got[-1]}")
        ok(any(g["kind"] == "오류" for g in got), "실행 오류도 사유로 잡는다")
        ok(all(len(g["message"]) > 5 for g in got), "사유를 잘라내지 않는다")

        # drive 가 incomplete 로 끝날 때 rounds 와 failures 를 같이 돌려주는가.
        # rounds 가 None 으로 찍히던 것도 실측으로 걸렸다.
        real = orch_solve.orchestrator.run_plan
        orch_solve.orchestrator.run_plan = lambda *a, **kw: {
            "status": "incomplete", "node_status": {"new_node": "failed"}}
        try:
            res = orch_solve.drive(str(run), max_repair_rounds=0, max_replans=0)
        finally:
            orch_solve.orchestrator.run_plan = real
        ok(res["status"] == "incomplete", "incomplete 로 끝난다")
        ok(isinstance(res.get("rounds"), int),
           f"rounds 가 None 이 아니다: {res.get('rounds')!r}")
        ok(len(res.get("failures") or []) == 3,
           f"결과에 기각 사유가 실린다: {len(res.get('failures') or [])}건")


def test_method_trace_separates_tweak_from_jump(failures: list) -> None:
    """수리가 **다듬은 것인지 갈아탄 것인지** 갈리는가.

    왜 재는가. 되먹임 루프가 국소 수선만 하는 기계라면 -- 상수를 바꾸고 반복 횟수를
    늘리는 정도라면 -- 애초에 알려진 방법 밖으로 나갈 수 없다. 텐서랭크 22 처럼
    "기존 네 갈래로는 아무도 못 한" 자리를 노린다면, 관측해야 할 것은 라운드 수가
    아니라 **판본 사이에서 방법이 실제로 갈아타는가**다. 네 번 다듬은 것과 네 번
    갈아탄 것이 "라운드 4" 라는 같은 숫자로 보이면 아무것도 관측하지 못한 것이다.

    거리만으로 가르면 눈금이 거칠다 -- 호출이 두 개뿐인 프로그램에 하나가 붙으면
    자카드 거리가 0.5 인데 그것은 방법이 바뀐 게 아니라 보조 계산이 붙은 것이다.
    그래서 갈래가 갈렸는지를 같이 본다."""
    print("\n[관측] 다듬기 / 부분 교체 / 갈아타기")
    import method_trace as mt
    import tempfile

    def ok(cond, msg):
        print(f"    {'OK  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    LSTSQ = "import numpy as np\ndef solve(i):\n    b,*_=np.linalg.lstsq(A,y,rcond=None)\n    return b\n"
    CONST = "import numpy as np\ndef solve(i):\n    b,*_=np.linalg.lstsq(A,y,rcond=1e-12)\n    return b\n"
    PLUS  = "import numpy as np\ndef solve(i):\n    U,S,V=np.linalg.svd(A)\n    b,*_=np.linalg.lstsq(A,y,rcond=None)\n    return b\n"
    OTHER = "import random, itertools\ndef solve(i):\n    for c in itertools.product(range(3),repeat=8):\n        if random.random()<0.5: pass\n    return c\n"

    with tempfile.TemporaryDirectory() as td:
        rd = Path(td)
        (rd / "history" / "n").mkdir(parents=True)
        (rd / "components").mkdir()
        for i, src in enumerate((LSTSQ, CONST, PLUS), 1):
            (rd / "history" / "n" / f"r{i:02d}.py").write_text(src, encoding="utf-8")
        (rd / "components" / "n.py").write_text(OTHER, encoding="utf-8")

        rows = mt.report(rd)["versions"]
        kinds = [r["kind"] for r in rows]
        ok(kinds == ["첫 판", "다듬기", "부분 교체", "**갈아타기**"],
           f"네 판본이 각각 다르게 읽혀야 한다: {kinds}")
        ok(rows[1]["dist"] == 0.0, f"상수만 바뀌면 거리 0: {rows[1]['dist']}")
        ok(rows[3]["dist"] == 1.0, f"호출이 통째로 바뀌면 거리 1: {rows[3]['dist']}")
        ok("선형대수/최소제곱" in rows[0]["tags"], f"갈래를 붙인다: {rows[0]['tags']}")
        ok(set(rows[3]["tags"]) == {"무작위 탐색", "완전 열거"},
           f"갈아탄 뒤 갈래도 바뀐다: {rows[3]['tags']}")
        ok("itertools.product" in rows[3]["new_calls"],
           f"새로 등장한 호출을 짚는다: {rows[3]['new_calls']}")

    # 알려진 갈래 어디에도 안 걸리는 코드는 '미분류' 로 남아야 한다 -- 그쪽이 흥미롭다.
    fp = mt.fingerprint("def solve(i):\n    t = {}\n    for k in range(9):\n        t[k] = k ^ 3\n    return t\n")
    ok(fp["tags"] == ["미분류"], f"알려진 갈래 밖이면 미분류: {fp['tags']}")


def main() -> int:
    failures: list[str] = []
    for t in (test_red_without_repair, test_green_repair_loop,
              test_escalation_to_replan, test_bad_repair_rejected,
              test_time_budget_makes_slowness_repairable, test_budget_off_is_explicit,
              test_planning_retries_on_broken_plan, test_llm_pool_reads_dotenv,
              test_llm_pool_waits_out_transient_outage,
              test_llm_pool_budgets_time_per_sweep,
              test_llm_pool_splits_rpm_from_daily_quota,
              test_llm_pool_resolves_allowlist_not_guesses,
              test_llm_pool_timeout_fits_measured_latency,
              test_replan_does_not_erase_injected_verifier,
              test_failure_reasons_surface,
              test_method_trace_separates_tweak_from_jump):
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
