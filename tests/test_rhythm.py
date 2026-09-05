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

from novel import flow, rhythm, style                                 # noqa: E402

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
src = Path(flow.__file__).read_text(encoding="utf-8")
ok("제일 짙은 것을 채택한다" in src, "끝내 못 고치면 제일 짙은 후보를 쓴다")
ok("그대로 채택한다" in src, "후보가 없으면 그대로라도 쓴다")
ok("앞서 통과한 후보를 채택한다" in src,
   "마지막 시도가 모순이면 앞의 후보로 되돌아간다  ← 리듬 재시도가 원고를 잃게 하면 안 된다")

print()
print("[일치] **코드가 재는 기준과 모델에게 주는 기준이 같아야** 고칠 수가 있다")
p = flow.write_prompt(flow.blank(flow.FIRST))
ok(f"{int(rhythm.LIMITS['long'] * 100)}%" in p, "긴 문장 비율을 프롬프트가 같이 말한다")
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
ok(not any("받아 올리는" in c for c in rhythm.check(REFERENCE)),
   "기준 문장은 통과한다  ← 자가 기준을 벌하면 자가 틀린 것이다")
ok(rhythm.score(FLAT) > rhythm.score(REFERENCE), "점수에도 실린다")
_p = flow.write_prompt(flow.blank())
ok(f"{rhythm.LIMITS['climb']}개마다" in _p, "프롬프트가 같은 숫자를 말한다")
ok("**점층**" in flow.write_prompt(dict(flow.blank(), chunks=["앞."])),
   "맨 끝 필수 목록에도 오른다  ← 묻히면 안 지켜진다")

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

print()
if fails:
    print(f"리듬: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("리듬: 기준 통과 · 나열 검출 · 소프트 개입 · 프롬프트 일치 · 문체 -- 통과")
