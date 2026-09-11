"""꾸러미 진입점을 **스크립트로 돌릴 때** 뿌리를 못 찾는 병을 붙든다.

실측 2026-09-11(VM): `python3 improve/run.py --부탁 ...` 가
`ModuleNotFoundError: No module named 'plan'` 로 죽었다. 파이썬은 스크립트의 디렉터리를
sys.path[0] 에 넣는다 -- `improve/run.py` 를 돌리면 sys.path[0] 이 `improve/` 이지 뿌리가 아니다.
`from plan import store` 가 거기서 죽는다.

**배선 읽기점검은 초록이었다.** `improve/run.py --틈만` 은 plan 을 안 쓰기 때문이다 --
얕은 점검이 깊은 길을 못 봤다. 그래서 여기서 두 가지로 붙든다:

  (1) 정적 -- 남의 꾸러미를 임포트하면서 `__main__` 이 있는 파일은 **뿌리를 sys.path 에 넣어야 한다**
  (2) 실측 -- 진입점을 **다른 cwd 에서** 스크립트로 돌려 임포트 단계를 실제로 지난다

실행: python3 tests/test_스크립트로_돈다.py
"""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


_건너뜀 = {".git", "venv", "__pycache__", "node_modules", "inbox", "tests", "scripts", "gates"}


def 꾸러미들() -> "set[str]":
    """뿌리의 하위 꾸러미 이름(디렉터리 + 뿌리의 .py 모듈)."""
    out = set()
    for p in 뿌리.iterdir():
        if p.is_dir() and (p / "__init__.py").is_file() and p.name not in _건너뜀:
            out.add(p.name)
        elif p.is_file() and p.suffix == ".py":
            out.add(p.stem)
    return out


def 남의꾸러미임포트(파일: Path, 제것: str, 꾸러미: "set[str]") -> "list[str]":
    """그 파일이 **자기 꾸러미 밖**의 저장소 모듈을 임포트하는가(꼭대기 수준이든 함수 안이든)."""
    try:
        나무 = ast.parse(파일.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return []
    out = []
    for n in ast.walk(나무):
        이름들 = []
        if isinstance(n, ast.Import):
            이름들 = [a.name.split(".")[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            이름들 = [n.module.split(".")[0]]
        for x in 이름들:
            if x in 꾸러미 and x != 제것 and x not in out:
                out.append(x)
    return out


def 뿌리를넣나(파일: Path) -> bool:
    본 = 파일.read_text(encoding="utf-8", errors="replace")
    return "sys.path.insert" in 본 and ("parent.parent" in 본 or "REPO" in 본)


print("== 정적: 남의 꾸러미를 쓰면서 스크립트로도 도는 파일은 뿌리를 넣어야 한다 ==")
꾸 = 꾸러미들()
진입점 = []
빠뜨린 = []
for d in sorted(x for x in 꾸 if (뿌리 / x).is_dir()):
    for f in sorted((뿌리 / d).rglob("*.py")):
        if "__pycache__" in f.parts or f.name == "__init__.py":
            continue
        본 = f.read_text(encoding="utf-8", errors="replace")
        if '__name__ == "__main__"' not in 본:
            continue
        남 = 남의꾸러미임포트(f, d, 꾸)
        if not 남:
            continue
        rel = str(f.relative_to(뿌리))
        진입점.append(rel)
        if not 뿌리를넣나(f):
            빠뜨린.append(f"{rel} (남의 것: {', '.join(남[:4])})")
ok(진입점, f"살펴본 진입점 {len(진입점)}개: {', '.join(진입점[:6])}…")
ok(not 빠뜨린, f"**전부 뿌리를 sys.path 에 넣는다** -- 빠뜨린 것: {빠뜨린}")

print("\n== 실측: 다른 cwd 에서 스크립트로 돌려 임포트 단계를 지난다 ==")
밖 = tempfile.mkdtemp(prefix="test-밖-")
샘 = [("improve/run.py", ["--상태"]), ("plan/store.py", ["--상태"]), ("research/run.py", ["--목표", "x", "--분해만"]),
     ("rehearsal.py", ["--판", "/없는판", "--초", "5"]), ("commit_guard.py", ["--배선"]), ("impact.py", ["--파일", "relay.py"])]
for rel, args in 샘:
    p = subprocess.run([sys.executable, str(뿌리 / rel), *args, *(["--저장소", str(뿌리)] if rel.endswith("run.py") or rel.endswith("store.py") else [])],
                       cwd=밖, capture_output=True, text=True, timeout=180)
    본 = (p.stdout or "") + (p.stderr or "")
    ok("ModuleNotFoundError" not in 본 and "No module named" not in 본,
       f"{rel} 이 다른 cwd 에서 임포트를 지난다 ({본.strip().splitlines()[-1][:60] if 본.strip() else '(조용)'})")

print("\n== 깊은 길: improve 의 부탁 경로가 plan 을 실제로 임포트한다 ==")
p = subprocess.run([sys.executable, str(뿌리 / "improve" / "run.py"), "--부탁", "x", "--좁게", "--저장소", str(뿌리)],
                   cwd=밖, capture_output=True, text=True, timeout=180)
본 = (p.stdout or "") + (p.stderr or "")
ok("No module named 'plan'" not in 본, f"**`--부탁` 이 plan 을 찾는다**(이 사고의 재현) ({본.strip().splitlines()[-1][:60]})")
import shutil
shutil.rmtree(밖, ignore_errors=True)

print("\n== 배선: 얕은 점검을 깊게 ==")
_wire = (뿌리 / "eval" / "wire.py").read_text(encoding="utf-8")
ok('"improve/run.py", "--임포트"' in _wire,
   "improve 읽기점검이 임포트까지 보는 길을 쓴다(--틈만 은 plan 을 안 지난다)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("스크립트로 돈다: 정적 뿌리 넣기 · 다른 cwd 실측 · 깊은 길 · 배선 -- 통과")
