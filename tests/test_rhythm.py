"""리듬은 **재서** 잡는다 -- 프롬프트에 적어두는 것만으로는 안 됐다.

실측 2026-09-04. `style.narrator()` 의 [리듬] 항목도, `flow.write_prompt()` 의
"장문과 단문을 섞어라" 도 이미 프롬프트에 있었다. 그렇게 나온 8,489자에 대한 평:

    "끝이 -다. 이거 너무 단조롭게 재미 없다고.
     문장이 너무 짧고 리듬감이 없다고. 대사가 너무 작위적이고 딱딱하다고"

부탁으로는 안 된다는 뜻이다. 그래서 센다.

실행: python3 tests/test_rhythm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# **이 검사는 cider 작법서의 규율을 붙든다.** 2026-09-10 에 기본 페르소나가 manga 로 바뀌었고
# (사용자 결정 2026-09-12: "만화체 기준으로 삼는다"), 만화 식 작법서에는 이 항목들이 없다.
# 기본값을 되돌리지 않고 **이 검사가 보는 페르소나를 못박는다** -- cider 는 PERSONAS 에 그대로
# 있고, 그 작법서의 규율이 무너지지 않는지는 여전히 봐야 한다.
import novel.style as _페르소나  # noqa: E402
_페르소나.use("cider")

import os
# **살아 있는 targets.json 을 안 읽는다.** 목표는 지금 겨누는 작품에 맞춰 좁혀지는데,
# 그때마다 이 테스트가 깨지면 목표를 조일 수 없게 된다(실측: A 하나로 좁히자 표본
# 넷이 폭을 벗어나 밤샘 루프가 preflight 에서 멈췄다). 여기서 고정하는 것은 관문의
# 논리이지 어느 작품의 수가 아니다.
os.environ["DRIFT_TARGETS"] = str(
    __import__("pathlib").Path(__file__).resolve().parent / "fixtures" / "targets.broad.json")


from novel import flow, rhythm, style                                 # noqa: E402


def _adopted(shock: bool = False):
    """확산에 확실히 걸리는 원고를 **실제로 채택시키고** (원고, 장부 갈래)를 돌려준다.

    호출은 없다 -- 추출기가 `{}` 를 돌려주면 원장은 그대로고 모순도 안 생긴다.
    소스에서 주석을 찾는 대신 이렇게 잰다: 주석에만 있는 낱말은 **그 기능을 지워도
    초록**이라 아무것도 재지 않는다(게이트 G016 이 그 자리를 잡는다)."""
    import contextlib, io
    bk = flow.blank("첫 문장이다.")
    bk["chunks"] = ["앞 덩어리."]
    if shock:
        bk["_shock"] = True
    _txt = ("그는 갔다. " * 40) + "\n" + ("비가 왔다. " * 40)
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        flow._adopt(bk, lambda _p: "{}", _txt)
    return bk, sorted(set(bk.get("owed", [])))


# **이 파일은 예전 프롬프트를 켜고 본다.** 기본은 axes 다(flow.PROMPT="axes") --
# 프롬프트를 재는 축에서 짓고, 손으로 쓴 문장론은 한 줄도 안 넣는다.
# 여기서 검사하는 것은 그 옛 작법서 블록의 내용이라 켜 놓고 본다.
flow.PROMPT = "legacy"


# **이 파일은 서사층까지 켜고 본다** -- 기본값은 문면층만이다(flow.LAYER = "text").
# 여기서 검사하는 것은 서사층 블록의 내용이라 켜 놓고 본다.
flow.LAYER = "all"


fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


# 기준으로 삼는 문장(style.py 의 [상황]/[점층] 예문). 이것이 걸리면 자가 틀린 것이다.
REFERENCE = """서른일곱 살이던 그때, 나는 좌석에 앉아 있었다. 그 거대한 비행기는 두터운 비구름을 뚫고 내려와, 함부르크 공항에 착륙을 시도하고 있었다.
11월의 차가운 비가 대지를 어둡게 물들이고 있었고, 비옷을 걸친 정비공들, 민둥민둥한 공항 빌딩 위에 나부끼는 깃발, 광고판 등 이런저런 것들이 어느 음울한 그림의 배경처럼 보였다.
비행기가 착륙하자 금연등이 꺼지고 기내의 스피커에서 조용한 배경음악이 흘러나오기 시작했다. 그것은 어떤 오케스트라가 감미롭게 연주하는 옛 곡이었다.
"정말 괜찮으세요?"
"괜찮아요, 고맙습니다."
나는 고개를 들어 상공에 떠 있는 어두운 구름을 바라보면서, 내가 이제까지 살아오면서 잃어버린 많은 것들에 대해 생각했다. 잃어버린 시간, 죽었거나 또는 사라져 간 사람들, 이젠 돌이킬 수 없는 지난 기억들을."""

FLAT = "\n".join(["그는 문을 열었다.", "밖은 어두웠다.", "비가 내렸다.",
                  "그는 담배를 물었다.", "불이 붙지 않았다.", "그는 기다렸다.",
                  "차가 지나갔다.", "그는 걸었다."])

print("[자] **'-다' 가 아니라 길이를 센다**")
print("      ← 기준 문장은 서술문의 86%가 '-다' 로 끝나고 여섯이 내리 이어진다.")
print("        그런데 단조롭지 않다 -- 그 '-다' 의 71%가 마흔 자를 넘기 때문이다.")
ok(rhythm.check(REFERENCE) == [], "기준 문장은 통과한다")
ok(rhythm.score(REFERENCE) == 0.0, "기준 문장의 점수는 0이다")
ok(rhythm.measure(REFERENCE)["da"] < 0.5, "긴 '-다' 는 세지 않는다")

print()
print("[자] **짧은 단문 나열은 걸린다**")
ok(len(rhythm.check(FLAT)) >= 3, "길이·연속·대사가 한꺼번에 걸린다")
ok(rhythm.measure(FLAT)["da"] == 1.0, "전부 짧은 '-다' 다")
ok(rhythm.score(FLAT) > rhythm.score(REFERENCE), "점수로 둘을 가른다")
ok(rhythm.check("그는 갔다.") == [], "너무 짧은 글은 재지 않는다  ← 통계가 의미 없다")

print()
print("[개입] **리듬은 원고를 죽이지 않는다** -- 모순만 죽인다")
# **소스에서 주석을 찾지 않는다.** 주석에만 있는 낱말은 기능을 지워도 초록이다(G016).
_bk_k, _owed_k = _adopted()
ok(len(_bk_k["chunks"]) == 2 and _owed_k,
   f"못 고친 것이 {len(_owed_k)}갈래 남았는데도 덩어리는 원고에 들어갔다  ← 폐기는 없다")
ok("대사 몫" in _owed_k and "짧은 '-다'" in _owed_k,
   f"못 고친 것은 버리는 대신 장부에 적는다 ({_owed_k})")
# **모순은 문장만 보낸다.** 3,200자를 통째로 다시 쓰던 자리다.
_lines = ["요우는 마흔둘이다.", "요우는 서른이다."]
_cp = flow.clash_prompt(["요우의 나이가 어긋난다"], _lines)
ok(all(x in _cp for x in _lines), "어긋난 문장은 프롬프트에 실린다")
ok("나머지 3200자" not in _cp and _cp.count("\n") < 40,
   "모순도 그 문장만 고쳐 살린다  ← 원고 전체를 보내지 않는다")
ok("고친 문장만" in _cp, "되받는 것도 고친 문장뿐이다")

print()
print("[일치] **코드가 재는 기준과 모델에게 주는 기준이 같아야** 고칠 수가 있다")
p = flow.write_prompt(flow.blank(flow.FIRST))
# 이제 이 숫자는 **덩어리마다 다르다** -- 고정 하한은 그 자체가 주기가 됐다.
_bk = flow.blank(flow.FIRST)
ok(f"{flow._telllong(_bk):.0%}" in p,
   "이 대목의 긴 문장 몫을 프롬프트가 같이 말한다  ← 자와 프롬프트가 같은 숫자를 봐야 한다")
ok("덩어리마다 다르다" in p, "고정값이 아니라고 말해 준다")
_seen = [0.12] * 6
ok(rhythm.aim("씨", 6, _seen, rhythm.LONG_LO, rhythm.LONG_HI) > sum(_seen) / len(_seen),
   "계속 짧게 나오면 목표를 올린다  ← 방향 탐색: 모자란 쪽으로 민다")
_seen = [0.38] * 6
ok(rhythm.aim("씨", 6, _seen, rhythm.LONG_LO, rhythm.LONG_HI) < sum(_seen) / len(_seen),
   "계속 길게 나오면 목표를 내린다")
ok(f"{int(rhythm.LIMITS['da'] * 100)}%" in p, "짧은 '-다' 비율을 프롬프트가 같이 말한다")
ok("네 번" in p, "연속 한도를 프롬프트가 같이 말한다")

print()
print("[문체] **'건조함' 을 '짧음' 으로 읽지 않게 한다**")
n = style.narrator()
ok("만연체를 쓰지 마라" not in n, "'만연체 금지' 를 뺐다  ← 리듬 규칙과 정면으로 부딪혔다")
ok("길이를 섞" in n, "길이를 섞으라고 먼저 말한다")
ok("말이 정보를 나르게 하지 마라" in n,
   "대사가 용건만 말하지 않게 한다  ← 딱딱함의 정체가 이것이다")

print()
print("[점층] **재지 않는 것은 안 지켜진다**")
print("      ← 지금까지 style.py 의 프롬프트에만 적혀 있었다. 이 세션에서 확인된 것이")
print("        하나 있다면 그것이다. 그래서 센다.")
CLIMBED = "\n".join([
    "비행기가 착륙하자 스피커에서 조용한 배경음악이 흘러나오기 시작했다.",
    "그것은 어떤 오케스트라가 감미롭게 연주하는 옛 곡이었다.",
    "그리고 그 멜로디는 언제나처럼 나를 어지럽혔다.",
    "아니, 다른 때와는 비교가 되지 않을 정도로 격렬하게 머리 속을 뒤흔들었다.",
    "나는 고개를 들어 상공에 떠 있는 어두운 구름을 오래 바라보았다.",
])
ok(rhythm.climb(CLIMBED) >= 3, f"기준 문장에서 점층을 잡아낸다 ({rhythm.climb(CLIMBED)}개)")
ok(not any("받아 올리는" in c for c in rhythm.check(CLIMBED)), "점층한 글은 통과한다")
ok(rhythm.climb(FLAT) == 0, "낱개로 선 문장들에서는 0이다")
ok(any("받아 올리는" in c for c in rhythm.check(FLAT)), "모자라면 짚는다")

print()
print("[회수] **심어 놓고 나중에 원인으로 돌려 놓는 것도 점층이다**")
print("      ← 사용자가 짚은 대목: 걸쳐 준 옷 한 벌이 여남은 문장 뒤에 땀으로 돌아온다.")
print("        이음말도 수도 동선도 아니어서 자가 못 봤다.")
HELD = "\n".join([
    "어머니는 두툼한 스웨터를 입혀 주었다.",
    "나는 혼자서 전철을 탔다.",
    "출입문 앞에 붙어 서서 바깥을 보았다.",
    "학교는 지도를 볼 것도 없이 찾을 수 있었다.",
    "가파른 고갯길에 아이들이 줄지어 걸었다.",
    "고갯길을 오르면서 스웨터 탓에 계속 땀을 흘렸다."])
ok(rhythm.holdclimb(HELD) >= 1, f"던진 것이 뒤에서 돌아오면 센다 ({rhythm.holdclimb(HELD)}개)")
ok(rhythm.holdclimb(FLAT) == 0, "대명사가 되풀이되는 것은 회수가 아니다")
ok(rhythm.holdclimb("\n".join(["같은 말. 같은 말."] * 3)) == 0,
   "바로 옆 문장의 되풀이도 회수가 아니다  ← 거리가 있어야 심은 것이 된다")
ok(rhythm.holdclimb("\n".join(f"{i}번 낱말{i} 낱말{i}." for i in range(40))
                    + "\n" + " ".join(f"낱말{i}" for i in range(40))) <= rhythm.HOLD_CAP,
   f"위로 열어 두지 않는다 (최대 {rhythm.HOLD_CAP})  ← 길기만 하면 저절로 통과한다")
_hp = flow.write_prompt(flow.blank())
ok("심어 놓고 회수한다" in _hp, "프롬프트가 심기와 회수를 시킨다  ← 재기만 하고 안 시키면 안 나온다")
ok("매번 달라야 한다" in _hp and f"{rhythm.HOLD_GAP}문장" not in _hp,
   "거리를 수로 못 박지 않는다  ← 적어 주면 원고가 정확히 그 수로 회수한다")
ok(not any("받아 올리는" in c for c in rhythm.check(REFERENCE)),
   "기준 문장은 통과한다  ← 자가 기준을 벌하면 자가 틀린 것이다")
ok(rhythm.score(FLAT) > rhythm.score(REFERENCE), "점수에도 실린다")
_p = flow.write_prompt(flow.blank())
ok(f"{rhythm.LIMITS['climb']}개마다" in _p, "프롬프트가 같은 숫자를 말한다")
ok("**점층**" in flow.write_prompt(dict(flow.blank(), chunks=["앞."])),
   "맨 끝 필수 목록에도 오른다  ← 묻히면 안 지켜진다")

print()
print("[늘어짐] **'길게 써라' 가 '절을 이어 붙여라' 로 풀린다**")
print("      ← 길이를 글자수로 재니, 글자수를 늘리는 제일 싼 답이 '-고 · -면서 · -는데' 다.")
print("        게다가 손질 지시가 짧은 문장마다 '쉼표로 이어 붙여 넘겨라' 라고 시켰다.")
GLUED = "\n".join(["그는 문을 열고 밖을 보면서 담배를 물었는데 불이 붙지 않아서 "
                   "다시 주머니를 뒤졌다."] * 10)
ok(rhythm.glue(GLUED) > rhythm.GLUE_MAX, f"늘어진 글을 잡는다 ({rhythm.glue(GLUED):.1f}개)")
for _f in ("tests/sample_outside.txt", "tests/sample_job.txt"):
    _t = (Path(__file__).resolve().parent.parent / _f).read_text(encoding="utf-8")
    ok(rhythm.glue(_t) <= rhythm.GLUE_MAX,
       f"{_f.split('_')[-1][:-4]} 표본은 통과한다 ({rhythm.glue(_t):.1f}개)  ← 자가 기준을 벌하면 자가 틀렸다")
ok(any("길이를 절로 벌지 마라" in c for c in rhythm.check(GLUED)), "무엇이 문제인지 말해 준다")
ok("glue" in rhythm.spots(GLUED), "걸린 문장을 짚어 준다  ← 그 문장만 고치면 된다")
ok(rhythm.check(REFERENCE) == [], "기준 문장은 여전히 통과한다")
_pt = flow.write_prompt(flow.blank())
ok("쉼표로 이어 붙여" not in _pt,
   "'쉼표로 이어 붙여라' 를 뺐다  ← 늘어짐을 시키는 지시가 프롬프트에 있었다")
ok("절을 잇대서 늘이지 마라" in flow.PATCHABLE["long"],
   "짧은 문장을 늘릴 때도 절을 잇대지 말라고 한다")

print()
print("[박자] **하한만 두면 하한을 정확히, 규칙적으로 맞춘다**")
print("      ← 실측 2026-09-05: '단문 3에 장문 1이 너무 반복적으로 나온다.'")
print("        긴 문장 15% 이상을 요구했더니 정확히 네 문장에 하나씩 길게 썼다.")


def _mk(lens):
    return "\n".join("가" * n + "다." for n in lens)


ok(rhythm.beat(REFERENCE)[1] > rhythm.BEAT_MIN_VAR,
   f"기준 문장은 통과한다 (들쭉날쭉 {rhythm.beat(REFERENCE)[1]:.2f})")
ok(rhythm.beat(_mk([20, 20, 20, 60] * 5))[1] < rhythm.BEAT_MIN_VAR,
   "단문3+장문1 반복은 걸린다  ← 간격이 3, 3, 3, 3 이면 그건 박자표다")
ok(rhythm.beat(_mk([18, 22, 19, 25, 70] * 4))[1] < rhythm.BEAT_MIN_VAR,
   "단문4+장문1 반복도 걸린다  ← 주기의 길이는 상관없다")
ok(rhythm.beat(_mk([12, 55, 90, 9, 18, 22, 7, 60, 15, 11, 25, 80]))[1]
   > rhythm.BEAT_MIN_VAR, "제멋대로면 통과한다")
ok(rhythm.beat("가다. 나다.")[0] < rhythm.BEAT_MIN,
   "긴 문장이 몇 개 없으면 주기를 안 따진다  ← 셋으로는 규칙인지 우연인지 모른다")
ok(any("규칙적인 자리" in c for c in rhythm.check(_mk([20, 20, 20, 60] * 5))),
   "걸리면 무엇이 문제인지 말해 준다")

# **자가 원문 서식에 흔들리면 목표값이 통째로 거짓이 된다.** 표본 A 의 07·12장은
# 온점 뒤에 공백이 없어서, 공백만 보는 자로 재니 줄 하나가 통째로 한 문장이 되었다
# -- 온점 131개에 문장 58개, 묘사 문장 평균 82자. 표본이 두 봉우리로 갈라져 보였고
# 목표값 마흔일곱 개가 전부 그 위에서 나왔다.
print("\n[문장 끝] **공백으로만 알 수 없다**")
_t, _ = rhythm._lines("갔다.그는 왔다.")
ok(len(_t) == 2, f"온점 뒤에 공백이 없어도 끊는다 ({_t})")
_t, _ = rhythm._lines("갔다. 그는 왔다.")
ok(len(_t) == 2, "공백이 있으면 당연히 끊는다")
_t, _ = rhythm._lines('그는 "가자." 라고 했다. 나는 따라갔다.')
ok(len(_t) == 2, f'닫는 따옴표가 끼어도 끊는다 ({_t})')
_t, _ = rhythm._lines("3.5초였다.그리고 끝났다.")
ok(len(_t) == 2 and _t[0] == "3.5초였다.", f"숫자의 온점은 안 끊는다 ({_t})")
_t, _ = rhythm._lines("갔다…돌아왔다.")
ok(len(_t) == 2, f"말줄임도 문장 끝이다 ({_t})")
_stuck = "그는 걸었다.해는 졌다.바람이 불었다.문이 닫혔다."
ok(len(rhythm._lines(_stuck)[0]) == 4,
   "온점 넷이면 문장 넷이다  ← 여기가 틀리면 문장 평균 길이가 네 배로 나온다")

print()
if fails:
    print(f"리듬: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("리듬: 기준 통과 · 나열 검출 · 소프트 개입 · 프롬프트 일치 · 문체 -- 통과")
