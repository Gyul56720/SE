"""능동성과 압박 -- 2026-09-04 피드백의 첫 항목을 기계로 옮긴 것.

피드백: "주인공이 철저하게 수동적이다. 사건의 단서를 타인의 입을 통해 일방적으로 전달받는다.
상황을 타개하려는 의지나 구체적인 반작용(Action)을 보이지 않는다."

그 지적이 맞았고 원인은 문장이 아니라 조립이었다. 역방향 조립은 **무엇이 참이 되는가**
(establishes)만 물었지 **누가 그것을 했는지** 묻지 않았다. 그래서 조건이 저절로 성립하고
화자는 구경했다.

여기서 고정하는 것:
  1. 조립 단계가 driver/cost/deadline_hours 없이는 비트를 받지 않는다
     (이 셋은 산문이 아니라 선언이라, 씬 관문에서 잡으면 수리 루프가 못 고친다 -- V009 가
      정확히 그렇게 회차를 세웠다)
  2. 같은 마감 안에서 시계가 되감기면 V023 이 보고한다

실행: python3 tests/test_agency.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import drive as D, gate                                    # noqa: E402
from novel.state import Scene                                         # noqa: E402
from novel.world_romance import build, OUTCOMES                       # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


n = build()
POV = n.pov_character

print("[결말] 모든 결말 블록에 시계가 달려 있는가")
ok(all(o.get("deadline") and o.get("deadline_hours") for o in OUTCOMES),
   f"15개 결말 전부 마감·남은시간을 갖는다")
ok(all(o.get("stake") for o in OUTCOMES), "못 지키면 잃는 것도 정해져 있다")
first, last = OUTCOMES[0], OUTCOMES[-1]
ok(last["deadline_hours"] < first["deadline_hours"],
   f"후반이 더 촉박하다 ({first['deadline_hours']}h -> {last['deadline_hours']}h)")

print("[조립] 선언이 없으면 비트를 받지 않는가  ← 산문 수리로는 못 고치는 자리다")
clock = 14.0
bad = D._check_pressure({"driver": "", "cost": "x", "deadline_hours": 9}, n, clock)
ok(bad and "움직이는 사람" in bad[0], f"driver 가 비면 되돌려보낸다 ({bad})")

bad = D._check_pressure({"driver": "없는사람", "cost": "x", "deadline_hours": 9}, n, clock)
ok(bad and "등장인물이 아니다" in bad[0], "등장인물이 아닌 이름도 잡는다")

bad = D._check_pressure({"driver": POV, "cost": "", "deadline_hours": 9}, n, clock)
ok(bad and "치른 대가" in bad[0],
   f"화자가 움직였는데 대가가 없으면 잡는다 ({bad})  ← 공짜로 얻으면 긴장이 죽는다")

bad = D._check_pressure({"driver": "공명", "cost": "", "deadline_hours": 9}, n, clock)
ok(not bad, "화자가 아닌 사람이 움직인 장면은 대가 없이도 통과  ← 과잉 기각 방지")

bad = D._check_pressure({"driver": "사건", "cost": "", "deadline_hours": 9}, n, clock)
ok(not bad, "'사건' 도 유효한 driver 다")

print("[보정] 시계는 산수다 -- 되돌려보내지 않고 고쳐서 쓴다")
print("      ← 300초짜리 디렉터 호출을 산수 하나 때문에 버리면 척추가 사라진다")
b = {"driver": "공명", "cost": "", "deadline_hours": "9시간"}
bad = D._check_pressure(b, n, clock)
ok(not bad, f"문자열이어도 기각하지 않는다 ({bad})")
ok(b["deadline_hours"] == round(clock - 1, 1),
   f"장면 시작보다 작은 값으로 보정한다 ({b['deadline_hours']})")

b = {"driver": "공명", "cost": "", "deadline_hours": 20}
bad = D._check_pressure(b, n, clock)
ok(not bad, "되감긴 값도 기각하지 않는다")
ok(b["deadline_hours"] < clock, f"줄어든 값으로 고친다 ({b['deadline_hours']} < {clock})")

b = {"driver": "공명", "cost": "", "deadline_hours": 9}
D._check_pressure(b, n, clock)
ok(b["deadline_hours"] == 9, "멀쩡한 값은 건드리지 않는다")

bad = D._check_pressure({"driver": POV, "cost": "정우에게 빚을 졌다",
                         "deadline_hours": 9}, n, clock)
ok(not bad, "다 갖춘 비트는 통과한다")

print("[V023] 시계가 되감기면 보고하는가")
n3 = build()
a = Scene(id="s1", episode=1, deadline="마감", deadline_hours=9)
b = Scene(id="s2", episode=1, deadline="마감", deadline_hours=12)
n3.scenes = [a, b]
v = [x for x in gate.check(b, n3) if x.rule == "V023"]
ok(v and v[0].severity == "soft", f"되감김을 잡는다 ({v})")
ok(v and "되감겼다" in v[0].detail, "무엇이 문제인지 말해준다")
b.deadline_hours = 6
ok(not [x for x in gate.check(b, n3) if x.rule == "V023"], "줄어들면 통과")
b.deadline, b.deadline_hours = "다른 마감", 100
ok(not [x for x in gate.check(b, n3) if x.rule == "V023"],
   "마감이 바뀌면 새 시계다 -- 늘어도 된다  ← 과잉 기각 방지")

print()
if fails:
    print(f"압박: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("압박: 시계 · 조립 강제 · 되감김 -- 통과")
