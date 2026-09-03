"""런 하나가 **실제로 탐색하고 있는지** 증거를 모아 보여준다. 표준 라이브러리만 쓴다.

왜 필요한가. 로그에 "라운드 4" 라고 찍혀도 그것은 네 번 시도했다는 뜻일 뿐이다.
같은 답을 네 번 상수로 적어 넣은 것과, 네 번 다른 알고리즘을 돌려본 것이 같은 숫자로
보인다. 실측(2026-09-03)으로 다섯 번 내리 상수로 적어 넣은 런이 있었고, 로그만 봐서는
구별할 수 없었다.

그래서 "계산했다"는 주장을 뒷받침할 수 있는 것만 모은다.

  코드 구조   실질 호출이 있는가. 반복문과 난수가 있는가 (ast 로 본다)
  실행 시간   노드가 예산을 다 쓴 흔적이 있는가. 즉시 반환했으면 계산하지 않았다
  scratch     시도 사이에 파일을 남기고 있는가. 남기면 이어서 계산하는 것이다
  버전 변화   시도마다 방법이 바뀌는가, 숫자만 바뀌는가
  기각 사유   심판이 무엇을 문제라고 했는가

증거가 없으면 **"판정 불가"** 라고 말한다. "아마 탐색 중"이라고 말하지 않는다 --
모르는데 안다고 말하는 것이 이 저장소에서 가장 많이 고친 버그다.

    python3 tools/run_status.py                    # 최신 런
    python3 tools/run_status.py <런 디렉토리>
    python3 tools/run_status.py --watch 60         # 60초마다 다시
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "orchestrator"))


def latest_run(pattern: str = "tensorrank-*") -> Path | None:
    runs = sorted((REPO / "orchestrator" / "runs").glob(pattern),
                  key=lambda p: p.stat().st_mtime if p.exists() else 0)
    return runs[-1] if runs else None


def _age(ts: float) -> str:
    d = max(0.0, time.time() - ts)
    if d < 90:
        return f"{d:.0f}초 전"
    if d < 5400:
        return f"{d / 60:.0f}분 전"
    return f"{d / 3600:.1f}시간 전"


def _procs() -> list:
    """돌고 있는 관련 프로세스. pgrep 이 없으면 빈 목록."""
    try:
        out = subprocess.run(["pgrep", "-af", "problems/.*/run.py"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [l for l in out.splitlines() if l.strip()]


def code_evidence(src: str) -> dict:
    """계산했다는 주장을 뒷받침하는 구조 지표. 없으면 없다고 말한다."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}
    loops = whiles = randoms = 0
    biggest = 0
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.AsyncFor)):
            loops += 1
        elif isinstance(n, ast.While):
            whiles += 1
        elif isinstance(n, ast.Call):
            name = ""
            f = n.func
            while isinstance(f, ast.Attribute):
                name = f.attr
                f = f.value
            if isinstance(f, ast.Name) and not name:
                name = f.id
            if name in ("random", "randint", "randn", "choice", "shuffle",
                        "uniform", "normal", "sample", "permutation"):
                randoms += 1
        elif isinstance(n, ast.Constant) and isinstance(n.value, int):
            biggest = max(biggest, n.value)
    try:
        import method_trace
        fp = method_trace.fingerprint(src)
        tags, sig = fp["tags"], sorted(fp["sig"])
    except Exception:
        tags, sig = ["(추적기 없음)"], []
    return {"loops": loops, "whiles": whiles, "randoms": randoms,
            "biggest_int": biggest, "tags": tags, "sig": sig,
            "lines": len([l for l in src.splitlines() if l.strip()])}


def scratch_evidence(run_dir: Path) -> dict:
    """scratch 에 무엇을 남겼는가. 남겼으면 시도 사이에 이어서 계산하는 것이다."""
    d = run_dir / "scratch"
    if not d.is_dir():
        return {"exists": False, "files": []}
    files = [(p.relative_to(d), p.stat().st_size, p.stat().st_mtime)
             for p in sorted(d.rglob("*")) if p.is_file()]
    return {"exists": True, "files": files,
            "total": sum(s for _, s, _ in files)}


def plan_evidence(run_dir: Path) -> dict:
    """노드 상태, 시도 횟수, 예산 초과 흔적, 마지막 기각 사유."""
    path = run_dir / "plan.json"
    if not path.is_file():
        return {"error": "plan.json 이 없다"}
    plan = json.loads(path.read_text(encoding="utf-8"))
    nodes = []
    for n in plan.get("nodes", []):
        atts = n.get("attempts", [])
        budget_hits = sum(1 for a in atts
                          if "예산" in str(a.get("error", "")) and "초과" in str(a.get("error", "")))
        rejects = [a["rejected"] for a in atts if a.get("rejected")]
        errors = [a["error"] for a in atts if a.get("error")]
        nodes.append({"id": n.get("id"), "status": n.get("status"),
                      "verifier": n.get("verifier"), "component": n.get("component"),
                      "n_attempts": len(atts), "budget_hits": budget_hits,
                      "last_reject": rejects[-1] if rejects else None,
                      "last_error": errors[-1] if errors else None,
                      "is_final": n.get("id") == plan.get("final")})
    return {"final": plan.get("final"), "nodes": nodes}


def verdict(run_dir: Path, plan: dict, scratch: dict, evid: dict) -> list:
    """증거를 모아 한 줄로 판정한다. 증거가 없으면 판정 불가라고 말한다."""
    out = []
    tags = set(evid.get("tags") or [])
    no_method = tags & {"계산 없음(상수로 적음)", "계산 없음(빈 배열만)", "미완성(내용 없음)"}
    computes = bool(evid.get("sig")) and not no_method

    if no_method:
        out.append(f"**계산하지 않는다** -- 최종 코드가 '{', '.join(sorted(no_method))}' 로 "
                   f"분류된다. 답을 적어 넣은 것이지 찾은 것이 아니다")
    elif computes:
        out.append(f"**계산은 한다** -- 실질 호출 {len(evid['sig'])}개, 반복문 "
                   f"{evid['loops']}+{evid['whiles']}개, 난수 {evid['randoms']}회")
    else:
        out.append("판정 불가 -- 최종 노드 코드를 읽지 못했다")

    budget = sum(n["budget_hits"] for n in plan.get("nodes", []))
    if budget:
        out.append(f"실행 시간을 다 쓴 흔적 {budget}회 -- 즉시 반환하지 않고 오래 돌았다")
    elif computes:
        out.append("실행 시간을 다 쓴 흔적은 없다 -- 계산이 짧게 끝난다는 뜻이다")

    if scratch["exists"] and scratch["files"]:
        out.append(f"scratch 에 파일 {len(scratch['files'])}개({scratch['total']}바이트) -- "
                   f"시도 사이에 이어서 계산하고 있다")
    elif scratch["exists"]:
        out.append("scratch 가 비어 있다 -- 매 시도가 처음부터 다시 시작한다")

    return out


def report(run_dir: Path) -> int:
    print("=" * 78)
    print(f"런  {run_dir}")
    print(f"    마지막 변화 {_age(run_dir.stat().st_mtime)}")
    procs = _procs()
    print(f"    프로세스 {len(procs)}개" + ("" if procs else "  (끝났거나 죽었다)"))
    for p in procs:
        print(f"      {p[:110]}")

    print("-" * 78)
    print("[규칙이 걸려 있는가]")
    rule = run_dir / "code_rule.json"
    print(f"    계산 강제(code_rule.json)  {'있다' if rule.is_file() else '**없다**'}")
    scratch = scratch_evidence(run_dir)
    print(f"    이어쓰기 자리(scratch/)    {'있다' if scratch['exists'] else '**없다**'}")
    plan = plan_evidence(run_dir)
    if "error" in plan:
        print(f"    plan.json: {plan['error']}")
        return 1
    fin = next((n for n in plan["nodes"] if n["is_final"]), None)
    v = (fin or {}).get("verifier")
    ok_v = bool(v and v.startswith("verifiers/"))
    print(f"    주입 심판                  {v}  {'' if ok_v else '<-- **주입본이 아니다**'}")

    print("-" * 78)
    print("[진행]")
    for n in plan["nodes"]:
        mark = " (최종)" if n["is_final"] else ""
        print(f"    {n['id']}{mark}: {n['status']}, 시도 {n['n_attempts']}회"
              + (f", 예산 초과 {n['budget_hits']}회" if n["budget_hits"] else ""))
        if n["last_reject"]:
            for line in str(n["last_reject"]).split(" | "):
                print(f"        기각: {line[:150]}")
        if n["last_error"]:
            print(f"        오류: {str(n['last_error'])[:150]}")

    print("-" * 78)
    print("[탐색 증거 -- 최종 노드 코드]")
    comp = run_dir / ((fin or {}).get("component") or "")
    evid = {}
    if comp.is_file():
        evid = code_evidence(comp.read_text(encoding="utf-8", errors="replace"))
        if "error" in evid:
            print(f"    {evid['error']}")
        else:
            print(f"    {comp.name}  {evid['lines']}줄")
            print(f"    분류      {', '.join(evid['tags'])}")
            print(f"    실질 호출  {', '.join(evid['sig']) or '(없음)'}")
            print(f"    반복문    for {evid['loops']}개, while {evid['whiles']}개"
                  f"   난수 {evid['randoms']}회   가장 큰 정수 {evid['biggest_int']}")
    else:
        print(f"    최종 노드 코드를 못 찾았다: {comp}")

    if scratch["exists"] and scratch["files"]:
        print("-" * 78)
        print("[scratch -- 시도 사이에 남긴 것]")
        for rel, size, mt in scratch["files"][:12]:
            print(f"    {str(rel):40} {size:>10}바이트  {_age(mt)}")

    print("-" * 78)
    print("[버전 변화]")
    try:
        import method_trace
        rows = method_trace.report(run_dir)["versions"]
    except Exception as e:
        rows = []
        print(f"    추적 실패: {type(e).__name__}: {e}")
    for r in rows:
        d = "  -  " if r["dist"] is None else f"{r['dist']:.3f}"
        print(f"    {r['name']:26} 거리 {d:>6}  {r['kind']:14} {', '.join(r['tags'])}")
        if r["new_calls"]:
            print(f"    {'':26} + {', '.join(r['new_calls'][:6])}")
    if not rows:
        print("    버전이 없다 -- 수리가 한 번도 돌지 않았다")

    print("=" * 78)
    print("[판정]")
    for line in verdict(run_dir, plan, scratch, evid):
        print(f"  · {line}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="런이 실제로 탐색 중인지 증거를 모은다")
    ap.add_argument("run_dir", nargs="?", default=None, help="비우면 최신 런")
    ap.add_argument("--pattern", default="tensorrank-*", help="최신 런을 찾을 이름 패턴")
    ap.add_argument("--watch", type=float, default=0, help="N초마다 다시 (0=한 번)")
    a = ap.parse_args()

    while True:
        run_dir = Path(a.run_dir).resolve() if a.run_dir else latest_run(a.pattern)
        if run_dir is None or not run_dir.is_dir():
            print(f"런을 못 찾았다 (패턴 {a.pattern})", file=sys.stderr)
            return 1
        rc = report(run_dir)
        if a.watch <= 0:
            return rc
        print(f"\n({a.watch:.0f}초 뒤 다시 -- Ctrl-C 로 나감)\n")
        try:
            time.sleep(a.watch)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
