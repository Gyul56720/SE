"""씨앗 세계의 규격 -- 10화가 실제로 이어지는가.

블록을 셋으로 갈랐다(1~3 / 4~6 / 7~10). 갈랐으면 **사슬이 이어지는지**를 기계가 봐야
한다. 뒤 블록의 requires 가 앞 블록의 establishes 로 갚아지지 않으면 V018 이 개연성
구멍으로 잡는데, 그때는 이미 디렉터 호출을 수십 번 쓴 뒤다. 여기서 먼저 잡는다.

실행: python3 tests/test_seeded_world.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import seed as S, world_seeded as W                        # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


SEED = S.draw(random.Random(7))
O = W.outcomes(SEED)

print("[규격] 10화가 빈틈없이 덮이는가")
eps = [e for o in O for e in range(o["eps"][0], o["eps"][1] + 1)]
ok(eps == list(range(1, 11)), f"1~10화가 겹침도 빈틈도 없이 덮인다 ({O[0]['eps']} {O[1]['eps']} {O[2]['eps']})")
ok([o["seq"] for o in O] == [1, 2, 3], "블록 번호가 순서대로다")

print("[사슬] 뒤 블록의 requires 를 앞 블록이 갚는가  ← 안 갚으면 V018 이 구멍으로 잡는다")
have: set = set()
for o in O:
    missing = [c for c in o["requires"] if c not in have]
    ok(not missing, f"블록 {o['seq']} 의 미충족 조건 {missing or '없음'}")
    have.update(o["establishes"])
ok("판 전체를 가져갔다" in have, "마지막 블록이 최종 상태를 세운다")

print("[사이다] 결말이 성취인가  ← 대가를 치르는 결말은 이 장르에서 고구마다")
for o in O:
    bad = [w for w in ("대가", "잃는다", "치른다", "포기") if w in o["summary"]]
    ok(not bad, f"블록 {o['seq']} 결말에 손해 어휘가 없다 ({bad or '깨끗'})")
ok(all(o["stake"] for o in O), "걸린 것은 있다  ← 잃을 것이 없으면 이겨도 시시하다")

print("[규모] 판이 커지는가")
ok([o["scale"] for o in O] == sorted(o["scale"] for o in O),
   f"사건 규모가 뒷걸음질하지 않는다 ({[o['scale'] for o in O]})")
ok([o["deadline_hours"] for o in O] == sorted((o["deadline_hours"] for o in O), reverse=True),
   f"블록마다 시계가 조여든다 ({[o['deadline_hours'] for o in O]})")

print("[척추] steps 가 블록 간에 겹치지 않는가")
print("      ← 겹치면 뒤 블록의 씨앗이 앞 블록의 establishes 로 갚아져 사라진다")
steps = [st for o in O for st in o["steps"]]
ok(len(steps) == len(set(steps)), f"{len(steps)}개 전부 고유")
ok(all(o["steps"] for o in O), "블록마다 척추 씨앗이 있다")

print("[인물] 이름이 조사와 함께 제대로 붙는가  ← '설윤가' 사고가 있었던 자리다")
names = S.cast_names(SEED)
text = " ".join([o["summary"] for o in O] + steps + [o["stake"] for o in O])
ok(all(nm in text for nm in names), f"세 인물이 모두 등장한다 ({names})")
ok("이가" not in text and "을를" not in text, "조사가 겹쳐 붙지 않는다")

print("[재현] 같은 씨앗이면 같은 세계")
ok([o["summary"] for o in W.outcomes(SEED)] == [o["summary"] for o in O],
   "두 번 불러도 같다")

print()
if fails:
    print(f"씨앗 세계: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("씨앗 세계: 10화 덮기 · 인과 사슬 · 성취 결말 · 규모/시계 · 척추 고유성 -- 통과")
