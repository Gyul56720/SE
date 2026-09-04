"""메아리 -- **앞에 쓴 문장을 그대로 다시 뱉는 것.**

실측(2026-09-04, flow3.json): 한 덩어리 2,024자 중 **610자(30%)가 글자 하나 안 틀리고
반복**이었다. 대사 일곱 줄과 서술 일곱 줄이 통째로 두 번 나온다. 리듬 자도 확산 자도
이것을 통과시켰다 -- 반복된 문장은 그 자체로는 리듬이 좋고 농도가 짙기 때문이다.

취향이 아니라 결함이다. 모순과 같은 급으로 다룬다.

실행: python3 tests/test_echo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import diffusion as F, echo, flow                          # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


ONCE = "\n".join([
    "그는 창가에 앉아 눈보라를 바라보았다. 항구 쪽에서 불어오는 바람에 생선 냄새가 섞였다.",
    '"커피 드실래요?"',
    '"아뇨, 방금 마셨습니다. 아니, 마신 것 같기도 하고."',
    "노인은 젖은 걸레를 내려놓고 구석의 나무 상자를 발로 툭 찼다.",
])
TWICE = ONCE + "\n" + ONCE

print("[자] **글자 하나 안 틀리고 반복된 것을 센다**")
rate, dup = echo.selfish(TWICE)
ok(rate > 0.4, f"통째로 복사한 덩어리를 잡는다 ({rate:.0%})")
ok(len(dup) >= 3, f"반복된 줄을 짚어 준다 ({len(dup)}줄)")
ok(echo.selfish(ONCE)[0] == 0.0, "멀쩡한 덩어리는 0%")
ok(echo.check(ONCE, "") == [], "멀쩡한 덩어리는 통과")
ok(any("다시 적지 마라" in c for c in echo.check(TWICE, "")), "무엇을 하지 말라고 말한다")

print()
print("[관용] **말버릇까지 반복으로 세면 안 된다**")
print("      ← '난 안 가' 를 두 번 말하는 것은 반복이 아니라 성격이다.")
habit = ONCE + '\n"난 안 가."\n그는 또 말했다.\n"난 안 가."'
ok(echo.check(habit, "") == [], f"짧은 되풀이는 넘어간다 ({echo.selfish(habit)[0]:.0%})")

print()
print("[꼬리] **옮겨 적은 앞부분은 판정하지 않고 도려낸다**")
print("      ← 이미 원고에 있는 글자다. 호출을 한 번 더 쓰는 것보다 자르는 편이 싸다.")
prev = "앞서 쓴 것들.\n" + ONCE
kept, dropped = echo.trim(ONCE + "\n그러고 나서 문이 열렸다.\n낯선 남자가 서 있었다.\n"
                          "그는 아무 말도 하지 않았다.", prev)
ok(dropped > 0, f"꼬리를 옮겨 적은 만큼 도려낸다 ({dropped}자)")
ok(kept.startswith("그러고 나서"), "본문은 그대로 남는다")
ok(echo.trim("완전히 새로운 글이다.", prev) == ("완전히 새로운 글이다.", 0),
   "새 글은 건드리지 않는다")

print()
print("[개입] **메아리는 원고를 죽인다** -- 리듬·농도와 달리 반드시 다시 받는다")
src = Path(flow.__file__).read_text(encoding="utf-8")
ok("메아리는 모순과 같은 급이다" in src, "모순과 같은 급으로 다룬다")
ok("앞 글을 옮겨 적은" in src, "잘라낸 만큼 로그에 남긴다")
# 프롬프트는 줄을 접어 쓰므로 낱말 사이 줄바꿈을 지우고 본다.
_flat = " ".join(flow.write_prompt(flow.blank()).split())
ok("앞에 쓴 문장을 다시 적지 마라" in _flat and "옮겨 적으라고 준 것이 아니다" in _flat,
   "프롬프트가 꼬리의 쓰임을 못박는다  ← 모델은 그것을 이어 붙일 원고로 읽는다")

print()
print("[회수] **회수는 다시 부르는 것이 아니라 다시 쓰는 것이다**")
print("      ← 실측: 한 덩어리에 '1982년형 볼보' 4회, '삼십 년 전' 4회, '주머니' 5회.")
print("        그동안 볼보는 아무것도 하지 않는다 -- 헤드라이트를 깜빡이며 서 있다.")
led = {"people": {"올라프손": {}}, "places": {"양조장": "x"},
       "objects": {"볼보": "차"}, "facts": {}, "time": []}
spam = "볼보가 섰다. 볼보의 문. 볼보의 불빛. 볼보의 연식. 올라프손. 올라프손. 올라프손."
over = F.overused(spam, F.props(led))
ok(dict(over).get("볼보") == 4, f"과다 호명을 센다 ({over})")
ok(F.overused(ONCE, F.props(led)) == [], "정상 덩어리는 걸리지 않는다")
ok(any("다시 부르는 것이 아니라" in c for c in F.check(spam, led, led)),
   "이름을 또 적지 말고 그것이 무언가를 하게 하라고 말한다")

print()
print("[라벨] **구체성은 명사를 꾸미는 데서 오지 않는다**")
labels = "1982년형 볼보와 1978년산 판화집과 1950년대 상자와 1984년의 밤과 1959년 모델."
ok(F.labels(labels) == 5, f"연도 표기를 센다 ({F.labels(labels)})")
ok(F.labels(ONCE) == 0, "연도가 없는 글은 0")
ok(any("접두사를 붙이지 마라" in c for c in F.check(labels, led, led)), "라벨 붙이기를 짚는다")
# 확산 지시는 첫 덩어리에는 실리지 않는다(세계가 서기 전이다). 이어 쓰는 상태로 본다.
_mid = flow.blank(); _mid["chunks"] = ["앞 덩어리."]
_midflat = " ".join(flow.write_prompt(_mid).split())
ok(f"{F.LABEL_MAX}개까지다" in _midflat, "프롬프트가 같은 상한을 말한다")
ok(f"{F.ECHO_MAX}번까지만 부른다" in _midflat, "한 이름을 몇 번까지 부를지도 말한다")
ok("이름과 연도와 상표를 대라" not in _midflat,
   "'연도를 대라' 와 '연도가 많다' 가 부딪히지 않는다  ← 지시가 서로 싸우면 안 된다")

print()
print("[자유] **감탄사와 깨진 문법을 벌하지 않는다**")
print("      ← 자가 문법을 요구하면 대사가 다시 딱딱해진다. 여기는 풀어주는 자리다.")
loose = "\n".join([
    "끼얏호, 하고 누군가 외쳤다.",
    '"어라랍쇼."', '"뭐야 그게."',
    '"몰라. 아버지가 놀라면 늘 그러셨거든. 어라랍쇼, 어라랍쇼 하면서 뒷걸음질을 '
    '치는데 그게 또 묘하게 위엄이 있었단 말이지."',
    '"쓰읍."',
    "그는 숨을 들이켰고, 항구 쪽에서 불어오는 바람에는 생선과 디젤과 눈 냄새가 "
    "한꺼번에 섞여 있었다.",
    '"푸하."', '"웃지 마."', '"안 웃었어. 웃은 건 저 사람이고."',
])
from novel import rhythm                                              # noqa: E402
ok(rhythm.check(loose) == [], "리듬 자가 통과시킨다")
ok(echo.check(loose, "") == [], "'어라랍쇼' 를 두 번 말해도 메아리가 아니다  ← 그건 성격이다")
short, long = F.talk(loose)
ok(short >= 4, f"짧은 감탄사가 대사 리듬을 살린다 (짧은 대사 {short}개)")
_flat = " ".join(flow.write_prompt(flow.blank()).split())
ok("감탄사를 지어내라" in " ".join(__import__("novel.style", fromlist=["x"]).narrator().split()),
   "화자에게 없는 감탄사를 만들라고 한다")
ok("말끝을 다듬으면 그게 딱딱함이다" in _flat, "문법을 놓으라고 한다")
_mid2 = flow.blank(); _mid2["chunks"] = ["앞."]
ok("입버릇·감탄사가 있으면 그것까지 적어라" in flow.extract_prompt("x"),
   "카드에 입버릇을 적는다  ← 그 사람이 다음에도 같은 소리를 내야 한다")

print()
print("[낱말] **없는 말을 지어내고 변명을 단다**")
print("      ← 문법이 깨지는 건 변명이 필요 없다. 사전에 없는 낱말은 다르다 --")
print("        그냥 던지면 오타로 읽히고, 뜻을 달면 그 순간 세계의 일부가 된다.")
import novel.style as _st                                             # noqa: E402
_n = " ".join(_st.narrator().split())
ok("없는 낱말을 지어내라" in _n, "화자에게 낱말을 만들라고 한다")
ok("변명은 **매번 다른 꼴로** 해라" in _n,
   "변명의 꼴을 갈라 준다  ← 같은 방식이 세 번 나오면 그것도 버릇이다")
for form in ("우리 동네 말입니다", "틀린 어원을 진지하게 댄다", "취했거나",
             "두 번째로 쓰일 때 뜻이 저절로 드러나게"):
    ok(form in _n, f"변명 꼴: {form[:18]}")
ok("한둘이면 충분하다" in _n, "한 덩어리에 한둘까지  ← 그 이상은 글이 아니라 암호다")
ok("끝까지 그 뜻이다" in _n, "한 번 준 뜻은 안 바뀐다")

_led = flow.blank()["ledger"]
ok("words" in _led, "원장에 낱말 칸이 있다")
ok(not flow._merge(_led, {"words": {"꿉꿉하다": "눅눅한데 마음 쪽에 쓰는 말"}}),
   "낱말은 기록만 한다")
ok(not flow._merge(_led, {"words": {"꿉꿉하다": "아주 다른 뜻"}}),
   "뜻이 달라져도 기각하지 않는다  ← 게이트는 최소로만 개입한다")
ok("지어낸 말" in flow.brief(_led), "브리핑에 실려 다음 덩어리가 뜻을 지킨다")
ok("지어낸 낱말은 words 에" in flow.extract_prompt("x"), "추출기가 낱말을 뽑는다")
_mid3 = flow.blank(); _mid3["chunks"] = ["앞."]
ok("없는 말을 태연히 쓰고 뜻을 달아 주는 것도 같은 몸짓이다"
   in " ".join(flow.write_prompt(_mid3).split()),
   "급발진의 일부로 실린다  ← 변명하는 꼴이 딱 급발진 이후 유유자적이라서다")

print()
if fails:
    print(f"메아리: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("메아리: 검출 · 관용 · 꼬리 절단 · 하드 개입 · 과다 호명 · 라벨 -- 통과")
