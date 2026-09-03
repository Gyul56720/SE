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

# 언어 기본 살림. 이것만으로는 방법을 말할 수 없으므로 지문에서 뺀다.
TRIVIAL = {
    "range", "len", "list", "dict", "tuple", "set", "sorted", "reversed", "enumerate",
    "zip", "map", "filter", "sum", "abs", "max", "min", "round", "int", "float", "str",
    "print", "append", "extend", "insert", "pop", "items", "keys", "values", "get",
    "copy", "join", "split", "strip", "format", "update", "add", "isinstance", "any",
    "all", "Fraction", "loads", "dumps", "read_text", "write_text", "open", "super",
}

# 배열을 만들거나 모양을 바꾸는 것뿐인 호출. **이것만 있으면 방법이 아니다.**
# 실측(2026-09-03, tensorrank mm333=22): 판본이 np.zeros 하나만 부르는데 추적기가
# "미분류 -- 알려진 갈래 밖" 이라고 찍었다. 실제로는 23x9 영행렬을 할당해 놓고 채우지
# 못한 것이었다. 상수표를 걸러냈더니 이번에는 **빈 배열**이 같은 자리로 새어 들어왔다.
ALLOC = {
    "zeros", "ones", "empty", "full", "array", "asarray", "zeros_like", "ones_like",
    "empty_like", "full_like", "arange", "linspace", "eye", "identity", "reshape",
    "ravel", "flatten", "tolist", "astype", "deepcopy", "fromiter", "transpose", "T",
}

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
    funcs, assigned = set(), set()
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
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            assigned.add(n.id)
    calls.discard("")

    # **지역에서 만든 이름과 언어 기본 살림은 방법이 아니다.** 이것을 안 걷어내면
    # 도우미 함수 이름이 바뀐 것만으로 "갈아타기"가 뜬다 -- 실측(2026-09-03)에서
    # get_mm222/get_mm333/get_w_state 라는 지역 함수 세 개가 등장한 것을 방법이
    # 통째로 바뀐 것으로 읽었다. 실제로는 상수표를 적어넣은 것이었다.
    sig = {c for c in calls
           if c.split(".")[-1] not in TRIVIAL
           and c not in funcs and c.split(".")[0] not in (funcs | assigned)}
    recursive = sorted(f for f in funcs if f in calls)
    tags = sorted(k for k, pat in MARKERS.items()
                  if any(p.lower() in c.lower() for c in sig for p in pat))
    if not tags:
        # **"미분류"가 두 가지를 뭉치고 있었다.** 알려진 갈래 밖의 새 방법과, 아예
        # 방법이 없는 것(상수표를 그대로 적어넣기)은 완전히 다른 사건이다. 후자는
        # 탐색이 아니라 기억이고, 아무도 모르는 값(<3,3,3> 의 22)에는 쓸 수 없다.
        dense = counts["num"] >= 30 and not counts["while"]
        alloc_only = bool(sig) and all(c.split(".")[-1] in ALLOC for c in sig)
        tags = ["상수표(계산 없음)"] if (not sig and dense) else \
               ["골격/미완"] if not sig else \
               ["할당만(계산 없음)"] if alloc_only else ["미분류"]
    return {"calls": calls, "sig": sig, "imports": imports, "counts": counts,
            "recursive": recursive, "tags": tags,
            "lines": len([l for l in src.splitlines() if l.strip()])}


def _dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}".lstrip(".")
    return ""


def distance(a: dict, b: dict) -> float:
    """**실질 호출** 집합의 자카드 거리. 상수만 바뀌면 0, 방법이 갈리면 1 에 가깝다.

    지역 함수 이름과 언어 기본 살림(range, len, append ...)은 빼고 잰다. 그것까지
    세면 도우미 함수 이름만 바꿔도 거리가 1 이 나온다."""
    x, y = a.get("sig") or set(), b.get("sig") or set()
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
    # 양쪽 다 실질 호출이 없으면 거리가 0 으로 나온다 -- 잴 것이 없기 때문이지 같아서가
    # 아니다. 골격에서 상수표로 간 것을 "다듬기"라 부르면 거짓말이다.
    if not (prev.get("sig") or fp.get("sig")):
        return "성격 변화" if set(prev["tags"]) != set(fp["tags"]) else "다듬기"
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
                     "nums": fp.get("counts", {}).get("num", 0),
                     "calls": sorted(fp["sig"]), "counts": fp.get("counts", {}),
                     "new_calls": sorted(fp["sig"] - prev["sig"]) if prev else [],
                     "gone_calls": sorted(prev["sig"] - fp["sig"]) if prev else []})
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
    print(f"{'판본':22} {'거리':>6}  {'구분':12} {'줄':>4} {'상수':>5}  갈래")
    for r in res["versions"]:
        d = "  -  " if r["dist"] is None else f"{r['dist']:.3f}"
        print(f"{r['name']:22} {d:>6}  {r['kind']:12} {r['lines']:>4} {r['nums']:>5}  "
              f"{', '.join(r['tags'])}")
        if r["new_calls"] or r["gone_calls"]:
            if r["new_calls"]:
                print(f"{'':22} + {', '.join(r['new_calls'][:8])}")
            if r["gone_calls"]:
                print(f"{'':22} - {', '.join(r['gone_calls'][:8])}")
        if a.calls:
            print(f"{'':22}   호출: {', '.join(r['calls'])}")
    print(f"\n갈아타기 {res['n_jumps']}회 · 등장한 갈래: {', '.join(res['families'])}")
    if "미분류" in res["families"]:
        print("'미분류' 는 실질 호출이 있는데 알려진 갈래에 안 걸린 것이다 -- 그쪽이 흥미롭다")
    if "할당만(계산 없음)" in res["families"]:
        print("'할당만(계산 없음)' 도 방법이 없는 것이다. 배열을 만들어 놓고 채우지 "
              "못한 것이므로 미분류로 세면 안 된다")
    if "상수표(계산 없음)" in res["families"]:
        print("'상수표(계산 없음)' 는 방법이 없는 것이다. 답을 적어넣은 것이지 찾은 것이 "
              "아니므로, 아무도 모르는 값에는 쓸 수 없다 -- 탐색이 아니라 기억이다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
