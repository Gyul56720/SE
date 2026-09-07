"""**문장도 사건도 아닌 것** -- 시제 · 인칭 · 비유 · 감각 · 주어.

문면(문장)과 서사(사건)를 다 맞춰도 다른 글이 되는 자리가 있다. 누가 말하고 있는가,
어느 시제로 보는가, 무엇에 빗대는가, 어느 감각으로 쓰는가. 읽는 사람이 "문체" 라고
부르는 것의 절반이 여기다. 전부 정규식이다 -- **LLM 호출 0회.**

여기서 고정하는 계약:

  · **자국이 없으면 그 축은 안 낸다** -- 0 으로 채우면 "안 쓴다" 와 "알 수 없다" 가
    같은 값이 되고, 그 0 들이 폭을 아래로 끌어내린다
  · **감각은 비로만 본다** -- 낱말 사전이 작아서 몫의 절대값은 뜻이 없다
  · 이름을 붙인 축은 전부 재는 축이다(compose 의 계약을 여기서도 지킨다)

실행: python3 tests/test_voice.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import voice                                              # noqa: E402

fails = []


def ok(cond, label):
    print(("  OK  " if cond else "  실패 ") + label)
    if not cond:
        fails.append(label)


print("[시제]")
past = voice.measure("그는 걸었다. 문이 닫혔다. 바람이 불었다.")
now = voice.measure("그는 걷는다. 문이 닫힌다. 바람이 분다.")
ok(past["tense_now"] == 0.0, "과거형만 쓰면 0")
ok(now["tense_now"] == 1.0, "현재형만 쓰면 1")
ok("tense_now" not in voice.measure("문. 바람. 빛."),
   "시제 자국이 없으면 축을 안 낸다  ← 0 은 '안 쓴다' 라는 거짓말이다")

print("\n[인칭]")
ok(voice.measure("나는 걸었다. 내가 보았다.")["person_1"] == 1.0, "'나' 만 쓰면 1")
ok(voice.measure("그는 걸었다. 그녀가 보았다.")["person_1"] == 0.0, "'그' 만 쓰면 0")
ok("person_1" not in voice.measure("문이 닫혔다."), "인칭 자국이 없으면 안 낸다")

print("\n[비유 · 부정 · 피동]")
ok(voice.measure("눈처럼 희었다.")["simile"] > 0, "'처럼' 을 센다")
ok(voice.measure("불빛이 물결 같았다.")["simile"] > 0, "'같았다' 도 센다")
ok(voice.measure("그는 걸었다.")["simile"] == 0.0, "안 빗대면 0")
ok(voice.measure("가지 않았다.")["neg"] > 0, "'-지 않' 을 센다")
ok(voice.measure("문이 닫혔다. 그는 열었다.")["passive"] > 0, "피동을 센다")

print("\n[감각 -- 비로만 본다]")
m = voice.measure("빛이 보였다. 빛이 눈에 들어왔다. 소리가 들렸다.")
ok(abs(sum(v for k, v in m.items() if k.startswith("sense_")) - 1.0) < 1e-6,
   "다섯 감각의 합이 1이다  ← 사전 크기에 안 흔들린다")
ok(m["sense_eye"] > m["sense_ear"], "눈이 귀보다 많으면 그렇게 나온다")
ok(not any(k.startswith("sense_") for k in voice.measure("그는 갔다.")),
   "감각 자국이 하나도 없으면 안 낸다")

print("\n[그 밖]")
ok(voice.measure("그러나 그는 갔다.")["conj_head"] == 1.0, "문두 접속부사를 센다")
ok(voice.measure("그는 갔다.")["conj_head"] == 0.0, "가운데 있는 것은 안 센다")
ok(voice.measure("그날 갔다. 이튿날 왔다.")["timeword"] > 0, "때를 가리키는 말을 센다")
ok(voice.measure("갔다. 왔다.")["nosubj"] == 1.0, "주격 표지가 없으면 주어 없음")
ok(voice.measure("그는 갔다.")["nosubj"] == 0.0, "주격 표지가 있으면 아니다")
ok(voice.measure("두근두근 뛰었다.")["mimic"] > 0, "첩어를 센다")

print("\n[대사 안의 높임 -- 서술의 말투와 따로 본다]")
# A 는 서술을 낮춤으로 쓰면서 대사는 높임으로 쓴다. 잔차에서 어요·예요·지요·에요·
# 아요 가 1,091 대 0 으로 나왔는데 재는 축이 없었다. polite 는 서술문만 본다.
_t = '그는 걸었다.\n"어디 가세요?"\n"그냥요." 하고 그가 말했다.\n"어디 가?"\n'
_m = voice.measure(_t)
ok(abs(_m["talk_polite"] - 2 / 3) < 0.01,
   f"높임 대사의 몫을 센다 ({_m['talk_polite']:.2f})")
ok('"그냥요." 하고' in _t and _m["talk_polite"] > 0.5,
   "닫는 따옴표 앞에서 끝나는 '요' 도 센다  ← 지문이 붙은 대사를 반말로 셌다")
ok(_m["polite"] == 0.0, "서술문은 낮춤 그대로  ← 대사의 말투와 섞지 않는다")
ok("talk_polite" not in voice.measure("그는 걸었다."),
   "대사가 없으면 안 낸다  ← '반말만 쓴다' 와 '대사가 없다' 는 다르다")
ok(_m["say_verb"] > 0, "'말했다' 로 발화를 대는 횟수를 센다")

print("\n[배선]")
ok(voice.measure("") == {}, "글이 없으면 빈 것을 돌려준다  ← 0 으로 채우지 않는다")
ok(set(voice.SAY) >= set(voice.axes()), "이름 없는 축이 없다")
from novel import compose                                            # noqa: E402
ok(all(compose.SAY.get(k) for k in voice.axes()),
   "프롬프트가 쓸 이름이 다 있다(compose.SAY)")
from novel import dyn                                                # noqa: E402
_d = dyn.load()
ok(all("aim" in (_d.get(k) or {}) for k in voice.axes()),
   "어떻게 맞추는지도 데이터로 있다(directives.json)")

print()
if fails:
    print(f"목소리: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("목소리: 시제 · 인칭 · 비유 · 감각 · 배선 -- 통과")
