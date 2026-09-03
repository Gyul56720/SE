"""
플래너: 문제를 받아 DAG(plan.json + 노드별 solve/verify 코드)로 분해하고, 실행이 실패하면
그 실패 사유를 되먹여 노드를 수리(repair)하거나 계획을 다시 세우는(replan) 최상위 계층.

이 계층이 가장 불안정하다(LLM 추론). 그래서 검증된 오케스트레이터 위에 얹혀, 엉뚱한 계획을
내도 각 노드의 verifier(신뢰)가 통과 안 시키면 채택되지 않는다 -- "제안이 아니라 검증된 채택".

역할 분배:
  플래너(여기)  : 문제를 하위 작업 DAG 로 쪼갠다. 단일 알고리즘이면 노드 1개, 복합이면
                 여러 노드(예: 인수분해 -> 소수별 계산 -> CRT). 각 노드의 solve/verify 코드도
                 생성한다. 실행이 실패하면 실패 사유를 받아 다시 시도한다.
  오케스트레이터 : 그 DAG 를 위상정렬로 실행하고 노드별 verifier 로 검증(orchestrator.py).
  verifier      : 무엇이 정답인지 판정(신뢰). 노드별 + 필요시 최종 조합.

왜 되먹임이 필요한가 (실측):
  runs/20260829-224043 은 factor / sub_equations 가 verified 된 뒤 최종 노드 crt_combine 이
  `solve: 7`(KeyError) 로 죽은 채 영구히 남아 있었다. 원인은 결과가 JSON 으로 왕복하며 dict 키
  7 이 "7" 이 된 것뿐이고, solutions_mod[str(p1)] 한 곳이면 끝나는 버그였다. 그런데 실패 사유가
  attempts 에 쌓이기만 하고 아무도 읽지 않아서(플래너를 다시 부르는 경로 자체가 없었다) 재개해도
  같은 코드를 그대로 다시 돌렸고, attempts 에는 똑같은 `solve: 7` 이 두 번 쌓였다.
  즉 계획->실행->검증까지만 이어진 개루프였다. 목적지향 에이전트가 되려면 검증 실패가 계획으로
  돌아가는 간선이 있어야 한다: 목표 -> 계획 -> 실행 -> 검증 -> (실패) -> 재계획 -> 목표 달성까지.
  이 파일의 repair_node / replan 이 그 간선이고, solve.drive 가 그 루프를 돈다.

수리의 안전 규칙 -- verifier 는 절대 다시 쓰지 않는다:
  실패를 "verifier 를 고쳐서" 없애면 검증 채택 원칙이 무너진다(자기가 채점표를 고치는 것).
  repair_node 는 component(solve) 코드만 덮어쓰고 verifier 파일은 읽기 전용으로 프롬프트에
  넣는다. 계획 자체가 틀려 verifier 까지 다시 세워야 하는 경우는 replan 으로 승격하며, 이때도
  이전 plan/components/results 는 지우지 않고 attempts/attemptN/ 으로 보존한다.

모든 LLM 호출은 llm_pool.call 로 나가 쿼터/모델 자동전환(429/404/503)을 견딘다.

LLM 출력 계약(JSON): {
  "nodes": [
    {"id","goal","deps":[...],
     "component_code": "def solve(inputs): ...",
     "verifier_code":  "def check(output, inputs): return (bool, msg)"}
  ],
  "final": "<id>"
}
플래너는 이 JSON 을 받아 run 디렉토리에 plan.json + components/*.py 로 풀어 쓴다.
그다음은 orchestrator.run_plan(run_dir) 이 실행/검증/복원을 담당한다.
수리 호출의 출력 계약은 JSON 이 아니라 파이썬 코드 한 덩어리다(코드 이스케이프 사고를 줄인다).
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm_pool  # noqa: E402
from orchestrator import NODE_TIMEOUT  # noqa: E402  (아래 계층 -- 실행 예산을 프롬프트에 싣는다)
from plan_schema import Plan, Node  # noqa: E402

# 노드 결과는 파일(JSON)로 오가므로 파이썬 값이 그대로 보존되지 않는다. 이걸 계약으로 못박지
# 않아서 실제로 runs/20260829-224043 이 죽었다(dict 키 7 -> "7").
JSON_CONTRACT = (
    "노드의 solve 결과는 JSON 파일로 저장돼 다음 노드의 inputs 로 전달된다. 따라서 dict 의 키는 "
    "반드시 문자열로 되돌아오고(정수 키를 넣었으면 inputs 에서는 str 키다), 튜플·집합·복소수 등 "
    "JSON 이 아닌 값은 쓸 수 없다. 다음 노드에서 값을 꺼낼 때 이 왕복을 계산에 넣어라."
)

# 오케스트레이터가 노드마다 이 예산을 강제한다. 프롬프트에 실어야 애초에 지수 시간 알고리즘을
# 덜 낸다 -- 예산 초과는 attempts 에 남아 되먹임으로 돌아오므로 '느림'도 수리 대상이 된다.
TIME_CONTRACT = (
    f"각 노드의 solve 와 check 는 {NODE_TIMEOUT:g}초 안에 끝나야 한다. 초과하면 실행이 끊기고 "
    f"실패로 기록된다. 전수 탐색이 그 안에 안 끝날 규모면 더 나은 알고리즘을 써라."
)

PLANNER_SYSTEM = (
    "너는 문제를 푸는 알고리즘 파이프라인을 설계하는 플래너다. 주어진 문제를 하위 작업들의 "
    "DAG 로 분해하라. 단일 알고리즘으로 충분하면 노드 1개, 여러 알고리즘이 필요하면 의존 관계를 "
    "가진 여러 노드로 나눠라(예: 인수분해 -> 소수별 제곱근 -> CRT 결합).\n"
    "각 노드마다 solve(inputs: dict)->dict 파이썬 함수와, 그 출력을 '독립적으로' 검증하는 "
    "check(output: dict, inputs: dict)->(bool, str) 함수를 작성하라. inputs 에는 선행 노드 "
    "결과가 {dep_id: result} 로 들어온다. check 는 출력이 정말 맞는지 수학적으로/재계산으로 "
    "확인해야 한다(그냥 True 반환 금지).\n"
    + JSON_CONTRACT + "\n" + TIME_CONTRACT + "\n"
    "오직 아래 JSON 형식 하나만 출력하라(설명·코드펜스 금지):\n"
    '{"nodes":[{"id":"...","goal":"...","deps":[...],'
    '"component_code":"def solve(inputs):\\n    ...","verifier_code":"def check(output, inputs):\\n    ..."}],'
    '"final":"..."}'
)

REPAIR_SYSTEM = (
    "너는 파이프라인에서 실패한 노드 하나의 solve 코드를 고치는 수리자다. 아래에 원 문제, 그 "
    "노드의 목표, 지금 코드, 이 노드를 채점하는 verifier(고칠 수 없다), 선행 노드가 실제로 넘겨준 "
    "값, 그리고 실패 이력이 주어진다.\n"
    "실패 이력을 먼저 읽고 같은 실패를 반복하지 마라. 예외라면 그 예외가 나는 정확한 지점을, "
    "verifier 거부라면 거부 사유가 요구하는 성질을 짚어서 고쳐라.\n"
    + JSON_CONTRACT + "\n" + TIME_CONTRACT + "\n"
    "verifier 는 신뢰 기반이므로 절대 바꾸려 하지 말고, 그 verifier 를 통과하는 solve 를 써라.\n"
    "오직 파이썬 코드만 출력하라(설명·코드펜스 금지). 최상위에 def solve(inputs): 가 있어야 하고, "
    "필요한 import 는 코드 안에 포함하라."
)


def _parse_plan_json(text: str) -> dict:
    """LLM 응답에서 JSON 을 추출. 코드펜스가 있으면 벗겨낸다."""
    t = text.strip()
    if "```" in t:
        seg = t.split("```", 2)
        t = seg[1] if len(seg) > 1 else t
        if t.startswith("json"):
            t = t[4:]
        t = t.rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return json.loads(t[start:end + 1])


def _parse_code(text: str) -> str:
    """LLM 응답에서 파이썬 코드를 추출. 코드펜스가 있으면 벗겨낸다."""
    t = text.strip()
    if "```" in t:
        seg = t.split("```", 2)
        t = seg[1] if len(seg) > 1 else t
        for tag in ("python", "py"):
            if t.startswith(tag):
                t = t[len(tag):]
                break
        t = t.rsplit("```", 1)[0]
    return t.strip("\n")


def _code_defect(code: str, fn: str) -> str:
    """수리 결과를 채택하기 전의 최소 검사. 통과 못 하면 빈 문자열이 아닌 사유를 반환."""
    if not code.strip():
        return "빈 응답"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"문법 오류: {e}"
    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn
               for n in tree.body):
        return f"최상위에 def {fn}(...) 이 없다"
    return ""


def _computation_defect(run_dir: Path, code: str) -> str:
    """**답을 계산했는가, 적어 넣었는가.** 런이 code_rule.json 으로 요구할 때만 본다.

    왜 필요한가(실측 2026-09-03). 오케스트레이터가 텐서 분해를 다섯 판 내리 상수표로
    냈다. 인자행렬을 리터럴로 적고, 그것도 안 되면 영행렬을 할당해 놓고 채우지 못한 채
    끝냈다. 갈아타기 0 회. 계산 시간 600 초와 이어쓰기 자리를 알려준 뒤에도 같았다.

    그럴 만했다. 계약이 "인자행렬을 반환하라"이므로 표를 적어도 형식은 맞고, **계산을
    강제하는 것이 아무것도 없었다.** 심판은 출력만 보므로 어떻게 얻었는지 묻지 않는다.

    그래서 규칙을 하나 건다 -- 방법을 지시하는 것이 아니라 판의 규칙이다(외부
    라이브러리 금지와 같은 층). 답은 계산해서 내야 한다. 상수표도, 빈 배열도 아니다.
    mm333=22 처럼 아무도 모르는 값에서는 어차피 기억이 통하지 않으므로, 이 규칙이 무는
    자리는 외워서 넘길 수 있는 rung 뿐이다.

    무늬로 완전히 막을 수는 없다(뜻 없는 반복문을 끼워 넣으면 통과한다). 그래도 "표를
    적으면 그대로 채택된다"와 "적으면 반려된다"는 다르고, 판본 추적이 실제로 무엇을
    했는지 계속 찍는다."""
    rule_path = run_dir / "code_rule.json"
    if not rule_path.is_file():
        return ""
    try:
        rule = json.loads(rule_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    if not rule.get("require_computation"):
        return ""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import method_trace
        tags = method_trace.fingerprint(code)["tags"]
    except Exception:
        return ""                      # 추적기가 없으면 막지 않는다. 조용히 통과가 낫다
    blocked = {"상수표(계산 없음)", "할당만(계산 없음)", "골격/미완"}
    hit = sorted(set(tags) & blocked)
    if hit:
        return (f"계산하지 않았다({', '.join(hit)}). 이 런은 답을 **계산해서** 내야 한다 "
                f"-- 인자를 리터럴로 적거나 빈 배열을 반환하면 반려된다. "
                f"실질 호출이 하나도 없다")
    return ""


def _format_attempts(node: Node, limit: int = 8) -> str:
    """노드의 실패/수리 이력을 프롬프트용으로 편다. 이걸 읽혀야 같은 실패를 반복하지 않는다."""
    rows = []
    for a in node.attempts[-limit:]:
        ts = time.strftime("%m-%d %H:%M", time.localtime(a.get("ts", 0)))
        if "error" in a:
            rows.append(f"- [{ts}] 실행 중 예외: {a['error']}")
        elif "rejected" in a:
            rows.append(f"- [{ts}] verifier 가 거부: {a['rejected']}")
        elif "repaired_by" in a:
            rows.append(f"- [{ts}] 여기서 수리를 시도했다(모델 {a['repaired_by']}) "
                        f"-- 아래 '지금 코드'가 그 결과이고, 그래도 위 실패가 났다")
        elif "repair_rejected" in a:
            rows.append(f"- [{ts}] 수리안이 형식 검사에서 반려됨: {a['repair_rejected']}")
    return "\n".join(rows) or "(이력 없음)"


def _dep_snippets(plan: Plan, node: Node, run_dir: Path, limit: int = 1200) -> str:
    """선행 노드가 '실제로' 남긴 결과 JSON. 상상한 입력이 아니라 파일의 값을 보여준다."""
    out = []
    for d in node.deps:
        dep = plan.node(d)
        if not dep.result_ref:
            continue
        txt = (run_dir / dep.result_ref).read_text(encoding="utf-8")
        if len(txt) > limit:
            txt = txt[:limit] + "\n... (생략)"
        out.append(f"[inputs[\"{d}\"] 의 실제 값]\n{txt}")
    return "\n\n".join(out) or "(선행 노드 없음)"


def _read(run_dir: Path, rel: str) -> str:
    path = (run_dir / rel.split("#", 1)[0])
    return path.read_text(encoding="utf-8") if path.exists() else "(파일 없음)"


def repair_count(node: Node) -> int:
    """이 노드에 지금까지 몇 번 수리를 시도했는가(plan.json 에 남아 재개해도 이어진다)."""
    return sum(1 for a in node.attempts if "repaired_by" in a)


def _build_plan(problem: str, spec: dict) -> tuple:
    """LLM 스펙 -> (Plan, [(경로, 내용)]). 파일은 아직 쓰지 않는다 -- 검증을 통과한 계획만
    디스크에 남기기 위해서다(실패한 시도의 코드 조각이 런 디렉토리에 쌓이지 않게)."""
    nodes, files = [], []
    for nd in spec["nodes"]:
        nid = nd["id"]
        comp_rel, ver_rel = f"components/{nid}.py", f"components/{nid}_verify.py"
        files.append((comp_rel, nd["component_code"]))
        files.append((ver_rel, nd["verifier_code"]))
        nodes.append(Node(id=nid, goal=nd.get("goal", ""), deps=nd.get("deps", []),
                          component=comp_rel, verifier=ver_rel))
    return Plan(problem=problem, nodes=nodes, final=spec["final"]), files


def make_plan(problem: str, run_dir: str, pool=None, pool_id="planner", feedback: str = "",
              attempts: int = 3) -> dict:
    """문제 -> run 디렉토리에 plan.json + components/*.py 를 생성한다. 요약 dict 반환.
    pool 을 주입하면 그걸 쓰고(테스트), 없으면 환경 키로 build_pool.
    feedback 은 이전 계획이 왜 실패했는지(replan 시). 비어 있으면 최초 계획.

    계획 자체가 실패하면(JSON 파싱 불가, 필수 키 누락, 사이클·미정의 의존·final 부재) 그 사유를
    프롬프트에 되먹여 attempts 회까지 다시 시도한다. 이것이 없으면 계획 단계는 되먹임이 없는
    한 번뿐인 관문이 된다 -- 실행 실패는 수리로 이어지는데 계획 실패만 그대로 죽는다.
    실측(2026-09-01 벤치 h3): 명세가 길어 노드 코드가 길어지자 LLM 이 구조가 깨진 DAG 를 냈고,
    재시도 경로가 없어 런 전체가 planning_failed 로 끝났다. 문제는 풀 수 있는 것이었다.
    출력 계약이 'JSON 문자열 안에 코드를 이스케이프해 넣는' 형태라 코드가 길수록 깨지기 쉽다 --
    같은 이유로 repair_node 는 애초에 JSON 이 아니라 코드 한 덩어리를 받는다."""
    run_dir = Path(run_dir).resolve()
    (run_dir / "components").mkdir(parents=True, exist_ok=True)

    if pool is None:
        pool = llm_pool.build_pool()
    base = PLANNER_SYSTEM + "\n\n[문제]\n" + problem
    if feedback:
        base += "\n\n[이전 시도의 실패 기록]\n" + feedback

    history, label = [], None
    for i in range(1, max(1, attempts) + 1):
        prompt = base
        if history:
            prompt += ("\n\n[직전 응답이 거부된 이유 -- 같은 실수를 반복하지 마라]\n"
                       + "\n".join(f"- {h}" for h in history))
        text, label = llm_pool.call(pool, prompt, pool_id=pool_id)

        try:
            spec = _parse_plan_json(text)
            plan, files = _build_plan(problem, spec)
        except Exception as e:                                # noqa: BLE001
            history.append(f"{i}번째 응답을 계획으로 읽을 수 없었다 ({type(e).__name__}: {e}). "
                           f"설명·코드펜스 없이 지정된 JSON 하나만, 코드의 줄바꿈은 \\n 으로 "
                           f"이스케이프해서 출력하라.")
            continue

        errs = plan.validate()
        if errs:
            history.append(f"{i}번째 계획의 구조 오류: {'; '.join(errs)}")
            continue

        for rel, content in files:                            # 검증 통과 -> 이제 쓴다
            (run_dir / rel).write_text(content, encoding="utf-8")
        plan.save(run_dir / "plan.json")
        return {"status": "planned", "run_dir": str(run_dir), "nodes": [n.id for n in plan.nodes],
                "final": plan.final, "model": label, "planning_attempts": i,
                "planning_retries": history}

    return {"status": "invalid_plan", "errors": history, "model": label,
            "planning_attempts": max(1, attempts)}


def repair_node(run_dir: str, node_id: str, pool=None, pool_id="planner") -> dict:
    """실패한 노드 하나의 solve 코드를 실패 사유를 보고 다시 쓴다(verifier 는 건드리지 않는다).

    채택 전에 _code_defect 로 최소 검사를 하고, 통과 못 하면 파일을 덮어쓰지 않는다 --
    깨진 수리안이 그나마 돌던 코드를 지워버리면 재개 기반이 무너지기 때문이다.
    채택되면 status 를 pending 으로 되돌려 오케스트레이터가 다시 시도하게 한다."""
    run_dir = Path(run_dir).resolve()
    plan_path = run_dir / "plan.json"
    plan = Plan.load(plan_path)
    node = plan.node(node_id)

    if pool is None:
        pool = llm_pool.build_pool()

    prompt = (
        REPAIR_SYSTEM
        + "\n\n[원 문제]\n" + plan.problem
        + f"\n\n[이 노드]\nid: {node.id}\n목표: {node.goal}\n의존: {node.deps}"
        + "\n\n[지금 코드 (" + node.component + ")]\n" + _read(run_dir, node.component)
        + "\n\n[이 노드를 채점하는 verifier -- 읽기 전용, 고칠 수 없다 (" + node.verifier + ")]\n"
        + _read(run_dir, node.verifier)
        + "\n\n[선행 노드가 실제로 넘겨준 값]\n" + _dep_snippets(plan, node, run_dir)
        + "\n\n[실패 이력]\n" + _format_attempts(node)
    )
    text, label = llm_pool.call(pool, prompt, pool_id=pool_id)
    code = _parse_code(text)

    defect = _code_defect(code, "solve") or _computation_defect(run_dir, code)
    if defect:
        node.attempts.append({"ts": time.time(), "repair_rejected": defect, "model": label})
        plan.save(plan_path)
        return {"status": "repair_rejected", "node": node_id, "reason": defect, "model": label}

    # **덮어쓰기 전에 이전 판을 남긴다.** 남기지 않으면 "수리가 같은 알고리즘을 다듬은
    # 것인지, 아예 다른 알고리즘으로 갈아탄 것인지"를 나중에 잴 수 없다. 그 구별이
    # 이 장치로 무엇을 관측하는가의 핵심이다 -- 되먹임이 국소 수선만 하는 기계라면
    # 애초에 알려진 방법 밖으로 나갈 수 없다.
    prev = _snapshot_code(run_dir, node)
    (run_dir / node.component).write_text(code, encoding="utf-8")
    node.attempts.append({"ts": time.time(), "repaired_by": label, "prev_code": prev})
    node.status = "pending"
    plan.save(plan_path)
    return {"status": "repaired", "node": node_id, "model": label,
            "repairs": repair_count(node)}


def _snapshot_code(run_dir: Path, node) -> str:
    """수리 전 코드를 history/<노드>/rNN.py 로 보존하고 그 상대경로를 돌려준다."""
    src = run_dir / node.component
    if not src.is_file():
        return ""
    d = run_dir / "history" / node.id
    d.mkdir(parents=True, exist_ok=True)
    n = 1
    while (d / f"r{n:02d}.py").exists():
        n += 1
    dest = d / f"r{n:02d}.py"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return str(dest.relative_to(run_dir))


def plan_feedback(plan: Plan) -> str:
    """계획 전체가 왜 실패했는지 요약 -- replan 프롬프트에 그대로 들어간다."""
    lines = [f"[문제] {plan.problem}", "이전 계획의 노드별 결과:"]
    for n in plan.nodes:
        lines.append(f"- ({n.status}) {n.id}: {n.goal}")
        for a in n.attempts[-3:]:
            if "error" in a:
                lines.append(f"    예외: {a['error']}")
            elif "rejected" in a:
                lines.append(f"    verifier 거부: {a['rejected']}")
    lines.append("노드 코드를 고쳐도 통과하지 못했다. 같은 분해를 반복하지 말고 "
                 "다른 구조(다른 알고리즘·다른 노드 경계·더 단순한 단일 노드)로 다시 세워라.")
    return "\n".join(lines)


def _archive_attempt(run_dir: Path) -> int:
    """이전 plan/components/results 를 attempts/attemptN/ 으로 옮긴다(지우지 않는다).
    replan 은 노드 id 를 재사용할 수 있어서, 남아 있는 옛 결과를 새 계획이 주워 먹으면
    검증 없이 채택된 것처럼 보인다. 그래서 결과까지 통째로 치운다."""
    arch = run_dir / "attempts"
    arch.mkdir(exist_ok=True)
    n = 1
    while (arch / f"attempt{n}").exists():
        n += 1
    dest = arch / f"attempt{n}"
    dest.mkdir()
    for name in ("plan.json", "components", "results"):
        src = run_dir / name
        if src.exists():
            src.rename(dest / name)
    return n


def replan(run_dir: str, pool=None, pool_id="planner") -> dict:
    """노드 수리로 안 되는 경우의 승격: DAG 를 통째로 다시 세운다. 이전 시도는 보존된다."""
    run_dir = Path(run_dir).resolve()
    plan = Plan.load(run_dir / "plan.json")
    feedback = plan_feedback(plan)
    n = _archive_attempt(run_dir)
    res = make_plan(plan.problem, str(run_dir), pool=pool, pool_id=pool_id, feedback=feedback)
    res["replanned"] = True
    res["archived_as"] = f"attempts/attempt{n}"
    return res


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("problem", nargs="?", help="새 계획을 세울 문제(생략하면 --repair/--replan)")
    parser.add_argument("--repair", metavar="NODE_ID", help="실패한 노드 하나를 수리한다")
    parser.add_argument("--replan", action="store_true", help="계획 전체를 다시 세운다")
    args = parser.parse_args()
    if args.repair:
        out = repair_node(args.run_dir, args.repair)
    elif args.replan:
        out = replan(args.run_dir)
    elif args.problem:
        out = make_plan(args.problem, args.run_dir)
    else:
        parser.error("problem, --repair NODE_ID, --replan 중 하나가 필요하다")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
