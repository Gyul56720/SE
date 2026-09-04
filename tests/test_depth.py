"""심층 -- 겉은 가볍고 속은 무겁게. **그리고 절대 말하지 않게.**

철학을 소설에 넣는 가장 흔한 실패는 인물이 그것을 설명하는 것이다. '정언명령' 이나
'변증법' 이 텍스트에 나오는 순간 소설이 강의가 된다. 그래서 이 축은 세 칸으로 갈라져 있다:

    claim   한 줄 명제  -- **사람만 읽는다. 프롬프트에 안 실린다**
    test    플롯이 그것을 시험하는 방식(주인공이 하게 될 선택) -- 이것만 실린다
    cover   겉으로 보여야 하는 가벼운 재미 -- 이것도 실린다

여기서 고정하는 것: 사상가 이름과 개념어가 **프롬프트 어디에도 새지 않는가.**

실행: python3 tests/test_depth.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import seed as S, world_seeded as W, drive as D            # noqa: E402
from novel.state import Scene                                         # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


# 프롬프트에 절대 나오면 안 되는 말. 이름과 개념어 둘 다.
FORBIDDEN = ("칸트", "헤겔", "니체", "키르케고르", "레비나스", "도스토옙스키",
             "아우구스티누스", "욥기", "대속",
             "정언명령", "변증법", "실존주의", "신정론", "형이상학", "존재론")

print("[축] 심층이 세 칸을 다 갖는가")
ok(len(S.DEPTH) >= 8, f"{len(S.DEPTH)}개")
missing = [d.get("who") for d in S.DEPTH
           if not (d.get("claim") and d.get("test") and d.get("cover"))]
ok(not missing, f"claim/test/cover 가 다 있다 ({missing or '전부'})")
ok(all(len(d["test"]) > 20 for d in S.DEPTH),
   "시험이 한 줄 이상이다  ← '선택하게 한다' 만 적으면 아무것도 지시하지 못한다")

print("[검사] 시험이나 겉모습이 없으면 씨앗을 거부하는가")
bad = dict(S.draw(random.Random(3)))
bad["depth"] = {"who": "칸트", "claim": "x", "test": "", "cover": ""}
ok(any("심층" in e for e in S.validate(bad)), "거부한다")

print("[세계] 원고가 심층을 들고 다니는가  ← 재개해도 같은 물음을 시험해야 한다")
SEED = S.draw(random.Random(11))
nv = W.build(SEED)
ok(nv.depth.get("test") == SEED["depth"]["test"], "Novel.depth 에 실린다")

print()
print("[누출] 사상가 이름과 개념어가 프롬프트에 새지 않는가")
print("      ← 프롬프트에 '칸트' 가 있으면 모델은 텍스트에 '칸트' 를 쓴다")


def scene(kind="cider", ep=1):
    return Scene(id="s1", episode=ep, kind=kind, location="탑 1층 대기소",
                 punctum="식은 커피", participants=[nv.pov_character])


spec = W.outcomes(SEED)[0]
prompts = {
    "화자": D.narrator_prompt(nv, scene()),
    "배우": D.actor_prompt(nv, scene(), nv.pov_character),
    "디렉터": D.director_prompt(nv, scene()),
    "결말": D.outcome_prompt(nv, 1, 3),
    "비트": D.beat_prompt(nv, spec, ["조건"], 1),
    "서브플롯": D.subplot_prompt(nv, 1, spec["summary"]),
}
for name, p in prompts.items():
    leaked = [w for w in FORBIDDEN if w in p]
    ok(not leaked, f"{name} 프롬프트 깨끗 ({leaked or '누출 없음'})")

print("[적재] 시험과 겉모습은 실리는가  ← 안 실리면 심층이 없는 것과 같다")
ok(SEED["depth"]["test"][:20] in prompts["화자"], "화자에게 시험이 실린다")
ok(SEED["depth"]["cover"][:10] in prompts["화자"], "겉모습도 실린다")
ok("대사로 옮기지 마라" in prompts["화자"], "말하지 말라고 못박는다")
ok(SEED["depth"]["test"][:20] in prompts["디렉터"], "디렉터에게도 실린다")
ok("선택" in prompts["디렉터"], "디렉터는 선택으로 만들라고 지시받는다")

print("[문체] 화자 규율이 강의를 막는가")
ok("소설이 강의가 된다" in prompts["화자"], "이유까지 적혀 있다")
ok("교훈으로 닫지 마라" in prompts["화자"] and "답을 주지 마라" in prompts["화자"],
   "답을 주지 않는다  ← 물음이 닫히면 두 번 읽을 이유가 없다")

print("[표층] 씨앗이 탑·영웅·희생 쪽인가")
joined = " ".join(t for w in S.WORLDS for t, _ in w["times"]) \
         + " ".join(e for w in S.WORLDS for e in w["events"]) \
         + " ".join(w["order"] + w["cruelty"] for w in S.WORLDS)
ok("탑" in joined, "탑이 있다")
ok(any(w in joined for w in ("영웅", "구조", "희생")), "영웅·구조·희생이 있다")

print()
if fails:
    print(f"심층: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("심층: 세 칸 · 검사 · 원고 적재 · 이름 누출 없음 · 강의 금지 -- 통과")
