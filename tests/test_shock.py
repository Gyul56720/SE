"""충격 -- **점층을 끊고 제3자가 들이닥친다.**

확산만 돌리면 이야기는 한 방향으로 계속 짙어진다. 짙어지는 건 좋은데 짙어지기만 하면
프롬프트가 원장으로 차고(기술적 한계), 인물들이 같은 방에서 같은 이야기를 점점 자세히
하게 된다(서사적 정체). 사용자 평: "충격적인 사건이 많지 않아. 프롬포트가 터질 것
같거나, 일정 한도를 넘어가면, 점층을 하지 말고 충격적인 사건을 넣어."

**사건은 한 덩어리만 대신한다. 그 다음부터는 다시 점층이다.**

실행: python3 tests/test_shock.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import flow, shock as SH                                   # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[뽑기] **목록 하나를 돌려 쓰면 세 번째부터 예측된다** -- 축을 갈라 조합한다")
combos = len(SH.WHO) * len(SH.HOW) * len(SH.MARK) * len(SH.SCALE) * len(SH.TONE)
ok(combos > 1_000_000, f"조합이 백만 가지를 넘는다 ({combos:,})")
ok(SH.draw("a", 0) == SH.draw("a", 0), "같은 씨앗·같은 번호는 같은 사건  ← 이어 쓰기 재현")
ok(SH.draw("a", 0) != SH.draw("b", 0), "씨앗이 다르면 다른 사건")

print()
print("[뽑기] **연달아 같은 톤이면 신선함이 죽는다**")
print("      ← 처음엔 축 다섯을 한 난수원에서 연달아 뽑았더니 0~3번 온도가 넷 다 같았다.")
for axis in ("who", "how", "mark", "scale", "tone"):
    dup = sum(SH.draw("s", i)[axis] == SH.draw("s", i + 1)[axis] for i in range(200))
    ok(dup == 0, f"{axis}: 연속으로 같은 값이 나오지 않는다 ({dup}건)")
spread = Counter(SH.draw("s", i)["tone"] for i in range(400))
ok(len(spread) == len(SH.TONE), f"온도가 한쪽으로 쏠리지 않는다 ({len(spread)}/{len(SH.TONE)}종)")

print()
print("[때] **분량이 찼거나, 프롬프트가 부풀었거나**")
ok(SH.due(SH.EVERY, 0), "약 2,000자를 쓰면 터진다")
ok(not SH.due(SH.EVERY - 1, 0), "그 전에는 안 터진다")
ok(SH.due(0, SH.PRESSURE), "원장이 부풀면 자릿수를 안 채웠어도 터진다  ← 터지기 전에 환기")

print()
print("[개입] **사건은 확산을 한 덩어리만 대신한다**")
src = Path(flow.__file__).read_text(encoding="utf-8")
ok("다음 덩어리부터는 **다시 점층이다.**" in src, "사건 뒤에는 다시 점층이라고 못박는다")
ok("사건 덩어리는 확산으로 재지 않는다" in src,
   "사건 덩어리는 확산 자로 재지 않는다  ← 넓히라고 시키지 않았으니 그것으로 벌하지 않는다")
ok("리듬만 본다" in src, "리듬은 사건이든 아니든 지킨다  ← 대사와 길이는 늘 지켜야 한다")

bk = flow.blank("첫 문장.")
bk["chunks"] = ["x" * 2500]
bk["since"] = 2500
bk["_shock"] = SH.draw("첫 문장.", 0)
p = flow.write_prompt(bk)
ok("[사건]" in p, "사건 차례에는 사건 지시가 실린다")
ok("[확산]" not in p, "그 덩어리에는 확산 지시가 빠진다  ← 둘을 한꺼번에 시키지 않는다")
ok("문제를 풀어주지 않는다" in p,
   "사건이 문제를 풀지 않는다  ← 딱 맞춰 나타나 구해주는 것은 편의주의다")
ok("환기해라" in p, "사건 뒤에 공간이 바뀌어 있게 한다")

bk["_shock"] = None
ok("[확산]" in flow.write_prompt(bk), "사건이 아닌 덩어리에는 확산이 돌아온다")

print()
print("[셈] **사건이 터지면 분량을 0부터 다시 센다**")
b2 = flow.blank("첫 문장.")
b2["chunks"] = ["앞 덩어리"]
b2["since"] = 2500
b2["_shock"] = SH.draw("x", 0)
flow._after(b2, "사건 본문")
ok(b2["shocks"] == 1 and b2["since"] == 0, "사건 뒤 계수가 오르고 분량이 초기화된다")
flow._after(b2, "그 다음 덩어리")
ok(b2["shocks"] == 1 and b2["since"] == len("그 다음 덩어리"),
   "그 다음 덩어리는 다시 쌓기 시작한다")
ok(flow.blank()["shocks"] == 0 and "since" in flow.blank(),
   "새 원고는 사건 0에서 시작한다")

print()
if fails:
    print(f"충격: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("충격: 조합 · 연속 회피 · 때 · 확산 교대 · 셈 -- 통과")
