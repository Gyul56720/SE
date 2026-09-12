"""dispatch.py -- 고정 명령의 배선을 붙든다.

붙드는 것: (1) 모르는 말은 None 이라 에이전트 길을 뺏지 않는다, (2) !소설 이 예전
그대로 들린다(배선을 옮기다 떨어뜨리면 배포판 명령이 통째로 죽는데, 그것은 화면에서
'봇이 멍청해졌다' 로만 보인다), (3) !실험 은 공개 채널에서 읽기만 되고 관리 채널에서
argv 배열로 격리 러너를 부른다 -- 셸 문자열이 없다.

LLM·네트워크·실제 실행 없이 돈다(runner 주입). 실행: python3 tests/test_dispatch.py
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import dispatch  # noqa: E402
from sandbox import discord_cmd as 실험 # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


불림 = []


def 가짜러너(argv, 초=0, **_):
    불림.append((list(argv), 초))
    return 0, "가짜 결과"


print("== 모르는 말은 에이전트로 ==")
ok(dispatch.run("아무 말이나") is None, "일반 문장은 None -- 에이전트 길을 안 뺏는다")
ok(dispatch.run("") is None, "빈 말도 None")
ok(dispatch.run("!모르는명령 하나") is None, "모르는 !접두사도 None")
ok(dispatch.run("!실험실은 어디에 있나") is None,
   "붙여 쓴 것은 남의 말이다 -- `!실험실` 은 명령이 아니다")

print("\n== !소설 이 예전 그대로 들린다 ==")
답 = dispatch.run("!소설")
ok(답 is not None and "소설" in 답, f"도움말이 나온다 ({(답 or '')[:40]!r})")

print("\n== !실험 -- 도움말과 경계 ==")
답 = dispatch.run("!실험")
ok(답 is not None and "깨끗한 판" in 답, "도움말이 나온다")
답 = dispatch.run("!실험 이상한말")
ok(답 is not None and "모르는 말" in 답, "모르는 하위 명령은 도움말로")
답 = dispatch.run("!실험 검사 dig", allow_write=False)
ok(답 is not None and "관리 채널" in 답 and not 불림,
   "공개 채널에서는 안 돌린다 -- 러너가 안 불렸다")

print("\n== !실험 검사/게이트 -- argv 배열만, 셸 문자열 없음 ==")
답 = dispatch.run("!실험 검사 dig", runner=가짜러너, allow_write=True)
ok(len(불림) == 1 and 불림[0][0] == ["bash", "scripts/tests.sh", "-k", "dig"],
   f"검사가 argv 배열로 넘어간다 ({불림})")
ok(답 is not None and "가짜 결과" in 답, "러너의 결과가 답이 된다")
불림.clear()
답 = dispatch.run("!실험 게이트", runner=가짜러너, allow_write=True)
ok(불림 and 불림[0][0] == ["python3", "gatekeeper.py"], f"게이트도 argv 배열 ({불림})")
불림.clear()
답 = dispatch.run("!실험 검사 dig; rm -rf /", runner=가짜러너, allow_write=True)
ok(not 불림 and 답 is not None and "글자" in 답,
   "**글자꼴 밖의 <말>은 러너에 닿기 전에 거절된다**")
답 = dispatch.run("!실험 검사", runner=가짜러너, allow_write=True)
ok(not 불림 and 답 is not None, "<말> 없는 전체 검사도 거절된다(6분짜리)")

print("\n== !감사 · !기억 -- 새 명령의 경계 ==")
답 = dispatch.run("!감사", allow_write=False)
ok(답 is not None and "관리 채널" in 답, "!감사 는 공개 채널에서 안 돌린다")
감사불림 = []


def 가짜감사(커밋=False):
    감사불림.append(커밋)
    return {"결과": [], "안덮임": [], "안봄": [], "변경": ["x.py"]}


답 = dispatch.run("!감사 커밋", runner=가짜감사, allow_write=True)
ok(감사불림 == [True], f"!감사 커밋 이 커밋 감사로 간다 ({감사불림})")
답 = dispatch.run("!기억")
ok(답 is not None and "깃발" in 답, "!기억 도움말이 나온다")
답 = dispatch.run("!기억 밤", allow_write=False)
ok(답 is not None and "관리 채널" in 답, "!기억 밤 은 공개 채널에서 안 돈다")
ok(dispatch.run("!기억력이 좋다") is None, "붙여 쓴 `!기억력` 은 명령이 아니다")

print("\n== 기관마다 에이전트 프롬프트에 이름이 적혀 있다 ==")
# **왜 이 검사가 있나.** 디스코드에서 사용자는 `!실험` 처럼 치지 않고 **말로 부탁한다.**
# 그러면 dispatch 가 None 을 돌려주고 에이전트가 받는데, 에이전트가 아는 것은
# ADMIN_SYSTEM_PROMPT 뿐이다 -- 거기 안 적힌 기관은 **자연어로는 영영 안 닿는다.**
# 실측: 여섯 기관을 머지한 직후가 정확히 그 상태였다(공개 채널 프롬프트는 dig/run.py 를
# 이름을 대고 시키는데, 관리 채널 프롬프트는 새 기관을 한 줄도 몰랐다). 고정 명령만
# 있으면 '배포판' 은 되지만 사람이 쓰는 길은 안 열린다.
_bot2 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
_프롬프트 = _bot2.split("ADMIN_SYSTEM_PROMPT = (", 1)[-1].split("\n)", 1)[0]
# 기관 꾸러미 -> 프롬프트에 반드시 있어야 하는 말(진입점). 새 기관을 더하면 여기도 늘어야
# 하고, 프롬프트에 안 적으면 이 검사가 빨간불을 낸다.
_적혀야 = {"sandbox": "run_experiment", "audit": "audit/run.py", "graph": "graph/night.py",
         "eval": "eval/run.py", "router": "router/check.py", "intent": "intent/store.py",
         "novel": "drift.sh",
         # 중계는 사람이 켜는 스위치다 -- 에이전트 진입점이 아니라 '안내' 가 적혀야 한다.
         "relay": "!중계 켜기",
         "delegate": "delegate 도구",
         "dig": "dig/harvest.py",
         # 열쇠는 사람이 치는 명령이다 -- 에이전트에겐 '이 꼴로 청하라' 가 적혀야 한다.
         "keys": "!열쇠 이름=값",
         "repair": "repair 도구",
         # secaudit 의 에이전트 진입점은 도구다(delegate 와 같다).
         "secaudit": "security_audit 도구",
         "codify": "codify/run.py",
         "research": "research 도구",
         # 계획은 사람이 치는 명령이다 -- 에이전트에겐 '승인은 사람만' 이 적혀야 한다.
         "plan": "!계획",
         # 자가개선도 사람이 치는 명령이다 -- 승인은 사람만.
         "improve": "!자가개선",
         # 조사는 긴 호흡 루프 -- 에이전트가 dispatch_command 로 친다. 머지는 사람.
         "investigate": "!조사 <증상> :: <재현 명령>",
         # 거짓초록 사냥은 사람이 켜는 긴 사냥이다 -- 에이전트에겐 그 명령이 적혀야 한다.
         "falsegreen": "!거짓초록"}
for _모듈 in dispatch.명령들:
    _꾸러미 = _모듈.__name__.split(".")[0]
    if _꾸러미 == "evolve":
        # 진화는 제 진입점이 self_challenge 다 -- 그 이름으로 본다.
        ok("self_challenge" in _프롬프트, "evolve: 프롬프트가 self_challenge 를 가리킨다")
        continue
    _말 = _적혀야.get(_꾸러미)
    ok(_말 is not None, f"{_꾸러미}: _적혀야 표에 올라 있다  <- 새 기관이면 여기부터 적어라")
    if _말:
        ok(_말 in _프롬프트,
           f"{_꾸러미}: 프롬프트가 `{_말}` 를 이름을 대고 시킨다  <- 없으면 자연어로 안 닿는다")
ok("승인 없는 목표는 집히지 않는다" in _프롬프트,
   "**승인 경계를 프롬프트에도 적는다** -- 에이전트가 스스로 승인하지 않게")

print("\n== 실험 모듈 단독으로도 규약을 지킨다 ==")
ok(실험.run("엉뚱한 말") is None, "접두사가 다르면 None")
ok(실험.PREFIX == "!실험", "PREFIX 가 있다 -- dispatch 규약")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("dispatch: 모르는 말 통과 · !소설 유지 · !실험 경계와 argv 배선 -- 통과")
