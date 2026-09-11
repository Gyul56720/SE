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
for cmd in ("!목표 승인 abc", "!계획 승인", "!열쇠 GITHUB_TOKEN=x"):
    돼, 왜 = dispatch.도구로쳐도되나(cmd)
    ok(not 돼 and 왜, f"거절 {cmd.split('=')[0]!r} -- {왜[:30]}")
ok(not dispatch.도구로쳐도되나("연구 해줘")[0], "`!` 없는 글은 명령이 아니다")

print("\n== 그 밖은 허용되고 실제로 답이 온다 ==")
for cmd in ("!수집 상태", "!연구 상태", "!계획 상태", "!목표 다음", "!코드화 상태", "!경로", "!진화"):
    돼, _ = dispatch.도구로쳐도되나(cmd)
    답 = dispatch.run(cmd, allow_write=True) if 돼 else None
    ok(돼 and isinstance(답, str) and 답, f"{cmd} -> 답 {len(답 or '')}자")
ok(dispatch.도구로쳐도되나("!계획 켜기 x")[0] and dispatch.도구로쳐도되나("!목표 제안 x")[0], "켜기·제안은 봇이 쳐도 된다(승인만 사람)")

print("\n== 배선 ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def dispatch_command" in _도구 and "_d.도구로쳐도되나(command)" in _도구, "도구가 경계 함수를 거친다")
ok(_서버.count(" dispatch_command,") >= 2, "임포트·ADMIN_TOOLS")
ok("dispatch_command 도구" in _서버 and "목록을 보여 주고" in _서버, "프롬프트: 목록 말고 명령을 쳐라")
ok(relay.무거운일("t-dc", [("dispatch !수집 틈으로", True)]) and not relay.무거운일("t-dc", [("dispatch !경로", True)]),
   "무거운 명령을 쳤으면 무거운 일, 조회 명령은 아니다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("dispatch_command: 승인·열쇠 거절 · 허용 명령 실답 · 배선 -- 통과")
