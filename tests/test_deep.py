"""**의미층을 재서 시킨다** -- 인과 · 갈등 · 복선 · 거리 · 속도.

문면만 맞추면 문장은 겹쳐도 이야기는 안 겹친다. 연구용으로 최대한 복제하는 것이
목적이면 의미층도 재야 하고, 재려면 읽는 것을 시켜야 한다. 여기서 고정하는 계약:

  · **한 번에 다 묻는다** -- 칸마다 따로 물으면 스물두 배가 든다. 토막당 한 번,
    spine 이 칸 하나 받던 그 호출로 스물두 칸을 받는다
  · **정해진 낱말이 아니면 버린다** -- 새 낱말이 섞이면 분포가 조용히 망가진다
  · **분포가 아니라 그 대목의 값을 시킨다** -- 복제가 목적이면 "대개 장면이다" 가
    아니라 "이번 대목은 여파다" 라야 한다
  · **같은 자로 우리 원고도 잰다** -- 재지 않는 요구는 지켜졌는지 알 수 없다

실행: python3 tests/test_deep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import deep                                               # noqa: E402

fails = []


def ok(cond, label):
    print(("  OK  " if cond else "  실패 ") + label)
    if not cond:
        fails.append(label)


print("[묻기 -- 한 번에 다]")
q = deep.ask("어떤 대목이다.")
ok(all(k in q for k in deep.PICK), f"고르는 칸 {len(deep.PICK)}개를 다 묻는다")
ok(all(k in q for k in deep.NUM), f"수로 받는 칸 {len(deep.NUM)}개를 다 묻는다")
ok("원문 문장을 옮기지 마라" in q, "원문을 옮기지 말라고 못박는다")
ok(len(q) < 3000, f"물음이 짧다 ({len(q):,}자)")

print("\n[다듬기 -- 정해진 낱말이 아니면 버린다]")
raw = {"장면꼴": "장면", "속도": "빠름", "갈등세기": "3", "인물수": 99,
       "무엇": "문이 잠겼다", "누구": "그", "심은것": "열쇠"}
c = deep.clean(raw)
ok(c["장면꼴"] == "장면", "정해진 낱말은 그대로 둔다")
ok(c["속도"] == "", "없는 낱말('빠름')은 버린다  ← 새 낱말이 분포를 망친다")
ok(c["갈등세기"] == 3, "문자로 온 수도 수로 받는다")
ok(c["인물수"] == 12, "범위를 넘으면 범위 안으로 접는다")
ok(c["심은것"] == "열쇠", "자유 서술 세 칸은 그대로")

print("\n[분포]")
recs = []
for i in range(12):
    r = deep.clean({"장면꼴": "장면" if i % 3 else "여파", "갈등세기": i % 5,
                    "거둔거리": 4 if i == 5 else 0, "심은것": "열쇠" if i == 2 else "",
                    "속도": "장면", "닫는법": "질문"})
    recs.append(r)
d = deep.learn(recs)
ok(abs(d["share"]["장면꼴"]["장면"] - 8 / 12) < 0.01,
   f"고르는 칸은 몫으로 낸다 (장면 {d['share']['장면꼴']['장면']:.0%})")
ok("갈등세기" in d["band"], "수는 폭으로 낸다")
ok(d["복선"]["사거리 가운데"] == 4,
   "복선 사거리는 거둔 것만 모아 본다  ← 0이 섞이면 뭉개진다")
ok(abs(d["심는 몫"] - 1 / 12) < 0.01, "심는 몫을 따로 센다")

print("\n[시키기 -- 분포가 아니라 그 대목의 값]")
one = deep.clean({"장면꼴": "여파", "속도": "늘임", "거리": "생각속",
                  "갈등축": "자신과", "갈등세기": 2, "갈등끝": "유예",
                  "닫는법": "여운", "무엇": "돌아가지 않기로 한다", "누구": "그",
                  "심은것": "편지", "거둔거리": 7, "인물수": 2, "새인물": 0})
b = deep.brief(0, path=None) if False else None
import json, tempfile                                                # noqa: E402
with tempfile.TemporaryDirectory() as t:
    p = Path(t) / "deep.json"
    p.write_text(json.dumps({"recs": [one]}, ensure_ascii=False), encoding="utf-8")
    b = deep.brief(0, path=p)
    b9 = deep.brief(9, path=p)
ok("여파" in b and "늘임" in b and "생각속" in b, "그 대목의 값을 그대로 싣는다")
ok("돌아가지 않기로 한다" in b, "달라지는 것 하나를 싣는다")
ok("편지" in b and "놓기만 하고" in b, "심을 것을 시킨다")
ok("7대목쯤 전" in b, "거둘 것을 시킨다")
ok("네가 정한다" in b, "무엇으로 그렇게 되는지는 안 시킨다  ← 본보기를 박지 않는다")
ok(b9 == b, "원고가 표본보다 길어지면 마지막 것을 쓴다")
ok(len(b) < 900, f"한 덩이가 짧다 ({len(b)}자)")

print("\n[견주기 -- 같은 자로 우리 원고도 잰다]")
mine = dict(one)
ok(deep.gap(mine, one)["겹친 몫"] == 1.0, "똑같으면 1.0")
mine2 = dict(one, 장면꼴="장면", 갈등세기=4)
g = deep.gap(mine2, one)
ok(g["겹친 몫"] < 1.0 and any("장면꼴" in m for m in g["어긋난 것"]),
   f"어긋나면 무엇이 어긋났는지 댄다 ({g['겹친 몫']})")
ok(deep.gap({}, one)["잰 칸"] == 0, "못 잰 칸은 안 센다  ← 빈 것을 통과로 세지 않는다")

print()
if fails:
    print(f"의미층: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("의미층: 묻기 · 다듬기 · 분포 · 시키기 · 견주기 -- 통과")
