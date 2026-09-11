"""plan(계획 승인 = 그림자 diff, 사람이 승인)을 임시 git 저장소에서 **끝까지 돌려** 붙든다.

격차표 '계획 승인': 저장소를 고치는 요청이면 diff 계획을 먼저 띄우고 승인 후 실행.

붙드는 것: (1) 켜기가 HEAD 그림자 워크트리를 꺼내고 상태 파일을 남긴다, (2) 편집은 그림자에만
닿고 실제 트리는 안 바뀐다, (3) 보기 = 코드가 만든 diff, (4) 승인 = git apply --index 로 실제
트리에 붙고 그림자·상태가 사라진다, (5) 실제 트리가 같은 자리를 먼저 바꿨으면 **코드가 거절**한다,
(6) 버림은 실제 트리를 안 건드린다, (7) 배선 -- !계획 · edit_file/run_shell 이 계획판으로 갈린다.

LLM·디스코드 없이 돈다. 실행: python3 tests/test_plan.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from plan import store as P  # noqa: E402
import filetools             # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
임시 = Path(tempfile.mkdtemp(prefix="test-plan-"))
repo = 임시 / "repo"
repo.mkdir()
git(repo, "init", "-q")
(repo / "a.txt").write_text("hello\n", encoding="utf-8")
git(repo, "add", "-A"); git(repo, "commit", "-qm", "init")

try:
    print("== 켜기: 그림자 + 상태 ==")
    ok(P.현재판(repo) is None and "꺼짐" in P.상태(repo), "처음엔 꺼져 있다")
    말 = P.켜기("a 를 bye 로", repo=repo, 누가="검사")
    판 = P.현재판(repo)
    ok(판 is not None and 판.is_dir() and (판 / "a.txt").read_text() == "hello\n", f"그림자 워크트리가 HEAD 로 선다 ({말[:30]})")
    ok((repo / "plan" / "state.json").is_file() and "켜짐" in P.상태(repo), "상태 파일 + 상태 켜짐")
    ok("이미 켜져" in P.켜기("또", repo=repo), "두 번 켜면 거절")

    print("\n== 편집은 그림자에만 ==")
    r = filetools.편집("a.txt", "hello", "bye", repo=판)
    ok((판 / "a.txt").read_text() == "bye\n" and (repo / "a.txt").read_text() == "hello\n",
       "**그림자만 바뀌고 실제 트리는 그대로** " + r)
    (판 / "new.txt").write_text("새 파일\n", encoding="utf-8")
    보 = P.보기(repo)
    ok("-hello" in 보 and "+bye" in 보 and "new.txt" in 보, "보기 = 코드가 만든 diff(새 파일 포함)")

    print("\n== 리허설이 승인의 전제다 ==")
    ok("아직 안 돌려 봤다" in P.승인(repo, 누가="검사"), "**돌려 보지 않은 diff 는 승인이 거절한다**")
    P.리허설기 = lambda repo, 판, 초, 전부=False, 전부초=1800: {"판": str(판), "그림자": True, "바뀐것": ["a.txt"], "걸음": [("문법", 1, "깨짐")],
                                  "통과": False, "못잼": [], "걸린초": 0.1}
    P.시험하기(repo)
    ok("리허설이 빨강" in P.승인(repo, 누가="검사"), "**리허설이 빨강이면 거절한다**")
    P.리허설기 = lambda repo, 판, 초, 전부=False, 전부초=1800: {"판": str(판), "그림자": True, "바뀐것": [], "걸음": [], "통과": True, "못잼": [], "걸린초": 0.0}
    P.시험하기(repo)
    filetools.편집("a.txt", "bye", "bye2", repo=판)                # 시험한 뒤 또 고쳤다
    ok("또 바뀌었다" in P.승인(repo, 누가="검사"), "**시험한 diff 와 지금 diff 가 다르면 거절한다**")
    filetools.편집("a.txt", "bye2", "bye", repo=판)                # 되돌리고 다시 시험
    P.시험하기(repo)

    print("\n== 승인: git apply --index ==")
    말 = P.승인(repo, 누가="검사")
    ok("적용됨" in 말 and (repo / "a.txt").read_text() == "bye\n" and (repo / "new.txt").is_file(),
       f"**승인하면 실제 트리에 붙는다** ({말[:40]})")
    ok(P.현재판(repo) is None and not 판.exists(), "승인 뒤 그림자·상태가 사라진다")
    staged = git(repo, "diff", "--cached", "--name-only").stdout.split()
    ok(sorted(staged) == ["a.txt", "new.txt"], f"index 에 올라 있다(커밋은 git_sync) ({staged})")
    git(repo, "commit", "-qm", "apply")

    print("\n== 충돌: 코드가 거절 ==")
    P.켜기("다시", repo=repo)
    판 = P.현재판(repo)
    filetools.편집("a.txt", "bye", "ciao", repo=판)
    P.시험하기(repo)
    (repo / "a.txt").write_text("hola\n", encoding="utf-8")          # 실제 트리가 같은 자리를 먼저 바꿨다
    말 = P.승인(repo)
    ok("적용 실패" in 말 and (repo / "a.txt").read_text() == "hola\n" and P.현재판(repo) is not None,
       "**같은 자리를 먼저 고쳤으면 apply 가 거절하고 계획판은 남는다**")
    말 = P.버림(repo)
    ok("버렸다" in 말 and P.현재판(repo) is None and (repo / "a.txt").read_text() == "hola\n", "버림은 실제 트리를 안 건드린다")
    ok("바뀐 것이 없어" in (P.켜기("빈", repo=repo) and P.승인(repo)), "바뀐 것 없이 승인하면 그대로 끈다")
    git(repo, "checkout", "--", "a.txt")                          # 실제 트리를 HEAD 로 되돌린다(앞 갈래가 hola 를 남겼다)
    P.켜기("건너뛰기", repo=repo)                                  # 그림자는 HEAD("bye")에서 선다
    filetools.편집("a.txt", "bye", "ciao", repo=P.현재판(repo))
    ok("건너뜀" in P.승인(repo, 건너뛰기=True), "사람이 명시하면 리허설을 건너뛸 수 있다(그렇다고 적힌다)")
finally:
    P.리허설기 = None
    s = P.읽기(repo)
    if s:
        P._끄기(repo, s)
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
import dispatch  # noqa: E402
ok("계획" in (dispatch.run("!계획", allow_write=True) or "") and "승인" in (dispatch.run("!계획", allow_write=True) or ""), "!계획 도움말")
ok("읽기만" in (dispatch.run("!계획 켜기 x", allow_write=False) or ""), "공개 채널은 켜기·승인 못 한다(승인 주체는 사람)")
ok("꺼짐" in (dispatch.run("!계획 상태", allow_write=False) or ""), "상태는 공개 채널도 읽는다")
ok(dispatch.run("!계획기 x") is None, "붙여 쓴 `!계획기` 는 명령이 아니다")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
ok("filetools.편집(path, old, new, repo=_계획판())" in _도구, "**edit_file 이 계획판이면 그림자에 쓴다**")
ok('cwd=str(_계획판() or REPO_DIR)' in _도구, "**run_shell 이 계획판이면 그림자에서 돈다**")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("!계획" in _서버 and "승인" in _서버, "프롬프트가 !계획 을 이름을 대고 '승인은 사람만' 을 적는다")
ok("시험" in (dispatch.run("!계획", allow_write=True) or ""), "도움말이 `!계획 시험` 을 말한다")
_st = (뿌리 / "plan" / "store.py").read_text(encoding="utf-8")
ok("아직 안 돌려 봤다" in _st and "리허설이 빨강" in _st and "또 바뀌었다" in _st,
   "**승인은 리허설 초록 + 같은 diff 일 때만** (코드가 지킨다)")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"plan/**.py"' in _wf, "plan 이 배포 경로에")
ok("plan/state.json" in (뿌리 / ".gitignore").read_text(encoding="utf-8"), "상태 파일은 gitignore")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("plan: 켜기 · 그림자 편집 · diff · 승인 apply · 충돌 거절 · 버림 · 배선 -- 통과")
