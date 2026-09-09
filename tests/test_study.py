"""**취약점이 세어서 나오는가 -- 그리고 못 잰 것을 못 잰다고 하는가.**

    python3 tests/test_study.py

이 검사의 요점은 **약점을 못 찾는 쪽**이다. "너는 확률에 약해" 는 세 문제 틀리고도
할 수 있는 말이고, 그 말이 맞는지는 아무도 모른다. 학생은 맞는 줄 알고 엉뚱한 데
시간을 쓴다. 그래서 여기서 붙드는 것은 **표본이 짧을 때 약점이라고 말하지 않는가**다.

한 번에 세 군데를 잘못 짰고 셋 다 이 검사가 붙든다(실측 2026-09-09):

    (1) Holm 에 안 잰 태그까지 넣어 문턱을 부풀렸다  p=0.140 -> 0.560, 약점이 사라짐
    (2) MIN_N 과 최소p 를 둘 다 문턱으로 두어, 가릴 수 있는 것을 못 가린다고 했다
    (3) 판정과 조언이 **다른 자**를 썼다  "이미 갈릴 수 있다" 와 `못잼` 이 나란히 찍힘
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from study import note as NT                                   # noqa: E402
from study import plan as PL                                   # noqa: E402
from study import run as RN                                    # noqa: E402
from study import weak as WK                                   # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def 공책(맞틀: dict, 태그: dict) -> NT.공책:
    """`{문제id: 맞았나}` 와 `{문제id: [태그]}` 로 공책 하나."""
    n = NT.공책()
    for qid, ts in 태그.items():
        n.넣기(NT.문제(id=qid, 말=f"{qid} 문제", 정답="정", 태그=list(ts), 출처="검사"))
    for qid, 맞 in 맞틀.items():
        n.시도.append(NT.시도(문제id=qid, 낸답=("정" if 맞 else "오"), 맞았나=맞,
                            언제=NT.지금()))
    return n


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = RN.main(argv)
    return code, buf.getvalue()


print("── 채점: **모르면 모른다고 한다** ──────────────────────")
ok(NT.채점("3/10", "3/10") is True, "같으면 맞음")
ok(NT.채점("3/10", " 3 / 10 ") is True, "공백·대소문자는 고른다")
ok(NT.채점("0.2", "0.20") is True, "수는 수로 견준다")
ok(NT.채점("4", "5") is False, "짧은 답이 다르면 틀림")
긴정답 = "두 사건 A,B에 대해 P(B|A)=P(A∩B)/P(A) 로, A가 일어났다는 조건 아래 B의 확률"
ok(NT.채점(긴정답, "조건부확률은 A가 일어났을 때 B가 일어날 확률이다") is None,
   "**서술형은 None** -- 억지로 참·거짓을 내면 그 우김 위에서 취약점이 돈다")
ok(NT.채점("", "3") is None and NT.채점("3", "") is None, "빈 것은 None")

print()
print("── 이항 꼬리 · 도달 가능한 최소 p ───────────────────────")
ok(abs(WK.이항꼬리(2, 2, 0.5) - 0.25) < 1e-9, "P(X>=2|2,0.5)=0.25")
ok(abs(WK.이항꼬리(0, 5, 0.3) - 1.0) < 1e-9, "k=0 이면 1")
ok(WK.이항꼬리(6, 5, 0.3) == 0.0, "n 보다 많이는 못 틀린다")
ok(abs(WK.도달가능최소p(3, 0.5) - 0.125) < 1e-9,
   "**다 틀려도 나올 수 있는 가장 작은 p** = p0^n")
ok(WK.도달가능최소p(0, 0.5) == 1.0, "표본이 없으면 1")

print()
print("── 짧은 표본에서는 **약점이라고 말하지 않는다** ──────────")
짧은 = 공책({"a1": False, "a2": False, "a3": False, "b1": True, "b2": True},
           {"a1": ["확률"], "a2": ["확률"], "a3": ["확률"],
            "b1": ["대수"], "b2": ["대수"]})
것들 = WK.취약점(짧은)
확 = next(w for w in 것들 if w.태그 == "확률")
ok(확.판정 == "못잼",
   f"**세 문제를 다 틀려도 '약함' 이 아니다** ({확.판정}) -- 못 잰 것이다")
보 = PL.취약점보고(짧은)
ok("못 잰 것이지 잘하는 것이 아니다" in 보, "못잼에 그 말을 붙인다")
ok("문제쯤 더 풀면 갈린다" in 보,
   "**몇 개 더 풀면 갈리는지 적는다** -- 안 적으면 학생은 다음에 무엇을 할지 모른다")

print()
print("── 표본이 차면 **약점이라고 말한다** ────────────────────")
맞틀, 태그 = {}, {}
for i in range(1, 9):                                # 조건부 7/8 틀림
    맞틀[f"c{i}"], 태그[f"c{i}"] = (i == 8), ["조건부"]
for i in range(1, 9):                                # 대수 1/8 틀림
    맞틀[f"a{i}"], 태그[f"a{i}"] = (i != 1), ["대수"]
for i in range(1, 9):                                # 수열 1/8 틀림
    맞틀[f"s{i}"], 태그[f"s{i}"] = (i != 1), ["수열"]
찬 = 공책(맞틀, 태그)
것들 = WK.취약점(찬)
조 = next(w for w in 것들 if w.태그 == "조건부")
대 = next(w for w in 것들 if w.태그 == "대수")
ok(조.판정 == "약함", f"7/8 틀린 태그는 약함 (보정 p={조.p보정:.3f})")
ok(대.판정 == "평범", f"1/8 틀린 태그는 평범 ({대.판정})")
ok(조.문제들 == [f"c{i}" for i in range(1, 8)], "**근거 문제 id 를 들고 있다**")
ok(것들[0].판정 == "약함", "약한 것이 앞에 온다")

print()
print("── (회귀) Holm 에 **안 잰 태그**를 넣어 문턱을 부풀렸다 ──")
# 실측: ps 에 None 까지 통째로 넘겼더니 holm 이 m=len(ps) 로 세어, 잰 것이 하나뿐인데
# 문턱을 넷으로 조였다 -- p=0.140 이 0.560 으로 부풀어 약점이 사라졌다.
섞임 = 공책({**{f"x{i}": (i > 6) for i in range(1, 9)},          # x: 6/8 틀림
             "y1": True, "y2": True},                            # y: 2문제뿐(안 잼)
            {**{f"x{i}": ["엑스"] for i in range(1, 9)},
             "y1": ["와이"], "y2": ["와이"]})
것들 = WK.취약점(섞임)
잰것 = [w for w in 것들 if w.p is not None]
ok(len(잰것) == 1, f"실제로 잰 태그는 하나 ({[w.태그 for w in 잰것]})")
x = next(w for w in 것들 if w.태그 == "엑스")
ok(abs(x.p보정 - x.p) < 1e-12,
   f"**잰 것이 하나면 Holm 이 안 조인다** (p={x.p:.3f} 보정={x.p보정:.3f})")
y = next(w for w in 것들 if w.태그 == "와이")
ok(y.p보정 is None and y.판정 == "못잼", "안 잰 태그는 못잼 -- 평범이 아니다")

print()
print("── (회귀) 판정과 조언이 **같은 자**를 쓰는가 ────────────")
# 실측: 몇개더 는 날 p0(0.333)를, 판정은 라플라스로 민 것(0.364)을 써서
# 같은 태그에 "이미 갈릴 수 있다" 와 `못잼` 이 나란히 찍혔다.
for w in WK.취약점(짧은):
    if w.판정 != "못잼":
        continue
    더 = WK.몇개더(w, 짧은 and WK.전체기저(짧은)[2],
                  m=sum(1 for z in WK.취약점(짧은) if z.p is not None) or 1)
    ok(더 != 0,
       f"**못잼인데 '이미 갈릴 수 있다'(0)고 하지 않는다** ({w.태그}: {더})")
ok(all(w.쓴기저 > 0 for w in WK.취약점(찬)),
   "판정에 쓴 자를 약점이 들고 다닌다 -- 화면이 딴 자를 쓰면 어긋난다")

print()
print("── (회귀) MIN_N 과 최소p 를 둘 다 문턱으로 두지 않는다 ──")
ok(WK.MIN_N == 3,
   f"MIN_N 은 밑바닥이지 자가 아니다 ({WK.MIN_N}) -- 가르는 일은 도달가능최소p 가 한다")
셋다틀림 = 공책({**{f"c{i}": False for i in range(1, 4)},
                **{f"a{i}": (i > 1) for i in range(1, 9)}},
               {**{f"c{i}": ["씨"] for i in range(1, 4)},
                **{f"a{i}": ["에이"] for i in range(1, 9)}})
c = next(w for w in WK.취약점(셋다틀림) if w.태그 == "씨")
ok(c.p is not None, "n=3 이어도 **재기는 한다** -- 4 로 막아 두었던 자리")

print()
print("── 같은 문제를 여러 번 풀어도 한 번만 센다 ──────────────")
n = 공책({}, {"q1": ["가"], "q2": ["가"], "q3": ["가"]})
for _ in range(5):
    n.시도.append(NT.시도(문제id="q1", 낸답="오", 맞았나=False, 언제=NT.지금()))
n.시도.append(NT.시도(문제id="q2", 낸답="정", 맞았나=True, 언제=NT.지금()))
n.시도.append(NT.시도(문제id="q3", 낸답="정", 맞았나=True, 언제=NT.지금()))
전, 틀, _ = WK.전체기저(n)
ok((전, 틀) == (3, 1),
   f"**문제 하나를 한 번만 센다** ({전}문제 {틀}틀림) -- 열 번 틀려도 문제 열 개가 아니다")
n.시도.append(NT.시도(문제id="q1", 낸답="정", 맞았나=True, 언제=NT.지금()))
전2, 틀2, _ = WK.전체기저(n)
ok((전2, 틀2) == (3, 0), "**마지막 시도를 본다** -- 다시 풀어 맞히면 는 것이 보인다")
ok(len(n.틀린것()) == 5, "그래도 오답노트에는 그 다섯 줄이 남는다 -- 덮어쓰지 않는다")

print()
print("── 교안: **확인된 약점만** ──────────────────────────────")
교 = PL.교안(찬, "검사")
ok("### 1. 조건부" in 교, "약한 것부터 넣는다")
ok("대수" not in 교.split("## 여기 안 넣은 것")[0],
   "**평범한 태그는 교안에 안 들어간다** -- 넣으면 없는 약점을 가르친다")
ok("c1" in 교 and "근거 문제" in 교, "근거 문제 id 를 붙인다")
ok("이 교안이 안 보는 것" in 교 and "왜" in 교,
   "**세는 것으로는 태그까지다** -- 까닭은 사람이 적는다고 밝힌다")

교2 = PL.교안(짧은, "짧은")
ok("아직 교안을 못 만든다" in 교2,
   "**약점이 없으면 교안을 안 만든다** -- 일반론으로 채우지 않는다")
ok("이 오답노트를 안 보고도" in 교2, "왜 일반론을 안 쓰는지 적는다")
ok("문제쯤 더" in 교2 or "이미 갈릴 수 있다" in 교2, "대신 몇 개 더 풀면 되는지 적는다")

print()
print("── 오답노트: 줄이지 않는다 ─────────────────────────────")
n2 = 공책({"q1": False}, {"q1": ["가"]})
n2.문제["q1"].해설 = "이러이러하다"
n2.시도[0].메모 = "이렇게 풀었다"
n2.시도[0].짚은것 = "여기를 잘못 봤다"
오 = PL.오답노트(n2)
for 말 in ("문제:", "낸 답:", "정답:", "해설:", "내 메모:", "짚은 것:", "출처:"):
    ok(말 in 오, f"오답노트에 '{말}' 가 있다")
빈 = PL.오답노트(공책({}, {"q1": ["가"]}))
ok("틀린 것이 없다" in 빈 and "아직 채점된 것이 없다" in 빈,
   "안 푼 것과 다 맞은 것을 갈라 말한다")

print()
print("── 저장·읽기 ───────────────────────────────────────────")
with tempfile.TemporaryDirectory() as d:
    자리 = Path(d) / "공책"
    NT.저장(찬, 자리)
    다시 = NT.읽기(자리)
    ok(len(다시.문제) == len(찬.문제) and len(다시.시도) == len(찬.시도), "되읽는다")
    ok(WK.전체기저(다시) == WK.전체기저(찬), "되읽어도 셈이 같다")
    (자리 / "시도.jsonl").write_text('{"문제id":"c1","맞았나":false}\n깨진 줄\n'
                                    '{"문제id":"c2","맞았나":true}\n', encoding="utf-8")
    ok(len(NT.읽기(자리).시도) == 2,
       "**한 줄이 깨져도 나머지는 산다** -- 다 버리면 오답노트가 통째로 없어진다")
    ok(NT.읽기(Path(d) / "없다").시도 == [], "없는 자리로 안 죽는다")

print()
print("── CLI ──────────────────────────────────────────────────")
with tempfile.TemporaryDirectory() as d:
    자리 = str(Path(d) / "공책")
    qs = Path(d) / "q.json"
    qs.write_text(json.dumps([
        {"id": "q1", "말": "1+1은?", "정답": "2", "태그": ["산수"], "출처": "검사"},
        {"id": "q2", "말": "정답 없는 문제", "태그": ["산수"]}], ensure_ascii=False),
        encoding="utf-8")
    code, out = run(["--공책", 자리, "--넣기", str(qs)])
    ok(code == 0 and "문제 2개 넣었다" in out, "넣는다")
    ok("정답이 없는 것 1개" in out and "출처 없는 것" in out,
       "**정답·출처가 없으면 그 자리에서 말한다** -- 나중에 못 세는 것들이다")

    code, out = run(["--공책", 자리, "--낼것"])
    ok(code == 0 and "q1" in out, "안 푼 문제를 낸다")
    ok("2" not in out.split("답:")[0].replace("q1", "").replace("1+1", ""),
       "**정답을 안 보여 준다** -- 안 그러면 검사가 아니다")

    code, out = run(["--공책", 자리, "--답", "q1", "3", "--메모", "잘못 셌다"])
    ok(code == 0 and "틀렸다" in out and "정답: 2" in out, "채점하고 정답을 보여 준다")
    ok("--짚기" in out, "왜 틀렸는지 짚어 두라고 알려 준다")

    code, out = run(["--공책", 자리, "--답", "없는id", "3"])
    ok(code == 1 and "그런 문제가 없다" in out, "없는 id 로 안 죽는다")

    code, out = run(["--공책", 자리, "--오답노트"])
    ok(code == 0 and "1+1은?" in out and "잘못 셌다" in out, "오답노트가 나온다")

    code, out = run(["--공책", 자리, "--취약점"])
    ok(code == 0 and "못잼" in out, "표본이 하나면 못잼")

    code, out = run(["--공책", 자리])
    ok(code == 3 and "공책:" in out, "아무것도 안 주면 상태와 쓸 것을 보여 준다")

print()
if fails:
    print(f"study: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("채점(모르면 None) · 이항 꼬리 · 짧으면 못잼 · 차면 약함 · "
      "Holm 에 잰 것만 · 한 자로 판정과 조언 · 문제 하나를 한 번만 · "
      "확인된 약점만 교안 -- 통과")
