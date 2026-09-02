"""
orchestrator_tool 회귀 테스트 -- LLM 없이 도구의 행동을 실측한다.

무엇을 지키려는가:
  1. 런 디렉토리 인자가 orchestrator/runs/ 밖으로 나가지 못한다(G014 와 같은 카나리).
     막히지 않으면 orchestrator_status 가 저장소 밖 파일을 읽고 orchestrator_stop 이
     무관한 프로세스를 죽인다.
  2. "백그라운드로 시작했다"가 실제로 도는 프로세스를 뜻한다. 이 저장소는 백그라운드로
     띄웠다고 보고했는데 아무것도 안 돌던 사고를 이미 겪었다(CLAUDE.md). 그래서 런을
     띄우고 끝까지 돌려서 최종 결과가 status 에 나오는지 본다.
  3. 죽은 런은 status 가 '미완이고 프로세스도 없다'고 정확히 말한다 -- 추측 대신 파일을
     읽어 보고하는 경로가 살아 있어야 한다.

LLM 은 쓰지 않는다. 계획을 손으로 깔아 둔 런을 resume_run 으로 돌리면 오케스트레이터가
그 DAG 를 실행/검증만 하므로 키 없이도 전 구간이 실측된다.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import orchestrator_tool as ot  # noqa: E402

FAILURES: list[str] = []

ESCAPES = ["../escaped", "../../etc/passwd", "sub/../../escaped", "/etc/passwd",
           "nested/dir/x", "", "."]


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def test_run_dir_cannot_escape() -> None:
    for canary in ESCAPES:
        try:
            resolved = ot._resolve_run_dir(canary)
        except ValueError:
            continue
        FAILURES.append(f"_resolve_run_dir({canary!r}) 가 막히지 않고 {resolved} 를 돌려줬다.")
    inside = ot._resolve_run_dir("20260101-000000")
    check(inside.parent == ot.RUNS_DIR.resolve(),
          f"정상 런 이름까지 막으면 도구를 못 쓴다: {inside}")
    # 도구가 돌려준 런 이름을 그대로 다시 넣었을 때 다른 런을 가리키면 안 된다 --
    # 정규화가 이름을 조용히 바꾸면 status/resume 이 엉뚱한 곳을 본다.
    for name in ("20260101-000000", "zztest-orchestrator-tool-ok"):
        check(ot._safe_run_name(name) == name,
              f"런 이름 {name!r} 이 정규화로 {ot._safe_run_name(name)!r} 로 바뀐다.")


def _plant_run(name: str, component: str, verifier: str) -> Path:
    """LLM 없이 돌릴 수 있는 한 노드짜리 런을 깔아 둔다."""
    run_dir = ot._resolve_run_dir(name)
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "components").mkdir(parents=True)
    (run_dir / "components" / "node.py").write_text(component, encoding="utf-8")
    (run_dir / "components" / "node_verify.py").write_text(verifier, encoding="utf-8")
    (run_dir / "plan.json").write_text(json.dumps({
        "problem": "테스트: 6 * 7 을 구하라",
        "final": "node",
        "nodes": [{"id": "node", "goal": "6*7", "deps": [],
                   "component": "components/node.py",
                   "verifier": "components/node_verify.py#check",
                   "status": "pending", "result_ref": "", "attempts": []}],
    }, ensure_ascii=False), encoding="utf-8")
    return run_dir


def _wait_done(run_dir: Path, timeout: float = 30.0) -> bool:
    """자식이 끝날 때까지 기다린다. 끝났으면 True.

    띄우지도 못한 런을 기다리며 timeout 을 통째로 태우지 않는다 -- tool_meta.json 에 pid 가
    없으면 시작 자체가 실패한 것이므로 즉시 False 다(실측: 이 구분이 없어서 테스트가
    아무것도 안 도는 런을 30초씩 두 번 기다리다 죽었다)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pid = ot._read_meta(run_dir).get("pid")
        if not pid:
            return False
        if not ot._alive(pid):
            return True
        time.sleep(0.2)
    return False


def test_background_run_actually_runs() -> None:
    run_dir = _plant_run(
        "zztest-orchestrator-tool-ok",
        "def solve(inputs):\n    return {'value': 6 * 7}\n",
        "def check(output, inputs):\n"
        "    ok = output.get('value') == 42\n"
        "    return ok, ('' if ok else 'value != 42')\n")
    try:
        started = ot.resume_run(run_dir.name)
        # 작은 런은 1초 안에 끝나므로 "시작했다"가 아니라 "바로 끝났다"로 올 수 있다.
        # 어느 쪽이든 시작 실패로 보고해서는 안 된다.
        check("실패:" not in started and "죽었다" not in started,
              f"런이 시작되지 않았다: {started}")
        check(_wait_done(run_dir), "런이 시간 안에 끝나지 않았다.")
        status = ot.run_status(run_dir.name)
        check("[OK] node" in status, f"검증된 노드가 status 에 안 보인다:\n{status}")
        check("풀렸다" in status, f"풀린 런을 풀렸다고 보고하지 않는다:\n{status}")
        check('"value": 42' in status or "'value': 42" in status,
              f"최종 결과가 status 에 안 실린다:\n{status}")
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_failed_run_is_reported_as_resumable() -> None:
    run_dir = _plant_run(
        "zztest-orchestrator-tool-fail",
        "def solve(inputs):\n    raise RuntimeError('일부러 터뜨림')\n",
        "def check(output, inputs):\n    return True, ''\n")
    try:
        ot.resume_run(run_dir.name)
        check(_wait_done(run_dir), "실패 런이 시간 안에 끝나지 않았다.")
        status = ot.run_status(run_dir.name)
        check("[실패] node" in status, f"실패한 노드를 실패로 보고하지 않는다:\n{status}")
        check("일부러 터뜨림" in status, f"실패 사유가 status 에 안 실린다:\n{status}")
        check("orchestrator_resume" in status,
              f"미완인데 재개 경로를 알려주지 않는다:\n{status}")
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_status_of_unknown_run() -> None:
    out = ot.run_status("없는런_" + str(int(time.time())))
    check(out.startswith("실패:"), f"없는 런을 있다고 답한다: {out}")


def main() -> int:
    for fn in (test_run_dir_cannot_escape, test_background_run_actually_runs,
               test_failed_run_is_reported_as_resumable, test_status_of_unknown_run):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("orchestrator_tool: 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
