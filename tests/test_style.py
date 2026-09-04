"""문체 규율 -- 페르소나가 실제로 프롬프트에 실리고 배분이 목표에 수렴하는가.

관문에서 취향 검사를 뺐으므로(2026-09-04) 문체를 지키는 것은 기각이 아니라 규율이다.
규율은 **실려야** 존재한다 -- 이 저장소가 반복 실증한 것이 그것이다(읽히지 않는 산문 규칙은
아무것도 막지 못한다). 여기서 고정하는 것:

  1. 고른 페르소나의 규율이 층별로(화자/배우/디렉터) 실리는가
  2. **다른 페르소나의 규율이 새지 않는가** -- 둘 다 실리면 모델은 둘 다 반쯤 지킨다
  3. 씬 종류 배분이 그 페르소나의 목표 비율에 수렴하는가
  4. 페르소나를 갈아끼우면 종류·풀·결말까지 통째로 바뀌는가

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


def scene(kind, ep=1):
    return Scene(id="s1", episode=ep, kind=kind, location="길드 접수처",
                 punctum="깨진 유리", participants=[POV, "공명"])


print("[기본] 기본 페르소나는 사이다다")
ok(style.ACTIVE == "cider", f"ACTIVE={style.ACTIVE}")
ok(sorted(style.PERSONAS) == ["cider", "hardboiled"], f"{sorted(style.PERSONAS)}")

print("[배분] 씬 종류가 목표 비율에 수렴하는가")
counts: dict = {}
for i in range(300):
    counts_k = style.pick_kind(style.subplot_pool() if i % 3 else style.spine_pool(), counts)
    counts[counts_k] = counts.get(counts_k, 0) + 1
share = {k: v / 300 for k, v in counts.items()}
for k, spec in style.kinds().items():
    got, want = share.get(k, 0), spec["share"]
    ok(abs(got - want) <= 0.03, f"{k} {got:.0%} (목표 {want:.0%})")
ok(style.pick_kind(style.spine_pool(), {"cider": 99}) == "pingpong",
   "역전이 넘치면 대사 씬으로 간다")

print("[배분] 재개해도 이어서 센다")
ok(style.tally([scene("cider"), scene("cider"), scene("routine")])
   == {"cider": 2, "routine": 1}, "이미 쓴 씬의 종류를 센다")
ok(style.tally([Scene(id="x")]) == {},
   "종류가 없는 씬은 세지 않는다  ← 옛 원고를 이어받아도 죽지 않는다")
got = {style.pick_kind(style.subplot_pool(), {"cider": 3, "praise": 1}) for _ in range(20)}
ok(len(got) == 1, f"무작위가 아니라 결손 최대로 고른다 ({got})  ← 재현되지 않으면 못 잰다")

print()
print("[화자] 하루키 문장 + 사이다 템포가 함께 실려 있는가")
p = D.narrator_prompt(N, scene("cider"))
ok("건조한 번역투 단문" in p and "만연체를 쓰지 마라" in p, "문장은 하루키 쪽 -- 건조한 단문")
ok("마이너스 퇴고" in p, "마이너스 퇴고")
ok("느낌표" in p, "느낌표 배제 -- 이긴 쪽은 조용하다")
ok("주저하지 않는다" in p, "속도는 사이다 쪽 -- 지연 금지")
ok("딜레마" in p and "흔들리지 않는다" in p, "갈등 거세")
ok("농담" in p and "과장된 반응은 전부 조연 몫" in p, "코믹은 조연에게 맡긴다")
ok("3줄 이하" in p, "모바일 여백")

print("[화자] 상태창을 지웠는가  ← 문장을 UI 로 바꾸면 필력이 제일 먼저 죽는다")
ok("호감도" not in p and "등급   D" not in p, "상태창 블록이 없다")
ok("상태창·게이지를 쓰지 마라" in p, "쓰지 말라고 명시한다")
ok("status" not in style.kinds(), f"상태창 씬 종류가 없다 ({sorted(style.kinds())})")

print("[화자] 종류별 규율이 그 씬에만 실린다")
ok("걸림돌을 그 자리에서" in D.narrator_prompt(N, scene("cider")), "사이다 씬")
ok("손이 하는 일" in D.narrator_prompt(N, scene("routine")), "행동 쉼표 씬")
ok("거의 전부 대사다" in D.narrator_prompt(N, scene("pingpong")), "핑퐁 씬")
ok("방금 일을 되짚는다" in D.narrator_prompt(N, scene("praise")), "확인 씬")
ok("국수를 삶고" not in D.narrator_prompt(N, scene("cider")),
   "다른 종류의 규율은 안 실린다  ← 넷을 다 실으면 어느 것도 안 지켜진다")
ok(style.brief("없는종류") == "", "모르는 종류에는 규율을 지어내지 않는다")

print("[3화 법칙] 회차 구조가 1·2·3화에만 실린다")
ok("곤경과 손실" in D.narrator_prompt(N, scene("cider", ep=1)), "1화 -- 곤경과 손실")
ok("관계 프레임 확정" in D.narrator_prompt(N, scene("cider", ep=2)), "2화 -- 관계 프레임")
ok("규칙 마찰" in D.narrator_prompt(N, scene("cider", ep=3)), "3화 -- 규칙 마찰")
ok(style.episode_brief(4) == "", "4화부터는 없다  ← 남은 자들이 진짜 독자다")

print()
print("[배우] 핑퐁과 조연 도구화")
a = D.actor_prompt(N, scene("pingpong"), "공명")
ok("한 번에 한두 문장" in a, "짧게 주고받는다")
ok("대사로 증명" in a, "설정을 대사로 증명한다")
ok("놀라고 감탄하는 것은 조연" in a, "조연은 주인공을 빛낸다")
ok("반동은 분명해야" in a, "방해자는 애매하지 않다")

print("[디렉터] 성취 전시와 정보 비대칭")
d = D.director_prompt(N, scene("pingpong"))
ok("한 걸음이다" in d and "정체하는 장면을 짜지 마라" in d, "매 장면이 한 걸음이다")
ok("다음 화로 미루지 마라" in d, "지연 금지")
ok("선역이라도 반동" in d, "방해자는 즉각 반동으로 규정")
ok("대가를 치르게 하지 마라" in d, "대가 없음")
ok("먼저 아는 것" in d and "상태창도 수치도 없다" in d,
   "반칙은 앎으로만 드러난다  ← 수치로 드러내면 문장이 UI 가 된다")

print()
print("[교체] 페르소나를 갈아끼우면 통째로 바뀌는가")
ok(style.finale_kind() == "cider", "사이다의 결말은 가장 큰 성취다")
style.use("hardboiled")
try:
    hp = D.narrator_prompt(N, scene("routine"))
    ok("불가능은 하나뿐" in hp, "순수 하드보일드 규율이 실린다")
    ok("주저하지 않는다" not in hp and "농담" not in hp, "사이다 템포가 새지 않는다")
    ok(style.spine_pool() == ("delivery", "routine"), f"풀도 바뀐다 ({style.spine_pool()})")
    ok(style.finale_kind() == "resolution", "결말 종류도 바뀐다")
    ok(style.episode_brief(1) == "", "3화 법칙은 사이다의 것이다 -- 여기엔 없다")
finally:
    style.use("cider")
ok(style.ACTIVE == "cider", "되돌아온다")

bad = False
try:
    style.use("없는페르소나")
except ValueError:
    bad = True
ok(bad, "모르는 이름은 사실대로 실패한다  ← 조용히 기본값으로 물러서면 아무도 모른다")

print()
if fails:
    print(f"문체 규율: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("문체 규율: 배분 수렴 · 층별 적재 · 종류 격리 · 3화 법칙 · 페르소나 교체 -- 통과")
