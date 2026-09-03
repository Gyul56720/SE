"""수리 판본들이 **같은 알고리즘을 다듬은 것인지, 다른 알고리즘으로 갈아탄 것인지** 잰다.

왜 이것을 재는가. 되먹임 루프가 국소 수선만 하는 기계라면 -- 상수를 바꾸고 반복 횟수를
늘리는 정도라면 -- 애초에 알려진 방법 밖으로 나갈 수 없다. 반대로 판본 사이에서 호출하는
함수 집합 자체가 바뀐다면(최소제곱 -> 무작위 탐색 -> 완전 열거 -> 대수적 구성), 그것은
탐색이 방법의 공간에서 움직이고 있다는 뜻이다. **알고리즘 점프**라고 부를 만한 사건은
이것이고, 이 파일은 그것이 실제로 일어나는지만 본다.

LLM 을 쓰지 않는다. ast 로 지문을 뜬다:

    호출 이름   ast.Call 의 함수 이름을 점 표기로 (np.linalg.lstsq, itertools.product, ...)
    수입 모듈   import 문
    구조        for / while / 내포 / 재귀 / try 의 개수
    상수        숫자 리터럴 개수

두 판본의 거리는 **호출 이름 집합의 자카드 거리**로 잰다. 상수만 바뀐 판본은 거리 0 이고
호출 집합이 갈리면 1 에 가까워진다. 이것이 "다듬기"와 "갈아타기"를 가르는 기준이다.

표지(marker)는 서술을 위한 것이지 판정 기준이 아니다. 어느 갈래에도 안 걸리는 판본이
나오는 것이 오히려 이 실험이 바라는 결과다 -- 알려진 네 갈래 밖이라는 뜻이므로.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

# 서술용 표지. 여기 없는 것이 나오면 "미분류"로 남긴다 -- 그것이 흥미로운 쪽이다.
MARKERS = {
    "선형대수/최소제곱": ("lstsq", "pinv", "solve", "svd", "eig", "eigh", "qr", "inv", "det"),
    "반복 최적화": ("normal", "randn", "gradient", "grad", "step", "lr", "descent", "als"),
    "무작위 탐색": ("random", "randint", "choice", "shuffle", "uniform", "sample", "seed"),
    "완전 열거": ("product", "permutations", "combinations", "chain"),
    "충족/기호계산": ("sympy", "Symbol", "groebner", "satisfiable", "z3", "Poly", "nsolve"),
}


def fingerprint(src: str) -> dict:
    """소스 하나의 구조 지문. 파싱 실패면 오류만 남긴다."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}", "calls": set(), "imports": set()}

    calls, imports, counts = set(), set(), {"for": 0, "while": 0, "comp": 0,
                                            "try": 0, "def": 0, "num": 0}
    funcs = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            calls.add(_dotted(n.func))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            imports.add(getattr(n, "module", None) or
                        ",".join(a.name for a in n.names))
        elif isinstance(n, (ast.For, ast.AsyncFor)):
            counts["for"] += 1
        elif isinstance(n, ast.While):
            counts["while"] += 1
        elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            counts["comp"] += 1
        elif isinstance(n, ast.Try):
            counts["try"] += 1
        elif isinstance(n, ast.FunctionDef):
            counts["def"] += 1
            funcs.add(n.name)
        elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            counts["num"] += 1
    calls.discard("")
    recursive = sorted(f for f in funcs if f in calls)
    tags = sorted(k for k, pat in MARKERS.items()
                  if any(p.lower() in c.lower() for c in calls for p in pat))
    return {"calls": calls, "imports": imports, "counts": counts,
            "recursive": recursive, "tags": tags or ["미분류"],
            "lines": len([l for l in src.splitlines() if l.strip()])}


def _dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}".lstrip(".")
    return ""


def distance(a: dict, b: dict) -> float:
    """호출 이름 집합의 자카드 거리. 상수만 바뀌면 0, 방법이 갈리면 1 에 가깝다."""
    x, y = a.get("calls") or set(), b.get("calls") or set()
    if not x and not y:
        return 0.0
    return 1.0 - len(x & y) / len(x | y)


def versions(run_dir) -> list:
    """수리 판본을 시간순으로. history/<노드>/rNN.py 가 옛 판본, components/ 가 현재."""
    run_dir = Path(run_dir)
    out = []
    for hist in sorted((run_dir / "history").glob("*/r*.py")) if (run_dir / "history").is_dir() else []:
        out.append((f"{hist.parent.name}:{hist.stem}", hist))
    for cur in sorted((run_dir / "components").glob("*.py")) if (run_dir / "components").is_dir() else []:
        if not cur.name.endswith("_verify.py"):
            out.append((f"{cur.stem}:현재", cur))
    return out


def classify(prev: dict, fp: dict, d: float,
             jump_at: float = 0.75, near: float = 0.5, tweak_at: float = 0.2) -> str:
    """거리만으로 가르면 눈금이 거칠다. 호출이 두 개뿐인 프로그램에 하나가 추가되면
    자카드 거리가 0.5 인데, 그것은 방법이 바뀐 것이 아니라 보조 계산이 붙은 것이다.

    그래서 **갈래가 바뀌었는지**를 같이 본다. 거리가 크면서 갈래도 갈렸을 때만
    갈아타기로 부른다. 갈래가 같은 채로 호출만 늘면 부분 교체다."""
    if d is None:
        return "첫 판"
    if d >= jump_at or (d >= near and set(prev["tags"]) != set(fp["tags"])):
        return "**갈아타기**"
    return "다듬기" if d < tweak_at else "부분 교체"


def report(run_dir, **kw) -> dict:
    rows, prev = [], None
    for name, path in versions(run_dir):
        fp = fingerprint(path.read_text(encoding="utf-8", errors="replace"))
        d = None if prev is None else distance(prev, fp)
        kind = classify(prev, fp, d, **kw)
        rows.append({"name": name, "path": str(path), "dist": d, "kind": kind,
                     "tags": fp["tags"], "lines": fp["lines"],
                     "calls": sorted(fp["calls"]), "counts": fp.get("counts", {}),
                     "new_calls": sorted(fp["calls"] - prev["calls"]) if prev else [],
                     "gone_calls": sorted(prev["calls"] - fp["calls"]) if prev else []})
        prev = fp
    jumps = [r for r in rows if r["kind"] == "**갈아타기**"]
    return {"versions": rows, "n_jumps": len(jumps),
            "families": sorted({t for r in rows for t in r["tags"]})}


def main() -> int:
    ap = argparse.ArgumentParser(description="수리 판본 사이의 알고리즘 점프를 잰다")
    ap.add_argument("run_dir")
    ap.add_argument("--calls", action="store_true", help="판본마다 호출 이름을 전부 찍는다")
    a = ap.parse_args()
    res = report(a.run_dir)
    if not res["versions"]:
        print("판본이 없다 -- 수리가 한 번도 돌지 않았거나 history/ 가 비었다")
        return 1
    print(f"{'판본':22} {'거리':>6}  {'구분':12} {'줄':>4}  갈래")
    for r in res["versions"]:
        d = "  -  " if r["dist"] is None else f"{r['dist']:.3f}"
        print(f"{r['name']:22} {d:>6}  {r['kind']:12} {r['lines']:>4}  {', '.join(r['tags'])}")
        if r["new_calls"] or r["gone_calls"]:
            if r["new_calls"]:
                print(f"{'':22} + {', '.join(r['new_calls'][:8])}")
            if r["gone_calls"]:
                print(f"{'':22} - {', '.join(r['gone_calls'][:8])}")
        if a.calls:
            print(f"{'':22}   호출: {', '.join(r['calls'])}")
    print(f"\n갈아타기 {res['n_jumps']}회 · 등장한 갈래: {', '.join(res['families'])}")
    if "미분류" in res["families"]:
        print("'미분류' 는 알려진 네 갈래 어디에도 안 걸린 판본이다 -- 그쪽이 흥미롭다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
