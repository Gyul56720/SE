"""만화 식 소설 -- **시킨 것이 실제로 나왔는지 재는가.**

`style.MANGA` 가 문체를 시키고 `manga.py` 가 잰다. 여기서 보는 것은 그 눈금이 로판과
만화 식을 실제로 가르는가, 그리고 **기각 권한이 없는가**다 -- 관문이 작가가 되면 원고가
균질해진다(gate.py 의 V020 이 겪은 것).

실행: python3 tests/test_manga.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import manga as MG                                         # noqa: E402
from novel import space as SP                                         # noqa: E402
from novel import style as ST                                         # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def codes(vs):
    return sorted({v.rule for v in vs})


# 대사가 미는 글 -- 만화 식
COMIC = "\n".join([
    '그가 문을 열었다.', '"늦었군."', '"길이 막혔어. 다리가 끊겼거든."', '쿵.',
    '잔이 흔들렸다.', '"그래서?"', '남자가 잔을 내려놓았다. 손끝이 젖어 있었다.',
    '"……."', '창밖에서 종이 울렸다.', '"가자."',
] * 4)

# 지문이 미는 글 -- 로판 쪽
PROSE = "\n".join([
    "그는 오래도록 창가에 서서 저물어 가는 도시의 불빛을 바라보았다. 그 빛은 어릴 적 "
    "어머니가 켜 두던 등불과 닮아 있었고, 그래서 그는 자신이 여태 무엇을 잃어버린 채로 "
    "살아왔는지를 비로소 알 것 같았다. 바람이 불었고 커튼이 흔들렸다.",
] * 8)


print("[센다] 대사 · 지문 · 여백")
_c, _p = MG.measure(COMIC), MG.measure(PROSE)
ok(_c["대사비율"] > _p["대사비율"], f"대사 비율이 갈린다 ({_c['대사비율']:.0%} vs {_p['대사비율']:.0%})")
ok(_c["지문평균"] < _p["지문평균"], f"지문 길이가 갈린다 ({_c['지문평균']:.0f}자 vs {_p['지문평균']:.0f}자)")
ok(_c["짧은문단"] > _p["짧은문단"], f"짧은 문단이 갈린다 ({_c['짧은문단']:.0%} vs {_p['짧은문단']:.0%})")
ok(_c["문단"] == 40, f"줄 하나가 문단 하나다 (센 것: {_c['문단']})")
ok(MG.measure("")["문단"] == 0, "빈 글도 죽지 않는다")

print("\n[대사를 알아본다]")
ok(MG.is_talk('"늦었군."'), "큰따옴표")
ok(MG.is_talk('「늦었군.」'), "겹낫표")
ok(not MG.is_talk('그가 "늦었군" 이라고 말한 뒤 오래도록 창밖을 바라보고 서 있었다.'),
   "따옴표가 있어도 지문이 절반을 넘으면 지문이다")
ok(not MG.is_talk("그가 문을 열었다."), "따옴표가 없으면 지문")

print("\n[잰다] 벗어난 자리를 짚는다")
ok(codes(MG.fit(PROSE)) == ["M201", "M203"], f"지문이 미는 글은 대사와 여백을 짚는다: {codes(MG.fit(PROSE))}")
ok("M201" not in codes(MG.fit(COMIC)), "만화 식은 대사 비율을 안 짚는다")
_long = "\n".join(['"짧은 말."', "가" * 400] * 3)
ok("M202" in codes(MG.fit(_long)), f"{MG.NARR_MAX}자 넘는 지문 문단을 짚는다")
ok(MG.fit("짧다.") == [], "200자 미만은 재지 않는다 -- 비율이 뜻을 잃는다")

print("\n[문체는 기각하지 않는다] 관문이 작가가 되면 원고가 균질해진다")
ok(not [v for _t in (COMIC, PROSE, _long) for v in MG.fit(_t) if v.severity != "soft"],
   "문체 눈금은 어떤 글에도 하드를 내지 않는다")

print("\n[누출만 hard] 이것은 문체가 아니라 사실이다")
# 실측 2026-09-09: 첫 덩어리 1,115자에 '화자' 가 일곱 번 나왔다.
_leak = "\n".join(['결코 멈출 줄을 모르는 화자의 걸음이 이어졌다.', '"늦었군."'] * 20)
ok("M204" in codes(MG.fit(_leak)), "'화자' 가 본문에 나오면 잡는다")
ok([v for v in MG.fit(_leak) if v.rule == "M204"][0].severity == "hard",
   "누출은 hard -- gate.py 가 누출을 하드로 잡는 것과 같은 종류")
ok(MG.measure(_leak)["누출"] == 20, f"몇 번인지 센다 (센 것: {MG.measure(_leak)['누출']})")
ok("M204" in codes(MG.fit("화자가 걸었다.")), "짧아도 누출은 본다 -- 길이와 무관하다")
ok("M204" not in codes(MG.fit(COMIC)), "누출이 없으면 안 잡는다")

print("\n[M205] 명사형 종결 -- 컷처럼 보이려고 동사를 지우면 콘티가 된다")
_noun = "\n".join(["사방을 가득 채운 고요함.", "비웃음을 흘리며 철퇴를 겨누는 남자의 모습.",
                  "젖은 흙이 감겨 오는 감촉."] * 12)
ok("M205" in codes(MG.fit(_noun)), "명사로 끝나는 지문을 잡는다")
ok(MG.measure(_noun)["명사형"] > 0.9, "명사형 비율을 센다")
ok(MG.measure(COMIC)["명사형"] < MG.NOUN_MAX, "동사로 맺으면 안 잡힌다")

print("\n[M206] 현재형 종결 -- 각본의 말투")
ok(MG._is_present("연회장으로 향한다."), "~ㄴ다 를 현재형으로 본다")
ok(MG._is_present("검집을 확인한다."), "~한다")
ok(not MG._is_present("바닥으로 떨어졌다."), "과거형은 아니다")
ok(not MG._is_present("단순하고도 잔인했다."), "'했다' 는 과거형")
_now = "\n".join(["남자가 문을 부수고 들어간다.", "잔이 떨어졌다."] * 12)
ok("M206" in codes(MG.fit(_now)), "현재형 지문이 있으면 잡는다")
ok("M206" not in codes(MG.fit(COMIC)), "과거형만 있으면 안 잡는다")

print("\n[보고] 사람이 읽는 꼴")
_r = MG.report(PROSE)
ok("대사 비율" in _r and "지문 평균" in _r and "짧은 문단" in _r, "세 눈금을 보여 준다")
ok("M201" in _r, "짚은 것을 같이 보여 준다")
ok("만화 식으로 나왔다" in MG.report(COMIC), "통과하면 통과했다고 말한다")
ok("명사형 종결" in _r and "현재형 종결" in _r and "누출" in _r, "새 눈금 셋도 보여 준다")

print("\n[페르소나] style.MANGA")
ST.use("manga")
ok(ST.P()["label"].startswith("만화 식"), "만화 식 페르소나를 고를 수 있다")
ok(abs(sum(v["share"] for v in ST.kinds().values()) - 1.0) < 1e-6, "씬 종류의 배분이 1이다")
ok(set(ST.spine_pool()) | set(ST.subplot_pool()) <= set(ST.kinds()), "축과 서브플롯이 종류 안에 있다")
ok(ST.finale_kind() in ST.kinds(), "결말 종류가 종류 안에 있다")
for _k in ST.kinds():
    ok(bool(ST.brief(_k)), f"종류 '{_k}' 에 규율이 있다")
ok("대사가 민다" in ST.narrator(), "지문이 아니라 대사가 민다고 시킨다")
ok("겸하기" in ST.narrator(), "겸하기가 실린다")
ok("반전은 다음 대목의 첫 줄" in ST.narrator(), "넘김을 대목의 사이로 옮겨 시킨다")
ok("상태창" in ST.narrator(), "상태창 금지를 이어받는다")
# 실측 2026-09-09 첫 덩어리가 셋 다 어겼다 -- 그래서 [문장] 블록을 앞에 세웠다
ok("과거로 쓴다" in ST.narrator(), "과거형으로 쓰라고 한다")
ok("명사로 끝내지 마라" in ST.narrator(), "명사형 종결을 막는다  ← 컷이 콘티가 되던 자리")
ok("'화자' 라는 말을 본문에 쓰지 마라" in ST.narrator(), "'화자' 누출을 막는다")
ok("각본을 옮겨 적지 마라" in ST.narrator(), "각본을 베끼지 말라고 한다")
ok("지문이 세 문단 이어지면" in ST.narrator(), "대사를 셀 수 있는 지시로 준다")
ok("목적" in ST.episode_brief(1), "1화에 목적을 내라고 한다")
ok(ST.episode_brief(9) == "", "없는 회차 지시는 빈 것")
ST.use("ropan")
ok("대사가 민다" not in ST.narrator(), "다른 페르소나는 안 물든다 -- 규율이 섞이지 않는다")

print("\n[컷 칸] space.py")
ok(len(SP.names("컷")) == 10, f"컷 문법 열 개 (센 것: {len(SP.names('컷'))})")
for _n in ("겸하기", "決めゴマ", "여백", "배경 복선", "끊기"):
    ok(_n in SP.names("컷"), f"'{_n}' 이 있다")
for _n in ("노드", "컷의 꼴"):
    ok(_n not in SP.names("컷"), f"'{_n}' 은 없다  ← 인쇄의 규율이라 산문에 자리가 없다")

print("\n[배선] 컷이 집필 프롬프트에 실린다")
from novel import beat as BT                                          # noqa: E402
from novel import flow                                                # noqa: E402

_b = flow.blank("첫 문장이다.")
_b["seed_id"] = "씨"
_b["chunks"] = ["가" * 100]
_b["card"] = {"ep": 0, "질문": "q", "방해": "x", "비트": [{"무엇": "a", "꼴": "장면"}],
              "답": "반만", "갈고리종류": "피", "갈고리": "팔이 문틀에 끼인다"}

ST.use("manga")
_m = BT.brief(_b)
ok("· 컷:" in _m, "만화 식이면 컷 칸이 실린다")
ok("· 연출:" not in _m, "연출 칸은 안 실린다 -- 두 칸이 서로를 대신하지 못한다")
ST.use("ropan")
_r = BT.brief(_b)
ok("· 연출:" in _r and "· 컷:" not in _r, "다른 페르소나는 예전대로 연출이 실린다")
ST.use("cider")

print()
if fails:
    print(f"만화 식: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("만화 식: 눈금이 문체를 가른다 · 기각하지 않는다 · 페르소나 · 컷 칸 -- 통과")
