"""세계관 설정집 -- 게임의 설정집처럼 **한 벌로 묶여 있는가.**

축을 전부 따로 뽑아 조합했더니 이런 씨앗이 나왔다(실측): 세계는 '귀신이 도는 반도' 인데
국면은 '탑이 조용했던 다음 날' 이고, 인물은 '영웅 지망생' 이며, 장치는 '12층 출입증' 이다.
종족·의식주·법·시민의식은 서로를 결정하므로 **세계가 나머지를 정해야** 한다.

여기서 고정하는 것:
  1. 세계마다 여덟 항목(법칙·등급·종족·세력·의식주·시민의식·위협·잔혹)이 다 차 있는가
  2. 국면·사건·인물·장치가 **그 세계의 것에서만** 뽑히는가
  3. 설정집이 프롬프트에 실리고, "지어내지 마라" 가 함께 실리는가

실행: python3 tests/test_world_bible.py
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


print("[설정집] 세계마다 여덟 항목이 다 차 있는가")
NEED = ("order", "ranks", "races", "nations", "living", "ethic", "threat",
        "cruelty", "bond")
for w in S.WORLDS:
    miss = [k for k in NEED if not w.get(k)]
    ok(not miss, f"{w['name']}: {miss or '전부 있다'}")
ok(len(S.WORLDS) >= 3, f"세계가 {len(S.WORLDS)}개")

print("[설정집] 세계마다 자기 축을 갖는가  ← 이것이 없으면 다시 섞인다")
for w in S.WORLDS:
    ok(len(w["times"]) >= 3 and len(w["events"]) >= 3
       and len(w["people"]) >= 4 and len(w["motifs"]) >= 4,
       f"{w['name']}: 국면 {len(w['times'])} · 사건 {len(w['events'])} · "
       f"인물 {len(w['people'])} · 장치 {len(w['motifs'])}")

print("[검사] 빠진 항목이 있으면 거부하는가")
bad = dict(S.draw(random.Random(5)))
bad["world"] = dict(bad["world"], ethic="")
ok(any("세계관" in e for e in S.validate(bad)), "시민의식이 비면 잡는다")

print()
print("[일관성] 뽑힌 씨앗이 한 세계 안에서만 노는가")
print("      ← 실측: 귀신 반도에 '탑이 조용했던 날' 과 '12층 출입증' 이 섞여 나왔다")
for i in range(40):
    sd = S.draw(random.Random(i))
    w = sd["world"]
    ok_time = sd["time"]["what"] in [t for t, _ in w["times"]]
    ok_event = sd["event"] in w["events"]
    ok_motif = sd["motif"] in w["motifs"]
    ok_people = all(p["who"] in [q for q, _ in w["people"]] for p in sd["people"])
    if not (ok_time and ok_event and ok_motif and ok_people):
        ok(False, f"{w['name']} 씨앗이 다른 세계의 축을 물고 있다 "
                  f"(국면 {ok_time} 사건 {ok_event} 장치 {ok_motif} 인물 {ok_people})")
        break
else:
    ok(True, "마흔 번 뽑아도 전부 자기 세계 안이다")

seen = {S.draw(random.Random(i))["world"]["name"] for i in range(40)}
ok(len(seen) >= 3, f"세계가 골고루 뽑힌다 ({len(seen)}종)")

print()
print("[적재] 설정집이 프롬프트에 실리는가")
SEED = S.draw(random.Random(3))
nv = W.build(SEED)
ok(nv.world.get("name") == SEED["world"]["name"], "Novel.world 에 실린다")
brief = D._world_brief(nv)
w = SEED["world"]
for key, label in (("order", "법칙"), ("ranks", "등급"), ("races", "종족"),
                   ("nations", "세력"), ("living", "의식주"), ("ethic", "시민의식"),
                   ("threat", "위협"), ("cruelty", "잔혹"), ("bond", "관계")):
    ok(w[key][:18] in brief, f"{label}이 실린다")

print("[적재] 지어내지 말라는 규율이 함께 실리는가")
ok("새 종족·새 제도·새 등급을 지어내지 마라" in brief,
   "설정 밖으로 나가지 말라고 못박는다  ← 씬마다 다른 세계가 되면 관문이 못 잡는다")
ok("설정을 설명하지 마라" in brief, "설정 설명을 금지한다  ← 인물들에게는 다 아는 일이다")
ok("당연하게" in brief, "시민의식이 핵심이라고 짚어준다")
ok("잔혹은 설명하지 않는다" in brief, "잔혹을 설명하지 말라고 한다")

print("[관계] 로맨스가 제도로 들어가 있는가  ← 센티넬-가이드 자체가 페어 관계다")
ok("이 세계에서 연애는 제도다" in brief, "관계 규약이 실린다")
ok("끌림을 대사로 고백하지 마라" in brief, "고백이 아니라 감수로 보여준다")
ok("집착의 동기는 상처다" in brief and "선은 넘지 않는다" in brief, "집착의 선을 긋는다")
ok("스스로 밀어내고" in brief, "상대역이 구조받기만 하지 않는다")
ok("가장 아픈 형태의 폭력" in brief, "짝을 떼는 것이 이 세계의 폭력이라고 짚는다")
ok("남주" not in brief and "여주" not in brief, "성별 고정 표현은 쓰지 않는다")

print("[적재] 디렉터·비트 프롬프트에도 실리는가")
spec = W.outcomes(SEED)[0]
sc = Scene(id="s1", episode=1, kind="cider", location="x", punctum="y",
           participants=[nv.pov_character])
ok(w["ethic"][:15] in D.beat_prompt(nv, spec, ["조건"], 1), "비트 프롬프트")
ok(w["ethic"][:15] in D.subplot_prompt(nv, 1, spec["summary"]), "서브플롯 프롬프트")

print()
if fails:
    print(f"세계관: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("세계관: 여덟 항목 · 세계별 축 · 일관성 · 프롬프트 적재 · 지어내기 금지 -- 통과")
