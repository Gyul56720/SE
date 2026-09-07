"""가설 -> 증명. **유도가 이어지는가** -- LLM 도 네트워크도 안 쓴다.

여기까지 파이프라인은 자식 식을 **주장**만 했다. "경계화를 걸면 이런 식이 된다" 고 적을
뿐, 부모 식에서 그리로 가는 길을 보이지 않았다 -- 그것이 겉핥기고 이름 짓기와 다를 바가
없다. `유도` 는 그 길을 걸음마다 적는 칸이고, 이 자가 걸음마다 판정한다.

**증명과 도약은 같은 걸음에 못 들어간다.** 유도가 E0 = E1 = ... = En 이면 자식은 부모와
동치다 -- 다시 쓴 것이지 새것이 아니다. 진짜 도약(Cohn-Umans 의 군대수 매장)은 등식이
아니라 **사상**이라, 사슬로는 증명되지 않는다. 그래서 증명 의무를 셋으로 나눈다:

    항등 이주      유도 사슬로 증명    (sympy)
    사상 도약      왕복 검산으로 증명  (부호화 -> 해독 -> Brent. recall.py)
    물음 갈아타기  증명할 수 없다      (omega 에는 Strassen 점이 없다 -- 정직한 한계)

무엇을 고정하나:
  · 셋으로 판정한다 -- **미정이 요점이다**. 극한·체 바꿈은 대수 항등식이 아니다
  · 반례로 거짓을 잡는다 (자유 기호에 유리수를 넣어 한 점이라도 어긋나면)
  · 풀리지 않은 Limit/Sum 때문에 거짓이 미정으로 새지 않는다
  · 갈래를 가른다 -- 도약이 "미정" 으로 뭉개지지 않는다
  · **격리**: sympify 는 임의 코드를 실행한다. 부모가 그 수식을 파싱하지 않는다
"""
from __future__ import annotations

import io
import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import prove as PR
from mathdrift import space as SP

fails = []


def ok(cond, what):
    print(("    OK   " if cond else "    실패 ") + what)
    if not cond:
        fails.append(what)


def rec(steps, op="쌍대", dist=1, sid="S9"):
    return {"id": sid, "계보": {"부모": "S1", "연산자": op, "거리": dist},
            "유도": [{"식": e, "근거": w} for e, w in steps]}


print("[사슬] **참 · 거짓 · 미정 셋이다**")
_r = rec([("(x+1)**2", "부모"), ("x**2 + 2*x + 1", "항등")])
_v = PR.check(_r)
ok(_v["판정"] == "이어짐" and _v["셈"]["참"] == 1, "옳은 걸음은 참")
_r2 = rec([("(x+1)**2", "부모"), ("x**2 + 2*x + 2", "항등")])
_v2 = PR.check(_r2)
ok(_v2["판정"] == "끊김" and _v2["셈"]["거짓"] == 1,
   "**틀린 걸음은 거짓** -- 사슬이 끊겼다고 말한다")
ok("차이" in _v2["걸음"][0]["왜"], f"어디서 어긋났는지 적는다 ({_v2['걸음'][0]['왜']})")
_r3 = rec([("x**2 + 2*x + 2", "부모"), ("exp(I*x)", "항등")])
ok(PR.check(_r3)["셈"]["거짓"] == 1, "반례로도 거짓을 잡는다")
_r4 = rec([("exp(I*x)", "부모"), ("cos(x) + I*sin(x)", "항등")])
ok(PR.check(_r4)["셈"]["참"] == 1, "오일러는 참 (기호로 줄어든다)")

print()
print("[미정] **가를 수 없는 것과 가를 것이 아닌 것은 다르다**")
_r5 = rec([("zeta(3)", "부모"), ("pi**3/25", "정의")])
_v5 = PR.check(_r5)
ok(_v5["셈"]["거짓"] == 1 or _v5["셈"]["미정"] == 1, "수로 가를 수 있으면 가른다")
_r6 = rec([("f(x)", "부모"), ("g(x)", "극한")])
_v6 = PR.check(_r6)
ok(_v6["셈"]["미정"] == 1, "모르는 함수끼리는 미정")
ok(_v6["걸음"][0]["대수밖"],
   "**근거가 극한이면 '대수 밖' 으로 표시한다** -- 못 가른 것이 아니라 가를 것이 아니다")
ok(not PR.check(rec([("x", "부모"), ("y", "항등")]))["걸음"][0]["대수밖"],
   "근거가 항등인데 미정/거짓이면 대수 밖이 아니다")

print()
print("[안 풀린 것] Limit 이 남아 거짓이 미정으로 새지 않는가")
_r7 = rec([("Limit(a*m + e, e, 0)", "부모"), ("a*m + 1", "항등")])
_v7 = PR.check(_r7)
ok(_v7["셈"]["거짓"] == 1,
   f"Limit 을 풀고 견준다 ({_v7['걸음'][0]['판정']}) ← 안 풀면 미정으로 샌다(실측)")

print()
print("[갈래] **도약이 미정에 묻히지 않는다**")
_t1 = PR.tier(rec([("x", "부모"), ("x", "항등")], op="쌍대", dist=1))
ok(_t1["갈래"] == "항등 이주" and _t1["증명"] == "유도 사슬", "거리 1 항등은 사슬로 증명")
_t2 = PR.tier(rec([("x", "부모"), ("rho(x)", "사상")], op="매장", dist=2))
ok(_t2["갈래"] == "사상 도약" and _t2["증명"] == "왕복 검산",
   "**사상은 사슬이 아니라 왕복이 증명 자리다** (Cohn-Umans 의 triple product property)")
_t3 = PR.tier(rec([("x", "부모")], op="점근화", dist=2))
ok(_t3["갈래"] == "물음 갈아타기" and _t3["증명"] == "없음",
   "물음이 바뀌면 시금석이 없다 -- 정직한 한계")
ok(PR.tier({"계보": {"연산자": "매장", "거리": 1}, "유도": []})["갈래"] == "사상 도약",
   "연산자 이름만으로도 갈래가 잡힌다")

print()
print("[없음] 유도가 없다고 벌하지 않는다")
_n = PR.check({"id": "S2", "계보": {"연산자": "쌍대", "거리": 1}})
ok(_n["판정"] == "없음", "유도가 없으면 없음")
_n2 = PR.check({"id": "S2", "계보": {"연산자": "매장", "거리": 2}})
ok("사슬이 증명 자리가 아니다" in _n2["왜"],
   "도약인데 유도가 없으면 **그건 결함이 아니라고** 말해 준다")
ok(PR.steps_of({"유도": "문자열"}) == [], "꼴이 어긋나도 안 터진다")

print()
print("[격리] **sympify 는 임의 코드를 실행한다** -- 부모는 그 수식을 파싱하지 않는다")
_mark = Path("/tmp/md_prove_ran")
_mark.unlink(missing_ok=True)
_evil = rec([(f"__import__('pathlib').Path('{_mark}').write_text('x')", "부모"),
             ("0", "항등")])
_ve = PR.check(_evil)
ok(_ve["판정"] in ("이어짐", "끊김", "일부 미정"), "험한 것이 와도 판정은 돌아온다")
# **정직하게**: 격리는 프로세스 분리이지 샌드박스가 아니다. 코드는 실제로 돈다 --
# 다만 부모가 아니라 자식에서 돈다. 그래서 부모의 상태(임포트·전역·심판)에 못 닿는다.
# 이 줄을 `not 존재 or True` 로 적었다가 스스로 가짜 green 을 만들 뻔했다(2026-09-08).
ok(_mark.exists(), "**샌드박스가 아니다** -- 수식 속 코드는 실제로 돈다 (자식에서)")
ok("sympy" not in sys.modules,
   "**부모가 sympy 를 임포트조차 안 했다** -- 파싱이 부모에 없다 (mathgen/_worker.py 규율)")
_mark.unlink(missing_ok=True)

print()
print("[원장] 갈래별로 나눠 센다")
_led = SP.load(SP.SEED)
for _e, _op, _d, _w in ((("x**2 + 2*x + 1"), "쌍대", 1, "항등"),
                        (("rho(x)"), "매장", 2, "사상"),
                        (("omega"), "점근화", 2, "점근")):
    _s = SP.add(_led, {"식": _e, "점": "p", "정의역": "F = R",
                       "유도": [{"식": "(x+1)**2", "근거": "부모"},
                                {"식": _e, "근거": _w}]},
                parent="S1", op=_op, dist=_d)
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    _rc = PR.report(_led)
_out = _buf.getvalue()
ok(_rc == 0 and "[항등 이주]" in _out and "[사상 도약]" in _out and "[물음 갈아타기]" in _out,
   "세 갈래를 나눠서 보여 준다")
ok("한계다" in _out, "물음 갈아타기가 한계라고 적혀 있다")
ok(all("증명" in x for x in (_led["spaces"][1], _led["spaces"][2])),
   "판정을 원장에 적어 둔다")

print()
if fails:
    print(f"mathdrift 증명: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("mathdrift 증명: 사슬 · 미정 · 안 풀린 것 · 갈래 · 없음 · 격리 · 원장 -- 통과")
