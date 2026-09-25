"""**sandbox 실행이 남긴 묵은 워크트리를 스스로 쓸어내는가.** 실측 2026-09-25.

## 무슨 일이 났나

`sandbox/run.py` 는 `finally` 에서 워크트리를 지운다. 그런데 앞선 실행이 **강제종료**되면
(OOM · 타임아웃 kill · 컨테이너 회수) `finally` 가 안 돈다. 그러면 `/tmp/sandbox-*` 워크트리가
남는다 -- 실측: 한 컨테이너에 **95벌**이 쌓여 있었고, VM 은 `[Errno 28] No space left` 로
봇이 죽었다.

`_묵은판치우기()` 가 **새 판을 깔기 전에** 묵은 것을 쓸어낸다. kill 로 트랩을 놓쳐도 다음
실행이 스스로 치운다. 다만 **지금 도는 형제 판**은 지우면 안 되므로 나이로 거른다.

## 무엇을 붙드나 -- 글자가 아니라 진짜 워크트리를 잰다

  1. 묵은 sandbox 워크트리는 지운다(디렉터리도, git 등록도).
  2. **갓 만든 것은 살린다** -- 지금 도는 판일 수 있다(나이 필터).
  3. 디렉터리만 사라진 죽은 등록은 prune 된다.
  4. 다른 이름(sandbox- 아님)은 안 건드린다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import sandbox.run as R  # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


repo = Path(tempfile.mkdtemp(prefix="sbrepo-"))
tmp뿌리 = Path(tempfile.mkdtemp(prefix="sbtmp-"))


def git(*a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)


def _등록목록():
    return git("worktree", "list", "--porcelain").stdout


def _판만들기(이름, 나이초):
    """repo 에 워크트리를 붙이고 그 디렉터리 mtime 을 나이초 만큼 과거로 민다."""
    d = tmp뿌리 / 이름
    git("worktree", "add", "--detach", str(d), "HEAD")
    과거 = time.time() - 나이초
    os.utime(d, (과거, 과거))
    return d


try:
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (repo / "x.txt").write_text("1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "처음")

    print("== 묵은 것은 지우고 갓 만든 것은 살린다 ==")
    묵은1 = _판만들기("sandbox-묵은1", 3 * 3600)   # 3시간 전 -- 지워야
    묵은2 = _판만들기("sandbox-묵은2", 3 * 3600)
    갓만든 = _판만들기("sandbox-갓만든", 0)          # 지금 -- 살려야(도는 판일 수 있다)
    남의것 = _판만들기("mutate-딴것", 3 * 3600)      # sandbox- 아님 -- 안 건드려야

    # 거짓초록 방지: 쓸기 전에 셋 다 진짜로 등록돼 있어야 한다.
    reg = _등록목록()
    ok(all(n in reg for n in ("sandbox-묵은1", "sandbox-갓만든", "mutate-딴것")),
       "쓸기 전엔 네 판이 다 등록돼 있다 -- 그래야 쓴 것이 일한 것이다")

    치운수 = R._묵은판치우기(repo, 나이초=7200, tmp뿌리=tmp뿌리)
    ok(치운수 == 2, f"묵은 sandbox 판 둘만 치웠다 (실제 {치운수})")

    ok(not 묵은1.exists() and not 묵은2.exists(),
       "**묵은 디렉터리가 사라졌다** -- /tmp 를 먹던 것")
    ok(갓만든.exists(),
       "**갓 만든 판은 살아 있다** -- 지금 도는 형제 판을 안 지운다(나이 필터)")
    ok(남의것.exists(),
       "**sandbox- 아닌 것은 안 건드린다** -- 제 것만 쓴다")

    reg2 = _등록목록()
    ok("sandbox-묵은1" not in reg2 and "sandbox-묵은2" not in reg2,
       "묵은 판의 git 등록도 지워졌다 -- 디렉터리만 지우면 등록이 남아 .git 이 분다")
    ok("sandbox-갓만든" in reg2, "갓 만든 판의 등록은 그대로다")

    print("\n== 디렉터리만 사라진 죽은 등록은 prune 된다 ==")
    죽은 = _판만들기("sandbox-크래시", 3 * 3600)
    shutil.rmtree(죽은, ignore_errors=True)          # 크래시로 디렉터리만 증발
    ok("sandbox-크래시" in _등록목록(), "쓸기 전엔 죽은 등록이 남아 있다")
    R._묵은판치우기(repo, 나이초=7200, tmp뿌리=tmp뿌리)
    ok("sandbox-크래시" not in _등록목록(),
       "**죽은 등록이 prune 됐다** -- 디렉터리가 없어도 등록은 git 이 붙들고 있다")

finally:
    # 남은 판 정리 후 임시 저장소·자리 삭제
    for d in tmp뿌리.glob("*"):
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(d)],
                       capture_output=True, text=True)
    shutil.rmtree(tmp뿌리, ignore_errors=True)
    shutil.rmtree(repo, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("sandbox 판치우기: 묵은 것만 쓴다 · 도는 판은 살린다 · 죽은 등록 prune · 남의 것 안 건드림 -- 통과")
