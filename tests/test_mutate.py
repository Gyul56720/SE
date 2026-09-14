"""반례 사냥(mutate)을 **진짜 저장소**로 붙든다.

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
# **실측 2026-09-13 (D_0): 자취를 '같음' 으로 보면 멀쩡한 변형이 버려진다.** 두 가지에 똑같은 줄이
# 있으면 맞바꿔도 그 줄은 안 바뀌므로 Δ 가 자취보다 **작다.** 보는 것은 `자취 밖이 바뀌었나` 다.
_쌍둥이 = """def 고르기2(x):
    if x:
        y = 1
        return y
    else:
        y = 2
        return y
"""
_스왑2 = [(새, 자취) for op, _s, 새, 자취 in M.변형들(_쌍둥이, "고르기2") if op == "branch_swap"]
ok(len(_스왑2) == 1, "가지 맞바꾸기가 나온다")
if _스왑2:
    _새2, _자취2 = _스왑2[0]
    _다른2 = {i + 1 for i, (a, b) in enumerate(zip(_쌍둥이.splitlines(), _새2.splitlines())) if a != b}
    ok(_다른2 < set(_자취2),
       f"바뀐 줄 {sorted(_다른2)} 가 선언한 자취 {sorted(_자취2)} 보다 **작다** -- `else:` 와 똑같은 줄은 그대로다")
    ok(M.단일변형인가(_쌍둥이, _새2, _자취2)[0],
       "**자취 안에 안 바뀐 줄이 있어도 단일 변형이다**(Δ ⊆ 자취) -- 같음을 요구하면 D_0 의 INVALID_MUTATION 5건이 된다")
    ok(M.변형유효한가(_새2, "x.py")[0], "그 변형은 컴파일된다 -- 버릴 까닭이 없었다")
ok(not M.단일변형인가(_쌍둥이, _쌍둥이.replace("def 고르기2(x):", "def 고르기2(x=0):"), frozenset({3, 4, 5, 6, 7}))[0],
   "자취 밖(1줄)이 바뀌면 여전히 단일 변형이 아니다")

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
    ok(any(x.get("classification") == M.미해결 and x.get("target", "").startswith("부름.py") for x in 원),
       "원장에 UNRESOLVED 줄이 남는다(분류 이름으로)")
    ok(any(x.get("꼴") == "사냥끝" for x in 원), "사냥 끝 줄이 남는다")
    보 = M.보고(판)
    ok("반례 사냥" in 보 and "부름.py" in 보 and M.미해결 in 보,
       f"보고가 원장을 읽어 사람 말로 적는다 ({보[:60]!r})")
    ok("거짓 초록" not in 보 and "FALSE_GREEN" not in 보,
       "**보고에 초록이라는 낱말이 없다** -- 못 찾은 것을 통과라 부르지 않는다")

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
       f"**안 덮인 줄의 변형은 '미해결' 이 아니라 '덮이지않음' 이다** (덮이지않음 {r6['덮이지않음']})")
    # 정의대로: 안 덮인 줄의 생존도 FG 다(의미가 달라졌는데 검사가 못 잡았다). 다만 **까닭이 다르다** --
    # 단언이 약한 것이 아니라 그 줄에 닿지 않은 것이다. 그래서 why 로 갈라 적고 보고가 따로 센다.
    ok(any(x.get("classification") == M.미해결 and x.get("why") == "not_covered"
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
    ok(rA.get(M.유효빨강, 0) >= 1 and rA.get(M.거짓빨강, 0) == 0 and rA.get(M.미해결, 0) == 0,
       f"Case A -- VALID_RED {rA.get(M.유효빨강, 0)} · FALSE_RED {rA.get(M.거짓빨강, 0)} · UNRESOLVED {rA.get(M.미해결, 0)}")
    ok(all(x.get("baseline_rerun_status") == "PASS" for x in M.원장읽기(판)
           if x.get("classification") == M.유효빨강),
       "**모든 VALID_RED 은 되돌림 재실행이 PASS 였다** -- 귀속이 차감으로 증명된다")
    # 길이가 같은 변형(a + b -> a - b)이 VALID_RED 로 남아야 한다 -- 낡은 .pyc 가 거짓 Red 를 만들던 자리
    ok(any(x.get("operator") == "arith_swap" and x.get("classification") == M.유효빨강 for x in M.원장읽기(판)),
       "**길이가 같은 변형도 VALID_RED** -- 바이트코드 캐시를 꺼서 거짓 Red 가 안 난다(실측 회귀)")

    print("  -- Case B: 틀린 값으로 바꿨는데 계속 PASS -> UNRESOLVED --")
    rB = M.사냥(판, 파일들=["부름.py"], 시한초=180, 말하기=lambda s: None)
    ok(rB.get(M.미해결, 0) >= 1 and rB.get(M.유효빨강, 0) == 0,
       f"Case B -- UNRESOLVED {rB.get(M.미해결, 0)} (부르기만 하는 검사)")
    ok(any(x.get("classification") == M.미해결 and x.get("why") == "weak_assertion"
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
    ok(M.신뢰(True, {M.유효빨강: 3, M.미해결: 1})["commit"] is False, "**FG 가 있으면 초록이어도 막는다**")
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
    ok("FR" in 둘 and "반례" in 둘, "둘을 같이 돌려 둘을 돌려준다")
    ok(둘["FR"]["잰것"] >= 4 and 둘["반례"]["잰변형"] >= 1, f"FR {둘['FR']['잰것']}개 · FG 변형 {둘['반례']['잰변형']}개")
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
    ok(둘2["반례"]["잰변형"] == 0 and 둘2["반례"]["못잼"] >= 1,
       f"**FG 가 그 검사를 바탕으로 쓰지 않는다 -- 변형을 하나도 안 재고 못잼으로 적는다** "
       f"(잰변형 {둘2['반례']['잰변형']} · 못잼 {둘2['반례']['못잼']})")
    # **실측 2026-09-13 (D_0): RG0 의 유효 기간은 영원하지 않다.** `tests/test_brief.py` 가 받은날을
    # 박아 두어서 사냥 도중에 날이 바뀌며 혼자 빨개졌고, RG0 를 파일마다 한 번만 재므로 그 뒤로
    # **FALSE_RED 가 107 번 잇따랐다.** 판정은 옳았지만(잡힘으로 안 셌다) 시한을 그만큼 버렸다.
    # 여기서는 시계 대신 **판 밖의 셈 파일**로 같은 일을 낸다 -- 세 번째 실행부터 혼자 빨강이다.
    셈파일 = Path(tempfile.mkdtemp(prefix="시계-")) / "셈.txt"
    (판 / "시계.py").write_text("def f(a):\n    return a + 1\n", encoding="utf-8")
    (판 / "tests" / "test_시계.py").write_text(
        'import sys\nsys.path.insert(0, ".")\nimport 시계\n'
        f'p = {str(셈파일)!r}\n'
        'n = 0\n'
        'try:\n    n = int(open(p).read())\nexcept OSError:\n    pass\n'
        'open(p, "w").write(str(n + 1))\n'
        'assert 시계.f(1) == 2\n'
        'assert n + 1 < 3, "날이 바뀌었다 -- 코드와 무관하게 빨강"\nprint("아직 초록")\n',
        encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "도중에 혼자 빨개지는 검사")
    무너짐 = M.사냥(판, 파일들=["시계.py"], 시한초=300, 말하기=lambda s: None)
    ok(무너짐["잰변형"] == M.잇단거짓빨강상한,
       f"**거짓 빨강이 {M.잇단거짓빨강상한}번 잇따르면 그 파일을 접는다** -- {무너짐['잰변형']}개만 쟀다"
       f"(안 접으면 연산자 수만큼 = D_0 의 107번)")
    ok(무너짐.get(M.못쓸바탕, 0) >= 1,
       f"접은 까닭을 **바탕이 못 쓸 것**으로 적는다 ({무너짐.get(M.못쓸바탕, 0)})")
    무너짐줄 = [x for x in M.원장읽기(판)
             if x.get("꼴") == "바탕무너짐" and x.get("파일") == "시계.py"]
    ok(len(무너짐줄) == 1 and M.못쓸바탕 in 무너짐줄[-1]["classification"],
       f"원장에 그 파일의 '바탕무너짐' 줄이 한 줄 남는다 ({len(무너짐줄)})")
    ok(무너짐[M.거짓빨강] == M.잇단거짓빨강상한,
       f"이미 적힌 거짓 빨강은 그대로 둔다 -- 그것도 사실이었다 ({무너짐.get(M.거짓빨강, 0)})")

    # **추적되는 요약** -- 원장은 logs/(gitignore) 에 있어 저장소에 안 남는다. D_0 를 비교하려면 남아야 한다.
    줄1 = M.요약적기(판)
    ok((판 / M.요약경로).is_file(), f"{M.요약경로} 가 생긴다")
    ok(줄1["잰변형"] >= 1 and 줄1["Killed"] + 줄1["미해결"] >= 1,
       f"요약이 잰 것을 담는다 (잰변형 {줄1['잰변형']} · Killed {줄1['Killed']} · FG {줄1['미해결']})")
    ok(줄1["점수"] == round(줄1["Killed"] / (줄1["Killed"] + 줄1["미해결"]), 4),
       f"**점수의 분모는 가를 수 있었던 것뿐이다** -- 동등·못쓸·거짓빨강은 검사 탓이 아니다 ({줄1['점수']})")
    ok(줄1["못믿을검사"] and "tests/test_붙은것.py" in 줄1["못믿을검사"],
       f"요약이 못믿을검사를 들고 간다 ({줄1['못믿을검사']})")
    M.요약적기(판)
    ok(len(M.요약들(판)) == 2, f"덧붙이기만 한다 -- D_0 를 지우고 D_1 을 쓰지 않는다 ({len(M.요약들(판))})")
    ok("점수" in M.요약보고(판) or "때" in M.요약보고(판), "요약보고가 추이를 찍는다")
    # **표본을 같이 남긴다** -- 사용자(2026-09-13): "FG 가 줄었다고 검사가 좋아진 것이 아니다.
    # D_0 가 100개를 재고 D_1 이 20개를 쟀다면 점수 0.90 -> 0.95 는 아무것도 증명하지 않는다."
    for 칸 in ("잰변형", "못잼", "동등", "거짓빨강", "못쓸", "시한초과", "안덮임", "약한단언",
             "파일수", "함수수", "검사수", "시한초", "씨앗", "칸", "바탕못잼"):
        ok(칸 in 줄1, f"요약이 `{칸}` 을 따로 남긴다 -- 점수만 남기면 분모를 못 본다")
    ok(줄1["잰변형"] == 줄1["Killed"] + 줄1["미해결"] + 줄1["못잼"],
       f"**잰변형 = Killed + FG + 못잼** -- 분모에서 빠진 수를 숨기지 않는다 "
       f"({줄1['잰변형']} = {줄1['Killed']} + {줄1['미해결']} + {줄1['못잼']})")
    ok(줄1["파일"] and any(v[M.잡힘] or v[M.살아남음] for v in 줄1["파일"].values()),
       f"파일별 셈이 비어 있지 않다 -- 변형 줄의 `target` 을 풀어야 채워진다 ({list(줄1['파일'])[:3]})")
    ok(줄1["안덮임"] + 줄1["약한단언"] >= 1,
       f"FG 를 `안덮임`/`약한단언` 으로 가른다 ({줄1['안덮임']} · {줄1['약한단언']})")
    ok(all("초" in v for v in 줄1["연산자"].values()),
       "연산자마다 **비용**을 담는다 -- R(m) = αFG + βFR + γΔJ - λCost 의 마지막 항이다")
    ok(줄1.get("동등장치") is True, "요약이 동등 장치가 살았는지 같이 적는다")

    print("\n== `동등 0` 이 장치가 죽어서 0 인지 가른다 (ledgerstat 의 여섯 칸이 늘 0 이던 자리) ==")
    살, 말 = M.동등장치살았나()
    ok(살, f"TCE 탐침이 켜진다 ({말})")
    _쌍 = "def f(a):\n    if a:\n        return 1\n    else:\n        return 1\n"
    _스왑 = [새 for op, _s, 새, _t in M.변형들(_쌍, "f") if op == "branch_swap"]
    ok(_스왑 and M.동등한가(_쌍, _스왑[0]),
       "**똑같은 두 가지를 맞바꾸면 동등이다** -- 이 자리에서 실제로 불이 켜진다(1111번 중 0번 켜졌던 장치)")
    ok(not M.동등한가(_쌍, _쌍.replace("return 1\n", "return 2\n", 1)),
       "**다른 것을 동등이라 하지 않는다** -- 한 방향만 건전하다(진짜 잡힘을 동등으로 빼면 점수가 거짓으로 오른다)")
    ok(not M.동등한가("def f(a):\n    return a + 0\n", "def f(a):\n    return a - 0\n"),
       "`a+0 -> a-0` 은 **안 잡는다**(CPython 이 접지 않는다) -- 그래서 FG 는 상한이고 점수는 하한이다")

    print("\n== 표본이 다르면 Δ 를 내지 않는다 (점수만 빼면 표본 축소가 개선으로 읽힌다) ==")
    큰 = {"사냥끝": True, "씨앗": 1,
         "칸": {f"a.py|op{i}": {"잰것": 10, M.잡힘: 9, M.살아남음: 1} for i in range(10)}}
    작 = {"사냥끝": True, "씨앗": 1,
         "칸": {"a.py|op0": {"잰것": 10, M.잡힘: 10, M.살아남음: 0}}}
    d = M.점수차(큰, 작)
    ok(d["Δ"] is None and not d["견줄수있나"],
       f"**공통칸에서 잰 수가 크게 다르면 Δ 가 없다** -- 0.90 -> 1.00 을 개선이라 하지 않는다 ({d['Δ']})")
    ok(any("너무 적다" in x or "너무 다르다" in x for x in d["까닭"]),
       f"왜 못 견주는지 말한다 ({d['까닭']})")
    같1 = {"사냥끝": True, "씨앗": 1,
          "칸": {f"a.py|op{i}": {"잰것": 10, M.잡힘: 9, M.살아남음: 1} for i in range(10)}}
    같2 = {"사냥끝": True, "씨앗": 1,
          "칸": {f"a.py|op{i}": {"잰것": 10, M.잡힘: 10, M.살아남음: 0} for i in range(10)}}
    d2 = M.점수차(같1, 같2)
    ok(d2["견줄수있나"] and d2["Δ"] == 0.1 and d2["공통칸수"] == 10,
       f"같은 표본이면 Δ 를 낸다 (Δ {d2['Δ']} · 공통칸 {d2['공통칸수']})")
    d3 = M.점수차(같1, {**같2, "씨앗": 99})
    ok(d3["Δ"] is None and any("씨앗" in x for x in d3["까닭"]),
       f"씨앗이 다르면 다른 추출이다 -- 안 견준다 ({d3['까닭']})")
    d4 = M.점수차(같1, {**같2, "사냥끝": False})
    ok(d4["Δ"] is None, "시한에 잘린 표본과는 안 견준다 -- 치우쳐 있다")
    d5 = M.점수차(같1, {"사냥끝": True, "씨앗": 1, "칸": {"b.py|op0": {"잰것": 5, M.잡힘: 5, M.살아남음: 0}}})
    ok(d5["Δ"] is None and d5["공통칸수"] == 0, "같이 잰 칸이 없으면 모른다고 한다")
    ok("Δ 를 내지 않는다" in M.요약보고(판) or "Δ점수" in M.요약보고(판),
       "요약보고가 Δ 를 점수차로 낸다(날로 빼지 않는다)")

    print("\n== 점수를 둘로 가른다: 덮음율 · 잡음율 ==")
    # 사용자 지시 2026-09-13: "`Killed/(Killed+FG)` 는 즉시 버리는 게 맞다. 검사율과
    # 성공률을 분리해야 한다." 하나로 뭉치면 **덜 재서 점수를 올리는** 길이 열린다 --
    # 못잼을 분모에서 빼 버리면 거의 안 재고도 점수가 좋아 보인다.
    요3 = M.요약(판)
    ok("덮음율" in 요3 and "잡음율" in 요3, "요약이 둘을 따로 낸다")
    if 요3["잰변형"]:
        ok(abs(요3["덮음율"] - (요3["Killed"] + 요3["미해결"]) / 요3["잰변형"]) < 5e-5,
           f"**덮음율 = (Killed+FG)/잰변형** ({요3['덮음율']}) -- 얼마나 제대로 쟀나")
    if 요3["Killed"] + 요3["미해결"]:
        ok(abs(요3["잡음율"] - 요3["Killed"] / (요3["Killed"] + 요3["미해결"])) < 5e-5,
           f"**잡음율 = Killed/(Killed+FG)** ({요3['잡음율']}) -- 잰 것 중 얼마나 죽였나")
        ok(요3["점수"] == 요3["잡음율"], "옛 이름 `점수` 는 잡음율과 같다(부르던 데가 안 깨진다)")
    # **덜 재면 잡음율은 오르고 덮음율은 떨어진다** -- 그래서 둘을 같이 봐야 한다
    덜잼 = {"잰변형": 100, "Killed": 5, "미해결": 5, "못잼": 90}
    덮 = (덜잼["Killed"] + 덜잼["미해결"]) / 덜잼["잰변형"]
    ok(덮 < 0.2, f"못잼이 90%면 덮음율이 {덮:.2f} 로 떨어진다")
    ok(덜잼["Killed"] / (덜잼["Killed"] + 덜잼["미해결"]) == 0.5,
       "**그런데 잡음율은 0.5 로 멀쩡해 보인다** -- 이것만 보면 못 잰 것이 안 보인다")

    print("\n== 완주 점검: 좋은 변형을 찾았나가 아니라 **쓸 만한 측정이었나** ==")
    좋 = {"잰변형": 10, "Killed": 4, "미해결": 3, "못잼": 3, "씨앗": 0, "판": "abc1234",
         "사냥끝": True, "잡힌것": [f"k{i}" for i in range(4)],
         "결정된것": [f"k{i}" for i in range(4)] + [f"f{i}" for i in range(3)],
         "덮음율": 0.7, "잡음율": 0.5714}
    # **되풀이 · 충돌 · 엇갈림은 다른 것이다.** 실측 2026-09-13 (D_1): 잡힌것 1467 <
    # Killed 1555 를 보고 "88개가 접혔다" 고 했는데, 같은 사냥을 두 번 돌려 재 보니
    # **전부 되풀이**였다(원장이 append-only 라 줄이 쌓인다). 되풀이는 결함이 아니다.
    좋 = {**좋, "신원충돌": 0, "엇갈림": 0, "되풀이": 0}
    ok(M.완주점검(좋)["쓸만한가"], "셋을 다 재 뒀고 0 이면 쓸 만하다")
    되 = {**좋, "되풀이": 12}                              # 같은 변형을 두 번 쟀다
    ok(M.완주점검(되)["쓸만한가"],
       "**되풀이는 막지 않는다** -- 원장이 append-only 라 두 번 재면 쌓인다(결함이 아니다)")
    ok(any("되풀이 12" in c["말"] for c in M.완주점검(되)["칸"]), "그래도 몇 개인지 적는다")
    충 = {**좋, "신원충돌": 3}
    ㅅ = M.완주점검(충)
    ok(not ㅅ["쓸만한가"] and any(c["이름"] == "신원충돌" and not c["됐나"] for c in ㅅ["칸"]),
       "**다른 변형이 한 신원이 되면 막는다** -- 형제가 서로를 가린다")
    섞임 = {**좋, "결정된것": 좋["결정된것"] + ["못잼하나"]}   # 결정된것이 Killed+FG 를 넘었다
    ㅁ = M.완주점검(섞임)
    ok(not ㅁ["쓸만한가"] and any(c["이름"] == "못잼섞임" and not c["됐나"] for c in ㅁ["칸"]),
       "**결정된것이 Killed+FG 를 넘으면 막는다** -- 못잼이 섞인 것이다")
    엇 = {**좋, "엇갈림": 5}
    ok(not M.완주점검(엇)["쓸만한가"]
       and any("FR 이 흔들리는" in c["말"] for c in M.완주점검(엇)["칸"]),
       "**같은 변형이 판마다 다르게 나면 알린다** -- FR 이 흔들리는 자리다")
    안잼 = {k: v for k, v in 좋.items() if k != "신원충돌"}
    ㅇ = M.완주점검(안잼)
    ok(any(c["이름"] == "신원" and "안 재 뒀다" in c["말"] for c in ㅇ["칸"]),
       "**안 재 뒀으면 '충돌이다' 가 아니라 '안 재 뒀다' 고 한다** -- 모르는 것을 단정하지 않는다")
    # 요약이 실제로 셋을 낸다
    요4 = M.요약(판)
    for 칸 in ("되풀이", "신원충돌", "엇갈림"):
        ok(칸 in 요4, f"요약이 `{칸}` 을 낸다")
    ok(요4["신원충돌"] == 0,
       f"**이 판에는 충돌이 없다** ({요4['신원충돌']}) -- 변형신원이 설명까지 넣어 가른다")
    for 빠진, 칸이름 in (("씨앗", "씨앗기록"), ("판", "세대기록")):
        없 = {k: v for k, v in 좋.items() if k != 빠진}
        ok(any(c["이름"] == 칸이름 and not c["됐나"] for c in M.완주점검(없)["칸"]),
           f"{빠진} 이 없으면 `{칸이름}` 이 막힌다")
    ok(any(c["이름"] == "사냥끝" and not c["됐나"]
           for c in M.완주점검({**좋, "사냥끝": False})["칸"]), "시한에 잘리면 막힌다")
    ok(not M.완주점검({})["쓸만한가"], "빈 줄은 쓸 만하지 않다(기본이 거절)")
    보 = M.완주보고(좋)
    ok("덮음율" in 보 and "잡음율" in 보, "완주 보고가 둘을 같이 낸다")
    ok("--완주점검" in (뿌리 / "mutate.py").read_text(encoding="utf-8"), "CLI 에 `--완주점검` 이 있다")

    print("\n== 비퇴행: 수가 아니라 **신원**으로 본다 ==")
    # **실측 2026-09-13.** 칸은 수만 셌다 -- {'잰것': 1, 'Killed': 0, 'Survived': 1}. 그래서 같은
    # 칸에서 Killed 3 -> Killed 3 이면 **그 셋이 다른 셋이어도** 통과했다. 원장 줄에는 이미
    # mutation_id 가 있었는데 요약이 그것을 안 들고 올라왔다. 비퇴행은 불변조건이라 점수보다
    # 먼저 봐야 하는데, 지금 꼴로는 **잴 수가 없었다.**
    앞 = {"잡힌것": ["a.py::f::cmp_negate::3", "a.py::g::return_none::9"],
         "잰것들": ["a.py::f::cmp_negate::3", "a.py::g::return_none::9", "a.py::h::bool_swap::1"]}
    같수 = {"잡힌것": ["a.py::f::cmp_negate::3", "a.py::h::bool_swap::1"],   # 수는 2 로 같다
          "잰것들": ["a.py::f::cmp_negate::3", "a.py::g::return_none::9", "a.py::h::bool_swap::1"]}
    같수 = {**같수, "결정된것": 같수["잰것들"]}
    v = M.비퇴행(앞, 같수)
    ok(v["비퇴행"] == "퇴행" and "a.py::g::return_none::9" in v["놓친"],
       f"**Killed 수가 2 로 같은데도 퇴행을 잡는다** -- 잡던 것을 놓치고 새것을 잡았다 ({v['말'][:60]})")
    ok(len(앞["잡힌것"]) == len(같수["잡힌것"]),
       "그 둘은 수로는 구별되지 않는다 -- 수로 재는 비퇴행이 못 잡는 자리다")
    ok(M.비퇴행(앞, {**앞, "결정된것": 앞["잰것들"],
                    "잡힌것": 앞["잡힌것"] + ["a.py::h::bool_swap::1"]})["비퇴행"] == "지킴",
       "잡던 것을 다 잡고 하나 더 잡으면 **지킴**이다(늘어난 것은 퇴행이 아니다)")
    print("  -- FR 을 놓침으로 세지 않는가 --")
    # **실측 2026-09-13, 사용자 경고에서 나왔다.** 처음엔 겹을 `잰것들`(결과가 있는 전부)로
    # 잡아서, 같은 변형이 앞에서 Killed 이고 뒤에서 **FR** 이면 `퇴행` 이라 답했다.
    # FR 은 "검사가 못 잡았다" 가 아니라 "변형을 빼도 빨갛다 -- 귀속을 못 했다" 다.
    # 그리고 FR 은 본디 흔들린다(이 저장소는 하루에 107연속 FR 을 겪었다). 그대로 두면
    # π 와 아무 상관 없는 이유로 REJECT 가 쏟아진다. 잰변형 = Killed + FG + **못잼** 이고
    # FR 은 못잼이다 -- 그 경계를 비퇴행도 써야 한다.
    ㄱ = {"잡힌것": ["a#1", "g#2"], "잰것들": ["a#1", "g#2"], "결정된것": ["a#1", "g#2"]}
    FR판 = {"잡힌것": ["a#1"], "잰것들": ["a#1", "g#2"], "결정된것": ["a#1"]}
    FG판 = {"잡힌것": ["a#1"], "잰것들": ["a#1", "g#2"], "결정된것": ["a#1", "g#2"]}
    v목 = M.비퇴행(ㄱ, FR판)
    ok(v목["비퇴행"] == "지킴" and v목["못잰것"] == 1,
       f"**뒤에서 FR 이 된 것은 놓침이 아니다** -- 못잼으로 따로 센다 ({v목['비퇴행']}·못잰것 {v목['못잰것']})")
    ok("못잼" in v목["말"], "그 수를 말에도 적는다 -- 조용히 빼지 않는다")
    ok(M.비퇴행(ㄱ, FG판)["비퇴행"] == "퇴행",
       "**뒤에서 진짜로 살아남은 것은 퇴행이다** -- FR 과 FG 를 가른다")
    ok(M.비퇴행(ㄱ, {"잡힌것": [], "잰것들": ["a#1", "g#2"]})["비퇴행"] == "못잼",
       "**`결정된것` 이 없는 옛 꼴 요약으로는 못 잰다** -- 옛 동작으로 조용히 되돌아가지 않는다")
    요2 = M.요약(판)
    ok("결정된것" in 요2 and set(요2["결정된것"]) <= set(요2["잰것들"]),
       "요약이 `결정된것` 을 낸다(잰것들의 부분집합)")
    ok(set(요2["잡힌것"]) <= set(요2["결정된것"]), "잡힌 것은 결정된 것의 부분집합이다")

    덜잰 = {"잡힌것": ["a.py::f::cmp_negate::3"], "잰것들": ["a.py::f::cmp_negate::3"],
          "결정된것": ["a.py::f::cmp_negate::3"]}
    v2 = M.비퇴행(앞, 덜잰)
    ok(v2["비퇴행"] == "지킴" and v2["겹친수"] == 1,
       "**시한에 잘려 안 닿은 변형을 '놓쳤다' 고 하지 않는다** -- 재지 않은 것을 빨강이라 하는 잘못이다")
    ok(M.비퇴행(앞, {"잡힌것": [], "잰것들": ["z.py::q::bool_swap::2"],
                    "결정된것": ["z.py::q::bool_swap::2"]})["비퇴행"] == "못잼",
       "**겹치는 표본이 없으면 못잼이다** -- 셋째 값이 없으면 못 잰 것이 초록으로 샌다")
    ok(M.비퇴행({}, 앞)["비퇴행"] == "못잼", "앞 판에 신원이 없으면 못잼(옛 D_0 가 그렇다)")
    # 요약이 실제로 신원을 담는가 -- 담지 않으면 위의 모든 검사가 빈 것을 견주게 된다
    요 = M.요약(판)
    ok("잡힌것" in 요 and "잰것들" in 요, f"요약이 신원을 들고 올라온다 ({sorted(요)[:3]}...)")
    ok(set(요["잡힌것"]) <= set(요["잰것들"]), "잡힌 것은 잰 것의 부분집합이다")
    # **mutation_id 만으로는 안 갈린다.** 실측: 한 줄에 같은 연산자가 두 번 걸리면 겹친다
    # (`x > 0`/`y < 3` 둘 다 cmp_negate::2). 그러면 형제가 서로를 가려 비퇴행이 눈을 감는다.
    겹치는소스 = "def f(x, y):\n    if x > 0 and y < 3:\n        return x + y\n    return 0\n"
    것 = M.변형들(겹치는소스, "f")
    아이디 = {f"a.py::f::{op}::{설명.split('줄')[0]}" for op, 설명, _, _ in 것}
    신원 = {M.변형신원({"mutation_id": f"a.py::f::{op}::{설명.split('줄')[0]}", "mutation": 설명})
          for op, 설명, _, _ in 것}
    ok(len(아이디) < len(것), f"**mutation_id 는 겹친다** (변형 {len(것)}개 -> id {len(아이디)}개)")
    ok(len(신원) == len(것), f"**변형신원은 하나도 안 겹친다** (변형 {len(것)}개 -> 신원 {len(신원)}개)")
    ok(all(M.변형신원({"mutation_id": f"a.py::f::{op}::1", "mutation": 설명}).startswith("a.py::f::")
           for op, 설명, _, _ in 것[:3]),
       "신원이 **사람이 읽을 수 있는 꼴**을 앞에 남긴다 -- 퇴행했을 때 어느 변형인지 찾아야 한다")
    ok(M.변형신원({}) == "" and M.변형신원({"mutation": "x"}) == "",
       "신원이 없으면 빈 글이다 -- 지어내지 않는다")
    보 = M.요약보고(판)
    ok("비퇴행" in 보, "요약보고가 **비퇴행을 점수보다 먼저** 적는다(불변조건이 목적함수보다 앞이다)")
    ok("비어 있다" in M.요약보고(Path(tempfile.mkdtemp(prefix="빈요약-"))),
       "요약이 없으면 **없다고 말한다** -- 안 잰 것을 0 점으로 읽지 않는다")

    홀로 = M.사냥(판, 파일들=["붙은것.py"], 시한초=120, 말하기=lambda s: None)
    ok(홀로["잰변형"] >= 1,
       f"**FR 을 먼저 안 돌리면 그 검사를 바탕으로 써 버린다** -- 그래서 순서가 판정을 바꾼다 ({홀로['잰변형']}개 쟀다)")
    # **시한을 넘긴 것은 빨강이 아니다 -- 못 잰 것이다**(실측 2026-09-13: D_0 의 `진짜빨강 5` 중
    # `tests/test_precheck.py` 는 빨강이 아니라 시한초과였다). 안 재고 빨강이라 하는 것은 이 저장소가
    # 오늘 배운 잘못이다 -- 막힌 것은 아무것도 못 고친다.
    (판 / "tests" / "test_늦다.py").write_text(
        'import time\ntime.sleep(30)\nprint("여기까지 안 온다")\n', encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "시한을 넘기는 검사")
    옛시한 = M.검사시한초
    M.검사시한초 = 2
    ok(M._돌려보기(판, ["tests/test_늦다.py"])[2].strip() == M.시한넘김표,
       "**시한을 부를 때 읽는다** -- 기본값에 박아 두면 이 흉내가 통째로 안 통한다")
    try:
        늦 = M.거짓빨강사냥(판, 검사들=["tests/test_늦다.py"], 시한초=60, 말하기=lambda s: None)
    finally:
        M.검사시한초 = 옛시한
    ok(늦[M.시한초과] == 1 and 늦[M.원래빨강] == 0,
       f"**시한을 넘기면 시한초과다 -- 진짜빨강이 아니다** (시한초과 {늦[M.시한초과]} · 진짜빨강 {늦[M.원래빨강]})")
    ok(늦["못잼"] >= 1, f"못잼으로 센다 ({늦['못잼']})")
    ok("tests/test_늦다.py" in M.못믿을검사들(판),
       "**바탕으로도 쓸 수 없다** -- RG0 가 시한을 넘기면 그 파일을 통째로 못 잰다")
    ok("시한초과" in M.FR보고(판) or M.시한초과 in M.FR보고(판),
       "FR 보고가 그것을 빨강과 따로 적는다")
    # **둘째 실행이 넘겼을 때도 시한초과다.** 실측 2026-09-13: 첫 실행만 보게 짜 놔서
    # `tests/test_improve.py` 가 "두 번째에 빨강" -> 상태오염으로 떨어졌다(까닭 글에는
    # "시한 초과" 가 찍혀 있었다). 2코어에서 부하가 걸리면 바로 나는 꼴이다.
    밖셈 = Path(tempfile.mkdtemp(prefix="둘째늦-")) / "셈.txt"
    (판 / "tests" / "test_둘째늦다.py").write_text(
        'import time\n'
        f'p = {str(밖셈)!r}\n'
        'n = 0\n'
        'try:\n    n = int(open(p).read())\nexcept OSError:\n    pass\n'
        'open(p, "w").write(str(n + 1))\n'
        'if n >= 1:\n    time.sleep(30)\n'          # 첫 실행은 빠르고 둘째가 시한을 넘긴다
        'print("첫 실행은 초록")\n', encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "둘째 실행이 시한을 넘기는 검사")
    옛2 = M.검사시한초
    M.검사시한초 = 2
    try:
        둘늦 = M.거짓빨강사냥(판, 검사들=["tests/test_둘째늦다.py"], 시한초=60, 말하기=lambda s: None)
    finally:
        M.검사시한초 = 옛2
    ok(둘늦[M.시한초과] == 1 and 둘늦[M.상태오염] == 0,
       f"**둘째 실행이 넘겨도 시한초과다 -- 상태오염이 아니다** "
       f"(시한초과 {둘늦[M.시한초과]} · 상태오염 {둘늦[M.상태오염]})")
    늦줄 = [x for x in M.원장읽기(판) if x.get("test") == "tests/test_둘째늦다.py"][-1]
    ok(늦줄.get("why") == "timeout_둘째" and 늦줄.get("baseline_pass") is True,
       f"어느 쪽이 넘겼는지 적는다 (why {늦줄.get('why')} · 첫 실행은 통과 {늦줄.get('baseline_pass')})")

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
    ok(둘3["반례"]["잰변형"] == 0,
       f"그래서 FG 가 여전히 그것을 바탕으로 쓰지 않는다 (잰변형 {둘3['반례']['잰변형']})")
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

    print("\n== 실행 산출물은 안 잰다 -- 고쳐야 할 코드가 아니다 ==")
    # **실측 2026-09-13 (D_0):** 19파일 중 4개가 `orchestrator/runs/` 의 커밋된 출력물이었고
    # 전부 Killed 0 · FG 40 이었다. 시한을 버리고 점수의 뜻도 흐린다(0.327 -> 산출물 빼면 0.341).
    산 = Path(tempfile.mkdtemp(prefix="test-산출물-"))
    try:
        git(산, "init", "-q")
        (산 / "tests").mkdir()
        (산 / "진짜.py").write_text("def f(a):\n    return a + 1\n", encoding="utf-8")
        (산 / "orchestrator" / "runs" / "20260101-000000" / "components").mkdir(parents=True)
        (산 / "orchestrator/runs/20260101-000000/components/out.py").write_text(
            "def g(a):\n    return a * 2\n", encoding="utf-8")
        git(산, "add", "-A"); git(산, "commit", "-qm", "init")
        것 = M._쟬파일들(산)
        ok("진짜.py" in 것, f"진짜 코드는 잰다 ({것})")
        ok(not any("/runs/" in x for x in 것),
           f"**실행 산출물은 목록에 없다** -- 아무도 검사하지 않는 출력물에 시한을 쓰지 않는다 ({것})")
        ok(M.안잴곳 and all(isinstance(x, str) for x in M.안잴곳), f"안 잴 곳을 한 군데에 적는다 ({M.안잴곳})")
        산사냥 = M.사냥(산, 시한초=120, 말하기=lambda s: None)
        적힌 = {str(x.get("target", "")).split(":")[0] for x in M.원장읽기(산) if x.get("outcome")}
        ok(not any("/runs/" in x for x in 적힌), f"사냥도 안 잰다 ({sorted(적힌)})")
    finally:
        shutil.rmtree(산, ignore_errors=True)

    print("\n== 사냥꾼이 사냥감이다: 검증기 자신을 겨눌 수 있는가 ==")
    # **실측 2026-09-13.** 검증기 파일은 처음부터 M 안에 있었다 -- `ls-files *.py` 에서
    # `tests/` 와 `안잴곳` 만 뺀다. 그런데 D0 는 6시간에 변형 1111개를 재고도 검증기 파일에
    # 한 번도 안 닿았다: 잴 수 있는 383개 중 5.0%(19개)만 돌았고, 검증기 24개 중 **0개**.
    # M 의 정의가 아니라 **시한에 잘린 순회**가 사각지대를 만들었다. 그래서 새 구조가 아니라
    # 겨냥이 필요하다.
    자기 = M.자기파일들(뿌리)
    ok(len(자기) >= 10, f"검증기 파일을 찾는다 ({len(자기)}개)")
    for 꼭 in ("mutate.py", "judge.py", "perf.py", "policy.py"):
        ok(꼭 in 자기, f"**{꼭} 가 제 사냥감 목록에 있다** -- 재는 장치도 잰다")
    ok(any(x.startswith("gates/") for x in 자기), "게이트도 사냥감이다")
    ok(not any(x.startswith("tests/") for x in 자기), "검사 자체는 여기서 안 변형한다(바탕이 된다)")
    전부 = M._쟬파일들(뿌리)
    ok(set(자기) <= set(전부),
       f"자기 목록은 **일반 목록의 부분집합이다** -- 안잴곳·tests 규칙을 우회하지 않는다 "
       f"(벗어난 것 {sorted(set(자기) - set(전부))[:3]})")
    ok("--자기" in (뿌리 / "mutate.py").read_text(encoding="utf-8"), "CLI 에 `--자기` 가 있다")
    # 손으로 적은 목록은 파일이 늘 때 조용히 낡는다 -- 추적 파일에서 걸러 내는지 본다
    ok(M.자기파일들(뿌리) == sorted(M.자기파일들(뿌리)), "목록이 정렬돼 있다(순서가 흔들리지 않는다)")

    print("\n== 병렬: 빨라지되 **판정이 바뀌지 않아야** 한다 ==")
    # 사용자(2026-09-13): "시간이 문제면 비동기로 하면 안 되나? 병렬로 한 번에 뿌려서."
    # 맞다. 다만 병렬은 판정을 바꿀 수 있다(판을 공유하면 서로의 되돌림을 본다). 그래서
    # **같은 표본을 순차로 한 번, 병렬로 한 번 재서 변형마다의 판정이 같은지** 본다.
    병 = Path(tempfile.mkdtemp(prefix="test-병렬-"))
    try:
        git(병, "init", "-q")
        (병 / "tests").mkdir()
        for 이 in ("하나", "둘", "셋"):
            (병 / f"{이}.py").write_text(
                f"def f(a):\n    if a > 1:\n        return a + 1\n    return 0\n", encoding="utf-8")
            (병 / "tests" / f"test_{이}.py").write_text(
                f'import sys\nsys.path.insert(0, ".")\nimport {이}\n'
                f'assert {이}.f(2) == 3\nassert {이}.f(0) == 0\nprint("본다")\n', encoding="utf-8")
        git(병, "add", "-A"); git(병, "commit", "-qm", "init")

        def 판정들(저장소):
            것 = {}
            for x in M.원장읽기(저장소):
                if x.get("mutation_id") and x.get("classification"):
                    것[x["mutation_id"]] = x["classification"]
            return 것

        순 = M.사냥(병, 시한초=300, 말하기=lambda s: None)
        순판정 = 판정들(병)
        (병 / M.원장상대).unlink()                 # 다음 재기를 섞지 않게
        병결과 = M.병렬사냥(병, 시한초=300, 일꾼=3, 말하기=lambda s: None)
        병판정 = 판정들(병)
        ok(병결과.get("일꾼") == 3, f"일꾼 3으로 돌았다 ({병결과.get('일꾼')})")
        ok(순["잰변형"] >= 3 and 순판정, f"순차가 잰 것이 있다 ({순['잰변형']}개)")
        ok(set(순판정) == set(병판정),
           f"**같은 변형 집합을 잰다** (순차 {len(순판정)} · 병렬 {len(병판정)} · "
           f"차이 {sorted(set(순판정) ^ set(병판정))[:3]})")
        다른 = {k: (순판정[k], 병판정[k]) for k in 순판정 if k in 병판정 and 순판정[k] != 병판정[k]}
        ok(not 다른, f"**판정이 하나도 안 바뀐다 -- 병렬이 측정을 바꾸지 않는다** (다른 것 {list(다른.items())[:3]})")
        ok(병결과["잰변형"] == 순["잰변형"],
           f"잰 수도 같다 ({순['잰변형']} vs {병결과['잰변형']})")
        ok(not list((병 / "logs").glob("거짓초록-일꾼*.jsonl")),
           "일꾼 샤드를 합친 뒤 치운다 -- 같은 판정이 두 벌 남지 않는다")
        ok(any(x.get("꼴") == "병렬시작" and x.get("일꾼") == 3 for x in M.원장읽기(병)),
           "원장에 몇 일꾼으로 쟀는지 적는다 -- 표본의 조건이다")
        홀 = M.병렬사냥(병, 시한초=120, 일꾼=1, 파일들=["하나.py"], 말하기=lambda s: None)
        ok(홀.get("일꾼") is None and 홀["잰변형"] >= 1,
           "일꾼 1이면 그냥 순차다 -- 다른 길이 아니다")
        ok(M._일꾼수(0) >= 2,
           f"**일꾼 0 이 1 로 무너지지 않는다** -- 2코어 기계에서 `코어수-1` 은 1이고 그것은 "
           f"병렬이 아니다(실측 2026-09-13: VM 의 nproc 가 2였다) ({M._일꾼수(0)} / 코어 {os.cpu_count()})")
        ok(M._일꾼수(5) == 5, "달라고 한 수는 그대로 준다")
        말한것 = []
        M.병렬사냥(병, 시한초=60, 일꾼=1, 파일들=["하나.py"], 말하기=말한것.append)
        ok(any("순차로 돈다" in x for x in 말한것),
           f"순차로 무너지면 **그렇다고 말한다** -- 빠른 줄 알고 기다리지 않게 ({말한것[:1]})")
    finally:
        shutil.rmtree(병, ignore_errors=True)

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
    ok("--일꾼 0" in _FC.run("!거짓초록 6", runner=보기),
       "**기본이 병렬이다** (코어수-1 -- 봇에게 한 코어는 남긴다)")
    ok("--일꾼 1" in _FC.run("!거짓초록 6 순차", runner=보기) and "21600" in _FC.run("!거짓초록 6 순차", runner=보기),
       "`순차` 는 병렬을 끈다 -- 시간은 그대로 읽는다")
    ok("--일꾼" not in _FC.run("!거짓초록 빨강만", runner=보기),
       "FR 만 돌릴 때는 일꾼을 안 준다 -- 두 번 돌려 상태오염을 보는 판정이다")
    ok("--둘다" not in _FC.run("!거짓초록 초록만", runner=보기), "`초록만` 은 FG 만")
    ok(_FC.run("!거짓초록 보고") is not None, "`보고` 는 둘 다 요약한다(즉시)")
    _요 = _FC.run("!거짓초록 요약") or ""
    ok("잰변형" in _요 or "비어 있다" in _요,
       f"`요약` 은 추적되는 요약(D_0 추이)을 찍는다 ({_요.splitlines()[0][:50] if _요 else '빈 것'})")
    ok("먼 검사" in (_FC.run("!거짓초록 먼검사") or "") or "비어 있다" in (_FC.run("!거짓초록 먼검사") or ""),
       "`먼검사` 는 먼 검사 기록을 찍는다")
    ok("farcheck.py" in (_FC.run("!거짓초록 먼검사 돌려", runner=보기) or ""),
       "`먼검사 돌려` 는 배경으로 한 바퀴 돌린다")
    ok("π" in (_FC.run("!거짓초록 정책") or ""), "`정책` 은 지금 π 를 찍는다")
    ok("이름" in (_FC.run("!거짓초록 정책 후보") or ""), "`정책 후보` 는 π' 후보를 찍는다")
    ok("관문" in (_FC.run("!거짓초록 성능 목록") or ""), "`성능 목록` 은 워크로드를 찍는다")
    ok("perf.py" in (_FC.run("!거짓초록 성능 재기 관문", runner=보기) or ""),
       "`성능 재기` 는 배경으로 잰다")
    ok("perf.py" in (뿌리 / ".github/workflows/deploy-oracle.yml").read_text(encoding="utf-8"),
       "배포가 perf.py 를 서버에 올린다")
    ok("farcheck.py" in (뿌리 / ".github/workflows/deploy-oracle.yml").read_text(encoding="utf-8"),
       "배포가 farcheck.py 를 서버에 올린다")

    # ---- 검사고르기: "이름이 닮았다" 는 **토막**이지 부분문자열이 아니다 -------------
    # 실측 2026-09-14: `줄기 in t` 라서 `cut/ff.py` 가 test_diffusion·test_payoff 를 뽑았고,
    # `한함수검사수 = 3` 이라 22개 파일에서 **진짜 검사가 상한 밖으로 밀려났다**.
    # 밀려난 자리는 조용하다 -- 그 변형을 재는 검사를 안 돌려 놓고 `살아남음` 으로 적힌다.
    ok(M._토막으로("test_cut.py", "cut"), "test_cut.py 는 cut 의 검사다")
    ok(M._토막으로("test_mathdrift_prove.py", "prove"), "밑줄 뒤 토막도 맞다")
    ok(M._토막으로("test_agent_context.py", "agent_context"), "밑줄이 든 줄기도 통째로 맞다")
    ok(not M._토막으로("test_payoff.py", "ff"), "'ff' 는 payoff 안에 **묻혀** 있다")
    ok(not M._토막으로("test_diffusion.py", "ff"), "'ff' 는 diffusion 안에 묻혀 있다")
    ok(not M._토막으로("test_improveloop.py", "prove"), "'prove' 는 improveloop 안에 묻혀 있다")
    ok(not M._토막으로("test_키찾기.py", "찾기"), "한글 이름에는 밑줄 경계가 없다 -- 안 맞는다")
    _고른 = M._검사고르기(뿌리, "attic/cut/ff.py")
    ok("tests/test_payoff.py" not in _고른 and "tests/test_diffusion.py" not in _고른,
       f"cut/ff.py 는 남의 검사를 안 끌어온다 ({_고른})")   # 실측 2026-09-14, 지금은 attic/
    _프 = M._검사고르기(뿌리, "mathdrift/prove.py")
    ok("tests/test_mathdrift_prove.py" in _프,
       f"진짜 검사가 상한 안에 남는다 ({_프})")

    # ---- 묶음: 지금 손대는 폴더만 겨눈다 -----------------------------------------
    # 2026-09-14 전에는 vne·cut 을 보기로 썼는데 그 둘을 attic/ 으로 얼렸다.
    # **살아 있는 폴더로 바꾼다** -- 얼린 것을 겨누는 검사는 얼린 것과 같이 낡는다.
    _묶 = M.묶음파일들(["improve", "dig"], repo=뿌리)
    ok(_묶 and all(x.startswith(("improve/", "dig/")) for x in _묶),
       f"--묶음 은 그 폴더 아래만 준다 ({len(_묶)}개)")
    ok("dig/search.py" in _묶 and "mutate.py" not in _묶, "저장소 전체가 아니다")
    ok(not M.묶음파일들(["attic"], repo=뿌리) or
       all(x.startswith("attic/") for x in M.묶음파일들(["attic"], repo=뿌리)),
       "얼린 폴더를 겨누면 얼린 것만 준다 -- 새어 나오지 않는다")
    ok(not any(x.startswith("tests/") for x in _묶), "검사 파일은 사냥감이 아니다")
    ok(M.묶음파일들(["없는폴더"], repo=뿌리) == [], "없는 폴더는 빈 목록 -- 조용히 전체로 안 번진다")


    # ---- 상한은 **π 뒤에서** 자른다 (앞에서 자르면 꼬리가 영영 안 나온다) ----------
    # 실측 2026-09-14: `변형들` 의 기본 상한이 24 였고 **생성 순서 앞에서** 잘랐다. 그래서
    # 25번째부터는 어떤 씨앗으로도 안 나왔다 -- π 가 보기도 전에 목록에서 사라졌다.
    #     함수 418개가 잘림 · 후보 37857 중 **7319(19.3%)가 영영 못 닿음**
    # 하필 그 꼬리에 `_한변형` 의 `if 또빨강:` 이 있었다 -- **RED(증서)와 FR 을 가르는 줄**이다.
    # (그 줄의 변형 12개를 심어 보니 12개 다 잡혔다. 결함이 숨어 있진 않았지만, 숨을 수는 있었다.)
    _긴것 = (뿌리 / "mutate.py").read_text(encoding="utf-8")
    _온 = M.변형들(_긴것, "_한변형")
    _잘 = M.변형들(_긴것, "_한변형", 상한=24)
    ok(len(_온) > 24, f"**상한 없이 부르면 전수를 준다** ({len(_온)}개)")
    ok(len(_잘) == 24, f"상한을 주면 그만큼만 ({len(_잘)}개)")
    ok(M.변형들(_긴것, "_한변형", 상한=0) == _온, "상한 0 = 안 자른다")
    _꼬리 = [x for x in _온 if x not in _잘]
    ok(_꼬리, "옛 상한 밖에 있던 꼬리가 실제로 있다 (위 검사가 공허하지 않다)")
    ok(any("또빨강" in 설 for _op, 설, _a, _b in _꼬리),
       "**증서를 가르는 `또빨강` 변형이 그 꼬리에 있었다** -- 이것이 못 닿던 것이다")

    # π 로 섞은 뒤 자르면 **씨앗마다 다른 24개**가 온다 -- 판을 거듭하면 다 닿는다
    import random as _r
    _ㄱ = {x[1] for x in M.변형뽑기(_온, None, _r.Random(1))[:24]}
    _ㄴ = {x[1] for x in M.변형뽑기(_온, None, _r.Random(2))[:24]}
    ok(_ㄱ != _ㄴ, "**씨앗이 다르면 보는 24개가 다르다** -- 앞에서 자르면 늘 같은 24개였다")
    ok(_ㄱ | _ㄴ > _ㄱ, f"두 씨앗을 합치면 더 많이 닿는다 ({len(_ㄱ)} -> {len(_ㄱ | _ㄴ)})")
    _모 = set()
    for _s in range(12):
        _모 |= {x[1] for x in M.변형뽑기(_온, None, _r.Random(_s))[:24]}
    ok(len(_모) == len(_온),
       f"**씨앗을 거듭하면 전수에 닿는다** (12개 씨앗에 {len(_모)}/{len(_온)})")
    ok(M.한함수변형수 == 24, f"한 판에 볼 변형 수는 그대로 24 다 ({M.한함수변형수})")

    # ---- 판정의 이름: **초록을 뺐다** ------------------------------------------
    # 사용자(2026-09-14): "RED = 반례 발견 · UNRESOLVED = 못 찾음 · EQUIVALENT = 증명.
    # GREEN 이라는 단어 자체를 없애는 것도 좋은 선택이다."  까닭은 TCE 가 한 방향만
    # 건전하기 때문이다 -- 동등은 증명해도 **비동등은 증명 못 한다**. 그런데 옛 이름
    # `FALSE_GREEN` 은 "이 초록은 거짓이다", 곧 변형이 실제로 다르다고 단정했다.
    # 실측 2026-09-14 그 대가를 치렀다: `cut/일반화.py` 의 항등 `round` 둘이 그렇게
    # 적혔는데 실제로는 동등변형이었다.
    ok(M.미해결 == "UNRESOLVED", f"살아남은 변형의 이름은 UNRESOLVED 다 ({M.미해결})")
    ok(not hasattr(M, "거짓초록") and not hasattr(M, "유효초록"),
       "**초록이 붙은 판정 상수가 없다**")
    ok("GREEN" not in M.유효빨강 + M.미해결 + M.동등변형 + M.거짓빨강 + M.못쓸변형 + M.못쓸바탕,
       "판정 이름 어디에도 GREEN 이 없다")
    ok(M.동등변형 == "EQUIVALENT_MUTANT" and M.유효빨강 == "VALID_RED",
       "RED 와 EQUIVALENT 는 그대로다 -- 둘은 실제로 증명되는 쪽이다")

    # **옛 원장을 계속 읽는다.** 원장은 append-only 라 D_0·D_1 에 옛 이름이 그대로 있다.
    ok(M.판정풀기("FALSE_GREEN") == M.미해결, "옛 이름을 지금 이름으로 푼다")
    ok(M.판정풀기("VALID_RED") == "VALID_RED", "다른 이름은 안 건드린다")
    ok(M.판정풀기(None) is None, "없는 값에 이름을 지어내지 않는다")
    _섞 = [{"classification": "FALSE_GREEN", "outcome": M.살아남음, "operator": "x"},
          {"classification": M.미해결, "outcome": M.살아남음, "operator": "x"}]
    _센 = {}
    for _x in _섞:
        _c = M.판정풀기(_x["classification"])
        _센[_c] = _센.get(_c, 0) + 1
    ok(_센 == {M.미해결: 2},
       f"**옛 줄과 새 줄이 한 칸으로 합쳐진다** ({_센}) -- 안 그러면 D_t 가 둘로 쪼개진다")

    # ---- 요약 줄의 칸 이름도 바뀌었다 (2026-09-14) --------------------------------
    # 판정 이름만 고치고 **칸 이름은 `FG` 로 남아 있었다.** 그래서 같은 것을 두 낱말로
    # 부르고 있었고, 사용자가 "뭐가 뭔지 모르겠다" 고 한 자리가 그것이다. 칸도 고치되
    # **요약 원장은 append-only** 라 `FG` 로 적힌 줄이 남아 있다 -- 안 받으면 옛 판의
    # 수가 0 으로 읽혀 D_0 -> D_1 이 어긋난다. 이 검사가 그 자리를 붙든다.
    ok(M._미해결수({"미해결": 7}) == 7, "새 칸을 읽는다")
    ok(M._미해결수({"FG": 7}) == 7, "**옛 칸(FG)도 읽는다** -- 옛 요약 줄의 수가 0 이 되지 않는다")
    ok(M._미해결수({"미해결": 0, "FG": 9}) == 0,
       "**새 칸이 있으면 새 칸이 이긴다** -- 0 을 '없다' 로 읽어 옛 칸으로 새지 않는다")
    ok(M._미해결수({}) == 0, "둘 다 없으면 0")
    # 새로 적는 줄이 새 칸을 쓴다는 것은 위 '요약' 묶음이 이미 붙들고 있다
    # (`줄1["미해결"]`). 여기서 실제 원장을 훑어 "FG 가 없다" 고 하면 안 된다 --
    # 그 원장에는 이름을 바꾸기 전의 줄이 **남아 있어야 맞기** 때문이다(append-only).
    ok(M.칸미해결 == "미해결" and M.옛칸미해결 == "FG",
       "쓰는 이름과 읽어 주는 옛 이름이 둘 다 한 자리에 적혀 있다")

finally:
    shutil.rmtree(판, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("mutate: 조용한 변형 · 본다/안 본다 · 절제와의 차이 · 비등가·덮임·동등 · Case A~D · 2차 메타검증 · 거짓빨강 사냥(상태오염·환경의존·진짜빨강) · 둘다 · 못잼 · 시한 · 원장 · 배선 -- 통과")
