"""거짓 초록 사냥(mutate)을 **진짜 저장소**로 붙든다.

사용자(2026-09-12): "거짓 초록이 문제인데, 그냥 거짓 초록을 24시간 동안 보는 기능을 만들어."
그리고 물었다 -- 절제(red-green)를 넣었으면 거짓 초록은 이론적으로 안 걸리나?

안 걸린다. 절제는 몸통을 `raise` 로 바꾸므로 **그 함수를 부르기만 하는 검사도** 빨개진다.
즉 절제가 증명하는 것은 '검사가 그것을 부른다' 이고 '결과를 본다' 가 아니다. 변형은 그 자리를
본다: 조용히 틀린 값을 돌려줘도 초록이면 그 검사는 부르기만 하고 보지 않는다.

붙드는 것: (1) 변형이 조용하다(예외를 안 던진다), (2) 결과를 단언하는 검사는 변형을 죽인다,
(3) 부르기만 하는 검사는 변형을 **살려** 둔다(= 거짓 초록, 원장에 남는다), (4) 절제는 그 둘을
구별하지 못한다(같은 검사로 보여 준다), (5) 원래 빨간 검사는 못잼으로 적고 판정하지 않는다,
(6) 재는 검사가 없는 파일도 못잼, (7) 시한을 지킨다, (8) 원장은 덧붙이기만 하고 보고가 그것을 읽는다.

실행: python3 tests/test_mutate.py
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

import mutate as M  # noqa: E402
import rehearsal as R  # noqa: E402

FAIL: list = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})

print("== 변형은 조용하다 -- 터뜨리지 않고 틀린 값을 돌려준다 ==")
src = "def 더하기(a, b):\n    if a == 0:\n        return b\n    return a + b\n"
변 = M.변형들(src, "더하기")
ok(변 and all("raise" not in 새 for _설명, 새 in 변), f"예외를 던지는 변형이 없다 ({len(변)}개)")
ok(any("return None" in 새 for _s, 새 in 변), "반환값을 None 으로 바꾸는 변형이 있다")
ok(any("a != 0" in 새 for _s, 새 in 변), "비교를 뒤집는 변형이 있다")
ok(M.변형들(src, "없는함수") == [], "없는 함수는 빈 목록")
ok(M.변형들("def f(): pass\n", "f") == [], "바꿀 것이 없는 함수는 빈 목록(한 줄 pass)")

판 = Path(tempfile.mkdtemp(prefix="test-mut-"))
try:
    git(판, "init", "-q")
    (판 / "tests").mkdir()
    (판 / "계산.py").write_text("def 더하기(a, b):\n    return a + b\n", encoding="utf-8")
    # 보는 검사: 값을 단언한다. 안 보는 검사: 부르기만 한다.
    (판 / "tests" / "test_계산.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport 계산\nassert 계산.더하기(1, 2) == 3\nprint("본다")\n',
        encoding="utf-8")
    (판 / "부름.py").write_text("def 곱하기(a, b):\n    return a * b\n", encoding="utf-8")
    (판 / "tests" / "test_부름.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport 부름\n부름.곱하기(2, 3)\nprint("부르기만 한다")\n',
        encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "init")

    print("\n== 결과를 단언하는 검사는 변형을 죽인다 ==")
    r = M.사냥(판, 파일들=["계산.py"], 시한초=120, 말하기=lambda s: None)
    ok(r["잰변형"] >= 1 and r["살아남음"] == 0 and r["죽음"] == r["잰변형"],
       f"변형 {r['잰변형']}개가 다 죽었다 -- 그 검사는 본다 (살아남음 {r['살아남음']})")

    print("\n== 부르기만 하는 검사는 변형을 살린다 -- 증명된 거짓 초록 ==")
    r2 = M.사냥(판, 파일들=["부름.py"], 시한초=120, 말하기=lambda s: None)
    ok(r2["살아남음"] >= 1 and r2["살아남은것"][0]["파일"] == "부름.py",
       f"**부르기만 하는 검사에서는 변형이 살아남는다** ({r2['살아남음']}개)")
    ok(r2["살아남은것"][0]["함수"] == "곱하기" and "return None" in r2["살아남은것"][0]["변형"],
       f"어느 함수의 어떤 변형이 살았는지 적는다 ({r2['살아남은것'][0]['변형']})")
    원 = M.원장읽기(판)
    ok(any(x.get("꼴") == "살아남음" and x.get("파일") == "부름.py" for x in 원), "원장에 살아남은 변형이 남는다")
    ok(any(x.get("꼴") == "사냥끝" for x in 원), "사냥 끝 줄이 남는다")
    보 = M.보고(판)
    ok("거짓 초록" in 보 and "부름.py" in 보 and "곱하기" in 보, f"보고가 원장을 읽어 사람 말로 적는다 ({보[:60]!r})")

    print("\n== 절제는 그 둘을 구별하지 못한다 (그래서 변형이 따로 필요하다) ==")
    w = Path(tempfile.mkdtemp(prefix="판-"))
    git(판, "worktree", "add", "-q", "--detach", str(w), "HEAD")
    try:
        (w / "부름.py").write_text("def 곱하기(a, b):\n    return a * b + 0\n", encoding="utf-8")
        (w / "tests" / "test_부름.py").write_text(      # 패치에 검사가 들어야 절제가 잰다 -- 한 줄 더한다
            'import sys; sys.path.insert(0, ".")\nimport 부름\n부름.곱하기(2, 3)\nprint("부르기만 한다")\nprint("둘")\n',
            encoding="utf-8")
        절 = R.절제검사(판, w)
        ok(절["성립"] and [x["이름"] for x in 절["잰것"]] == ["부름.py:곱하기"],
           f"**절제는 '부르기만 하는 검사' 를 통과시킨다** -- raise 가 호출에서 터지므로 (성립 {절['성립']})")
    finally:
        git(판, "worktree", "remove", "--force", str(w))

    print("\n== 판정 정의: 비등가 · 덮임 · 동등제외를 가른다 (사용자 정의 2026-09-12) ==")
    # "원본이 통과한 뒤, 의미를 보존하지 않는 유한한 독립 변형 집합을 같은 검사·환경에서 돌려, 원본과
    # 구별되어 실패해야 할 **비등가** 변형이 하나라도 통과하면 거짓 Green. **동등 변형은 별도 판정으로 제외.**"
    ok(M.동등한가("def f(a):\n    return a + 1\n", "def f(a):\n    return a + 1\n"), "같은 글은 동등(TCE)")
    ok(M.동등한가("def f(a):\n    return a + 1\n", "def f(a):\n    # 주석\n    return a + 1\n"),
       "주석·줄번호만 다른 것은 동등 -- 의미가 보존됐다")
    ok(not M.동등한가("def f(a):\n    return a + 1\n", "def f(a):\n    return None\n"), "값이 달라지는 변형은 비등가")
    ok(not M.동등한가("def f(a):\n    return a + 1\n", "def f(a):\n    return a - 1\n"), "연산이 달라지는 변형은 비등가")

    (판 / "반쪽.py").write_text(
        "def 고르기(x):\n"
        "    if x > 100:\n"
        "        return '큰것'\n"
        "    return '작은것'\n", encoding="utf-8")
    (판 / "tests" / "test_반쪽.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport 반쪽\nassert 반쪽.고르기(1) == "작은것"\nprint("작은 쪽만 본다")\n',
        encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "반쪽만 덮는 검사")
    덮 = M.덮인줄(판, "반쪽.py", ["tests/test_반쪽.py"])
    ok(2 in 덮 and 4 in 덮 and 3 not in 덮, f"**실행된 줄만 덮임으로 센다** -- 큰 쪽(3줄)은 안 돌았다 ({sorted(덮)})")
    r6 = M.사냥(판, 파일들=["반쪽.py"], 시한초=180, 말하기=lambda s: None)
    ok(r6["덮이지않음"] >= 1 and any(x["변형"].startswith("3줄") for x in r6["덮이지않은것"]),
       f"**안 덮인 줄의 변형은 '거짓초록' 이 아니라 '덮이지않음' 이다** (덮이지않음 {r6['덮이지않음']})")
    ok(all(not x["변형"].startswith("3줄") for x in r6["살아남은것"]),
       "덮이지 않은 변형을 거짓초록으로 세지 않는다 -- 그랬으면 판정 자체가 거짓이 된다")
    ok(any(x.get("꼴") == "덮이지않음" for x in M.원장읽기(판)) and any(x.get("꼴") == "덮임" for x in M.원장읽기(판)),
       "원장에 덮임과 덮이지않음이 남는다")
    보2 = M.보고(판)
    ok("덮이지않음" in 보2 or "한 번도 실행되지 않는" in 보2, "보고가 둘을 갈라 말한다")

    print("\n== 못 재는 것은 못 잰다고 적는다 ==")
    (판 / "혼자.py").write_text("def 아무것(x):\n    return x + 1\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "검사 없는 파일")
    r3 = M.사냥(판, 파일들=["혼자.py"], 시한초=60, 말하기=lambda s: None)
    ok(r3["잰변형"] == 0 and r3["못잼"] == 1 and any(x.get("꼴") == "검사없음" for x in M.원장읽기(판)),
       f"재는 검사가 없으면 못잼 -- 그 자체가 틈이다 (못잼 {r3['못잼']})")
    (판 / "tests" / "test_깨진.py").write_text('raise SystemExit(1)\n', encoding="utf-8")
    (판 / "깨진.py").write_text("def f(a):\n    return a + 1\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "원래 빨간 검사")
    r4 = M.사냥(판, 파일들=["깨진.py"], 시한초=60, 말하기=lambda s: None)
    ok(r4["잰변형"] == 0 and r4["못잼"] == 1 and any(x.get("꼴") == "원래빨강" for x in M.원장읽기(판)),
       f"**원래 빨간 검사로는 아무것도 증명하지 못한다** -- 못잼으로 적는다 (못잼 {r4['못잼']})")

    print("\n== 시한을 지킨다 ==")
    import time as _t
    시작 = _t.monotonic()
    r5 = M.사냥(판, 파일들=["계산.py", "부름.py", "깨진.py"], 시한초=1, 말하기=lambda s: None)
    ok(_t.monotonic() - 시작 < 60, f"시한 1초를 주면 곧 멈춘다 ({_t.monotonic() - 시작:.1f}초)")
    ok(git(판, "worktree", "list").stdout.strip().count("\n") == 0, "변형 워크트리가 안 남는다")

    print("\n== 배선 ==")
    _서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
    ok("mutate" in (뿌리 / "dispatch.py").read_text(encoding="utf-8")
       or "거짓초록" in (뿌리 / "dispatch.py").read_text(encoding="utf-8"), "dispatch 가 거짓초록 명령을 안다")
    ok("mutate.py" in (뿌리 / ".github/workflows/deploy-oracle.yml").read_text(encoding="utf-8"),
       "배포가 mutate.py 를 서버에 올린다")
finally:
    shutil.rmtree(판, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("mutate: 조용한 변형 · 보는 검사는 죽인다 · 부르기만 하면 살린다 · 절제와의 차이 · 비등가·덮임·동등제외 · 못잼 · 시한 · 원장 · 배선 -- 통과")
