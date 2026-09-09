"""G018 배선 검사 -- 무시 규칙에 적어 놓고 추적을 안 끊은 파일을 잡는가.

**`.gitignore` 는 이미 추적 중인 파일에 아무 힘이 없다.** 규칙을 적어도 계속 커밋되고
계속 `git pull` 을 충돌시킨다. 이 저장소가 그것으로 세 번 앓았다.

여기서는 임시 저장소를 실제로 만들어 돌린다 -- 이 저장소의 상태에 기대지 않는다.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gatekeeper import GateContext                                    # noqa: E402
import importlib                                                     # noqa: E402

G = importlib.import_module("gates.G018_무시_규칙에_적어_놓고_추적을_안_끊었는가")

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(d, *a):
    return subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)


def repo(files: dict, ignore: str, add_before_ignore=()):
    """임시 저장소 하나. `add_before_ignore` 는 무시 규칙 **전에** 추적시킬 것들이다."""
    d = Path(tempfile.mkdtemp())
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "T")
    for name, body in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    for name in add_before_ignore:
        git(d, "add", name)
    (d / ".gitignore").write_text(ignore, encoding="utf-8")
    git(d, "add", ".gitignore")
    git(d, "commit", "-qm", "x")
    return d


print("== 규칙만 적고 추적을 안 끊으면 잡는다 ==")
_d = repo({"run/state.json": "{}"}, "run/state.json\n",
          add_before_ignore=["run/state.json"])
_v = G.check(GateContext(_d))
ok(len(_v) == 1, f"한 건 잡는다 ({len(_v)}건)")
ok(_v and "run/state.json" in _v[0], "파일 이름을 짚는다")
ok(_v and "git rm --cached" in _v[0], "**고치는 법을 같이 준다** -- 규칙만 적으면 안 끊긴다")

print("\n== 추적을 실제로 끊으면 초록이다 ==")
git(_d, "rm", "-q", "--cached", "run/state.json")
git(_d, "commit", "-qm", "untrack")
ok(G.check(GateContext(_d)) == [], "`git rm --cached` 뒤에는 안 잡는다")
ok((_d / "run" / "state.json").exists(), "**파일은 디스크에 남는다** -- 추적만 끊긴다")

print("\n== 안 잡아야 할 것 ==")
_d2 = repo({"src/a.py": "x = 1\n"}, "run/\n", add_before_ignore=["src/a.py"])
ok(G.check(GateContext(_d2)) == [], "무시 규칙에 안 걸리는 파일은 그냥 둔다")

# `!` 는 "무시하지 마라" 라서 추적이 맞다
_d3 = repo({"cfg/keep.json": "{}", "cfg/skip.json": "{}"},
           "cfg/*.json\n!cfg/keep.json\n", add_before_ignore=["cfg/keep.json"])
_v3 = G.check(GateContext(_d3))
ok(_v3 == [], f"**부정 규칙(`!`)은 안 잡는다** -- 추적이 맞다 ({len(_v3)}건)")

# 빈 디렉터리를 남기려고 일부러 커밋한 것
_d4 = repo({"logs/.gitkeep": ""}, "logs/\n", add_before_ignore=["logs/.gitkeep"])
ok(G.check(GateContext(_d4)) == [], ".gitkeep 은 일부러 넣은 것이라 안 잡는다")

print("\n== 이 저장소에서 ==")
_here = GateContext(Path(__file__).resolve().parent.parent)
_v5 = G.check(_here)
ok(_v5 == [], f"지금 저장소에는 없다 ({len(_v5)}건)"
   + ("\n        " + "\n        ".join(_v5) if _v5 else ""))
# 규칙이 실제로 적혀 있는가 -- 이번에 고친 자리
_gi = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
ok("mathdrift/*.bak" in _gi,
   "`mathdrift/*.bak` 이 무시 규칙에 있다  ← 다른 브랜치에서 병합 충돌을 냈다")
ok("novel/*.bak" in _gi, "novel 쪽은 원래 있었다 -- 같은 부류다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("G018: 잡기 · 끊으면 초록 · 부정 규칙 · .gitkeep · 이 저장소 -- 통과")
