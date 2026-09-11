"""도구 호출 수를 **코드가 센다** -- 중계가 스스로 줄을 적는 네 도구만 세던 것을 붙든다.

실측 2026-09-11: 사용자가 "도구 호출이 계속 0 (모델 바꿀 때만 1)" 이라 했다. 중계는
run_shell · run_experiment · edit_file · delegate 와 모델 전환 줄만 적고 있었으므로,
에이전트가 search_memory · read_file 을 불렀어도 0 으로 보였고, 정말 0 이어도 '도구 1'
(모델 전환 줄)로 보였다. 둘 다 거짓이다.

붙드는 것: (1) invoke 결과의 messages 에서 마지막 사람 말 뒤의 tool_calls 만 센다,
(2) 스스로 줄을 안 적는 도구는 🔧 줄로 중계되고 스스로 적는 도구는 두 번 안 센다,
(3) 중계판의 '도구 N개' 는 도구 줄만 세고 모델 전환·되묻기 줄은 안 센다, (4) 되묻기
규칙 -- 실측 낌새가 있거나 답에 수가 셋 이상이면 되묻고, 인사말은 안 되묻는다,
(5) 배선 -- bot_tools 가 턴마다 세고 서버가 도구 0회 답을 한 번 되묻는다(원문 검사).

LLM·디스코드 없이 돈다. 실행: python3 tests/test_도구수.py
"""
from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path
from types import SimpleNamespace as NS

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import relay  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 사람(t):
    return NS(type="human", content=t, tool_calls=[])


def 모델(t="", *calls):
    return NS(type="ai", content=t, tool_calls=[{"name": c, "args": {}, "id": c} for c in calls])


def 도구(name):
    return NS(type="tool", content="...", name=name, tool_calls=None)


print("== 마지막 사람 말 뒤만 센다 ==")
msgs = [사람("앞 물음"), 모델("", "run_shell"), 도구("run_shell"), 모델("앞 답"),
        사람("이번 물음"), 모델("", "search_memory", "read_file"), 도구("search_memory"), 도구("read_file"),
        모델("", "run_shell"), 도구("run_shell"), 모델("이번 답")]
ok(relay.도구호출들(msgs) == ["search_memory", "read_file", "run_shell"],
   f"이번 턴의 도구만 순서대로 ({relay.도구호출들(msgs)})")
ok(relay.도구호출들([사람("x"), 모델("지식으로 답")]) == [], "도구 없는 턴은 빈 목록")
ok(relay.도구호출들([]) == [] and relay.도구호출들(None) == [], "빈 입력에 안 죽는다")
ok(relay.도구호출들([사람("x"), NS(type="ai", content="", tool_calls=[NS(name="delegate")])]) == ["delegate"],
   "tool_calls 가 객체여도 이름을 읽는다")

print("\n== 턴기록: 🔧 줄은 스스로 안 적는 도구만 ==")
편집된 = []


async def 편집(text):
    편집된.append(text)


async def 본():
    loop = asyncio.get_running_loop()
    판 = relay.중계판(편집, loop, 최소간격=0.01)

    def 실행기():
        relay.등록(판)
        try:
            이름들 = relay.턴기록("t1", msgs)
            relay.적기(relay.줄("python3 x.py", 0, 0.2))      # run_shell 이 스스로 적는 줄
            relay.적기("↻ 모델 전환 → gemma (앞 1개 후보 막힘)")
            relay.적기("↺ 도구 0회 -- 실측을 요구하고 한 번 되묻는다")
            return 이름들
        finally:
            relay.해제()
    이름들 = await loop.run_in_executor(None, 실행기)
    await asyncio.sleep(0.1)
    await 판.마무리()
    return 판, 이름들

판, 이름들 = asyncio.run(본())
ok(relay.마지막도구["t1"] == ["search_memory", "read_file", "run_shell"], "thread_id 별로 이번 턴 도구가 남는다")
ok([x for x in 판.줄들 if x.startswith("🔧")] == ["🔧 search_memory", "🔧 read_file"],
   f"🔧 줄은 스스로 안 적는 도구만 -- run_shell 은 두 번 안 센다 ({판.줄들})")
ok(판.도구수 == 3, f"**'도구 N개' 는 도구 줄만 센다** -- 모델 전환·되묻기 줄은 제외 ({판.도구수})")
ok("도구 3개" in 편집된[-1] and "✅ 끝" in 편집된[-1] and "호출 없음" not in 편집된[-1], "마무리 머리에 도구 3개")

print("\n== 도구 0회 마무리는 그렇다고 말한다 (모델 전환 줄이 있어도) ==")


async def 본2():
    loop = asyncio.get_running_loop()
    판 = relay.중계판(편집, loop, 최소간격=0.01)
    판.적기("↻ 모델 전환 → gemma (앞 1개 후보 막힘)")
    await asyncio.sleep(0.05)
    await 판.마무리()
    return 판

판2 = asyncio.run(본2())
ok(판2.도구수 == 0 and "도구 호출 없음" in 편집된[-1] and "도구 0개" in 편집된[-1],
   f"**모델 전환만 있으면 도구 0개 · '호출 없음'** -- 예전엔 '도구 1개' 로 보였다 ({편집된[-1][:60]!r})")

print("\n== 되묻기 규칙 ==")
ok(relay.실측필요("chainlink 시세를 mathdrift 로 방정식 만들고 뉴스 시나리오 줘", "…"), "실측 낌새(시세·뉴스·만들어)면 되묻는다")
ok(relay.실측필요("이거 어때", "LINK 는 3.2% 올라 14.1 달러, 거래량 120만"), "물음이 밋밋해도 답에 수가 셋 이상이면 되묻는다")
ok(not relay.실측필요("안녕, 고마워", "천만에요"), "인사말은 안 되묻는다")
ok("도구를 한 번도 안 불렀다" in relay.되묻는말 and "실측 불필요" in relay.되묻는말,
   "되묻는 말은 실측을 요구하되 필요 없으면 그렇다고 적을 길을 준다")
ok("실측 불필요가 아니다" in relay.되묻는말 and "dig/harvest.py" in relay.되묻는말 and "--진단" in relay.되묻는말,
   "**오류·실패는 실측 불필요가 아니다** -- 진단 도구와 제2의 뇌로 (실측: 5.7.8 에 '정책 때문' 이라 하고 멈췄다)")

print("\n== 배선 (봇은 여기서 임포트 못 하므로 원문) ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok(_도구.count("relay.턴기록(base_thread_id, result[\"messages\"])") == 2,
   "invoke_with_recovery 가 두 invoke 자리 모두에서 턴을 센다")
ok("relay.마지막도구.get(thread_id)" in _서버 and "relay.되묻는말" in _서버 and "relay.도구없음표" in _서버,
   "run_admin_agent 가 도구 0회 답을 되묻고, 그래도 0 이면 답에 적는다")
ok(_서버.index("relay.실측필요(prompt, reply)") < _서버.index("reply={reply[:200]!r}"),
   "되묻기가 답을 돌려주기 전에 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("도구수: 턴 세기 · 🔧 중계 · 도구 N개 · 되묻기 규칙 · 배선 -- 통과")
