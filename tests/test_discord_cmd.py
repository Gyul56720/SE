"""디스코드 고정 명령 -- **에이전트를 안 거치고, 사용자 글이 명령줄에 안 낀다.**

왜 이 검사가 있나: 봇은 모든 메시지를 임의 셸을 가진 에이전트에 넘긴다. 그래서
"라노벨 상황극 써 줘" 가 `scripts/drift.sh` 를 20줄짜리 촌극으로 덮었다(4cd4473).
배포판이란 남이 같은 말을 쳤을 때 같은 일이 나는 것이고, 그 보장이 여기 있다.

실행: python3 tests/test_discord_cmd.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import discord_cmd as C                                    # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


class Runner:
    """가짜 실행기. **아무것도 안 돌린다** -- 무엇을 부르려 했는지만 잡아 둔다."""

    def __init__(self, rc=0, out="돌았다"):
        self.rc, self.out, self.calls = rc, out, []

    def __call__(self, args, env):
        self.calls.append((list(args), dict(env)))
        return self.rc, self.out


print("[안 뺏는다] 모르는 말은 예전처럼 에이전트로 간다")
for _t in ("안녕", "소설 써줘", "라노벨 상황극 써 줘", "", "!소설이야기", "!소설가", "!소설을 써줘"):
    ok(C.parse(_t) is None, f"{_t!r} 은 이 파일이 안 건드린다")
ok(C.run("라노벨 상황극 써 줘") is None, "run 도 None -- 봇이 넘겨받는다")
ok(C.parse(None) is None, "문자열이 아니어도 안 죽는다")

print("\n[도움말]")
ok(C.parse("!소설") == {"cmd": "help"}, "접두사만 치면 도움말")
_h = C.run("!소설")
ok("시작" in _h and "이어" in _h, "무엇을 할 수 있는지 적혀 있다")
ok("Gemini" in _h, "산문을 누가 쓰는지 밝힌다  ← 배포판이면 받는 사람이 알아야 한다")
ok("몰라" in str(C.parse("!소설 뭐래")), "모르는 말은 모른다고 한다")
ok("`뭐래` 는 모르는 말" in C.run("!소설 뭐래"), "무엇을 못 알아들었는지 짚는다")

print("\n[뜯기] 문체 · 갈래 · 글자수")
_g = C.parse("!소설 시작 만화 라노벨 8000")
ok(_g["cmd"] == "start" and _g["문체"] == "manga" and _g["갈래"] == "lanobe" and _g["글자수"] == 8000,
   f"셋을 다 뜯는다: {_g}")
ok(C.parse("!소설 시작")["글자수"] == 0, "생략하면 비운다 -- drift.sh 의 기본값이 이긴다")
ok(C.parse("!소설 시작 manga")["문체"] == "manga", "영문 이름도 받는다")
ok(C.parse("!소설 이어 50000")["cmd"] == "go", "이어 = go")
ok(C.parse("!소설 재기")["cmd"] == "재기", "재기는 drift.sh 가 아니다")

print("\n[화이트리스트] 아는 이름만 넘어간다")
_g = C.parse("!소설 시작 없는문체 없는갈래")
ok(_g["문체"] == "" and _g["갈래"] == "", "모르는 문체·갈래는 그냥 버린다")
_, _env = C.argv(_g)
ok(_env == {}, f"환경변수에 안 실린다: {_env}")
ok(C.parse("!소설 시작 99")["글자수"] == 0, "세 자리 미만은 글자수로 안 본다")
ok(C.parse("!소설 시작 12345678")["글자수"] == 0, "일곱 자리를 넘으면 안 본다")

print("\n[주입] **사용자 글이 명령줄에 끼지 않는다**")
for _bad in ("!소설 시작 ; rm -rf /", "!소설 시작 $(whoami)", "!소설 시작 `id`",
             "!소설 시작 만화&&curl", "!소설 이어 8000; cat /etc/passwd"):
    _args, _env = C.argv(C.parse(_bad))
    _joined = " ".join(_args) + " " + " ".join(_env.values())
    ok(all(x not in _joined for x in (";", "$", "`", "&&", "|")),
       f"{_bad[6:26]!r} -> {_args[1:]} {_env}")
_args, _ = C.argv(C.parse("!소설 시작 만화 8000"))
ok(isinstance(_args, list) and all(isinstance(x, str) for x in _args),
   "argv 는 리스트다 -- 셸 문자열을 짓지 않는다")
ok(_args[0].endswith("scripts/drift.sh"), f"부르는 것은 drift.sh 하나: {_args[0]}")

print("\n[부르기] 무엇을 어떻게 부르는가")
_r = Runner()
_out = C.run("!소설 시작 만화 라노벨 8000", _r)
ok(len(_r.calls) == 1, "한 번만 부른다")
_args, _env = _r.calls[0]
ok(_args[1:] == ["start", "8000"], f"인자: {_args[1:]}")
ok(_env == {"STYLE": "manga", "GENRE": "lanobe"}, f"환경변수: {_env}")
ok(_out == "돌았다", "돌아온 것을 그대로 보여 준다")

_r2 = Runner(rc=1, out="원고가 없다")
ok("(끝난 값 1)" in C.run("!소설 읽기", _r2), "실패하면 끝난 값을 같이 말한다  ← 조용히 성공한 척하지 않는다")

_r3 = Runner()
C.run("!소설 재기", _r3)
ok(_r3.calls[0][0][:3] == ["python3", "-m", "novel.manga"], f"재기는 만화 눈금: {_r3.calls[0][0][:3]}")

print("\n[공개 채널] 읽는 것만 -- 아무나 남의 런을 멈추면 안 된다")
_r4 = Runner()
for _v, _label in (("멈춤", "stop"), ("시작", "start"), ("이어", "go"), ("보내기", "send")):
    _out = C.run(f"!소설 {_v}", _r4, allow_write=False)
    ok("읽는 것만 된다" in _out, f"'{_v}' 는 공개 채널에서 막힌다")
ok(len(_r4.calls) == 0, "막힌 명령은 **아무것도 안 부른다**")
for _v in ("상태", "읽기", "각본", "세계", "남은것", "설정집", "재기"):
    _r5 = Runner()
    C.run(f"!소설 {_v}", _r5, allow_write=False)
    ok(len(_r5.calls) == 1, f"'{_v}' 는 공개 채널에서도 된다")
ok(C.run("!소설", Runner(), allow_write=False).startswith("**소설"), "도움말은 어디서나 나온다")
_r6 = Runner()
ok("읽는 것만" not in C.run("!소설 멈춤", _r6), "관리 채널에서는 그대로 된다")
ok(len(_r6.calls) == 1, "관리 채널은 부른다")

print("\n[상한] 디스코드 한 메시지")
ok(len(C.clip("가" * 5000)) <= 1950, "1,900자 안으로 줄인다")
ok(C.clip("가" * 5000).endswith("가"), "**뒤를 남긴다** -- 결과는 끝에 있다")
ok("앞을 줄였다" in C.clip("가" * 5000), "줄였다고 말한다")
ok(C.clip("짧다") == "짧다", "짧으면 그대로")
ok(C.clip("") == "(빈 것)", "빈 것도 답이 있다 -- 디스코드는 빈 메시지를 못 보낸다")

print("\n[모든 명령이 뜯긴다]")
for _v in C.VERBS:
    _g = C.parse(f"!소설 {_v}")
    ok(_g is not None and _g["cmd"] != "help", f"'{_v}'")

print("\n[배선] 봇이 실제로 이것을 부르는가 -- 그리고 **셸 길이 안 끊겼는가**")
# 봇 자체는 임포트 못 한다(discord · langgraph · .env 가 있어야 한다). 그래서 원문을 본다 --
# `tests/test_drift_trigger.py` 가 drift.sh 를 보는 것과 같은 방식이다.
# 배선이 dispatch.py 로 옮겨갔다(고정 명령이 둘이 되면서). 그래서 두 단을 본다:
# 봇 -> dispatch, dispatch -> 이 모듈. 어느 단이 끊겨도 !소설 이 통째로 죽는데,
# 그것은 화면에서 '봇이 멍청해졌다' 로만 보인다.
_bot = (REPO / "discord_bot_server.py").read_text(encoding="utf-8")
import dispatch                                                        # noqa: E402
ok(C in getattr(dispatch, "명령들", ()), "봇이 이 모듈을 들여온다 (dispatch.명령들 안에)")
ok("asyncio.to_thread(dispatch.run" in _bot,
   "on_message 가 **딴 실에서** 부른다  ← subprocess 가 게이트웨이를 막으면 봇이 통째로 멎는다")
ok("may_write = admin and (not ADMIN_ALLOWED_USER_IDS" in _bot,
   "쓸 수 있는가를 관리 채널 + 화이트리스트로 정한다")
ok("dispatch.run, message.content, None, may_write" in _bot,
   "그 값을 그대로 넘긴다  ← 계산해 놓고 안 쓰면 아무 뜻이 없다")

# **이것이 이 검사의 핵심이다.** 고정 명령을 앞에 세우면서 에이전트 길을 끊으면,
# 셸로 VM 을 만지던 일이 통째로 막힌다. 사용자가 그 길을 계속 쓴다.
ok("_handle_admin_message(message)" in _bot, "관리 에이전트 길이 살아 있다  ← 셸 접근")
ok("_handle_public_message(message)" in _bot, "공개 에이전트 길이 살아 있다")
_after = _bot.split("if reply is not None:", 1)[-1]
ok("_handle_admin_message" in _after and "_handle_public_message" in _after,
   "**명령을 못 알아들으면 아래로 떨어진다** -- 모르는 말은 예전대로 에이전트가 받는다")

print()
if fails:
    print(f"디스코드 명령: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("디스코드 명령: 안 뺏는다 · 화이트리스트 · 주입 막힘 · 부르기 · 상한 -- 통과")
