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


print("[기본] 기본 페르소나를 못박는다")
# 2026-09-10 에 `cider` 에서 `manga` 로 바뀌었다(커밋 91091d9 "style: set active persona
# to manga"). **바꾼 쪽이 이 줄을 같이 안 고쳐서 여기가 빨간불로 남아 있었다** -- 그리고
# 아래 검사 마흔둘이 주변 기본값에 기대고 있던 탓에 한 줄이 마흔둘을 무너뜨렸다.
ok(style.ACTIVE == "manga", f"ACTIVE={style.ACTIVE}")
# **명부를 못박아 둔다.** 페르소나가 조용히 늘면 기본값이 바뀌었는지 아무도 모른다.
# 늘릴 때는 여기 한 줄을 같이 고친다 -- 그게 이 검사가 시키는 일이다.
ok(sorted(style.PERSONAS) == ["cider", "hardboiled", "manga", "ropan"], f"{sorted(style.PERSONAS)}")

# **아래는 사이다를 재는 자리다. 주변 기본값에 기대지 말고 여기서 못박는다.**
# 안 그러면 기본값이 바뀌는 날 이 파일이 통째로 무너지고, 무너진 이유가 사이다와 아무
# 상관이 없어서 읽는 사람이 엉뚱한 데를 고치게 된다(실측: 위 한 줄에 42개가 딸려 갔다).
style.use("cider")

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
# **'번역투' 라는 말을 뺐다.** 하루키 문체를 가리키려던 말인데, 모델에게 그것은
# 1980년대 한국어 번역문이다 -- 원고가 딱 그렇게 나왔다(사용자 평: "예전 한국 초기
# 문학 보는 것 같아"). 무엇이 건조함인지는 그대로 설명한다.
ok("번역투" not in p and "번역체" not in p,
   "화자에게 번역투로 쓰라고 하지 않는다  ← 그 말은 옛 번역문을 부른다")
ok("건조하게" in p and "길이를 섞어라" in p, "건조하되 길이는 섞는다")
ok("지금 쓰는 한국어로 써라" in p, "지금 한국어로 쓰라고 한다")
# **버릇의 꼴만 말하고 예문은 안 준다.** 예전에는 '-것이었다' 같은 낱말을 박아 두고
# 그것이 있는지를 검사했는데, 그 검사가 곧 그 낱말을 프롬프트에 붙박아 두는 힘이었다.
ok("옛 번역문의 버릇은 빼라" in p, "옛 번역문의 버릇을 짚어 준다")
ok("'-것이었다'" not in p, "그 버릇을 예문으로 박아 두지는 않는다")
# 느낌표 금지를 뺐다 -- [대사가 이야기다] 가 "느낌표를 써라" 라고 하고 있었다.
# **두 자리가 반대로 말하면 둘 다 안 지켜진다.** 화자는 감정에 이름을 안 붙이되,
# 인물이 자기 기분을 말하는 것은 자유다.
ok("화자는 감정에 이름을 붙이지 않는다" in p, "화자는 감정을 이름 붙이지 않는다")
ok("인물이 자기 기분을 말하는 것은 자유다" in p, "다만 대사는 자유다  ← 초고의 감정은 안 막는다")
# [속도] 를 뺐다. "내면의 갈등·죄책감을 서술하지 마라, 주인공은 흔들리지 않는다" 가
# 내현(잡념 · 억울함 · 고뇌)과 **정면으로 반대**였다. 두 자리가 반대로 말하면 둘 다
# 안 지켜진다. 지연 금지는 디렉터 쪽에 그대로 남아 있다.
ok("주저하지 않는다" not in p, "화자에게 '흔들리지 마라' 고 하지 않는다")
ok("농담" in p and "과장된 반응은 전부 조연 몫" in p, "코믹은 조연에게 맡긴다")
ok("3줄 이하" in p, "모바일 여백")

print("[문장론] 여섯 기법이 실려 있는가  ← 필력은 규율에서 나온다")
ok("좌표를 먼저 놓아라" in p, "1. 모든 것을 상황으로 -- 좌표부터")
# **예문을 뺐다.** 오늘 세 번 확인했다: 예문은 베껴진다('정확히 말하자면',
# '179번 · 87회 · 42회', 그리고 여기 있던 번역문). 예를 주면 원고 전체가 그 한
# 사람의 한 시절 문체가 된다.
ok("나쁨:" not in p and "좋음:" not in p,
   "   예문을 박지 않는다  ← 예문은 규칙보다 강하게 베껴진다")
ok("여기 예문은 주지 않는다" in p, "   왜 안 주는지 말해 준다")
ok("성의가 없다" in p, "   감정을 이름으로 적는 것은 성의가 없다고 못박는다")
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
# 점층 예문도 뺐다 -- 그 예문이 하필 옛 번역문이라 원고가 그 결을 베꼈다.
ok("넷째 문장쯤에서 처음 것과 뜻이 달라져 있으면" in p,
   "   점층이 됐는지 알아보는 법을 예문 없이 말해 준다")
ok("점층은 **끊길 때 끝난다.**" in p, "   끝나는 자리도 정해준다")
ok("외현" in p and "내현" in p, "4. 전환 -- 밖에서 안으로")
ok("안팎의 몫은 뒤쪽" in p, "   비율은 뽑기가 준다  ← 여기 또 적으면 두 숫자가 어긋난다")
ok("몽글한 것이 하나" in p, "5. 몽글한 어휘와 친절한 인물")
ok("외국어를 그대로 적어도 좋다" in p, "   외국어를 그대로 적어도 된다고 한다")
ok("가짜를 진짜처럼" in p and "그것의 이름을 짓고" in p,
   "6. 구체 -- 없는 것에도 이름과 속을 짓는다")
ok("그 흐릿함이 오히려 진짜처럼" in p, "   확실하지 않아도 된다")
ok("여기 예문은 주지 않는다" in p.split("[정밀]")[-1],
   "   정밀에도 예문을 안 준다  ← 예문을 주면 그 사물과 그 시대가 눌러앉는다")
ok("없는 것에도 **정말 있었던 것처럼** 세부를 붙여라" in p,
   "   없는 것에 세부를 붙이라고 한다")

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
print("[낱말] **낱말이 시대와 고장을 먼저 정한다**")
print("      ← 실측: 구문을 손봐도 옛 시골 이야기로 읽혔다. 원인은 구문이 아니라 어휘였다.")
_n = " ".join(style.narrator().split())
ok("이름은 바깥에서 온 것으로 짓는다" in _n,
   "이름을 토박이말·한자어 계열로만 짓지 말라고 한다")
ok("어느 나라 말인지는 여기서 정해 주지 않는다" in _n,
   "어느 말인지는 안 박는다  ← 박으면 원고가 그것으로 도배된다")
ok("꿉꿉" not in _n and "웅포" not in _n,
   "지어낸 말 예문을 뺐다  ← 그 예문이 원고를 옛 시골 쪽으로 끌고 갔다")
ok("토박이말 쪽으로만 만들지 마라" in _n, "지어낸 낱말의 계열도 못박는다")



print()
print("[로판] **잰 것에서 나왔지 지어낸 것이 아니다**")
print("      ← 원작 4편 · 378만 자를 profile.py 로 재서 나온 결이다(2026-09-07).")
print("        원문은 저장소에 안 들어온다 -- DATA.md 대로 수로 바뀌고 끝났다.")

ok("ropan" in style.PERSONAS, "명부에 있다")
style.use("ropan")
_n = style.narrator()

# 잰 것이 실제로 실려야 한다. 수는 안 싣고 **결**로 싣는다.
for _what, _mark in (("시제", "과거"), ("대사 줄", "혼자"), ("피동", "피동"),
                     ("감각", "눈"), ("존대", "존대")):
    ok(_mark in _n, f"{_what}가 실린다")

# **수를 프롬프트에 싣지 않는다.** 자를 시키면 자를 만족시키러 간다(turn.py 와 같은 계약).
for _num in ("0.4", "33자", "sent_len", "talk_len", "glue", "tense_now", "sense_eye"):
    ok(_num not in _n, f"'{_num}' 이 프롬프트에 없다  ← 자를 시키지 않고 일을 시킨다")

# **예문을 주지 않는다.** 주면 그 문장을 베껴 원고가 한 사람의 문체가 된다.
ok("예문은 주지 않는다" in _n, "예문 금지가 명시돼 있다")

# 작가마다 흩어진 축은 안 시킨다 -- 시키면 특정 작가 흉내가 된다.
ok("rally" not in _n and "para_len" not in _n, "흩어진 축은 안 실린다")

# **사용자 평(2026-09-08): 대사·리듬은 좋은데 스토리가 재미없다.** 덜 자극적이고
# (12세), 추상적이고, 로맨스가 없다. 잰 결 위에 이 셋은 **요구**로 얹는다 -- 잰 것이
# 아니므로 수는 없고 규율만 있다.
for _sec, _mark in (("[구체]", "손에 잡히는"), ("[살갗]", "성인 연재물"),
                    ("[자극]", "12세가 아니다")):
    ok(_sec in _n and _mark in _n, f"{_sec} 규율이 실린다")
ok("순서" in _n and "입술" in _n, "닿는 순서를 준다  ← 건너뛰면 육감이 아니라 요약이다")
ok("여럿" in _n, "남자가 여럿 붙는다고 말한다")
ok("집행된다" in _n, "위협이 집행된다  ← 협박만 하고 끝나면 12세다")

style.use("cider")          # 뒤 검사를 위해 되돌린다


# **요약은 맨 끝에 있어야 한다.** 2026-09-07 까지 이 블록이 205줄에 있었다 -- 파일은
# 233줄인데. 뒤에 붙인 검사는 종료 코드에 아무 영향을 못 줬다.
#
# **이 저장소에서 다섯 번째다** -- test_llm_pool_rpm.py(611줄 중 252) ·
# test_flow.py(605줄 중 402) · test_genre.py(473줄 중 251) · 그리고 여기.
# 다섯 번이면 개별 실수가 아니라 이 파일 꼴의 성질이다: 검사를 파일 끝에 덧붙이는
# 습관과, 종료 블록이 본문 사이에 있는 구조가 만나면 반드시 이렇게 된다.
# **게이트로 막아야 할 것이지 사람이 조심할 것이 아니다.**
print()
if fails:
    print(f"문체 규율: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("문체 규율: 배분 수렴 · 층별 적재 · 종류 격리 · 3화 법칙 · 페르소나 교체 · 로판 -- 통과")
