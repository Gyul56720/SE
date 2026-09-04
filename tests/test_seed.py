"""자유 씨앗 -- 무작위가 무작위이기만 하면 안 된다.

고정 세계로 뽑았더니 프롬프트가 매번 같아 같은 답이 나왔다(서브플롯 세 회차가 전부
"핫팩을 많이 사는 남자"). 축마다 따로 뽑아 조합하면 그 문제가 구조적으로 사라진다.

다만 무작위는 재미의 필요조건이지 충분조건이 아니다. 여기서 고정하는 것은 **기계가
거를 수 있는 최소한**이다. "재미있는가" 는 판정하지 않는다 -- 판정하려 들면 평균만 남는다.

실행: python3 tests/test_seed.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import seed as S                                           # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[공간] 조합이 반복을 걱정할 필요 없을 만큼 넓은가")
space = 0
for w in S.WORLDS:
    c = len(w["people"])
    space += (len(w["times"]) * len(w["events"]) * len(w["motifs"])
              * (c * (c - 1) * (c - 2) // 6)
              * len(S.IMPOSSIBLE) * len(S.VOICE) * len(S.THEME) * len(S.DEPTH))
ok(space > 1_000_000, f"조합이 {space:,}가지  ← 같은 씨앗이 두 번 나올 일이 없다")
ok(all(len(w["people"]) >= 4 for w in S.WORLDS),
   f"세계마다 인물 축이 {[len(w['people']) for w in S.WORLDS]}개 "
   f"(셋을 뽑으므로 조합이 더 는다)")

print("[규율] 반칙에 효과와 조건이 **전부** 붙어 있는가")
print("      ← 무한한 마법은 긴장을 죽인다. 마술적 리얼리즘의 규율이 이것이다")
bad = [r for r, cost, lim in S.IMPOSSIBLE if not cost or not lim]
ok(not bad, f"효과·조건 없는 반칙 없음 ({bad})")

print("[검사] 최소한만 거르는가")
rng = random.Random(1)
s = S.draw(rng)
ok(not S.validate(s), f"정상 씨앗은 통과 ({S.validate(s)})")

broken = dict(s, impossible={"rule": "무엇이든 된다", "cost": "", "limit": ""})
ok(S.validate(broken), "효과 없는 반칙은 걸린다")

same = dict(s, people=[s["people"][0]] * 3)
ok(any("서로 다른 축" in v for v in S.validate(same)), "인물 셋이 같으면 걸린다")

ok(any("이미 쓴" in v for v in S.validate(s, used={s["id"]})),
   "이미 쓴 씨앗은 다시 안 뽑는다")

print("[사이다] 반칙이 대가가 아니라 조건을 갖는가")
print("      ← 주인공이 손해를 감수하는 순간 그것이 고구마다. 제약은 남기되 다치게 하지 않는다.")
harm = [r for r, cost, limit in S.IMPOSSIBLE
        if any(w in cost for w in ("잃는다", "못 쓴다", "영영", "두 번 살아야"))]
ok(not harm, f"효과 칸에 손해가 없다 ({harm or '깨끗'})")
ok(all(limit for _, _, limit in S.IMPOSSIBLE), "전부 발동 조건을 갖는다  ← 무제한이면 긴장이 없다")
fake = dict(S.draw(random.Random(1)))
fake["impossible"] = {"rule": "x", "cost": "y", "limit": ""}
ok(any("조건" in e for e in S.validate(fake)), "조건이 없으면 검사가 잡는다")

print("[재현] 같은 난수 씨앗이면 같은 조합인가  ← 마음에 든 것을 다시 찾을 수 있어야 한다")
a = S.draw(random.Random(42))
b = S.draw(random.Random(42))
ok(a["id"] == b["id"], f"id 가 같다 ({a['id']})")
c = S.draw(random.Random(43))
ok(c["id"] != a["id"], "다른 씨앗이면 다른 조합")

print("[다양성] 스무 번 뽑으면 실제로 다 다른가")
rng = random.Random(0)
ids = {S.draw(rng)["id"] for _ in range(20)}
ok(len(ids) == 20, f"20개 전부 고유 ({len(ids)})")

print("[표시] 사람이 읽고 고를 수 있는가  ← LLM 호출 없이 판단하는 것이 요점이다")
txt = S.render(S.draw(random.Random(5)), long=True)
for key in ("시간", "규칙", "효과", "조건", "사건", "인물1", "장치", "목소리", "주제"):
    ok(key in txt, f"'{key}' 가 보인다")

print()
if fails:
    print(f"자유 씨앗: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("자유 씨앗: 공간 · 규율 · 검사 · 재현 · 다양성 · 표시 -- 통과")
