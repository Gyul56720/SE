"""**진단기가 잘못 진단하지 않는가.**

    python3 tests/test_discord_check.py

실측 2026-09-09: 사용자가 `novel/discord_check.py` 를 돌렸더니

    DISCORD_BOT_TOKEN    없음

이 찍혔다. **토큰이 없는 것이 아니라 이 도구가 `.env` 를 안 읽은 것**이었다
(`discord_bot_server.py` 는 처음부터 `load_dotenv()` 를 불렀는데 여기만 빠졌다).
그래서 진단이 "봇 경로를 쓸 수 없다 -> 웹훅을 새로 만들어라" 로 갔고, 그것은 물어본
것(이 id 가 채널이 맞나)과 아무 상관이 없는 길이었다.

**잘못 답하는 장치는 없느니만 못하다** -- 통과했다는 이유로 더 마음 놓고 엉뚱한 데로
간다. 이 저장소가 `scripts/pr_merged.sh` 에서 이미 적어 둔 그 자리다.

망은 안 탄다. `call()` 을 갈아 끼워 대답을 흉내 낸다.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from novel import discord_check as DC                          # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def run(argv, 대답, env):
    """`call` 을 갈아 끼우고 돌린다. `대답` = {(method, path): (status, code, body)}"""
    진짜call, 진짜env, 진짜argv = DC.call, dict(DC.os.environ), sys.argv
    DC.call = lambda m, p, *a, **k: 대답.get((m, p), (404, 10003, {"message": "Unknown"}))
    DC.os.environ.clear()
    DC.os.environ.update(env)
    sys.argv = ["discord_check.py"] + argv
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = DC.main()
    finally:
        DC.call, sys.argv = 진짜call, 진짜argv
        DC.os.environ.clear()
        DC.os.environ.update(진짜env)
    return code, buf.getvalue()


print("── .env 를 읽는가 ──────────────────────────────────────")
원본 = (ROOT / "novel" / "discord_check.py").read_text(encoding="utf-8")
ok("load_dotenv" in 원본,
   "**`.env` 를 읽는다** -- 안 읽으면 '토큰 없음' 이 '내가 못 봤다' 와 안 갈린다")
ok("except ImportError" in 원본, "python-dotenv 가 없어도 안 죽는다")

_, out = run([], {}, {})
ok(".env" in out and "못 읽음" in out,
   "**.env 를 못 읽었으면 그렇다고 먼저 말한다** -- '없음' 이 애매해지므로")
ok("이 도구가" in out and "못 본 것일 수 있다" in out,
   "없는 것과 못 본 것을 갈라 말한다")

_, out = run([], {}, {"DISCORD_BOT_TOKEN": "t", "DISCORD_CHANNEL_ID": "1"})
ok("(셸)" in out,
   "**값이 어디서 왔는지 적는다** -- 셸인지 .env 인지에 따라 고칠 데가 다르다")

print()
print("── 길드 id 를 채널 자리에 넣은 것을 갈라 내는가 ──────────")
길드답 = {("GET", "/users/@me"): (200, None, {"username": "SE-agent"}),
          ("GET", "/channels/999"): (404, 10003, {"message": "Unknown Channel"}),
          ("GET", "/guilds/999"): (200, None, {"name": "내 서버"})}
code, out = run(["--id", "999"], 길드답, {"DISCORD_BOT_TOKEN": "t"})
ok("채널이 아니라 길드" in out,
   "**404 로 끝내지 않고 길드로도 물어본다** -- 그 한 번이 '틀린 id' 와 "
   "'자리를 잘못 넣음' 을 가른다")
ok("내 서버" in out, "어느 서버인지 이름을 보여 준다")
ok("우클릭" in out and "ID 복사" in out, "무엇을 하면 되는지 적는다")
ok(code == 1, "못 쓰는 설정이므로 끝값 1")

print()
print("── 진짜 채널이면 그렇다고 한다 ─────────────────────────")
채널답 = {("GET", "/users/@me"): (200, None, {"username": "SE-agent"}),
          ("GET", "/channels/888"): (200, None, {"name": "일반", "type": 0,
                                                 "guild_id": "999"})}
code, out = run(["--id", "888"], 채널답, {"DISCORD_BOT_TOKEN": "t"})
ok("'일반'" in out and "guild=999" in out, "채널 이름과 어느 서버인지 낸다")
ok("채널이 아니라 길드" not in out, "**멀쩡한 채널을 길드라고 하지 않는다**")
ok(code == 0, "--send 없이 여기까지면 끝값 0")

말안됨 = {("GET", "/users/@me"): (200, None, {"username": "SE-agent"}),
          ("GET", "/channels/777"): (200, None, {"name": "음성", "type": 2,
                                                 "guild_id": "999"})}
_, out = run(["--id", "777"], 말안됨, {"DISCORD_BOT_TOKEN": "t"})
ok("텍스트 채널이 아니다" in out, "텍스트 채널이 아니면 짚는다")

print()
print("── 토큰이 죽었으면 채널 탓을 안 한다 ────────────────────")
죽은답 = {("GET", "/users/@me"): (401, 0, {"message": "401: Unauthorized"})}
code, out = run(["--id", "888"], 죽은답, {"DISCORD_BOT_TOKEN": "t"})
ok("토큰 값이 틀렸거나" in out and "채널이 아니라 길드" not in out,
   "**먼저 막힌 데서 멈춘다** -- 토큰이 죽었는데 채널을 의심하면 헛수고다")
ok(code == 1, "끝값 1")

print()
print("── --id 가 없으면 예전대로 환경변수를 쓴다 ──────────────")
code, out = run([], 채널답, {"DISCORD_BOT_TOKEN": "t", "DISCORD_CHANNEL_ID": "888"})
ok("'일반'" in out, "DISCORD_CHANNEL_ID 를 그대로 본다 -- 예전 쓰임이 안 깨진다")

print()
if fails:
    print(f"discord_check: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print(".env 를 읽음 · 없는 것과 못 본 것을 가름 · 길드/채널을 갈라 냄 · "
      "먼저 막힌 데서 멈춤 -- 통과")
