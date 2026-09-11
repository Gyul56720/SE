"""빠른 검사 목록을 **재서 고르는지** 붙든다 -- 손으로 적은 54줄을 없앤 자리.

사용자(2026-09-11): "가능한 모든 것들(시스템 망가짐을 방지하는 필수 원칙을 빼고) 나머지를
일반해로 바꿔."

`scripts/precheck.sh` 는 돌릴 검사를 **파일 이름 54개로 나열**하고 있었다. 검사를 새로 만들
때마다 사람이 그 줄에 또 적어야 했고, 안 적으면 그 검사는 밀기 전에 **안 돌았다.**
목록이 곧 구멍이었다.

붙드는 것: (1) 안 재 본 검사는 돌린다(새 검사가 저절로 들어온다), (2) 상한을 넘은 것만
빠지고 **몇 개가 왜 빠지는지 말한다**, (3) 커밋된 씨앗 위에 이 기계에서 잰 것이 덮인다,
(4) 셀 곳과 원장 둘 곳을 가른다(precheck 는 워크트리에서 돈다), (5) precheck 에 이름 목록이
없다, (6) **진짜 저장소를 지어 precheck 를 끝까지 돌려** 새 검사가 저절로 들어오는지,
원래 빨갰던 것과 내가 깬 것을 갈라 보는지 본다.

실행: python3 tests/test_testtimes.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import testtimes as T  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


d = Path(tempfile.mkdtemp(prefix="test-tt-"))
try:
    (d / "tests").mkdir()
    for 이름 in ("test_a.py", "test_b.py", "test_c.py"):
        (d / "tests" / 이름).write_text("print('ok')\n", encoding="utf-8")
    # 이 검사는 **precheck 를 실제로 돌린다** -- 이름 때문이 아니라 그 때문에 빠져야 한다.
    (d / "tests" / "test_precheck.py").write_text(
        'subprocess.run(["bash", "scripts/precheck.sh"])\n', encoding="utf-8")

    print("== 안 재 본 것은 돌린다 (새 검사가 저절로 들어온다) ==")
    돌릴, 건너 = T.고르기(d, 상한=25)
    ok(돌릴 == ["tests/test_a.py", "tests/test_b.py", "tests/test_c.py"],
       f"원장이 비면 전부 돌린다 ({돌릴})")
    ok("tests/test_precheck.py" not in 돌릴,
       "**되돌이만 뺀다** -- precheck 안에서 돌리면 그 검사의 '실제로 돌려 보기' 가 빈 검사가 된다")
    (d / "tests" / "test_또되돌이.py").write_text(
        'subprocess.run(["bash", "scripts/precheck.sh"])\n', encoding="utf-8")
    ok("tests/test_또되돌이.py" not in T.고르기(d, 상한=25)[0],
       "**이름이 아니라 무엇을 하는지 읽어서 가른다** -- precheck 를 돌리는 검사를 하나 더 만들어도 안 샌다")
    ok(T.되돌이인가(d / "tests" / "test_a.py") is False, "안 돌리는 검사는 그대로 든다")
    (d / "tests" / "test_또되돌이.py").unlink()

    print("\n== 상한을 넘은 것만 빠지고, 몇 개가 왜 빠지는지 말한다 ==")
    T.적기("tests/test_b.py", 91.5, d)
    T.적기("tests/test_a.py", 2.0, d)
    돌릴, 건너 = T.고르기(d, 상한=25)
    ok(돌릴 == ["tests/test_a.py", "tests/test_c.py"], f"느린 것이 빠진다 ({돌릴})")
    ok(건너 == [("tests/test_b.py", 91.5)], f"무엇이 얼마라서 빠졌는지 들고 있다 ({건너})")
    ok("건너뜀 test_b.py (91.5초)" in T.보고(d, 25) and "1개 건너뛴다" in T.보고(d, 25),
       "**조용히 빠지지 않는다** -- 보고가 이름과 시간을 적는다")
    ok(T.고르기(d, 상한=25, 다시=True)[0] == ["tests/test_a.py", "tests/test_b.py", "tests/test_c.py"],
       "--다시 는 잰 것을 무시하고 전부 돌린다(다시 재기)")

    print("\n== 새 검사를 만들면 아무 데도 안 적고 들어온다 ==")
    (d / "tests" / "test_새로.py").write_text("print('new')\n", encoding="utf-8")
    ok("tests/test_새로.py" in T.고르기(d, 상한=25)[0], "**목록에 적지 않아도 들어온다** -- 이것이 없애려던 구멍")

    print("\n== 커밋된 씨앗 위에 이 기계에서 잰 것이 덮인다 ==")
    (d / T.씨앗상대).write_text(json.dumps({"test_c.py": 999.0, "test_새로.py": 0.1}), encoding="utf-8")
    ok(T.고르기(d, 상한=25)[0] == ["tests/test_a.py", "tests/test_새로.py"],
       f"씨앗만 있는 것도 골라 준다 -- **처음 온 기계가 172개를 다 돌리지 않는다** ({T.고르기(d, 상한=25)[0]})")
    T.적기("tests/test_c.py", 1.0, d)
    ok("tests/test_c.py" in T.고르기(d, 상한=25)[0],
       "**잰 것이 씨앗을 이긴다** -- 이 기계가 더 빠르거나 느릴 수 있다")
    ok(T.씨앗쓰기(d) >= 4 and json.loads((d / T.씨앗상대).read_text(encoding="utf-8"))["test_c.py"] == 1.0,
       "--씨앗쓰기 가 잰 것을 씨앗으로 굳힌다(사람이 숫자를 안 적는다)")

    print("\n== 셀 곳과 원장 둘 곳을 가른다 (precheck 는 워크트리에서 돈다) ==")
    밖 = Path(tempfile.mkdtemp(prefix="test-tt-원장-"))
    try:
        (밖 / "logs").mkdir()
        (밖 / T.원장상대).write_text(json.dumps({"test_a.py": 300.0}), encoding="utf-8")
        돌릴2, 건너2 = T.고르기(d, 상한=25, 원장저장소=밖)
        ok("tests/test_a.py" not in 돌릴2 and ("tests/test_a.py", 300.0) in 건너2,
           f"**다른 곳의 원장을 읽는다** ({건너2})")
        ok("tests/test_새로.py" in 돌릴2, "검사 목록은 그대로 셀 곳에서 센다")
    finally:
        shutil.rmtree(밖, ignore_errors=True)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n== precheck 에 이름 목록이 없다 ==")
_sh = (뿌리 / "scripts" / "precheck.sh").read_text(encoding="utf-8")
# 주석은 뺀다 -- 왜 이렇게 바꿨는지 적은 글에 예전 이름이 나오는 것은 목록이 아니다.
_돈다 = "\n".join(l for l in _sh.splitlines() if not l.lstrip().startswith("#"))
_적힌 = re.findall(r"tests/test_[^\s\"']+\.py", _돈다)
ok(not _적힌, f"**돌아가는 줄에 검사 파일 이름을 한 줄도 안 적는다** ({_적힌[:4]})")
ok("testtimes.py --고르기" in _sh, "재서 고른 것을 쓴다")
ok("--적기" in _sh and '--원장저장소 "$root"' in _sh,
   "잰 것을 **진짜 저장소에** 남긴다(워크트리는 곧 지워진다)")
ok("merge-base" in _sh, "빨간 것은 갈림점에서 다시 돌려 본다")
ok(not re.compile(r"^\s*[가-힣][가-힣A-Za-z0-9_]*\s*=", re.M).findall(_sh),
   "셸에 한글 변수 이름을 쓰지 않는다")

print("\n== 진짜 저장소를 지어 precheck 를 끝까지 돌린다 ==")
# CLAUDE.md: "셸 스크립트를 검사할 때는 임시 저장소를 지어 실제로 돌린다."
os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
판 = Path(tempfile.mkdtemp(prefix="test-tt-판-"))
원격 = Path(tempfile.mkdtemp(prefix="test-tt-원격-"))
try:
    subprocess.run(["git", "init", "--bare", "-q", str(원격)], check=False)
    git(판, "init", "-q"); git(판, "checkout", "-qb", "main")
    (판 / "scripts").mkdir()
    shutil.copy(뿌리 / "scripts" / "precheck.sh", 판 / "scripts" / "precheck.sh")
    shutil.copy(뿌리 / "testtimes.py", 판 / "testtimes.py")
    (판 / "tests").mkdir()
    (판 / "tests" / "test_초록.py").write_text("print('초록')\n", encoding="utf-8")
    (판 / "tests" / "test_원래빨강.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    (판 / ".gitignore").write_text("logs/\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "init")
    git(판, "remote", "add", "origin", str(원격))
    git(판, "push", "-q", "-u", "origin", "main")

    def 돌리기():
        p = subprocess.run(["bash", "scripts/precheck.sh"], cwd=str(판),
                           capture_output=True, text=True, timeout=300)
        return p.returncode, p.stdout + p.stderr

    rc, 글 = 돌리기()
    ok("test_초록.py" in 글 and "test_원래빨강.py" in 글,
       "**아무 목록에도 안 적힌 검사 둘을 스스로 찾아 돌린다**")
    ok(rc == 0 and "갈림점에서도 빨강" in 글 and "초록이라고 말하지 않는다" in 글,
       f"원래 빨갰던 것은 밀기를 막지 않되 **그대로 말한다** (끝값 {rc})")
    ok((판 / "logs" / "test_times.json").is_file(), "잰 것이 원장에 쌓인다")
    잰 = json.loads((판 / "logs" / "test_times.json").read_text(encoding="utf-8"))
    ok("test_초록.py" in 잰, f"이름과 시간을 남긴다 ({잰})")

    print("\n  -- 내가 깬 것은 막는다 (갈림점에선 초록이었다) --")
    (판 / "tests" / "test_초록.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "깼다")
    rc, 글 = 돌리기()
    ok(rc == 1 and "내가 깬 것 1 개" in 글 and "갈림점에선 초록이었다" in 글,
       f"**내가 깬 것은 밀기를 막는다** (끝값 {rc})")
    ok("원래 빨갰던 것 1 개" in 글, "원래 빨간 것과 갈라 센다")

    print("\n  -- 갈림점에 없던 새 검사가 빨가면 내 탓이다 --")
    (판 / "tests" / "test_초록.py").write_text("print('초록')\n", encoding="utf-8")
    (판 / "tests" / "test_새검사.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "새 검사")
    rc, 글 = 돌리기()
    ok(rc == 1 and "갈림점엔 없던 검사다" in 글, f"새로 들어온 빨간 검사는 내 탓 (끝값 {rc})")

    print("\n  -- 느린 것은 빠지되 말한다 --")
    (판 / "tests" / "test_새검사.py").write_text("print('고쳤다')\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "고침")
    T.적기("tests/test_새검사.py", 999.0, 판)
    rc, 글 = 돌리기()
    ok("test_새검사.py" not in 글.split("갈림점")[0], "상한을 넘은 것은 안 돌린다")
    ok("건너뛴 1 개" in 글 or "1 개는 CI" in 글, f"몇 개를 건너뛰었는지 말한다 ({글.strip().splitlines()[-1][:70]})")
finally:
    shutil.rmtree(판, ignore_errors=True)
    shutil.rmtree(원격, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("testtimes: 재서 고르기 · 새 검사 자동 · 씨앗 · 원장 가르기 · 진짜 저장소에서 갈림점 판정 -- 통과")
