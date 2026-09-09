r"""G019 배선 검사 -- 검사가 남의 기계 경로를 만지는 것을 잡는가.

실측 2026-09-09: 게이트 워크플로가 오래 빨간불이었는데 **게이트는 다 통과했다.**
빨간 것은 검사 한 벌이었고, 원인이 이것이다.

    PermissionError: [Errno 13] Permission denied: '/root/.claude/uploads'

여기서는 그 경로가 없어서 `is_dir()` 이 False 를 주고 초록, CI 에서는 있는데 못
읽어서 터졌다.
"""
from __future__ import annotations

import errno
import importlib
import pathlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gatekeeper import GateContext                                    # noqa: E402

G = importlib.import_module("gates.G019_검사가_남의_기계_경로를_만지지_않는가")

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def repo(body: str, name: str = "test_x.py"):
    d = Path(tempfile.mkdtemp())
    (d / "tests").mkdir()
    (d / "tests" / name).write_text(body, encoding="utf-8")
    return d


print("== pathlib 이 무엇을 삼키는지부터 ==")
_ig = getattr(pathlib, "_IGNORED_ERRNOS", ())
ok(errno.ENOENT in _ig, f"없음(ENOENT={errno.ENOENT})은 삼킨다 -- 그래서 여기서는 초록이었다")
ok(errno.EACCES not in _ig,
   f"**못 읽음(EACCES={errno.EACCES})은 안 삼킨다** -- 그래서 CI 에서 터졌다 {_ig}")

print("\n== 기계 경로를 잡는다 ==")
# G019: 기계 경로 -- 아래는 **고정물 문자열**이다. 디스크를 안 만진다
for path in ("/root/.claude/uploads", "/home/ubuntu/SE/logs", "/Users/me/x", "/mnt/data"):
    _d = repo(f'from pathlib import Path\np = Path("{path}")\n')
    _v = G.check(GateContext(_d))
    ok(len(_v) == 1 and path in _v[0], f"{path} 를 잡는다")
# G019: 기계 경로 -- 고정물이다
_v = G.check(GateContext(repo('p = "/root/x"\n')))
ok(_v and "try/except OSError" in _v[0], "고치는 법을 같이 준다")
ok(_v and "EACCES" in _v[0], "왜 여기서는 초록이고 거기서는 터지는지 적어 준다")

print("\n== 안 잡아야 할 것 ==")
for path in ("/tmp/x", "/dev/null", "/usr/bin/python3", "/proc/self", "/etc/hosts"):
    _d = repo(f'p = "{path}"\n')
    ok(G.check(GateContext(_d)) == [], f"{path} 는 어디에나 있다 -- 안 잡는다")
ok(G.check(GateContext(repo("p = 'novel/flow.py'\n"))) == [], "상대경로는 안 잡는다")
# G019: 기계 경로 -- 표식이 먹는지 보는 고정물이다
ok(G.check(GateContext(repo(
    "# G019: 기계 경로 -- 일부러다\np = '/root/x'\n"))) == [],
   "**표식을 달면 넘어간다** -- 조용히가 아니라 눈에 보이게 고르게 한다")
ok(G.check(GateContext(Path(tempfile.mkdtemp()))) == [], "tests/ 가 없으면 빈 목록")

print("\n== 검사가 아닌 파일은 안 본다 ==")
# G019: 기계 경로 -- 고정물이다
_d = repo('p = "/root/x"\n', name="helper.py")
ok(G.check(GateContext(_d)) == [], "test_ 로 시작하지 않는 것은 안 본다")

print("\n== 이 저장소에서 ==")
_here = GateContext(Path(__file__).resolve().parent.parent)
_v5 = G.check(_here)
ok(_v5 == [], f"지금은 없다 ({len(_v5)}건)"
   + ("\n        " + "\n        ".join(_v5) if _v5 else ""))
_hwp = (Path(__file__).resolve().parent / "test_law_hwp.py")
if _hwp.exists():
    _t = _hwp.read_text(encoding="utf-8")
    ok("except OSError" in _t,
       "test_law_hwp 가 `except OSError` 로 감쌌다  ← 이번에 터진 그 자리")
    ok("건너뜀" in _t, "**건너뛴다고 말한다** -- 조용히 건너뛰면 그것도 가짜 green 이다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("G019: errno · 잡기 · 표준경로 통과 · 표식 · 이 저장소 -- 통과")
