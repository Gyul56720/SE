"""J(P) 가 **검증 가능한** 개선 함수인지 붙든다. 진짜 저장소를 지어 돌린다.

사용자(2026-09-12): "검증 가능한 개선 함수 J 를 만들어야 한다. 그 위에 Verified Improvement 를
세운 다음에야 Self-Improving Policy 로 갈 수 있다."  계층은 V(믿을 수 있는가) -> J(나아졌는가)
-> π(다음에는 어떻게 나아질 것인가).

J 가 검증 가능하다는 것은 **J 에 대한 반례를 만들 수 있다**는 뜻이다. 여섯 가지를 붙든다.

  1. 검사를 지우면 J 가 **떨어진다**        (지우기로 이기는 길을 막는다)
  2. 아무것도 단언하지 않는 검사를 더해도 J 가 **안 오른다**
  3. 변형이 잡히는 검사를 더하면 J 가 **오른다**
  4. 없는 이름을 부르는 코드를 넣으면 J 가 **떨어진다**
  5. 같은 나무에서 두 번 재면 **같은 수**다 (숨은 상태가 없다)
  6. 점수가 칸으로 **분해**된다 (어디서 왔는지 볼 수 있다)

그리고 argmax: V 를 지난 후보 중 J 최고를 고르고, V 를 못 지난 것은 **후보가 아니다.**

실행: python3 tests/test_judge.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import judge as Jd  # noqa: E402
import mutate as M  # noqa: E402

FAIL: list = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
판 = Path(tempfile.mkdtemp(prefix="test-J-"))
try:
    git(판, "init", "-q")
    (판 / "tests").mkdir()
    (판 / "계산.py").write_text("def 더하기(a, b):\n    return a + b\n", encoding="utf-8")
    (판 / "tests" / "test_계산.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport 계산\nassert 계산.더하기(1, 2) == 3\n', encoding="utf-8")
    (판 / "부름.py").write_text("def 곱하기(a, b):\n    return a * b\n", encoding="utf-8")
    (판 / "tests" / "test_부름.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport 부름\n부름.곱하기(2, 3)\n', encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "init")

    # 변형 원장을 실제로 쌓는다 -- J 의 절반은 mutate 의 판정에서 온다
    M.사냥(판, 파일들=["계산.py", "부름.py"], 시한초=240, 말하기=lambda s: None)

    print("== J 가 칸으로 분해된다 (불투명한 하나가 아니다) ==")
    _r = Jd.J(판); 점수, 칸 = _r['Y'], _r['칸']
    ok(set(Jd.무게) <= set(칸), f"무게가 걸린 칸이 다 있다 ({sorted(칸)})")
    ok(abs(점수 - sum(Jd.무게[k] * 칸[k] for k in Jd.무게)) < 1e-9, "점수가 칸의 가중합과 같다(숨은 항이 없다)")
    ok("관찰파일수" in Jd.보고(판) and "기여" in Jd.보고(판), "보고가 칸마다 기여를 적는다")
    ok(칸["관찰파일수"] == 1 and 칸["거짓초록수"] >= 1,
       f"**관찰파일수는 변형이 잡힌 파일만 센다** (계산.py 만: {칸['관찰파일수']}) · 거짓초록 {칸['거짓초록수']}")

    print("\n== 같은 나무를 두 번 재면 같은 수다 ==")
    _r2 = Jd.J(판); 점수2, 칸2 = _r2['Y'], _r2['칸']
    ok(점수 == 점수2 and 칸 == 칸2, f"재현된다 ({점수} == {점수2})")

    print("\n== 1. 검사를 지우면 J 가 떨어진다 (지우기로 이기는 길을 막는다) ==")
    전칸 = dict(칸)
    (판 / "tests" / "test_계산.py").unlink()
    git(판, "add", "-A"); git(판, "commit", "-qm", "검사를 지웠다")
    _r3 = Jd.J(판); 점수3, 칸3 = _r3['Y'], _r3['칸']
    ok(점수3 < 점수, f"J 가 떨어졌다 ({점수:.1f} -> {점수3:.1f})")
    나은가, 말 = Jd.더나은가(전칸, 칸3)
    ok(not 나은가 and "J" in 말, f"더나은가 가 '아니다' 라고 말한다 ({말[:70]})")
    ok(칸3["검사없는파일수"] > 전칸["검사없는파일수"], "검사없는파일수가 늘었다 -- 지움이 드러난다")
    git(판, "revert", "--no-edit", "-q", "HEAD")

    print("\n== 2. 아무것도 단언하지 않는 검사를 더해도 J 가 안 오른다 ==")
    _r4 = Jd.J(판); 점수4, 칸4 = _r4['Y'], _r4['칸']
    (판 / "tests" / "test_빈것.py").write_text("assert True\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "빈 검사를 더했다")
    _r5 = Jd.J(판); 점수5, 칸5 = _r5['Y'], _r5['칸']
    ok(점수5 <= 점수4, f"**빈 검사로는 J 가 안 오른다** ({점수4:.1f} -> {점수5:.1f})")
    ok(칸5["관찰파일수"] == 칸4["관찰파일수"], "관찰파일수는 Killed 가 있어야 오른다 -- 파일 수로는 안 오른다")

    print("\n== 3. 변형이 잡히는 검사를 더하면 J 가 오른다 ==")
    (판 / "tests" / "test_부름.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport 부름\nassert 부름.곱하기(2, 3) == 6\n', encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "부름을 실제로 단언한다")
    M.사냥(판, 파일들=["부름.py"], 시한초=240, 말하기=lambda s: None)
    _r6 = Jd.J(판); 점수6, 칸6 = _r6['Y'], _r6['칸']
    ok(점수6 > 점수5, f"**진짜 단언을 더하면 J 가 오른다** ({점수5:.1f} -> {점수6:.1f})")
    ok(칸6["관찰파일수"] > 칸5["관찰파일수"], f"관찰파일수가 늘었다 ({칸5['관찰파일수']} -> {칸6['관찰파일수']})")
    나은가2, 말2 = Jd.더나은가(칸5, 칸6)
    ok(나은가2, f"더나은가 가 '그렇다' 라고 말한다 ({말2[:70]})")

    print("\n== 4. 없는 이름을 부르는 코드를 넣으면 J 가 떨어진다 ==")
    _r7 = Jd.J(판); 점수7, 칸7 = _r7['Y'], _r7['칸']
    (판 / "깨진.py").write_text("def f(x):\n    return 없는것(x)\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "없는 이름")
    _r8 = Jd.J(판); 점수8, 칸8 = _r8['Y'], _r8['칸']
    ok(점수8 < 점수7 and 칸8["미정의수"] > 칸7["미정의수"],
       f"J 가 떨어졌다 ({점수7:.1f} -> {점수8:.1f}, 미정의 {칸7['미정의수']} -> {칸8['미정의수']})")

    print("\n== J(P, X, Θ, R): 평가에 영향을 주는 조건이 전부 파라미터다 ==")
    # 사용자(2026-09-12): "J(program, input/condition, objective, measurement protocol) -> evaluation result".
    # 조건을 코드에 박아 두면 같은 수를 다른 뜻으로 읽게 된다 -- 그것이 조용한 거짓 초록이다.
    기 = Jd.J(판)
    ok(set(기) >= {"Y", "칸", "X", "Θ", "R"}, f"Y 와 함께 (X, Θ, R) 을 되돌려준다 ({sorted(기)})")
    다른Θ = Jd.J(판, Θ={"무게": {"미정의수": -100.0}})
    ok(다른Θ["Y"] != 기["Y"] or 기["칸"]["미정의수"] == 0,
       "Θ(무게)를 바꾸면 Y 가 달라진다 -- 같은 P 라도 기준이 다르면 수가 다르다")
    ok(Jd.J(판, Θ={"방향": "최소"})["Y"] == -기["Y"], "Θ(방향)=최소 면 부호가 뒤집힌다")
    좁힌 = Jd.J(판, X={"파일들": ["계산.py"]})
    ok(좁힌["칸"]["코드파일수"] == 1 and 좁힌["X"]["파일들"] == ["계산.py"],
       f"X(파일 범위)를 좁히면 그 범위만 잰다 (코드파일수 {좁힌['칸']['코드파일수']})")
    가짜 = lambda P, 원장=None: {"관찰파일수": 7, "거짓초록수": 0, "미정의수": 0, "검사없는파일수": 0}
    ok(Jd.J(판, R={"측정자": 가짜})["Y"] == 70.0,
       "R(측정 프로토콜)을 갈아끼우면 그것으로 잰다 -- 검사가 J 의 논리만 따로 붙들 수 있다")
    델 = Jd.ΔJ(판, 판)
    ok(델["Δ"] == 0.0 and 델["나아졌나"] is False, "같은 나무의 ΔJ 는 0 이고 '나아졌다' 가 아니다")

    print("\n== Valid(J): 구별 가능성 Obs_J 를 기계로 확인한다 ==")
    # Pa ≁ Pb => J(Pa) ≠ J(Pb). 구별 못 하는 J 위의 argmax 는 아무 방향으로도 최적화하지 않는다.
    작 = lambda P, 원장=None: {"관찰파일수": 1, "거짓초록수": 0, "미정의수": 0, "검사없는파일수": 0}
    큼 = lambda P, 원장=None: {"관찰파일수": 5, "거짓초록수": 0, "미정의수": 0, "검사없는파일수": 0}
    ok(Jd.구별하나(판, 판, R={"측정자": 작})[0] is False,
       "**같은 수를 내면 구별하지 못한다고 말한다** (ledgerstat 의 여섯 칸이 늘 0 이던 자리)")
    눈먼 = Jd.타당한가([(판, 판, "다른 두 판인데 같은 수")], R={"측정자": 작})
    ok(눈먼["타당한가"] is False and "못 구별한다" in 눈먼["말"], f"Valid(J) 가 거짓이라고 말한다 ({눈먼['말'][:50]})")
    ok(Jd.타당한가([])["타당한가"] is False, "견줄 쌍이 없으면 타당성을 주장하지 않는다")

    print("\n== Improve(P,P') = V(P') ∧ Valid(J) ∧ ΔJ > 0 ==")
    개 = Jd.개선인가(판, 판, V=lambda P: (True, ""), 쌍들=[(판, 판, "같은 것")], R={"측정자": 작})
    ok(개["개선인가"] is False and any("Valid(J)" in x for x in 개["막힌것"]),
       "Valid(J) 가 안 서면 개선이라 하지 않는다")
    개2 = Jd.개선인가(판, 판, V=lambda P: (False, "V 빨강"), 쌍들=None)
    ok(개2["개선인가"] is False and any("V(P')=FAIL" in x for x in 개2["막힌것"]), "V 가 빨갛면 개선이 아니다")
    개3 = Jd.개선인가(판, 판, V=lambda P: (True, ""), 쌍들=None)
    ok(개3["개선인가"] is False and any("Valid(J) 를 안 쟀다" in x for x in 개3["막힌것"]),
       "**Valid(J) 를 안 쟀으면 개선을 주장하지 않는다** -- 모르는 것은 개선이 아니다")

    print("\n== argmax: V 를 지난 후보 중 J 최고를 고른다 ==")
    후보들 = [{"이름": "가", "점수될것": 1.0}, {"이름": "나", "점수될것": 9.0}, {"이름": "다", "점수될것": 5.0}]
    고 = Jd.고르기(후보들, V=lambda 후: (후["이름"] != "나", "V 빨강"), J자=lambda 후: (후["점수될것"], {}))
    ok(고["고른것"]["이름"] == "다",
       f"**V 를 못 지난 후보는 J 가 높아도 안 고른다** (고른 것: {고['고른것']['이름']})")
    ok([x["이름"] for x in 고["막힌것"]] == ["나"], "막힌 후보를 따로 적는다")
    고2 = Jd.고르기(후보들, V=lambda 후: (True, ""), J자=lambda 후: (후["점수될것"], {}))
    ok(고2["고른것"]["이름"] == "나", "전부 지나면 J 최고를 고른다")
    고3 = Jd.고르기(후보들, V=lambda 후: (False, "전부 빨강"), J자=lambda 후: (후["점수될것"], {}))
    ok(고3["고른것"] is None and "V 를 지난 후보가 없다" in 고3["왜"],
       "**하나도 V 를 못 지나면 고르지 않는다** -- 최선을 고르는 것이 아니다")
    고4 = Jd.고르기([{"이름": "가"}, {"이름": "나"}], V=lambda 후: (True, ""), J자=lambda 후: (3.0, {}))
    ok(고4["고른것"]["이름"] == "가" and "동점" in 고4["왜"], "동점이면 먼저 온 것 -- 흔들지 않는다")
    ok(Jd.고르기([])["고른것"] is None, "후보가 없으면 None")
finally:
    shutil.rmtree(판, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("judge: 칸 분해 · 재현 · 지움에 떨어짐 · 빈 검사에 안 오름 · 진짜 단언에 오름 · 결함에 떨어짐 · argmax -- 통과")
