"""**채널 설정을 옳게 읽는가.**

    python3 tests/test_channels.py

이 검사가 붙드는 것은 **조용히 안 듣는 것**이다. 채널 id 를 잘못 넣으면 봇이 그
채널에서 아무 말도 안 하는데, 그것이 '봇이 죽었다' 와 화면에서 똑같이 보인다.
그래서 못 읽은 값을 **버리지 않고 돌려주는지**를 여기서 붙든다 -- 버리면 켜질 때
경고를 찍을 수가 없다.

`main_public.py` 는 langgraph 를 임포트하므로 그것이 안 깔린 데서는 읽어 볼 수조차
없다. 그래서 파싱을 `channels.py` 로 뺐고, 그 덕에 이 검사가 존재할 수 있다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import channels as CH                                          # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


print("── 쪼개기 ──────────────────────────────────────────────")
ok(CH.쪼개기("111") == ([111], []), "하나")
ok(CH.쪼개기("111,222") == ([111, 222], []), "쉼표로 여럿")
ok(CH.쪼개기(" 111 , 222 ") == ([111, 222], []), "공백은 턴다")
ok(CH.쪼개기("111;222") == ([111, 222], []), "세미콜론도 받는다")
ok(CH.쪼개기("") == ([], []) and CH.쪼개기(None) == ([], []), "빈 것으로 안 죽는다")
ok(CH.쪼개기("111,,222") == ([111, 222], []), "빈 칸은 건너뛴다")
ok(CH.쪼개기("111,abc") == ([111], ["abc"]),
   "**수가 아닌 것을 버리지 않고 돌려준다** -- 버리면 경고를 못 찍는다")

print()
print("── 모으기: _2 · _3 로 잇는다 ────────────────────────────")
env = {"DISCORD_PUBLIC_CHANNEL_ID": "111",
       "DISCORD_PUBLIC_CHANNEL_ID_2": "222",
       "DISCORD_PUBLIC_CHANNEL_ID_3": "333,444"}
ids, 이상 = CH.공개채널(env)
ok(ids == [111, 222, 333, 444], f"차례대로 다 모은다 ({ids})")
ok(이상 == [], "이상한 것 없음")

ok(CH.공개채널({"DISCORD_PUBLIC_CHANNEL_ID": "111",
                "DISCORD_PUBLIC_CHANNEL_ID_2": "111"})[0] == [111],
   "**겹치면 하나로** -- 같은 채널을 두 번 처리하면 답이 두 번 나간다")
ok(CH.공개채널({"DISCORD_PUBLIC_CHANNEL_ID": "111",
                "DISCORD_PUBLIC_CHANNEL_ID_2": ""})[0] == [111],
   "빈 칸은 건너뛴다 -- 안 쓰는 자리를 비워 두는 것이 흔하다")
ok(CH.공개채널({"DISCORD_PUBLIC_CHANNEL_ID": "111",
                "DISCORD_PUBLIC_CHANNEL_ID_4": "444"})[0] == [111, 444],
   "**가운데가 비어도 뒤엣것을 읽는다** -- _2 를 지우고 _4 만 남기는 일이 있다")
ok(CH.공개채널({})[0] == [], "아무것도 없으면 빈 목록")
ok(CH.공개채널({"DISCORD_PUBLIC_CHANNEL_ID_2": "222"})[0] == [222],
   "첫째가 없어도 _2 는 읽는다 -- 없다고 정하는 것은 부르는 쪽 일이다")

ids, 이상 = CH.공개채널({"DISCORD_PUBLIC_CHANNEL_ID": "111",
                        "DISCORD_PUBLIC_CHANNEL_ID_2": "채널이름"})
ok(ids == [111] and 이상 == ["DISCORD_PUBLIC_CHANNEL_ID_2=채널이름"],
   f"**어느 변수가 이상한지까지 말한다** ({이상}) -- 그래야 고칠 데를 안다")

print()
print("── 수(): **빈 값으로 봇이 죽었다** (회귀) ────────────────")
# 실측 2026-09-09: `.env` 의 DISCORD_CHANNEL_ID 를 비웠더니
#   ValueError: invalid literal for int() with base 10: ''
# 모듈 읽는 중이라 봇이 뜨자마자 죽고 systemd 가 5초마다 되살렸다(counter 13).
ok(CH.수("X", 999, {"X": ""}) == 999,
   "**빈 값은 기본으로 돌아간다** -- os.getenv 는 키가 있으면 빈 문자열을 그대로 준다")
ok(CH.수("X", 999, {}) == 999, "없어도 기본")
ok(CH.수("X", 999, {"X": "  "}) == 999, "공백만 있어도 기본")
ok(CH.수("X", 999, {"X": "42"}) == 42, "제대로 된 수는 그대로")
ok(CH.수("X", 999, {"X": "-1"}) == -1, "음수도")
CH.이상한값.clear()
ok(CH.수("X", 999, {"X": "채널이름"}) == 999, "수가 아니면 기본으로")
ok(CH.이상한값 == ["X=채널이름"],
   f"**수로 못 읽은 것을 남긴다** ({CH.이상한값}) -- 조용히 기본으로 가면 "
   "왜 딴 채널을 보는지 아무도 모른다")
CH.이상한값.clear()

봇 = (ROOT / "discord_bot_server.py").read_text(encoding="utf-8")
ok("int(os.getenv(\"DISCORD_CHANNEL_ID\"" not in 봇,
   "**옛 꼴이 안 남아 있다** -- 그 한 줄이 봇을 통째로 멎게 했다")
ok('channels.수("DISCORD_CHANNEL_ID"' in 봇, "관리 채널을 수() 로 읽는다")
ok('channels.수("DISCORD_GUILD_ID"' in 봇, "길드도")
ok("channels.이상한값" in 봇, "못 읽은 설정을 켜질 때 찍는다")
streamer = (ROOT / "log_streamer.py").read_text(encoding="utf-8")
ok("channels.수(\"DISCORD_LOG_CHANNEL_ID\"" in streamer,
   "로그 중계 채널도 -- 빈 값이면 주소가 /channels//messages 가 된다")

print()
print("── 이름 목록 ───────────────────────────────────────────")
이름 = CH.공개채널이름들()
ok(이름[0] == "DISCORD_PUBLIC_CHANNEL_ID", "첫째는 예전 이름 그대로 -- 안 깨진다")
ok("DISCORD_PUBLIC_CHANNEL_ID_2" in 이름, "_2 를 본다")
ok(len(이름) == CH.최대, f"_2 부터 _{CH.최대} 까지 ({len(이름)}개)")
ok(len(set(이름)) == len(이름), "이름이 안 겹친다")

print()
print("── 봇이 실제로 이 목록을 보는가 ─────────────────────────")
# **문자열로 붙든다.** main_public 은 langgraph 없이는 임포트가 안 되므로 여기서
# 돌려 볼 수가 없다. 그래도 `== PUBLIC_CHANNEL_ID` 로 되돌아가면 둘째 채널이
# 조용히 안 듣게 되므로, 그 줄이 그대로인지는 붙들어야 한다.
봇 = (ROOT / "discord_bot_server.py").read_text(encoding="utf-8")
ok("in main_public.PUBLIC_CHANNEL_IDS" in 봇,
   "**공개 채널을 목록으로 견준다** -- `==` 로 돌아가면 둘째 채널이 안 듣는다")
ok("== main_public.PUBLIC_CHANNEL_ID:" not in 봇, "옛 비교가 안 남아 있다")
ok("PUBLIC_CHANNEL_이상" in 봇, "못 읽은 값을 켜질 때 경고로 찍는다")
ok("이건 길드 id 다" in 봇,
   "**길드 id 를 채널 자리에 넣은 것을 짚어 준다** -- 둘 다 같은 꼴의 수라 안 갈린다")
# 실측 2026-09-09: 8월에 만든 채널들과 9월에 만든 길드를 같이 켰더니 화면은
# '감시 중' 인데 그 채널 메시지가 전부 버려지는 자리가 났다.
ok("그 채널 메시지는 전부 버려진다" in 봇,
   "**보이는 것과 듣는 것을 가른다** -- 채널이 딴 길드에 있으면 길드 필터가 조용히 "
   "다 버리는데, 화면에는 '감시 중' 이라고 찍힌다")

공개 = (ROOT / "main_public.py").read_text(encoding="utf-8")
ok("PUBLIC_CHANNEL_IDS" in 공개 and "channels.공개채널()" in 공개, "한 자리에서 읽는다")
ok("PUBLIC_CHANNEL_ID = PUBLIC_CHANNEL_IDS[0]" in 공개,
   "예전 이름을 남긴다 -- 밖에서 쓰던 자리가 안 깨지게")

보기 = (ROOT / ".env.example").read_text(encoding="utf-8")
ok("DISCORD_PUBLIC_CHANNEL_ID_2" in 보기, ".env.example 에 적혀 있다")

print()
if fails:
    print(f"채널: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("쉼표·_2 로 잇기 · 겹침 하나로 · 가운데 빈 것 · 이상한 값을 안 버림 · "
      "봇이 목록으로 견줌 -- 통과")
