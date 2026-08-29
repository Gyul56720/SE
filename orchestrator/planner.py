"""
플래너: 문제를 받아 DAG(plan.json + 노드별 solve/verify 코드)로 분해하는 최상위 계층.

이 계층이 가장 불안정하다(LLM 추론). 그래서 검증된 오케스트레이터 위에 얹혀, 엉뚱한 계획을
내도 각 노드의 verifier(신뢰)가 통과 안 시키면 채택되지 않는다 -- "제안이 아니라 검증된 채택".

역할 분배:
  플래너(여기)  : 문제를 하위 작업 DAG 로 쪼갠다. 단일 알고리즘이면 노드 1개, 복합이면
                 여러 노드(예: 인수분해 -> 소수별 계산 -> CRT). 각 노드의 solve/verify 코드도
                 생성한다.
  오케스트레이터 : 그 DAG 를 위상정렬로 실행하고 노드별 verifier 로 검증(orchestrator.py).
  verifier      : 무엇이 정답인지 판정(신뢰). 노드별 + 필요시 최종 조합.

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
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm_pool  # noqa: E402
from plan_schema import Plan, Node  # noqa: E402

PLANNER_SYSTEM = (
    "너는 문제를 푸는 알고리즘 파이프라인을 설계하는 플래너다. 주어진 문제를 하위 작업들의 "
    "DAG 로 분해하라. 단일 알고리즘으로 충분하면 노드 1개, 여러 알고리즘이 필요하면 의존 관계를 "
    "가진 여러 노드로 나눠라(예: 인수분해 -> 소수별 제곱근 -> CRT 결합).\n"
    "각 노드마다 solve(inputs: dict)->dict 파이썬 함수와, 그 출력을 '독립적으로' 검증하는 "
    "check(output: dict, inputs: dict)->(bool, str) 함수를 작성하라. inputs 에는 선행 노드 "
    "결과가 {dep_id: result} 로 들어온다. check 는 출력이 정말 맞는지 수학적으로/재계산으로 "
    "확인해야 한다(그냥 True 반환 금지).\n"
    "오직 아래 JSON 형식 하나만 출력하라(설명·코드펜스 금지):\n"
    '{"nodes":[{"id":"...","goal":"...","deps":[...],'
    '"component_code":"def solve(inputs):\\n    ...","verifier_code":"def check(output, inputs):\\n    ..."}],'
    '"final":"..."}'
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


def make_plan(problem: str, run_dir: str, pool=None, pool_id="planner") -> dict:
    """문제 -> run 디렉토리에 plan.json + components/*.py 를 생성한다. 요약 dict 반환.
    pool 을 주입하면 그걸 쓰고(테스트), 없으면 환경 키로 build_pool."""
    run_dir = Path(run_dir).resolve()
    (run_dir / "components").mkdir(parents=True, exist_ok=True)

    if pool is None:
        pool = llm_pool.build_pool()
    prompt = PLANNER_SYSTEM + "\n\n[문제]\n" + problem
    text, label = llm_pool.call(pool, prompt, pool_id=pool_id)
    spec = _parse_plan_json(text)

    nodes = []
    for nd in spec["nodes"]:
        nid = nd["id"]
        comp_rel = f"components/{nid}.py"
        ver_rel = f"components/{nid}_verify.py"
        (run_dir / comp_rel).write_text(nd["component_code"], encoding="utf-8")
        (run_dir / ver_rel).write_text(nd["verifier_code"], encoding="utf-8")
        nodes.append(Node(id=nid, goal=nd.get("goal", ""), deps=nd.get("deps", []),
                          component=comp_rel, verifier=ver_rel))

    plan = Plan(problem=problem, nodes=nodes, final=spec["final"])
    errs = plan.validate()
    if errs:
        return {"status": "invalid_plan", "errors": errs, "model": label}
    plan.save(run_dir / "plan.json")
    return {"status": "planned", "run_dir": str(run_dir), "nodes": [n.id for n in nodes],
            "final": plan.final, "model": label}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("problem")
    args = parser.parse_args()
    print(json.dumps(make_plan(args.problem, args.run_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
