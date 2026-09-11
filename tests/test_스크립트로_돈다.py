"""꾸러미 진입점을 **스크립트로 돌릴 때** 뿌리를 못 찾는 병을 붙든다.

실측 2026-09-11(VM): `python3 improve/run.py --부탁 ...` 가
`ModuleNotFoundError: No module named 'plan'` 로 죽었다. 파이썬은 스크립트의 디렉터리를
sys.path[0] 에 넣는다 -- `improve/run.py` 를 돌리면 sys.path[0] 이 `improve/` 이지 뿌리가 아니다.
`from plan import store` 가 거기서 죽는다.

**배선 읽기점검은 초록이었다.** `improve/run.py --틈만` 은 plan 을 안 쓰기 때문이다 --
얕은 점검이 깊은 길을 못 봤다. 그래서 여기서 두 가지로 붙든다:

사용자가 다시 짚었다: "배선 읽기점검이 **하드코딩되면 안 된다**고." 맞다 -- 첫 판은 어느 파일을
볼지 내가 손으로 적었다. 그러면 새 모듈이 생길 때 같은 병이 또 난다. 그래서 목록을 없애고
`entrypoints` 가 **ast 로 세어 찾은 것**을 쓴다.

  (1) 정적 -- 세어 찾은 진입점에 위험(늦은 임포트 + 뿌리 안 넣음 + 스크립트 꼴 호출)이 없는가
  (2) 되살리기 -- 그 사고를 되살리면 **실제로 잡는지** 본다(검사가 검사 구실을 하는지)
  (3) 실측 -- 세어 찾은 꾸러미 진입점을 **다른 cwd 에서** 돌려 임포트 단계를 지난다

실행: python3 tests/test_스크립트로_돈다.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import entrypoints as E  # noqa: E402

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


print("== 정적: 코드가 **세어 찾은** 진입점에 위험이 없는가 (손으로 적은 목록 없음) ==")
진 = E.진입점들(뿌리)
위 = E.위험들(뿌리)
ok(len(진) > 50, f"진입점을 ast 로 세어 찾는다 ({len(진)}개)")
ok(sum(1 for e in 진 if e["늦은임포트"]) > 0, "함수 안에서 남의 꾸러미를 쓰는 진입점이 있다(사고가 숨는 자리)")
ok(not 위, "**위험 없음** -- 늦은 임포트가 있는 꾸러미 진입점은 전부 뿌리를 넣거나 -m 으로 불린다: "
   + "; ".join(f"{x['파일']}: {x['왜'][:60]}" for x in 위))

print("\n== 이 검사가 **그 사고를 실제로 잡는가** (되살려 본다) ==")
_불 = 뿌리 / "improve" / "run.py"
_원 = _불.read_text(encoding="utf-8")
_뺀 = _원.replace("if str(REPO) not in sys.path:\n    sys.path.insert(0, str(REPO))\n", "")
ok(_뺀 != _원, "improve/run.py 에서 뿌리 넣기를 뺄 수 있다(되살릴 거리가 있다)")
try:
    _불.write_text(_뺀, encoding="utf-8")
    되 = [x["파일"] for x in E.위험들(뿌리)]
    ok(되 == ["improve/run.py"], f"**뿌리 넣기를 빼면 바로 잡는다** ({되}) -- 목록에 적어서가 아니라 세어서")
finally:
    _불.write_text(_원, encoding="utf-8")
ok(_불.read_text(encoding="utf-8") == _원 and not E.위험들(뿌리), "되돌렸고 다시 위험 없음")

print("\n== 실측: **세어 찾은** 꾸러미 진입점을 다른 cwd 에서 돌려 임포트를 지난다 ==")
밖 = tempfile.mkdtemp(prefix="test-밖-")
# **깃발을 선언한 것만 민다.** argparse 가 없는 진입점은 `--help` 를 그냥 인자로
# 삼키고 제 일을 끝까지 한다 -- 실측: `eval/acceptance.py --help` 가 인수 검사 전부를
# 돌리다 120초를 넘겼다. 그것은 임포트 점검이 아니라 그냥 느린 검사다.
꾸진 = [e for e in 진 if e["꾸러미"] and e["늦은임포트"] and e["깃발"]][:8]
ok(꾸진, f"살펴볼 꾸러미 진입점 {len(꾸진)}개: {', '.join(e['파일'] for e in 꾸진[:5])}")
샌, 못 = [], []
for e in 꾸진:
    try:
        p = subprocess.run([sys.executable, str(뿌리 / e["파일"]), "--help"],
                           cwd=밖, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        못.append(e["파일"])          # 못 잰 것은 통과로 치지 않되, 임포트 사고와 갈라 적는다
        continue
    본 = (p.stdout or "") + (p.stderr or "")
    if "ModuleNotFoundError" in 본 or "No module named" in 본:
        샌.append(f"{e['파일']}: {본.strip().splitlines()[-1][:70]}")
ok(not 샌, f"다른 cwd 에서 전부 임포트를 지난다 -- 샌 것: {샌}")
ok(not 못, f"**--help 가 안 끝난 것은 못 잰 것이다**(초록이 아니다): {못}")

print("\n== 깊은 길: improve 의 부탁 경로가 plan 을 실제로 임포트한다 ==")
p = subprocess.run([sys.executable, str(뿌리 / "improve" / "run.py"), "--부탁", "x", "--좁게", "--저장소", str(뿌리)],
                   cwd=밖, capture_output=True, text=True, timeout=180)
본 = (p.stdout or "") + (p.stderr or "")
ok("No module named 'plan'" not in 본, f"**`--부탁` 이 plan 을 찾는다**(이 사고의 재현) ({본.strip().splitlines()[-1][:60]})")
import shutil
shutil.rmtree(밖, ignore_errors=True)

print("\n== 배선: 얕은 점검을 깊게 ==")
_wire = (뿌리 / "eval" / "wire.py").read_text(encoding="utf-8")
ok('"improve/run.py", "--임포트"' in _wire, "improve 읽기점검이 임포트까지 보는 길을 쓴다")
ok('"entrypoints.py"' in _wire, "**배선 점검이 진입점 세기를 부른다** -- 목록이 아니라 셈으로")
_run2 = (뿌리 / "improve" / "run.py").read_text(encoding="utf-8")
ok("entrypoints" in _run2, "**자가개선이 이 위험을 틈으로 집는다** -- 다음엔 에이전트가 스스로 고친다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("스크립트로 돈다: 정적 뿌리 넣기 · 다른 cwd 실측 · 깊은 길 · 배선 -- 통과")
