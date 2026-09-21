# -*- coding: utf-8 -*-
"""**읽은 것을 잰 것으로 세지 않는가.**

실측 2026-09-21. 사용자가 8탭 FIR MAC 데이터패스(3단 파이프라인 · 0.9V · 500MHz)를
물었고 봇이 교재 여덟 칸으로 답했다 -- 되짚기 · 지배식 · 어디에 쓰나 · 언제 묶이나.
글은 훌륭했다. 그런데 f_max · 면적 · 지연이 **전부 지어낸 수**였다. 저장소에 yosys 도
verilator 도 lab/se 도 house/ 도 있는데 한 번도 안 돌았다.

    사용자: "에이전트가 안하고 LLM이 하는데?"

기존 관문이 왜 못 잡았나: `textbook()` 은 **도구다.** 부르는 순간 '도구 0회' 가 아니게
되어 되묻기가 안 걸린다. 그런데 교재를 읽은 것은 **읽은 것**이지 **잰 것**이 아니다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_잰것과읽은것.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import relay                                                          # noqa: E402
import eda_prompt as E                                                # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


실제물음 = ("8-tap FIR MAC datapath, 3-stage pipeline, 0.9V, 500MHz target. "
        "최대 클럭 주파수(f_max)와 면적(logic cells/multipliers), 지연을 설계해서 알려줘")

print("[가름] 재야 답할 수 있는 물음을 알아보는가")
ok(relay.설계요구(실제물음), "사용자가 실제로 보낸 그 물음은 '재는 물음' 이다")
ok(relay.설계요구("이 필터 RTL 합성했을 때 셀 수 얼마나 나와?"), "합성·셀 수도 재는 물음")
ok(not relay.설계요구("CDC 동기화는 왜 두 단이 필요한가?"),
   "개념 물음은 재는 물음이 아니다 -- 교재로 답하는 것이 맞다")
ok(not relay.설계요구("메타스테빌리티가 뭐야?"), "정의를 묻는 것도 아니다")
ok(not relay.설계요구("오늘 비트코인 시세 알려줘"), "회로가 아닌 것은 걸리지 않는다")

print()
print("[셈] 교재를 읽은 것은 잰 것이 아니다")
T = "t1"
relay.마지막도구[T] = ["textbook", "concept", "search_memory"]
ok(not relay.잰적있나(T), "**textbook·concept 만 부른 턴은 '안 쟀다'** ← 여기가 뚫려 있었다")
relay.마지막도구[T] = ["textbook", "synth_rtl"]
ok(relay.잰적있나(T), "합성을 돌렸으면 쟀다")
relay.마지막도구[T] = ["textbook"]
ok(relay.잰적있나(T, [("python3 house/run.py --설계 8탭 FIR", 0)]),
   "셸로 house 를 돌린 것도 잰 것이다 -- 도구 이름으로만 세지 않는다")
ok(relay.잰적있나(T, [("yosys -p 'synth' fir.v", 0)]), "yosys 를 직접 부른 것도 잰 것")
ok(not relay.잰적있나(T, [("git status", 0)]), "아무 셸 줄이나 잰 것으로 세지 않는다")

print()
print("[되묻기] 되묻는 말이 '재라' 고 말하는가")
말 = relay.설계되묻는말
for 있어야 in ("place_rtl", "synth_rtl", "house/run.py", "못 잼", "지어낸 수"):
    ok(있어야 in 말, f"되묻는 말이 `{있어야}` 를 말한다")
ok("교재 여덟 칸" in 말, "왜 그 답이 답이 아닌지를 말한다 -- 규칙만 던지지 않는다")

print()
print("[프롬프트] 애초에 교재 틀로 들어가지 않게 적혀 있는가")
ok("개념·설계 물음에는" not in E.교재규칙,
   "**교재규칙이 더는 '설계' 를 제 것이라 하지 않는다** ← 이 한 낱말이 물음을 교재로 보냈다")
ok("여덟 칸은 '왜 그런가' 의 답이지" in E.교재규칙, "설계 요청은 재라고 적혀 있다")
ok("목표 주파수를 달성 주파수로 적지 마라" in E.교재규칙,
   "500 MHz 는 요구이지 달성이 아니다 -- 그 혼동을 못 박는다")
ok("house/run.py" in E.교재규칙, "규모가 크면 어디로 넘길지까지 적혀 있다")

print()
if fails:
    print(f"실패 {len(fails)}개: {fails}")
    raise SystemExit(1)
print("잰 것과 읽은 것: 가름 · 셈 · 되묻기 · 프롬프트 -- 통과")
