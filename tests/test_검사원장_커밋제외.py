"""**봇이 검사가 낳은 원장을 자동 커밋에 담는 것을 붙든다.** 실측 2026-09-25(재발방지).

## 무슨 일이 났나

봇이 Discord 요청을 처리하다 `eval/run.py`·`gatekeeper.py` 를 **직접** 돌렸다. 그 검사들이
추적되는 원장(eval·improve·router)에 줄을 쌓았는데, `git_sync` 의 `git add -A` 가 그것을
자동 커밋('SE-agent: … 자동 반영')에 쓸어 담았다. `ledgerroot`/`SE_LEDGER_ROOT` 는
**wire 로 부른 검사만** 막으므로(test_되돌이_끊기.py), 직접 돌린 것은 안 막혔다.

`gitsync.검사원장_스테이지에서빼기()` 가 커밋 문턱에서 그 다섯 원장을 스테이지에서 뺀다.
**글자가 아니라 진짜 커밋을 본다** -- 임시 저장소를 지어 실제로 add·restore·commit 을 돌리고,
커밋된 나무와 워크트리를 둘 다 잰다(seek.sh 가 '한 줄도 안 돌면서 초록'이던 값을 치른 뒤로,
이 저장소는 셸/깃 경로를 글자로 검사하지 않는다).

## 무엇을 붙드나

  1. 검사가 낳은 원장(다섯)은 **커밋에 안 담긴다** -- 그 실행이 진짜 add 되어 있었는데도.
  2. 진짜 일(.py)과 **검사 아닌 원장(research)** 은 그대로 커밋된다 -- 다 지우면 안 된다.
  3. `--worktree` 를 안 써서 **워크트리의 줄은 살아 있다** -- 남의 프로세스 일을 안 지운다.
  4. 그 다섯만 바뀐 턴이면 스테이지가 비어 'nothing to commit' 이 된다.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import gitsync  # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


임시 = Path(tempfile.mkdtemp(prefix="검사원장-"))


def git(a):
    return subprocess.run(["git", *a], cwd=str(임시), capture_output=True, text=True)


def _cached():
    return set(git(["diff", "--cached", "--name-only"]).stdout.split())


def _커밋된(경로):
    """마지막 커밋(HEAD)에 담긴 그 파일의 내용."""
    return git(["show", f"HEAD:{경로}"]).stdout


def _쓰기(경로, 글):
    p = 임시 / 경로
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(글, encoding="utf-8")


try:
    git(["init", "-q"])
    git(["config", "user.email", "t@t"])
    git(["config", "user.name", "t"])

    # 다섯 검사원장 + 검사 아닌 원장(research) + 진짜 코드 파일. 각 원장은 한 줄로 시작.
    for f in gitsync.검사원장:
        _쓰기(f, '{"처음":1}\n')
    _쓰기("research/ledger.jsonl", '{"진짜연구":1}\n')   # 검사 아님 -- 지우면 안 된다
    _쓰기("foo.py", "x = 1\n")
    git(["add", "-A"])
    git(["commit", "-q", "-m", "처음"])

    print("== 검사가 낳은 줄 + 진짜 일이 섞인 턴 ==")
    # 검사가 두 원장을 더럽힌다(eval·router). 진짜 일: foo.py 수정 + research 원장에 참줄.
    with open(임시 / "eval/ledger.jsonl", "a", encoding="utf-8") as fp:
        fp.write('{"검사가쌓은줄":1}\n')
    with open(임시 / "router/ledger.jsonl", "a", encoding="utf-8") as fp:
        fp.write('{"검사가쌓은줄":2}\n')
    _쓰기("foo.py", "x = 2\n")
    with open(임시 / "research/ledger.jsonl", "a", encoding="utf-8") as fp:
        fp.write('{"진짜연구":2}\n')

    git(["add", "-A"])
    스테이지_전 = _cached()
    # 거짓초록 방지: 빼기 전에 그 원장들이 **실제로 스테이지에 있었어야** 한다.
    # (없었으면 이 검사는 아무것도 증명하지 못한다 -- no-op 함수도 통과해 버린다.)
    ok("eval/ledger.jsonl" in 스테이지_전 and "router/ledger.jsonl" in 스테이지_전,
       "빼기 전엔 검사원장이 진짜로 스테이지에 있었다 -- 그래야 뺀 것이 일한 것이다")

    뺀것 = gitsync.검사원장_스테이지에서빼기(git)
    ok(뺀것 == ["eval/ledger.jsonl", "router/ledger.jsonl"],
       f"스테이지에 올라 있던 검사원장 둘만 뺐다(순서는 목록순) -- 실제 {뺀것}")

    스테이지_후 = _cached()
    ok("eval/ledger.jsonl" not in 스테이지_후 and "router/ledger.jsonl" not in 스테이지_후,
       "검사원장은 스테이지에서 빠졌다 -- 커밋에 안 담긴다")
    ok("foo.py" in 스테이지_후,
       "진짜 코드 변경은 그대로 스테이지에 있다 -- 일까지 빼면 안 된다")
    ok("research/ledger.jsonl" in 스테이지_후,
       "**검사 아닌 원장(research)은 그대로 있다** -- 다섯만 빼고 나머지 원장은 손대지 않는다")

    git(["commit", "-q", "-m", "SE-agent: Discord 요청 처리 결과 자동 반영"])
    ok(_커밋된("eval/ledger.jsonl") == '{"처음":1}\n',
       "**커밋된 eval 원장에 검사줄이 없다** -- 처음 한 줄 그대로")
    ok("검사가쌓은줄" not in _커밋된("router/ledger.jsonl"),
       "커밋된 router 원장에도 검사줄이 없다")
    ok(_커밋된("foo.py") == "x = 2\n", "진짜 코드 변경은 커밋됐다")
    ok('{"진짜연구":2}' in _커밋된("research/ledger.jsonl"),
       "검사 아닌 원장의 참줄은 커밋됐다")

    print("\n== --worktree 를 안 써서 워크트리의 줄은 살아 있다(남의 일 안 지움) ==")
    ok("검사가쌓은줄" in (임시 / "eval/ledger.jsonl").read_text(encoding="utf-8"),
       "**워크트리의 검사줄은 그대로다** -- HEAD 로 안 되돌렸다. 별 프로세스 일을 안 지운다")

    print("\n== 검사원장만 바뀐 턴이면 스테이지가 비어 nothing to commit ==")
    with open(임시 / "codify/ledger.jsonl", "a", encoding="utf-8") as fp:
        fp.write('{"검사가쌓은줄":3}\n')
    git(["add", "-A"])
    gitsync.검사원장_스테이지에서빼기(git)
    ok(_cached() == set(), "검사원장만 바뀐 턴은 빼고 나면 스테이지가 빈다 -- 커밋할 것이 없다")
    c = git(["commit", "-q", "-m", "x"])
    ok(c.returncode != 0, f"실제로 'nothing to commit'(끝값 {c.returncode})")

finally:
    shutil.rmtree(임시, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("검사원장 커밋제외: 다섯만 뺀다 · 진짜 일과 딴 원장은 지킨다 · 워크트리는 안 건드린다 -- 통과")
