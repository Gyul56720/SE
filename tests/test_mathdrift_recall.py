"""①재현 축의 심판 -- **LLM 도 네트워크도 안 쓴다.** 가짜 답을 Brent 항등식에 건다.

이 축이 있는 이유: 낱말 겹침으로 인과를 재던 자가 뒤집혀 있었다(실측 2026-09-07, 85개).
부모 이름에 연산자 어휘를 덧붙인 것이 최고점을 받고(S9 0.529), 이름이 정말 바뀐
"지수 대역(Exponent Cone)" -- Strassen 의 점근 스펙트럼 -- 이 "남의 공간" 으로
깎였다(S6 0.077). 카드를 펼치자 판별자가 이름이 아니라 되사상이었다:

    S34  "요네다 매몰을 통해 ... 재해석"        <- 차 있지만 공허하다
    S6   "역으로 텐서의 점근적 구성 방식을 복원"  <- 무엇을 하는지 말한다

되사상이 비었는지는 space.grade 가 본다. **차 있는데 공허한 것**은 못 본다. 그래서
설명으로 받지 않고 시켜 보고, 받은 수를 기계가 검산한다.

무엇을 고정하나:
  · 진짜 Strassen 은 통과하고 한 칸만 틀려도 떨어지는가 (심판이 살아 있는가)
  · 못 하겠다는 답과 못 읽는 답이 통과로 새지 않는가
  · 전치·분수 문자열처럼 꼴만 다른 것을 멀쩡한 답인데 버리지 않는가
  · 겹친 중괄호가 통째로 읽히는가 (해독 칸이 중첩이라 여기서 한 번 데었다)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import recall as R
from mathdrift import spread as SPR

fails = []


def ok(cond, what):
    print(("    OK   " if cond else "    실패 ") + what)
    if not cond:
        fails.append(what)


# 진짜 Strassen. U 의 행 a = i*2+l, V 의 행 = l*2+j, W 의 행 = i*2+j.
U = [[1, 0, 1, 0, 1, -1, 0], [0, 0, 0, 0, 1, 0, 1],
     [0, 1, 0, 0, 0, 1, 0], [1, 1, 0, 1, 0, 0, -1]]
V = [[1, 1, 0, -1, 0, 1, 0], [0, 0, 1, 0, 0, 1, 0],
     [0, 0, 0, 1, 0, 0, 1], [1, 0, -1, 0, 1, 0, 1]]
W = [[1, 0, 0, 1, -1, 0, 1], [0, 0, 1, 0, 1, 0, 0],
     [0, 1, 0, 1, 0, 0, 0], [1, -1, 1, 0, 0, 1, 0]]
GOOD = {"가능": True, "점": "…", "해독": {"U": U, "V": V, "W": W, "lambda": [1] * 7}}


def copy(d):
    return json.loads(json.dumps(d))


print("[심판] **판정에 LLM 이 한 방울도 안 들어간다** -- Brent 항등식이 정한다")
ok(R.judge(GOOD)[0] == "재현", "진짜 Strassen 은 통과한다")
_bad = copy(GOOD)
_bad["해독"]["W"][0][0] = 0
ok(R.judge(_bad)[0] == "틀림",
   "한 칸만 틀려도 떨어진다  ← 심판이 살아 있다는 증거다")
_z = copy(GOOD)
_z["해독"]["lambda"] = [0] * 7
ok(R.judge(_z)[0] == "틀림", "전부 0 인 답이 통과하지 않는다 (vacuous 방지)")

print()
print("[거절] **못 한다는 답이 통과로 새지 않는가**")
ok(R.judge({"가능": False, "못하는이유": "되사상이 없다"})[0] == "거절", "못 한다면 거절")
ok(R.judge({"가능": True, "점": "…"})[0] == "못읽음", "해독이 없으면 못읽음")
ok(R.judge({"가능": True, "해독": {"U": [[1, 2]], "V": U, "W": U,
                                 "lambda": [1] * 7}})[0] == "못읽음", "크기가 틀리면 못읽음")
ok(R.judge({"가능": True, "해독": {"U": U, "V": V, "W": W,
                                 "lambda": [1] * 3}})[0] == "못읽음", "lambda 가 모자라면 못읽음")

print()
print("[꼴] **멀쩡한 답을 꼴 때문에 버리지 않는다**")
_t = copy(GOOD)
_t["해독"]["U"] = [[U[a][r] for a in range(4)] for r in range(7)]
ok(R.judge(_t)[0] == "재현", "전치돼 와도 받는다  ← 규약을 적어 줘도 흔히 바꿔 온다")
_f = copy(GOOD)
_f["해독"]["lambda"] = ["2"] * 7
_f["해독"]["W"] = [[str(x) + "/2" for x in row] for row in W]
ok(R.judge(_f)[0] == "재현", "분수 문자열도 받는다")

print()
print("[겹친 중괄호] **해독 칸이 중첩이라 여기서 한 번 데었다**")
_nested = SPR.objects("```json\n" + json.dumps(GOOD) + "\n```")
ok(len(_nested) == 1 and "가능" in _nested[0],
   "겹친 것을 통째로 읽는다  ← 안쪽만 물면 '가능 칸이 없다' 며 거절로 샌다")

print()
print("[한 바퀴] 가짜 모델로")
_calls = []


def fake(p):
    _calls.append(p)
    return "```json\n" + json.dumps(GOOD) + "\n```"


_rec = {"id": "S9", "이름": "시험", "되사상": "…"}
_out = R.one(_rec, fake, log=lambda *a: None)
ok(_out.get("판정") == "재현" and _rec["재현"]["판정"] == "재현", "판정이 원장에 적힌다")
ok("Strassen" in _calls[0] and "i*2+l" in _calls[0],
   "프롬프트에 시금석과 첨자 규약이 실린다")
ok(R.one({"id": "S1"}, lambda p: "미안", log=lambda *a: None)["판정"] == "못읽음",
   "JSON 이 아니면 못읽음")


def boom(p):
    raise RuntimeError("쿼터")


ok(R.one({"id": "S1"}, boom, log=lambda *a: None) == {}, "호출이 터지면 빈 것")

print()
if fails:
    print(f"mathdrift 재현: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("mathdrift 재현: 심판 · 거절 · 꼴 · 겹친 중괄호 · 한 바퀴 -- 통과")
