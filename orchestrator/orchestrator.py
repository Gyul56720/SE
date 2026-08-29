"""
오케스트레이터: plan.json(DAG)을 실행하는 신뢰 가능한 실행 기반.

플래너(LLM)가 아니라 이 실행기가 substrate 다. 플래너는 이 위에 얹혀 plan.json 을 만들 뿐,
'무엇이 정답인가'는 각 노드의 verifier(신뢰)가 정한다. 그래서 플래너가 엉뚱한 계획을 내도
검증 안 된 결과는 채택되지 않는다 -- 이 저장소의 "제안이 아니라 검증된 채택" 원칙 그대로.

실행 규칙:
  - 위상정렬 순으로, 의존이 모두 verified 인 노드를 solve 한다.
  - 각 노드: component.solve(inputs) -> output 을 실행하고, verifier.check(output, inputs)
    로 검증한다. 통과해야 status=verified 로 확정하고 결과를 파일로 저장한다.
  - 실패하면 status 는 pending/failed 로 두고 attempts 에 사유를 남긴다(같은 실패 반복 방지).
  - 매 노드 처리 후 plan.json 을 즉시 저장한다 -> 프로세스가 죽어도 재시작 시 verified 노드를
    건너뛰고 이어서 재개(복원). git 커밋까지 하면 VM 회수도 견딘다.

component/verifier 계약:
  component 파일: def solve(inputs: dict) -> dict
  verifier 파일: def check(output: dict, inputs: dict) -> tuple[bool, str]
  (경로는 런 디렉토리 기준. verifier 는 "파일.py#함수명" 또는 "파일.py"(기본 check).)

안전: verifier 는 신뢰 대상이다. 노드 verifier 가 신뢰할 수 있어야 그 노드 결과도 신뢰된다.
자가 수정 실험처럼 verifier 무결성이 걸린 경우엔 gatekeeper(G008/G009/G010)와 함께 쓴다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

from plan_schema import Plan


def _load_callable(run_dir: Path, spec_str: str, default_fn: str):
    """"파일.py#함수" 또는 "파일.py" 를 로드해 (함수) 반환."""
    if "#" in spec_str:
        rel, fn = spec_str.split("#", 1)
    else:
        rel, fn = spec_str, default_fn
    path = (run_dir / rel).resolve()
    mod_name = f"_orch_{path.stem}_{fn}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, fn)


def _gather_inputs(plan: Plan, node, run_dir: Path) -> dict:
    """선행 노드들의 저장된 결과를 {dep_id: result} 로 모은다."""
    inputs = {}
    for d in node.deps:
        dep = plan.node(d)
        if dep.result_ref:
            inputs[d] = json.loads((run_dir / dep.result_ref).read_text(encoding="utf-8"))
    return inputs


def run_plan(run_dir: str, max_rounds: int = 100) -> dict:
    run_dir = Path(run_dir).resolve()
    plan_path = run_dir / "plan.json"
    plan = Plan.load(plan_path)
    errs = plan.validate()
    if errs:
        return {"status": "invalid_plan", "errors": errs}

    (run_dir / "results").mkdir(parents=True, exist_ok=True)

    for _ in range(max_rounds):
        ready = plan.ready_nodes()
        if not ready:
            break
        progressed = False
        for nid in ready:
            node = plan.node(nid)
            inputs = _gather_inputs(plan, node, run_dir)
            try:
                solve = _load_callable(run_dir, node.component, "solve")
                output = solve(inputs)
            except Exception as e:
                node.attempts.append({"ts": time.time(), "error": f"solve: {e}"})
                node.status = "failed"
                plan.save(plan_path)
                continue
            try:
                verify = _load_callable(run_dir, node.verifier, "check")
                ok, msg = verify(output, inputs)
            except Exception as e:
                node.attempts.append({"ts": time.time(), "error": f"verify: {e}"})
                node.status = "failed"
                plan.save(plan_path)
                continue

            if ok:
                ref = f"results/{nid}.json"
                (run_dir / ref).write_text(json.dumps(output, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
                node.result_ref = ref
                node.status = "verified"
                progressed = True
            else:
                node.attempts.append({"ts": time.time(), "rejected": msg})
                node.status = "failed"
            plan.save(plan_path)
        if not progressed:
            break

    final = plan.node(plan.final)
    done = final.status == "verified"
    return {
        "status": "solved" if done else "incomplete",
        "final": plan.final,
        "final_result": (json.loads((run_dir / final.result_ref).read_text()) if done else None),
        "node_status": {n.id: n.status for n in plan.nodes},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    args = parser.parse_args()
    print(json.dumps(run_plan(args.run_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
