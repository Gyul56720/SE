"""문체 규율 -- 12개 지시가 실제로 프롬프트에 실리고 배분이 목표에 수렴하는가.

관문에서 취향 검사를 뺐으므로(2026-09-04) 문체를 지키는 것은 이제 기각이 아니라 규율이다.
규율은 **실려야** 존재한다 -- 이 저장소가 반복 실증한 것이 그것이다(읽히지 않는 산문 규칙은
아무것도 막지 못한다). 그래서 여기서 고정하는 것은 두 가지다:

  1. 각 층의 프롬프트가 자기 층의 지시를 실제로 담고 있는가 (그리고 **모순되는 옛 지시가
     남아 있지 않은가** -- 1번 지시는 만연체 배제인데 옛 화자 프롬프트는 만연체를 요구했다)
  2. 씬 종류 배분이 목표 비율(50~60 / 20~25 / 15~20 / <5)에 수렴하는가

실행: python3 tests/test_style.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import style, drive as D                                   # noqa: E402
from novel.state import Scene                                         # noqa: E402
from novel.world_romance import build                                 # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


N = build()
POV = N.pov_character


def scene(kind="routine", ep=1):
    return Scene(id="s1", episode=ep, kind=kind, location="낡은 엘리베이터",
                 punctum="식은 커피", participants=[POV, "공명"])


print("[배분] 씬 종류가 목표 비율에 수렴하는가")
counts: dict = {}
for i in range(300):
    k = style.pick_kind(style.SUBPLOT_POOL if i % 3 else style.SPINE_POOL, counts)
    counts[k] = counts.get(k, 0) + 1
total = sum(counts.values())
share = {k: v / total for k, v in counts.items()}
ok(0.50 <= share.get("routine", 0) <= 0.60,
   f"routine {share.get('routine', 0):.0%} (목표 50~60%)")
ok(0.20 <= share.get("encounter", 0) <= 0.25,
   f"encounter {share.get('encounter', 0):.0%} (목표 20~25%)")
ok(0.15 <= share.get("delivery", 0) <= 0.20,
   f"delivery {share.get('delivery', 0):.0%} (목표 15~20%)")

ok(style.pick_kind(style.SPINE_POOL, {"routine": 9}) == "delivery",
   "루틴이 목표를 넘으면 척추는 배달로 간다  ← 서사를 미는 것은 밖에서 온 것")
ok(style.pick_kind(style.SPINE_POOL, {"delivery": 9}) == "routine",
   "배달이 넘치면 루틴으로 돌아온다  ← 매회 편지가 오면 그것도 원패턴이다")
ok(style.pick_kind(style.SUBPLOT_POOL, {"routine": 99}) == "encounter",
   "루틴이 넘치면 기묘한 조우로 넘어간다")

print("[배분] 재개해도 이어서 센다")
prev = [scene(k) for k in ("routine", "routine", "encounter")]
ok(style.tally(prev) == {"routine": 2, "encounter": 1},
   f"이미 쓴 씬의 종류를 센다 ({style.tally(prev)})")
ok(style.tally([Scene(id="x")]) == {},
   "종류가 없는 씬은 세지 않는다  ← 옛 원고를 이어받아도 죽지 않는다")

print("[결정성] 같은 입력에 같은 종류")
got = {style.pick_kind(style.SUBPLOT_POOL, {"routine": 3, "encounter": 1})
       for _ in range(20)}
ok(len(got) == 1,
   f"무작위가 아니라 결손 최대로 고른다 ({got})  ← 재현되지 않으면 배분을 잴 수 없다")

print()
print("[화자] 1·3·4·5·6 이 실려 있는가")
p = D.narrator_prompt(N, scene("routine"))
ok("단문" in p and "만연체를 쓰지 마라" in p, "건조한 번역투 단문을 요구한다")
ok("가차 없이 잘라낸다" in p, "마이너스 퇴고")
ok("느낌표" in p, "느낌표 배제")
ok("방관자" in p and "냉소적인 농담" in p, "하드보일드 거리두기와 허무주의 유머")
ok("재즈" in p and "다림질" in p, "팝 컬처 고유명사와 일상 행위")
ok("불가능은 하나뿐" in p and "설명하지 마라" in p,
   "마술적 리얼리즘 -- 불가능은 하나, 설명은 없다")
ok("쉼표처럼" in p, "행동 쉼표")
ok("샌드위치에 관해 이야기했다" in p, "대화의 선택적 압축 -- 예시까지 준다")

print("[화자] 모순되는 옛 지시가 남아 있지 않은가  ← 둘 다 실으면 둘 다 반쯤 지켜진다")
ok("만연체(60자 이상)를 회차마다" not in p, "만연체 요구가 지워졌다")
ok("비유는 아껴 쓰되 있어야 한다" not in p, "비유 요구가 지워졌다")
ok('"무언가 무너져 내리는 기척" 도 쓰지 마라' in p,
   "옛 프롬프트가 모범으로 들던 표현을 이제 금지 예시로 든다")

print("[화자] 종류별 규율이 그 씬에만 실린다")
ok("일상 루틴" in D.narrator_prompt(N, scene("routine")), "루틴 씬에 루틴 규율")
ok("불가능**" in D.narrator_prompt(N, scene("encounter")), "법이 작동하는 씬에 그 규율")
ok("능동적 탐색을 금지" in D.narrator_prompt(N, scene("delivery")), "배달 씬에 배달 규율")
ok("카타르시스는 증발" in D.narrator_prompt(N, scene("resolution")), "해결 씬에 해결 규율")
ok("일상 루틴 —" not in D.narrator_prompt(N, scene("encounter")),
   "다른 종류의 규율은 안 실린다  ← 넷을 다 실으면 어느 것도 안 지켜진다")
ok(style.brief("없는종류") == "", "모르는 종류에는 규율을 지어내지 않는다")

print("[액자] 11 은 주기로 준다  ← 매번 넣으면 액자가 본편이 된다")
ok("일기장" in D.narrator_prompt(N, scene("routine", ep=style.FRAME_EVERY)),
   f"{style.FRAME_EVERY}화마다 액자가 실린다")
ok("일기장" not in D.narrator_prompt(N, scene("routine", ep=style.FRAME_EVERY + 1)),
   "그 밖의 회차에는 안 실린다")

print()
print("[배우] 2 · 3 이 실려 있는가")
a = D.actor_prompt(N, scene("routine"), "공명")
ok("콜 앤 리스폰스" in a and "메아리" in a, "재즈 스윙 핑퐁 대화")
ok("단답형" in a, "단답형으로 끊는다")
ok("느낌표" in a, "배우도 느낌표를 안 쓴다")

print("[디렉터] 4 · 12 가 실려 있는가")
d = D.director_prompt(N, scene("encounter"))
ok("고유명사" in d and "다림질" in d, "두꺼운 현실을 먼저 깐다")
ok("새 초현실을 지어내지 마라" in d and "말하는 동물도" in d,
   "초현실은 금지다  ← 마술적 리얼리즘은 불가능이 하나뿐인 세계다")
ok("집요하게 묘사" in d and "현실의 공간으로 남는다" in d,
   "평범한 공간을 집요하게. 문이 열리지는 않는다")
ok("불가능은" in d and "규칙 하나뿐" in d, "디렉터도 이 씬의 종류를 안다")
ok('"슬프다/외롭다" 라고 서술되면 기각된다' not in d,
   "기각한다는 거짓말이 지워졌다  ← 관문은 더 이상 그것을 보지 않는다")

print()
print("[기승전결] 단편은 8시퀀스가 아니라 기승전결을 받는가")
from novel import arc                                                 # noqa: E402
short = build(); short.total_episodes = 3
long_ = build(); long_.total_episodes = 200
ok(arc.act_of(1, 3)["name"].startswith("기") and arc.act_of(3, 3)["name"].startswith("결"),
   f"3화의 단계 {[arc.act_of(e, 3)['name'] for e in (1, 2, 3)]}  ← 마지막은 반드시 결이다")
ok(arc.act_of(8, 8)["name"].startswith("결"), "총 회차가 몇이든 마지막은 결")
sl = D._stage_lines(short, 2)
ok("전(轉)" in sl and "단편" in sl, f"단편에는 기승전결이 실린다\n         {sl.splitlines()[0]}")
ok("시퀀스" not in sl, "200화용 시퀀스 브리프가 실리지 않는다  ← 세 회차가 시퀀스 1에 갇혔었다")
ll = D._stage_lines(long_, 15)
ok("시퀀스" in ll and "narrative_pull" in ll, "연재는 그대로 8시퀀스를 받는다")
ok("단편" not in ll, "연재에 단편 지시가 새지 않는다")
ok("동아리" not in arc.SCALES[1] and "조별과제" not in arc.SCALES[1],
   f"사건 규모 어휘가 장르 중립이다 ({arc.SCALES[1]})  ← 씨앗 세계에 로맨스 소재가 실렸었다")

print()
if fails:
    print(f"문체 규율: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("문체 규율: 배분 수렴 · 층별 적재 · 종류별 격리 · 액자 주기 · 옛 지시 제거 -- 통과")
