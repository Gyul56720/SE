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
ok("건조한 번역투" in p and "길이를 섞어라" in p,
   "문장은 하루키 쪽 -- 건조하되 길이는 섞는다"
   "  ← '만연체 금지' 는 뺐다. 짧게만 쓰라는 말로 읽혀서 리듬을 죽였다(실측)")
# 느낌표 금지를 뺐다 -- [대사가 이야기다] 가 "느낌표를 써라" 라고 하고 있었다.
# **두 자리가 반대로 말하면 둘 다 안 지켜진다.** 화자는 감정에 이름을 안 붙이되,
# 인물이 자기 기분을 말하는 것은 자유다.
ok("화자는 감정에 이름을 붙이지 않는다" in p, "화자는 감정을 이름 붙이지 않는다")
ok("인물이 자기 기분을 말하는 것은 자유다" in p, "다만 대사는 자유다  ← 초고의 감정은 안 막는다")
ok("주저하지 않는다" in p, "속도는 사이다 쪽 -- 지연 금지")
ok("딜레마" in p and "흔들리지 않는다" in p, "갈등 거세")
ok("농담" in p and "과장된 반응은 전부 조연 몫" in p, "코믹은 조연에게 맡긴다")
ok("3줄 이하" in p, "모바일 여백")

print("[문장론] 여섯 기법이 실려 있는가  ← 필력은 규율에서 나온다")
ok("좌표를 먼저 놓아라" in p, "1. 모든 것을 상황으로 -- 좌표부터")
ok("나쁨:" in p and "좋음:" in p,
   "   나쁜 예와 좋은 예를 함께 준다  ← 규칙만 주면 모델은 규칙을 요약해서 지킨다")
ok("성의가 없다" in p, "   '나는 아팠다' 는 성의가 없다고 못박는다")
# 숫자는 한 곳에만 둔다 -- 여기 "두 번" 과 게이트의 "네 번" 이 어긋나 있었다.
ok("몇 번까지인지는 뒤쪽에서 숫자로 준다" in p,
   "2. '-다' 단조로움 -- 숫자는 재는 자리에서만 말한다")
ok("생각을 붙인다" in p and "문장을 끝내지 않는다" in p, "   세 가지 수를 준다")
ok("앞 문장에서 한 단계 올린다" in p, "3. 점층 -- 문장은 독립적이지 않다")
# 예전에는 이 자리가 "'아니,' '정확히 말하자면,' 이 들어 있는가" 였다. **그 예시를 못
# 박은 것이 바로 문제였다** -- 원고가 그 넷으로 도배됐다(사용자 평: "'정확히 말하자면'
# 이 너무 많이 나와"). 자는 스물 몇 개를 세는데 프롬프트는 넷만 보여 줬으니, 모델이
# 아는 것이 넷뿐이었다. 이제 이음말은 덩어리마다 뽑아서 준다.
ok("정확히 말하자면" not in p,
   "   특정 이음말을 못 박지 않는다  ← 박아 두면 원고가 그것으로 도배된다")
ok("같은 이음말을 반복해서 쓰지 마라" in p, "   같은 말로 받지 말라고 한다")
ok("(좁힌다)" in p and "(키운다)" in p and "(뒤집어 더 키운다)" in p,
   "   네 줄짜리 점층 예시에 무엇을 했는지 이름표를 단다")
ok("점층은 **끊길 때 끝난다.**" in p, "   끝나는 자리도 정해준다")
ok("외현" in p and "내현" in p, "4. 전환 -- 밖에서 안으로")
ok("안팎의 몫은 뒤쪽" in p, "   비율은 뽑기가 준다  ← 여기 또 적으면 두 숫자가 어긋난다")
ok("몽글한 것이 하나" in p, "5. 몽글한 어휘와 친절한 인물")
ok("I only felt lonely" in p, "   외국어 병기 예시까지 준다")
ok("가짜를 진짜처럼" in p and "제목을 짓고" in p, "6. 구체 -- 없는 책도 제목과 내용을 짓는다")
ok("그 흐릿함이 오히려 진짜처럼" in p, "   확실하지 않아도 된다")
ok("못생긴 쌍둥이 형제" in p, "   지극히 개인적인 단정을 예시로 준다")
ok("없는 우물, 없는 책" in p, "   없는 것에 세부를 붙이라고 한다")

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
