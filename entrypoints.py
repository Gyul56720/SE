"""entrypoints -- 진입점을 **세어서 찾는다.** 목록을 손으로 적지 않는다.

사용자(2026-09-11): "배선 읽기점검이 하드코딩되면 안 된다고. 어떻게 해결할까 이런 문제를?"

맞는 지적이다. `improve/run.py` 가 `ModuleNotFoundError: No module named 'plan'` 로 죽었을 때
내가 한 고침은 **손으로 적은 목록**이었다 -- 어느 파일이 뿌리를 넣어야 하는지, 어느 진입점을
돌려 볼지. 그러면 **내일 새 모듈이 생기면 같은 병이 다시 난다.** 사람이 목록에 또 적어야 하니까.

그래서 목록을 없애고 **코드가 저장소를 읽어 스스로 세게** 한다.

  진입점  -- `if __name__ == "__main__"` 이 있는 파일 (ast 로 찾는다)
  깃발    -- 그 파일이 `add_argument("--…")` 로 선언한 것 전부 (ast 로 읽는다)
  늦은임포트 -- **함수 안에서** 남의 꾸러미를 임포트하는 자리 (이것이 사고의 꼴이었다 --
             모듈을 임포트할 땐 안 터지고, 그 갈래를 **실제로 밟을 때만** 터진다)
             뿌리에 있는 파일은 세지 않는다 -- 거기선 스크립트 디렉터리가 곧 뿌리라 본디 안전하다
  부르는자리 -- 저장소 어디에서 그 진입점을 어떻게 부르는가 (`python3 a/b.py` 인가 `-m a.b` 인가)

## 사고의 뿌리와 두 가지 고침

파이썬은 **스크립트의 디렉터리**를 sys.path[0] 에 넣는다. `python3 improve/run.py` 는
sys.path[0] 이 `improve/` 다 -- 뿌리가 아니라서 `from plan import …` 가 죽는다.

  구조로 없애기 -- `python3 -m improve.run` 으로 부르면 sys.path[0] 이 **cwd(뿌리)** 다.
                 그러면 뿌리를 넣는 줄이 아예 필요 없다. 병이 생길 자리가 없어진다.
  검사로 잡기   -- 스크립트 꼴로 부를 거면 그 파일이 뿌리를 sys.path 에 넣어야 한다.

둘 중 하나면 안전하다. `안전한가()` 가 그 둘을 본다 -- **어느 파일인지는 안 적는다.**

    python3 entrypoints.py            # 진입점·깃발·위험을 센다
    python3 entrypoints.py --위험만   # 안전하지 않은 것만. 끝값 1 이면 위험이 있다
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
_건너뜀 = {".git", "venv", "__pycache__", "node_modules", "inbox"}


def 꾸러미들(repo: Path) -> "set[str]":
    """저장소의 꼭대기 이름들 -- 디렉터리 꾸러미와 뿌리의 .py 모듈."""
    out = set()
    for p in repo.iterdir():
        if p.is_dir() and (p / "__init__.py").is_file() and p.name not in _건너뜀:
            out.add(p.name)
        elif p.is_file() and p.suffix == ".py":
            out.add(p.stem)
    return out


def _파이썬들(repo: Path) -> "list[Path]":
    return [p for p in repo.rglob("*.py")
            if p.is_file() and not any(x in _건너뜀 for x in p.relative_to(repo).parts)]


def _늦은임포트(나무: ast.AST, 제것: str, 꾸: "set[str]") -> "list[str]":
    """**함수 안에서** 남의 꾸러미를 임포트하는 자리. 모듈 꼭대기의 임포트는 안 센다 --
    그것은 임포트하자마자 터지므로 어떤 검사에도 걸린다. 늦은 것이 숨는다."""
    out = []
    for 함수 in ast.walk(나무):
        if not isinstance(함수, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in ast.walk(함수):
            이름들 = []
            if isinstance(n, ast.Import):
                이름들 = [a.name.split(".")[0] for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
                이름들 = [n.module.split(".")[0]]
            for x in 이름들:
                if x in 꾸 and x != 제것 and x not in out:
                    out.append(x)
    return out


def _깃발들(나무: ast.AST) -> "list[str]":
    out = []
    for n in ast.walk(나무):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument":
            for a in n.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--"):
                    if a.value not in out:
                        out.append(a.value)
    return out


def 진입점들(repo=None) -> "list[dict]":
    """{"파일","모듈","꾸러미","깃발","늦은임포트","뿌리넣나"} -- 손으로 적은 목록이 아니다."""
    repo = Path(repo or REPO)
    꾸 = 꾸러미들(repo)
    out = []
    for f in sorted(_파이썬들(repo)):
        rel = str(f.relative_to(repo))
        본 = f.read_text(encoding="utf-8", errors="replace")
        if '__name__ == "__main__"' not in 본 and "__name__ == '__main__'" not in 본:
            continue
        try:
            나무 = ast.parse(본)
        except SyntaxError:
            continue
        조각 = rel[:-3].split("/")
        제것 = 조각[0]
        out.append({
            "파일": rel,
            "모듈": ".".join(조각),
            "꾸러미": 제것 if len(조각) > 1 else "",
            "깃발": _깃발들(나무),
            "늦은임포트": _늦은임포트(나무, 제것, 꾸),
            "뿌리넣나": "sys.path.insert" in 본,
        })
    return out


# ---------------------------------------------------------------- 부르는 자리
_스크립트꼴 = re.compile(r"""["']python3["']\s*,\s*["']([\w./-]+\.py)["']|python3\s+([\w./-]+\.py)""")
_모듈꼴 = re.compile(r"""["']python3["']\s*,\s*["']-m["']\s*,\s*["']([\w.]+)["']|python3\s+-m\s+([\w.]+)""")


def 부르는자리(repo=None) -> dict:
    """{"스크립트": {파일: [부른 자리…]}, "모듈": {모듈: [부른 자리…]}} -- 저장소 전체에서 긁는다."""
    repo = Path(repo or REPO)
    결과 = {"스크립트": {}, "모듈": {}}
    거리 = [p for p in repo.rglob("*") if p.is_file() and p.suffix in (".py", ".sh", ".yml", ".yaml")
            and not any(x in _건너뜀 for x in p.relative_to(repo).parts)]
    for p in 거리:
        rel = str(p.relative_to(repo))
        try:
            본 = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _스크립트꼴.finditer(본):
            이름 = m.group(1) or m.group(2)
            결과["스크립트"].setdefault(이름, []).append(rel)
        for m in _모듈꼴.finditer(본):
            이름 = m.group(1) or m.group(2)
            결과["모듈"].setdefault(이름, []).append(rel)
    return 결과


def 안전한가(진입점: dict, 부름: dict) -> "tuple[bool, str]":
    """늦은 임포트가 있는 진입점은 **뿌리를 넣거나**, **-m 으로만 불려야** 안전하다.

    둘 다 아니면 그 갈래를 밟는 순간 ModuleNotFoundError 다 -- 모듈 임포트는 멀쩡하므로
    얕은 점검(`--help` · 안 밟는 깃발)에는 안 걸린다. 그것이 이 사고의 꼴이었다."""
    if not 진입점["꾸러미"]:
        # **뿌리에 있는 파일은 본디 안전하다.** 스크립트의 디렉터리가 곧 뿌리이므로
        # sys.path[0] 이 이미 뿌리다(어느 cwd 에서 불러도). 위험한 것은 하위 꾸러미 안의 진입점뿐이다.
        # (첫 판이 이것을 안 갈라 뿌리 파일 6개를 위험이라 했다 -- 늘 우는 경보는 아무도 안 듣는다.)
        return True, ""
    if not 진입점["늦은임포트"]:
        return True, ""
    if 진입점["뿌리넣나"]:
        return True, ""
    스 = 부름["스크립트"].get(진입점["파일"], [])
    if not 스:
        return True, "(아무 데서도 스크립트 꼴로 안 부른다)"
    return False, (f"늦은 임포트 {', '.join(진입점['늦은임포트'][:4])} 인데 뿌리를 안 넣고 "
                   f"스크립트 꼴로 불린다: {', '.join(스[:3])} -- `-m {진입점['모듈']}` 로 부르거나 뿌리를 넣어라")


def 위험들(repo=None) -> "list[dict]":
    repo = Path(repo or REPO)
    부름 = 부르는자리(repo)
    out = []
    for e in 진입점들(repo):
        ok, 왜 = 안전한가(e, 부름)
        if not ok:
            out.append({**e, "왜": 왜})
    return out


def 안밟은깃발(repo=None) -> "list[dict]":
    """선언은 됐는데 저장소 어디에서도 안 불리는 깃발 -- **아무도 안 밟아 본 갈래**다.
    빨간불로 치지는 않는다(사람이 손으로 치는 깃발이 많다). 자가개선이 볼 거리로 센다."""
    repo = Path(repo or REPO)
    본들 = {}
    for p in repo.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".sh", ".yml", ".yaml") and not any(x in _건너뜀 for x in p.relative_to(repo).parts):
            try:
                본들[str(p.relative_to(repo))] = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    out = []
    for e in 진입점들(repo):
        안 = []
        for 깃 in e["깃발"]:
            밟 = any(깃 in 본 for rel, 본 in 본들.items() if rel != e["파일"])
            if not 밟:
                안.append(깃)
        if 안:
            out.append({"파일": e["파일"], "안밟은": 안})
    return out


def 보고(repo=None) -> str:
    repo = Path(repo or REPO)
    진 = 진입점들(repo)
    위 = 위험들(repo)
    안 = 안밟은깃발(repo)
    줄 = [f"진입점 {len(진)}개 (코드가 세어 찾았다 -- 손으로 적은 목록이 아니다)",
         f"  늦은 임포트가 있는 것: {sum(1 for e in 진 if e['늦은임포트'])}개"]
    if 위:
        줄.append(f"  **위험 {len(위)}개** -- 그 갈래를 밟으면 ModuleNotFoundError:")
        for e in 위:
            줄.append(f"      ✗ {e['파일']}: {e['왜']}")
    else:
        줄.append("  위험 없음 -- 늦은 임포트가 있는 진입점은 전부 뿌리를 넣거나 -m 으로 불린다")
    if 안:
        줄.append(f"  아무도 안 밟아 본 깃발 {sum(len(x['안밟은']) for x in 안)}개 (빨간불은 아니다):")
        for x in 안[:6]:
            줄.append(f"      · {x['파일']}: {', '.join(x['안밟은'][:6])}")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="진입점·깃발·위험을 코드가 센다")
    ap.add_argument("--위험만", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--저장소", default="")
    a = ap.parse_args()
    repo = Path(a.저장소) if a.저장소 else None
    if a.json:
        import json
        print(json.dumps({"진입점": 진입점들(repo), "위험": 위험들(repo), "안밟은깃발": 안밟은깃발(repo)},
                         ensure_ascii=False, indent=1))
        return 1 if 위험들(repo) else 0
    if a.위험만:
        위 = 위험들(repo)
        for e in 위:
            print(f"  ✗ {e['파일']}: {e['왜']}")
        print(f"  위험 {len(위)}개")
        return 1 if 위 else 0
    print(보고(repo))
    return 1 if 위험들(repo) else 0


if __name__ == "__main__":
    raise SystemExit(main())
