r"""**먼 검사 사각지대** -- 전체 검사를 주기로 돌려 *늦음*을 재는가.

    python3 tests/test_farcheck.py

붙드는 것: 빨강을 찾나 · 언제부터 빨간지 세나 · 시한초과를 빨강이라 하지 않나 ·
고쳐진 것을 지우나 · **막지 않나**(끝값 0 -- 막으면 기다림이 돌아온다).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import farcheck as F                                              # noqa: E402

fails = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        fails.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})

판 = Path(tempfile.mkdtemp(prefix="test-먼-"))
git(판, "init", "-q")
(판 / "tests").mkdir()
(판 / "tests" / "test_초록.py").write_text("print('초록')\n", encoding="utf-8")
(판 / "tests" / "test_빨강.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
git(판, "add", "-A"); git(판, "commit", "-qm", "init")

print("== 한 바퀴: 깨끗한 HEAD 판에서 전부 돌린다 ==")
ok(sorted(F.검사목록(판)) == ["tests/test_빨강.py", "tests/test_초록.py"], "검사를 다 찾는다")
r1 = F.한바퀴(판, 말하기=lambda s: None)
ok(r1["잰것"] == 2, f"둘 다 쟀다 ({r1['잰것']})")
ok(r1["빨강"] == ["tests/test_빨강.py"], f"빨간 것만 빨강이다 ({r1['빨강']})")
ok(r1["까닭"].get("tests/test_빨강.py"), "까닭을 적는다")
ok(r1["판"] and len(r1["판"]) >= 7, f"어느 판에서 쟀는지 적는다 ({r1['판']})")

print("\n== 작업 디렉터리를 안 본다 -- 커밋된 나무만 본다(precheck 과 같은 까닭) ==")
(판 / "tests" / "test_안담김.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
r안 = F.한바퀴(판, 말하기=lambda s: None, 검사들=["tests/test_안담김.py"])
ok(r안["잰것"] == 0 and r안["빨강"] == [],
   f"커밋에 안 담긴 파일은 HEAD 판에 없다 -- 재지 않는다 ({r안['잰것']})")
(판 / "tests" / "test_안담김.py").unlink()

print("\n== 사건기록: 언제부터 빨간지 센다 ==")
줄1 = F.사건기록(판, r1)
ok((판 / F.기록경로).is_file(), f"{F.기록경로} 가 생긴다(추적되는 경로다)")
늦1 = (줄1.get("늦음") or {}).get("tests/test_빨강.py") or {}
ok(늦1.get("커밋수") == 0, f"처음 본 판에서는 늦음 0 이다 ({늦1.get('커밋수')})")
ok(줄1["새빨강"] == ["tests/test_빨강.py"], f"처음 본 것은 **새 빨강**이다 ({줄1['새빨강']})")
ok("tests/test_빨강.py" in F.처음본판(판), "처음 본 판을 기억한다")

(판 / "새것.py").write_text("x = 1\n", encoding="utf-8")
git(판, "add", "-A"); git(판, "commit", "-qm", "관계없는 커밋 하나")
r2 = F.한바퀴(판, 말하기=lambda s: None)
줄2 = F.사건기록(판, r2)
늦2 = (줄2.get("늦음") or {}).get("tests/test_빨강.py") or {}
ok(늦2.get("커밋수") == 1,
   f"**커밋 하나가 지나면 늦음이 1 이다** -- 그 사이의 초록 보고는 이 검사를 안 보고 있었다 ({늦2.get('커밋수')})")
ok(늦2.get("처음본판") == 줄1["판"], f"처음 본 판을 그대로 들고 간다 ({늦2.get('처음본판')})")
ok(줄2["새빨강"] == [], f"두 번째에는 새 빨강이 아니다 ({줄2['새빨강']})")
ok(len(F.기록들(판)) == 2, "덧붙이기만 한다")

print("\n== 고쳐지면 지운다 -- 복구도 측정으로 한다 ==")
(판 / "tests" / "test_빨강.py").write_text("print('이제 초록')\n", encoding="utf-8")
git(판, "add", "-A"); git(판, "commit", "-qm", "고쳤다")
r3 = F.한바퀴(판, 말하기=lambda s: None)
줄3 = F.사건기록(판, r3)
ok(줄3["빨강"] == [], f"빨강이 없다 ({줄3['빨강']})")
ok(줄3["고쳐진것"] == ["tests/test_빨강.py"], f"고쳐진 것을 적는다 ({줄3['고쳐진것']})")
ok(F.처음본판(판) == {}, "다시 빨개지면 늦음을 0 부터 센다 -- 영영 빨강으로 남지 않는다")

print("\n== 시한을 넘긴 것은 빨강이 아니다 -- 못 잰 것이다 ==")
(판 / "tests" / "test_늦다.py").write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
git(판, "add", "-A"); git(판, "commit", "-qm", "느린 검사")
옛 = F.검사시한초
F.검사시한초 = 2
try:
    r4 = F.한바퀴(판, 말하기=lambda s: None, 검사들=["tests/test_늦다.py"])
finally:
    F.검사시한초 = 옛
ok(r4["시한초과"] == ["tests/test_늦다.py"] and r4["빨강"] == [],
   f"**시한초과는 빨강이 아니다** (시한초과 {r4['시한초과']} · 빨강 {r4['빨강']})")
ok(r4["못잼"] == 1, f"못잼으로 센다 ({r4['못잼']})")

print("\n== 보고 · 그리고 막지 않는다 ==")
글 = F.보고(판)
ok("먼 검사" in 글 and "기록 3번" in 글, f"보고가 기록을 센다 ({글.splitlines()[0][:60]})")
ok("비어 있다" in F.보고(Path(tempfile.mkdtemp(prefix="빈먼-"))),
   "기록이 없으면 **없다고 말한다** -- 안 잰 것을 초록으로 읽지 않는다")
빈판 = Path(tempfile.mkdtemp(prefix="못꺼냄-"))
ok(F.한바퀴(빈판, 말하기=lambda s: None)["못잼"] >= 0, "git 이 아닌 데서도 터지지 않는다")
cwd = os.getcwd()
os.chdir(판)
try:
    옛REPO = F.REPO
    F.REPO = 판
    rc = F.main(["--검사", "tests/test_초록.py"])
finally:
    F.REPO = 옛REPO
    os.chdir(cwd)
ok(rc == 0, f"**끝값은 0 이다 -- 막는 관문이 아니다**(막으면 기다림이 돌아온다) ({rc})")
빨강있을때 = F.한바퀴(판, 말하기=lambda s: None, 검사들=["tests/test_늦다.py"])
ok(isinstance(빨강있을때, dict), "한 바퀴는 언제나 사전을 돌려준다")

print("\n== 주기: 되풀이한다(횟수로 멈춘다) ==")
전 = len(F.기록들(판))
cwd = os.getcwd()
os.chdir(판)
try:
    옛REPO = F.REPO
    F.REPO = 판
    rc주기 = F.main(["--검사", "tests/test_초록.py", "--주기", "1", "--횟수", "2"])
finally:
    F.REPO = 옛REPO
    os.chdir(cwd)
ok(rc주기 == 0 and len(F.기록들(판)) == 전 + 2,
   f"두 바퀴 돌고 멈춘다 ({전} -> {len(F.기록들(판))})")

print("\n== 밀기: 기록을 커밋하고 민다 -- 안 하면 배포의 reset --hard 가 지운다 ==")
먼 = Path(tempfile.mkdtemp(prefix="원격-")) / "bare.git"
git(판, "init", "-q", "--bare", str(먼))
git(판, "remote", "add", "origin", str(먼))
git(판, "branch", "-M", "일하는갈래")
git(판, "push", "-q", "-u", "origin", "일하는갈래")
됨, 왜 = F.밀기(판, 말하기=lambda s: None)
ok(됨, f"밀었다 ({왜})")
있나 = subprocess.run(["git", "-C", str(먼), "cat-file", "-e", f"일하는갈래:{F.기록경로}"],
                    capture_output=True, text=True)
ok(있나.returncode == 0, "**원격에 기록 파일이 실제로 올라갔다** -- 적었다고 말하고 안 올리면 없느니만 못하다")
됨2, 왜2 = F.밀기(판, 말하기=lambda s: None)
ok(not 됨2 and "적을 것이 없다" in 왜2, f"바뀐 것이 없으면 빈 커밋을 안 만든다 ({왜2})")
기록전 = (판 / F.기록경로).read_text(encoding="utf-8")
subprocess.run(["git", "-C", str(판), "reset", "--hard", "-q", "HEAD"], capture_output=True)
ok((판 / F.기록경로).read_text(encoding="utf-8") == 기록전,
   "**커밋했으니 reset --hard 가 지우지 못한다** -- 배포가 하는 것이 그것이다")

print()
if fails:
    print(f"먼검사: {len(fails)}개 실패 -- {fails}")
    raise SystemExit(1)
print("farcheck: 빨강 찾기 · 늦음 셈 · 복구 · 시한초과 · 안 막음 -- 통과")
