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
ok(변 and all("raise" not in 새 for _op, _설명, 새, _자취 in 변), f"예외를 던지는 변형이 없다 ({len(변)}개)")
ok(any("return None" in 새 for _op, _s, 새, _t in 변), "반환값을 None 으로 바꾸는 변형이 있다")
ok(any("a != 0" in 새 for _op, _s, 새, _t in 변), "비교를 뒤집는 변형이 있다")

print("\n== 사양이 정한 최소 범위를 다 덮는다 {Return, Constant, Comparison, Boolean, Branch} ==")
_풍부 = """def 고르기(x, y):
    if x > 100 and y:
        return x * 2
    else:
        a = 1
        return a
"""
_변2 = 변형들_ = M.변형들(_풍부, "고르기")
_종류 = {op for op, _s, _n, _t in _변2}
for _요구 in ("return_none", "return_zero", "return_minus1", "const_return", "const_num",
            "cmp_negate", "cmp_boundary", "bool_negate", "bool_swap",
            "branch_drop", "branch_force", "branch_swap"):
    ok(_요구 in _종류, f"연산자 {_요구} 가 있다")
ok(any("x <= 100" in 새 for op, _s, 새, _t in _변2 if op == "cmp_negate"), "`>` 의 부정 짝은 `<=` 다(사양)")
ok(any("x >= 100" in 새 for op, _s, 새, _t in _변2 if op == "cmp_boundary"), "경계 짝은 `>=` 다(off-by-one)")
ok(all("raise" not in 새 for _op, _s, 새, _t in _변2), "범위 안의 어느 변형도 예외를 던지지 않는다")

print("\n== Δ(P, Pm) = {m}: 자취를 선언하고 그대로인지 본다 ==")
_스왑 = [(op, 새, 자취) for op, _s, 새, 자취 in _변2 if op == "branch_swap"][0]
ok(len(_스왑[2]) > 1, f"가지 맞바꾸기는 여러 줄을 건드린다 (자취 {sorted(_스왑[2])})")
ok(M.단일변형인가(_풍부, _스왑[1], _스왑[2])[0],
   "**선언한 자취와 같으면 단일 변형이다** -- '한 줄' 이 단일성의 정의가 아니다")
ok(not M.단일변형인가(_풍부, _스왑[1], frozenset({3}))[0],
   "선언한 자취 밖이 바뀌었으면 단일 변형이 아니다(INVALID_MUTATION)")
_두개 = _풍부.replace("return x * 2", "return None").replace("a = 1", "a = 2")
ok(not M.단일변형인가(_풍부, _두개, frozenset({3}))[0], "두 곳을 바꾸면 단일 변형이 아니다")
ok(M.단일변형인가(_풍부, _풍부.replace("return x * 2", "return None"), 3)[0],
   "정수 한 줄로 주는 옛 꼴도 받는다")
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
    # 순서는 π0 의 씨앗으로 섞인다 -- 어느 변형이 먼저 오는지에 기대지 않는다(그러면 씨앗을 바꾸면 빨개진다)
    ok(all(x["함수"] == "곱하기" for x in r2["살아남은것"])
       and any("return" in x["변형"] for x in r2["살아남은것"]),
       f"어느 함수의 어떤 변형이 살았는지 적는다 ({[x['변형'][:28] for x in r2['살아남은것']][:3]})")
    원 = M.원장읽기(판)
    ok(any(x.get("classification") == M.거짓초록 and x.get("target", "").startswith("부름.py") for x in 원),
       "원장에 FALSE_GREEN 줄이 남는다(분류 이름으로)")
    ok(any(x.get("꼴") == "사냥끝" for x in 원), "사냥 끝 줄이 남는다")
    보 = M.보고(판)
    ok("거짓 초록" in 보 and "부름.py" in 보 and M.거짓초록 in 보, f"보고가 원장을 읽어 사람 말로 적는다 ({보[:60]!r})")

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
    # 정의대로: 안 덮인 줄의 생존도 FG 다(의미가 달라졌는데 검사가 못 잡았다). 다만 **까닭이 다르다** --
    # 단언이 약한 것이 아니라 그 줄에 닿지 않은 것이다. 그래서 why 로 갈라 적고 보고가 따로 센다.
    ok(any(x.get("classification") == M.거짓초록 and x.get("why") == "not_covered"
           for x in M.원장읽기(판)), "안 덮인 줄의 생존은 why=not_covered 로 적힌다")
    ok(any(x.get("꼴") == "덮임" for x in M.원장읽기(판)), "원장에 덮임 줄이 남는다")
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

    print("\n== 사양의 네 사례 (Case A~D) · 2차 메타검증 ==")
    # 사용자(2026-09-12): "Red/Green 은 1차 전이, FR/FG 는 그 판정이 옳았나를 보는 2차 메타층."
    #   Commit(P) = 1[ V(P)=1 ∧ T(P)=PASS ∧ (FG ∪ FR) = ∅ ]

    print("  -- Case A: 반환값을 바꾸면 검사가 잡는다 -> VALID_RED --")
    rA = M.사냥(판, 파일들=["계산.py"], 시한초=180, 말하기=lambda s: None)
    ok(rA.get(M.유효빨강, 0) >= 1 and rA.get(M.거짓빨강, 0) == 0 and rA.get(M.거짓초록, 0) == 0,
       f"Case A -- VALID_RED {rA.get(M.유효빨강, 0)} · FALSE_RED {rA.get(M.거짓빨강, 0)} · FALSE_GREEN {rA.get(M.거짓초록, 0)}")
    ok(all(x.get("baseline_rerun_status") == "PASS" for x in M.원장읽기(판)
           if x.get("classification") == M.유효빨강),
       "**모든 VALID_RED 은 되돌림 재실행이 PASS 였다** -- 귀속이 차감으로 증명된다")
    # 길이가 같은 변형(a + b -> a - b)이 VALID_RED 로 남아야 한다 -- 낡은 .pyc 가 거짓 Red 를 만들던 자리
    ok(any(x.get("operator") == "arith_swap" and x.get("classification") == M.유효빨강 for x in M.원장읽기(판)),
       "**길이가 같은 변형도 VALID_RED** -- 바이트코드 캐시를 꺼서 거짓 Red 가 안 난다(실측 회귀)")

    print("  -- Case B: 틀린 값으로 바꿨는데 계속 PASS -> FALSE_GREEN --")
    rB = M.사냥(판, 파일들=["부름.py"], 시한초=180, 말하기=lambda s: None)
    ok(rB.get(M.거짓초록, 0) >= 1 and rB.get(M.유효빨강, 0) == 0,
       f"Case B -- FALSE_GREEN {rB.get(M.거짓초록, 0)} (부르기만 하는 검사)")
    ok(any(x.get("classification") == M.거짓초록 and x.get("why") == "weak_assertion"
           for x in M.원장읽기(판)), "까닭이 weak_assertion 으로 적힌다(덮임의 구멍과 구별된다)")

    print("  -- Case D: 변형과 무관한 실패는 VALID_RED 가 아니다 -> FALSE_RED --")
    # 샌드박스 **밖**의 상태를 지우는 검사. 바탕은 지나가고(그때 지운다), 그 뒤의 모든 실행이 빨갛다.
    밖 = Path(tempfile.mkdtemp(prefix="밖-")) / "딸림.txt"
    밖.write_text("있다", encoding="utf-8")
    (판 / "밖읽기.py").write_text("def 읽기():\n    return 1\n", encoding="utf-8")
    (판 / "tests" / "test_밖읽기.py").write_text(
        'import os, sys\nsys.path.insert(0, ".")\nimport 밖읽기\n'
        f'p = {str(밖)!r}\n'
        'assert 밖읽기.읽기() == 1\n'
        'assert open(p).read() == "있다"\n'
        'os.remove(p)                      # 샌드박스 밖의 상태를 지운다 -- 다음 실행은 이것 때문에 빨갛다\n'
        'print("한 번만 통과한다")\n', encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "밖의 상태에 매인 검사")
    rD = M.사냥(판, 파일들=["밖읽기.py"], 시한초=180, 말하기=lambda s: None)
    ok(rD.get(M.유효빨강, 0) == 0,
       f"**Case D -- VALID_RED 이 하나도 없다** (변형 탓이 아닌 실패를 잡힌 것으로 세지 않는다): {dict((k, v) for k, v in rD.items() if isinstance(v, int))}")
    ok(rD.get(M.거짓빨강, 0) >= 1 or rD.get(M.못쓸바탕, 0) >= 1,
       f"Case D -- FALSE_RED {rD.get(M.거짓빨강, 0)} · INVALID_BASELINE {rD.get(M.못쓸바탕, 0)} 으로 적힌다")
    ok(any(x.get("classification") in (M.거짓빨강, M.못쓸바탕) and "FileNotFound" in (x.get("traceback", "") + x.get("failure_cause", ""))
           or x.get("classification") in (M.거짓빨강, M.못쓸바탕) for x in M.원장읽기(판)),
       "원장에 까닭이 남는다(fixture/config missing 류)")

    print("  -- 2차 메타검증: Commit = Green ∧ (FR∪FG)^c --")
    ok(M.신뢰(True, {M.유효빨강: 3})["commit"] is True, "1차 초록 + FG·FR 없음 -> 커밋 허용")
    ok(M.신뢰(True, {M.유효빨강: 3, M.거짓초록: 1})["commit"] is False, "**FG 가 있으면 초록이어도 막는다**")
    ok(M.신뢰(True, {M.유효빨강: 3, M.거짓빨강: 1})["commit"] is False, "**FR 이 있으면 초록이어도 막는다**")
    ok(M.신뢰(True, {M.못쓸변형: 1})["commit"] is False, "판정에 쓸 수 없는 것이 남으면 막는다")
    ok(M.신뢰(False, {M.유효빨강: 3})["commit"] is False and M.신뢰(False, {M.유효빨강: 3})["reliable"] is True,
       "1차가 Red 면 막지만, 그 Red 자체는 신뢰할 수 있다(두 층이 다르다)")
    ok(M.마지막사냥(판).get("꼴") == "사냥끝", "원장에서 마지막 사냥을 찾는다")
    ok(M.마지막사냥(Path(tempfile.mkdtemp(prefix="빈-"))) == {},
       "**사냥을 안 한 저장소는 빈 것을 준다** -- 안 한 것을 초록으로 읽지 않게")

    print("\n== 판정 순서: PASS/FAIL 을 보기 전에 Invalid · Equivalent 를 걸러낸다 ==")
    # 사용자(2026-09-12): "Mutation Outcome FAIL -> Killed, PASS -> FalseGreen 으로 바로 결정하면 안 된다.
    # 먼저 Equivalent, Invalid, FalseRed 를 걸러야 논리적으로 닫힌 구조가 된다."
    ok(M.다섯갈래 == (M.잡힘, M.살아남음, M.동등, M.거짓빨강결과, M.못쓸),
       f"변형 결과가 다섯 갈래다 {M.다섯갈래}")
    ok(M.변형유효한가("def f():\n    return 1\n")[0], "말이 되는 변형은 M_valid 다")
    ok(not M.변형유효한가("def f():\nreturn 1\n")[0], "**문법이 깨진 변형은 M_valid 가 아니다** -- Killed 로 세면 안 된다")
    ok(not M.변형유효한가("def f(:\n    return 1\n")[0], "괄호가 깨진 변형도 아니다")
    원 = M.원장읽기(판)
    ok(all(x.get("outcome") in M.다섯갈래 for x in 원 if x.get("outcome")),
       "원장의 모든 결과가 다섯 갈래 안에 있다")
    ok(all(x.get("mutation_valid") is not False for x in 원 if x.get("outcome") == M.잡힘),
       "Killed 로 센 것 중 M_valid 가 아닌 것이 없다")
    ok(all(x.get("single_mutation") is True and x.get("environment_preserved") is not False
           for x in 원 if x.get("outcome") == M.잡힘),
       "**Killed 는 Δ={m} 과 E(P)=E(Pm) 을 다 지난 것만이다**")
    ok(all(x.get("baseline_rerun_status") == "PASS" for x in 원 if x.get("outcome") == M.잡힘),
       "**Killed 는 되돌림 재실행이 PASS 인 것만이다** (Cause(FAIL)=m)")

    print("\n== D_t: π 가 배울 재료가 원장에 다 있나 (사용자 2026-09-12) ==")
    # R(m) = αFG(m) + βFR(m) + γΔJ(m) - λCost(m) -- 마지막 항을 쓰려면 **변형마다 cost** 가 있어야 한다.
    # 24시간 데이터는 한 번만 모인다: 그때 안 적으면 그 항을 영영 못 쓴다.
    원3 = [x for x in M.원장읽기(판) if x.get("operator")]
    ok(원3 and all(isinstance((x.get("cost") or {}).get("초"), (int, float)) for x in 원3),
       f"변형 줄마다 cost(초)가 있다 ({len(원3)}줄)")
    빠진 = [k for k in ("operator", "target", "outcome", "classification", "cost")
          if not all(k in x for x in 원3)]
    ok(not 빠진, f"D_t 의 칸(m · file · FG/FR · cost)이 다 있다 (빠진 것 {빠진})")
    표 = M.연산자표(판)
    ok("연산자" in 표 and "초/개" in 표 and "return_none" in 표,
       f"**연산자표가 무엇을 얼마에 찾았나를 낸다** -- π 의 재료 ({표.splitlines()[0][:40]!r})")
    ok("**연산자별**" in M.둘다보고(판), "둘다보고에 연산자표가 붙는다")

    print("\n== Obs(T, P): 검사가 결과를 관찰하나 (측정으로 정의한다) ==")
    됐나, 말 = M.관찰됐나(판, "계산.py:더하기")
    ok(됐나 and "잡혔다" in 말, f"값을 단언하는 검사 -> 관찰한다 ({말})")
    됐나2, 말2 = M.관찰됐나(판, "부름.py:곱하기")
    ok(not 됐나2 and "부르기만" in 말2, f"**부르기만 하는 검사 -> 관찰하지 않는다** ({말2})")
    됐나3, 말3 = M.관찰됐나(판, "없는.py:없는함수")
    ok(not 됐나3 and "재 본 적이 없다" in 말3, "재 본 적이 없으면 관찰됐다고 하지 않는다")

    print("\n== 거짓 빨강 사냥: 빨강이 거짓인 검사를 찾는다 ==")
    # 사용자(2026-09-12): "왜 거짓 빨강은 조사 안 해?"  맞는 지적이었다 -- FG 에는 사냥이 있는데 FR 에는 없었다.
    # 표본이 이미 있었다: CI 의 test_law_hwp(권한) · 이 컨테이너의 test_compression_judge(캐시) · Case D.
    (판 / "tests" / "test_멀쩡.py").write_text('print("늘 초록")\n', encoding="utf-8")
    (판 / "tests" / "test_진짜빨강.py").write_text('raise AssertionError("늘 빨강")\n', encoding="utf-8")
    (판 / "쓰는것.txt").write_text("있다", encoding="utf-8")
    (판 / "tests" / "test_오염.py").write_text(
        'import os\nassert open("쓰는것.txt").read() == "있다"\nos.remove("쓰는것.txt")\nprint("한 번만")\n',
        encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "FR 표본들")
    (판 / "안추적.txt").write_text("작업 트리에만 있다", encoding="utf-8")      # 커밋하지 않는다
    (판 / "tests" / "test_환경.py").write_text(
        'assert open("안추적.txt").read().startswith("작업")\nprint("작업 트리에서만 초록")\n', encoding="utf-8")
    git(판, "add", "tests/test_환경.py"); git(판, "commit", "-qm", "환경 의존 검사")
    fr = M.거짓빨강사냥(판, 검사들=["tests/test_멀쩡.py", "tests/test_진짜빨강.py",
                              "tests/test_오염.py", "tests/test_환경.py"],
                   시한초=240, 말하기=lambda s: None)
    ok(fr["잰것"] == 4, f"넷을 쟀다 ({fr['잰것']})")
    ok(fr[M.멀쩡] == 1, f"늘 초록인 검사는 멀쩡 ({fr[M.멀쩡]})")
    ok(fr[M.상태오염] == 1 and any(x["검사"] == "tests/test_오염.py" and x["분류"] == M.상태오염
                               for x in fr["찾은것"]),
       f"**두 번째에 빨강 -> 상태오염** (제 상태를 지운다) ({fr[M.상태오염]})")
    ok(fr[M.환경의존] == 1 and any(x["검사"] == "tests/test_환경.py" and x["분류"] == M.환경의존
                               for x in fr["찾은것"]),
       f"**깨끗한 판에서만 빨강 -> 환경의존** (추적 안 되는 파일에 매였다) ({fr[M.환경의존]})")
    ok(fr[M.원래빨강] == 1, f"둘 다 빨강이면 진짜 빨강 -- 거짓이 아니다 ({fr[M.원래빨강]})")
    원2 = M.원장읽기(판)
    ok(any(x.get("꼴") == "거짓빨강" and x.get("classification") == M.환경의존 for x in 원2),
       "원장에 분류와 까닭이 남는다")
    ok("거짓 빨강" in M.FR보고(판) and "환경의존" in M.FR보고(판), "FR보고가 원장을 읽는다")
    fr줄 = [x for x in M.원장읽기(판) if x.get("꼴") == "거짓빨강"]
    ok(fr줄 and all(isinstance((x.get("cost") or {}).get("초"), (int, float)) for x in fr줄),
       f"FR 줄마다 cost(초)가 있다 -- R(m) 의 λCost 항 ({len(fr줄)}줄)")
    ok(any(x.get("꼴") == "FR사냥시작" and (x.get("정책") or {}).get("seed") == 0 for x in M.원장읽기(판)),
       "**원장이 π0 를 적는다** -- seed 까지(그래야 π0 vs π1 차이가 씨앗 탓이 아니라고 말할 수 있다)")
    ok(git(판, "worktree", "list").stdout.strip().count("\n") == 0, "FR 사냥 워크트리가 안 남는다")

    print("\n== 둘 다 한 번에: 거짓 빨강 -> 거짓 초록 (순서가 뜻을 만든다) ==")
    둘 = M.둘다사냥(판, 시한초=300, 파일들=["계산.py"], 말하기=lambda s: None)
    ok("FR" in 둘 and "FG" in 둘, "둘을 같이 돌려 둘을 돌려준다")
    ok(둘["FR"]["잰것"] >= 4 and 둘["FG"]["잰변형"] >= 1, f"FR {둘['FR']['잰것']}개 · FG 변형 {둘['FG']['잰변형']}개")
    ok(set(둘["못믿을검사"]) >= {"tests/test_오염.py", "tests/test_환경.py"},
       f"**바탕으로 쓸 수 없는 검사를 먼저 알려 준다** ({둘['못믿을검사']})")
    ok(any(x.get("꼴") == "둘다끝" for x in M.원장읽기(판)), "원장에 둘다끝이 남는다")
    # 사용자(2026-09-12): "현재 테스트는 `뺄검사=[x] => x 제외` 만 보인다. 그것은 옵션이 동작한다는 말이고
    # **FR 이 찾은 것이 실제로 빠진다**는 말이 아니다." 맞는 지적이라 끝까지 잇는다:
    #   FR(x)  =>  x ∈ 못믿을검사  =>  FG 가 x 를 바탕으로 쓰지 않는다
    # 그리고 ReliableTest = RG0 ∧ ¬FR이력 -- **RG0 통과는 신뢰성이 아니다**(상태오염은 첫 실행이 초록이다).
    (판 / "붙은것.py").write_text("def g(a):\n    return a + 1\n", encoding="utf-8")
    (판 / "tests" / "test_붙은것.py").write_text(              # 제 상태를 남긴다 -> 두 번째에 빨강
        'import os, sys\nsys.path.insert(0, ".")\nimport 붙은것\n'
        'assert 붙은것.g(1) == 2\n'
        'assert not os.path.exists("찌꺼기.txt"), "두 번째 실행이다"\n'
        'open("찌꺼기.txt", "w").write("x")\nprint("한 번만 초록")\n', encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "상태를 남기는 검사 + 그것만이 재는 코드")
    깨 = Path(tempfile.mkdtemp(prefix="RG0-"))
    git(판, "worktree", "add", "-q", "--detach", str(깨), "HEAD")
    try:
        ok(M._돌려보기(깨, ["tests/test_붙은것.py"])[0] is False,
           "**RG0 는 통과한다** -- 첫 실행은 초록이다(그래서 RG0 만으로는 신뢰성을 판단할 수 없다)")
    finally:
        git(판, "worktree", "remove", "--force", str(깨))
    fr2 = M.거짓빨강사냥(판, 검사들=["tests/test_붙은것.py"], 시한초=120, 말하기=lambda s: None)
    ok(fr2[M.상태오염] == 1, f"**FR 사냥이 상태오염으로 잡는다** ({fr2[M.상태오염]})")
    ok("tests/test_붙은것.py" in M.못믿을검사들(판),
       f"**FR(x) => x ∈ 못믿을검사** -- 원장의 FR 이력으로 읽는다 ({M.못믿을검사들(판)})")
    행 = [x for x in M.원장읽기(판) if x.get("test") == "tests/test_붙은것.py"][-1]
    빠진칸 = [k for k in ("test", "baseline_pass", "repeat_fail", "cause", "classification") if k not in 행]
    ok(not 빠진칸, f"원장 줄에 사양의 칸이 다 있다 (빠진 것 {빠진칸})")
    ok(행["baseline_pass"] is True and 행["repeat_fail"] is True,
       f"그 줄이 'RG0 는 지났고 두 번째에 무너졌다' 를 적는다 ({행['baseline_pass']} · {행['repeat_fail']})")
    둘2 = M.둘다사냥(판, 시한초=300, 파일들=["붙은것.py"], 말하기=lambda s: None)
    ok("tests/test_붙은것.py" in 둘2["못믿을검사"], f"둘다사냥이 FR 결과를 그대로 들고 간다 ({둘2['못믿을검사']})")
    ok(둘2["FG"]["잰변형"] == 0 and 둘2["FG"]["못잼"] >= 1,
       f"**FG 가 그 검사를 바탕으로 쓰지 않는다 -- 변형을 하나도 안 재고 못잼으로 적는다** "
       f"(잰변형 {둘2['FG']['잰변형']} · 못잼 {둘2['FG']['못잼']})")
    홀로 = M.사냥(판, 파일들=["붙은것.py"], 시한초=120, 말하기=lambda s: None)
    ok(홀로["잰변형"] >= 1,
       f"**FR 을 먼저 안 돌리면 그 검사를 바탕으로 써 버린다** -- 그래서 순서가 판정을 바꾼다 ({홀로['잰변형']}개 쟀다)")
    # 보조: 고리 하나를 따로 붙든다(사용자 권고). 사슬이 깨졌을 때 **어느 고리가** 끊겼는지 짚으려면
    # 자동 사슬만으로는 모자란다 -- 수동 주입은 `뺄검사` 옵션 자체가 살아 있는지만 본다.
    손으로 = M.사냥(판, 파일들=["붙은것.py"], 시한초=120, 말하기=lambda s: None,
                뺄검사=["tests/test_붙은것.py"])
    ok(손으로["잰변형"] == 0 and 손으로["못잼"] >= 1,
       f"(보조) `뺄검사` 옵션 자체: 넣으면 그 검사를 안 쓴다 (잰변형 {손으로['잰변형']} · 못잼 {손으로['못잼']})")

    print("\n  -- U_t = (U_{t-1} \\ Clean_t) ∪ FR_t : 누적하되 증거로 복구된다 --")
    # 사용자(2026-09-12): "이번 호출 것만 넘기나, 원장의 누적을 넘기나? 후자가 더 안전하다."
    # 맞다 -- FR 에 시한의 일부만 주므로 **다 못 훑으면 못 닿은 검사가 조용히 신뢰받는다.**
    둘3 = M.둘다사냥(판, 시한초=180, 파일들=["붙은것.py"], 말하기=lambda s: None,
                 FR몫=0.01)                      # FR 시한을 최소로 -- 이번 호출은 거의 못 훑는다
    ok("tests/test_붙은것.py" in 둘3["못믿을검사"],
       f"**이번 사냥이 그 검사에 안 닿아도 원장 누적으로 빠진다** ({둘3['못믿을검사']})")
    ok(둘3["FG"]["잰변형"] == 0,
       f"그래서 FG 가 여전히 그것을 바탕으로 쓰지 않는다 (잰변형 {둘3['FG']['잰변형']})")
    # 복구: 그 검사를 고치면(상태를 안 남기게) 다음 FR 관측에서 멀쩡으로 빠져나온다
    (판 / "tests" / "test_붙은것.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport 붙은것\nassert 붙은것.g(1) == 2\nprint("이제 깨끗")\n',
        encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "상태를 안 남기게 고쳤다")
    M.거짓빨강사냥(판, 검사들=["tests/test_붙은것.py"], 시한초=120, 말하기=lambda s: None)
    ok("tests/test_붙은것.py" not in M.못믿을검사들(판),
       f"**고치면 빠져나온다 -- 복구도 측정으로 한다**(순수 누적이면 영영 제외된다) ({M.못믿을검사들(판)})")
    되찾음 = M.사냥(판, 파일들=["붙은것.py"], 시한초=120, 말하기=lambda s: None)
    ok(되찾음["잰변형"] >= 1, f"그 파일을 다시 잴 수 있다 ({되찾음['잰변형']}개)")

    print("\n== 배선 ==")
    _서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
    ok("mutate" in (뿌리 / "dispatch.py").read_text(encoding="utf-8")
       or "거짓초록" in (뿌리 / "dispatch.py").read_text(encoding="utf-8"), "dispatch 가 거짓초록 명령을 안다")
    ok("mutate.py" in (뿌리 / ".github/workflows/deploy-oracle.yml").read_text(encoding="utf-8"),
       "배포가 mutate.py 를 서버에 올린다")
    from falsegreen import discord_cmd as _FC
    보기 = lambda argv, 로그, 무엇: " ".join(argv[1:])
    ok("--둘다" in _FC.run("!거짓초록 24", runner=보기) and "86400" in _FC.run("!거짓초록 24", runner=보기),
       "**`!거짓초록 24` 는 둘 다 돌린다** (거짓 빨강 -> 거짓 초록)")
    ok("--거짓빨강" in _FC.run("!거짓초록 빨강만", runner=보기), "`빨강만` 은 FR 만")
    ok("--둘다" not in _FC.run("!거짓초록 초록만", runner=보기), "`초록만` 은 FG 만")
    ok(_FC.run("!거짓초록 보고") is not None, "`보고` 는 둘 다 요약한다(즉시)")
finally:
    shutil.rmtree(판, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("mutate: 조용한 변형 · 본다/안 본다 · 절제와의 차이 · 비등가·덮임·동등 · Case A~D · 2차 메타검증 · 거짓빨강 사냥(상태오염·환경의존·진짜빨강) · 둘다 · 못잼 · 시한 · 원장 · 배선 -- 통과")
