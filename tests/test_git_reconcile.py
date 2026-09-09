r"""origin 이 앞섰을 때 따라잡는 법. **진짜 저장소를 만들어 돌린다.**

실측 2026-09-08~09, 같은 브랜치에서 여섯 번 밀기가 막혔다. 봇이 자동으로
`git rebase origin/main` 을 걸고 있었고, 둘 다 틀렸다.

  · **origin/main 이 아니다** -- 지금 브랜치가 main 이 아니면 밑동이 통째로 바뀐다
  · **rebase 가 아니다** -- 원격에 봇이 같이 쓰므로, 내 커밋을 새로 쓰면
    fast-forward 가 영영 안 된다

CLAUDE.md 에 규칙을 적었는데도 계속 났다. **규칙은 사람에게 적혔고 그 줄은 봇에게
적혀 있었기 때문이다.** 그래서 여기서 붙든다.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(d, *a):
    return subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)


def world():
    """main 과 갈래 하나가 있고, **봇이 갈래에 따로 미는** 세상."""
    root = Path(tempfile.mkdtemp())
    bare = root / "remote.git"
    git(root, "init", "-q", "--bare", "remote.git")
    work = root / "work"
    git(root, "clone", "-q", str(bare), "work")
    git(work, "config", "user.email", "t@t")
    git(work, "config", "user.name", "T")
    (work / "base.txt").write_text("base\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    git(work, "branch", "-M", "main")
    git(work, "push", "-q", "-u", "origin", "main")
    # 갈래를 내고 여러 커밋을 쌓는다
    git(work, "checkout", "-q", "-b", "feat")
    for i in range(3):
        (work / f"f{i}.txt").write_text(f"{i}\n", encoding="utf-8")
        git(work, "add", "-A")
        git(work, "commit", "-qm", f"feat {i}")
    git(work, "push", "-q", "-u", "origin", "feat")
    # main 이 따로 앞서 간다 (다른 세션이 main 에 밀었다)
    other = root / "other"
    git(root, "clone", "-q", str(bare), "other")
    git(other, "config", "user.email", "o@o")
    git(other, "config", "user.name", "O")
    (other / "base.txt").write_text("main 이 고쳤다\n", encoding="utf-8")
    git(other, "add", "-A")
    git(other, "commit", "-qm", "main 쪽 변경")
    git(other, "push", "-q", "origin", "main")
    # **봇이 갈래에 민다** -- 이것이 원격을 움직인다
    git(other, "checkout", "-q", "-b", "feat", "origin/feat")
    (other / "bot.txt").write_text("SE-agent\n", encoding="utf-8")
    git(other, "add", "-A")
    git(other, "commit", "-qm", "SE-agent: Discord 요청 처리 결과 자동 반영")
    git(other, "push", "-q", "origin", "feat")
    # 나는 그 사이 갈래에서 하나 더 만든다
    (work / "mine.txt").write_text("내 것\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "내 새 작업")
    return root, work


print("== 이 세상에서 그냥 push 하면 막힌다 ==")
_root, _w = world()
_p = git(_w, "push", "origin", "feat")
ok(_p.returncode != 0, "non-fast-forward 로 거부된다  ← 실제로 난 그 상황이다")
ok("fetch first" in (_p.stderr or "") or "rejected" in (_p.stderr or ""),
   "거부 사유가 원격이 앞섰다는 것이다")

print("\n== 옛 방식(origin/main 에 rebase)은 여기서 못 푼다 ==")
git(_w, "fetch", "origin")
_r = git(_w, "rebase", "origin/main")
_conflict = _r.returncode != 0
git(_w, "rebase", "--abort")
if _conflict:
    ok(True, "**충돌한다** -- 봇이 보내 온 그 문구가 여기서 재현된다")
else:
    _p2 = git(_w, "push", "origin", "feat")
    ok(_p2.returncode != 0,
       "충돌이 안 나도 **밀리지 않는다** -- rebase 가 해시를 새로 써서 영영 fast-forward 가 안 된다")
    git(_w, "reset", "--hard", "-q", "origin/feat")

print("\n== 새 방식: 지금 브랜치의 origin 을 merge ==")
_root2, _w2 = world()
import gitsync as G                                                    # noqa: E402
# **봇 모듈을 임포트하지 않는다.** `discord` 가 없는 기계에서도 돌아야 한다
# (실측: 처음에 discord_bot_server 를 임포트했다가 ModuleNotFoundError 로 터졌다).

_caught, _why = G.reconcile(lambda a: git(_w2, *a))
ok(_caught, f"따라잡는다 ({_why})")
ok("origin/feat" in _why, f"**origin/main 이 아니라 origin/feat 이다** ({_why})")
_p3 = git(_w2, "push", "origin", "feat")
ok(_p3.returncode == 0, f"그리고 밀린다 ({_p3.stderr.strip()[:60]})")

print("\n== 아무것도 안 사라진다 ==")
_log = git(_w2, "log", "--format=%s", "origin/feat").stdout
ok("SE-agent: Discord 요청 처리 결과 자동 반영" in _log, "**봇 커밋이 살아 있다**")
ok("내 새 작업" in _log, "내 커밋도 살아 있다")
for i in range(3):
    ok(f"feat {i}" in _log, f"갈래의 옛 커밋 feat {i} 도 살아 있다")

print("\n== 충돌하면 사람에게 넘긴다 (--force 로 밀지 않는다) ==")
_root3, _w3 = world()
# 같은 파일을 양쪽이 다르게 고친다
git(_w3, "fetch", "origin", "feat")
(_w3 / "bot.txt").write_text("나는 다르게 썼다\n", encoding="utf-8")
git(_w3, "add", "-A")
git(_w3, "commit", "-qm", "같은 파일을 다르게")
_c, _cw = G.reconcile(lambda a: git(_w3, *a))
ok(_c is False, "충돌하면 따라잡았다고 안 한다")
ok("충돌" in _cw and "force" in _cw.lower(),
   f"**--force 를 쓰지 말라고 말한다** ({_cw[:60]}…)")
ok(git(_w3, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "feat",
   "merge --abort 로 되돌려 놓는다 -- 반쯤 병합된 채로 안 남긴다")

print("\n== 브랜치가 아니면 아무것도 안 한다 ==")
_root4, _w4 = world()
git(_w4, "checkout", "-q", "--detach", "HEAD")
_d, _dw = G.reconcile(lambda a: git(_w4, *a))
ok(_d is False and "detached" in _dw, f"detached HEAD 에서는 손대지 않는다 ({_dw})")

print("\n== 코드에 `git rebase` 가 남아 있지 않다 ==")
_root_dir = Path(__file__).resolve().parent.parent
for name in ("gitsync.py", "discord_bot_server.py", "agent_memory.py"):
    _src = (_root_dir / name).read_text(encoding="utf-8")
    _code = [l for l in _src.split("\n")
             if '"rebase"' in l and not l.strip().startswith("#")]
    ok(not _code, f"{name} 에 `git rebase` 호출이 없다 ({len(_code)}줄)")
ok('f"origin/{br}"' in (_root_dir / "gitsync.py").read_text(encoding="utf-8"),
   "gitsync 가 **지금 브랜치의** origin 을 본다")
# **한 군데에만 있어야 한다.** 두 벌이면 한 벌을 고쳐도 다른 벌이 계속 깨뜨린다.
for name in ("discord_bot_server.py", "agent_memory.py"):
    _src = (_root_dir / name).read_text(encoding="utf-8")
    ok("gitsync.reconcile(" in _src, f"{name} 이 gitsync 를 쓴다 -- 제 복사본이 없다")
    ok('"merge", "--no-edit"' not in _src, f"{name} 에 merge 복사본이 안 남았다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("git 따라잡기: 막힘 재현 · 옛 방식 실패 · merge 로 풂 · 아무것도 안 사라짐 · 충돌은 사람에게 -- 통과")
