"""dispatch_command(봇이 고정 명령을 직접 친다)의 경계를 붙든다 -- 승인·열쇠는 사람만.

실측 2026-09-11: 봇이 자연어 부탁에 고정 명령 **목록을 보여 주고** 끝냈다. 목록이 아니라
알맞은 명령을 제가 쳐야 한다. 단 승인 주체는 사람이다.

붙드는 것: (1) `!목표 승인`·`!계획 승인`·`!열쇠 …` 는 거절, (2) 그 밖의 고정 명령은 허용되고
dispatch.run 으로 실제 답이 온다, (3) `!` 없는 글은 명령이 아니다, (4) 배선 -- 도구·ADMIN_TOOLS·
프롬프트('목록을 보여 주고 … 하지 마라')·무거운셸 표지.

LLM·디스코드 없이 돈다. 실행: python3 tests/test_dispatch_tool.py
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import dispatch  # noqa: E402
import relay     # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== 사람만 치는 것 ==")
for cmd in ("!목표 승인 abc", "!계획 승인", "!열쇠 GITHUB_TOKEN=x", "!조사 머지 201", "!머지 201"):
    돼, 왜 = dispatch.도구로쳐도되나(cmd)
    ok(not 돼 and 왜, f"거절 {cmd.split('=')[0]!r} -- {왜[:30]}")
ok(not dispatch.도구로쳐도되나("연구 해줘")[0], "`!` 없는 글은 명령이 아니다")

print("\n== 그 밖은 허용되고 실제로 답이 온다 ==")
for cmd in ("!수집 상태", "!연구 상태", "!계획 상태", "!목표 다음", "!코드화 상태", "!경로", "!진화"):
    돼, _ = dispatch.도구로쳐도되나(cmd)
    답 = dispatch.run(cmd, allow_write=True) if 돼 else None
    ok(돼 and isinstance(답, str) and 답, f"{cmd} -> 답 {len(답 or '')}자")
ok(dispatch.도구로쳐도되나("!계획 켜기 x")[0] and dispatch.도구로쳐도되나("!목표 제안 x")[0], "켜기·제안은 봇이 쳐도 된다(승인만 사람)")

print("\n== 자연어 -> 명령: 코드가 고른다 ==")
표 = [
    ("RIS 최신 논문 좀 모아줘", "!연구 "),
    ("chainlink 시세 방법론 조사해줘", "!연구 "),
    ("arxiv 2501.12345 수식 코드로 바꿔줘", "!코드화 논문 2501.12345"),
    ("2501.12345 구현해줘", "!코드화 논문 2501.12345"),
    ("내 노트북 취약점 점검해줘", "!점검"),
    ("자가 약점 틈 메워", "!수집 틈으로"),
    ("참고 이득 좀 재줘", "!평가 과제"),
    ("게이트 검사 돌려봐", "!실험 게이트"),
    ("바뀐 파일 검사해줘", "!감사"),
    ("비용 얼마나 썼어", "!경로 요약"),
    ("간추려서 장기기억으로", "!기억 밤"),
    ("전에 뭐라고 했더라", "!기억 "),
    ("bot_tools.py 에 기능 하나 추가해줘", "!계획 켜기 "),
    ("저장소 코드 좀 고쳐줘", "!계획 켜기 "),
    ("리팩터링 해줘", "!계획 켜기 "),
]
for 말, 기대 in 표:
    명, 왜 = dispatch.고르기(말)
    ok(명 is not None and 명.startswith(기대), f"{말!r} -> {기대!r} (실제 {명!r})")

print("\n== 못 고르면 아무 명령이나 치지 않는다 ==")
for 말, 낌새 in [("오늘 날씨 어때", "못 골랐다"), ("승인해줘", "사람이 친다"), ("토큰 등록해줘", "사람이 친다"),
              ("이 명령이 오류가 나 python3 x.py", "재현 명령")]:
    명, 왜 = dispatch.고르기(말)
    ok(명 is None and 낌새 in 왜, f"{말!r} -> 못 고름 + 까닭({낌새}) [{왜[:40]}]")
ok(dispatch.고르기("!평가 과제")[0] == "!평가 과제", "`!` 로 시작하면 그대로 쓴다")
ok(dispatch.고르기("")[0] is None, "빈 말은 안 고른다")

print("\n== 배선 ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def dispatch_command" in _도구 and "_d.고르기(command)" in _도구 and "_d.도구로쳐도되나(골라진)" in _도구,
   "**도구가 자연어를 표로 고르고, 그 뒤 경계 함수를 거친다**")
ok(_서버.count(" dispatch_command,") >= 2, "임포트·ADMIN_TOOLS")
ok("dispatch_command 도구로 실행한다" in _서버 and "명령 목록을 나열하거나" in _서버, "프롬프트: 목록 말고 실행하라")
ok(relay.무거운일("t-dc", [("dispatch !수집 틈으로", True)]) and not relay.무거운일("t-dc", [("dispatch !경로", True)]),
   "무거운 명령을 쳤으면 무거운 일, 조회 명령은 아니다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("dispatch_command: 승인·열쇠 거절 · 허용 명령 실답 · 배선 -- 통과")
