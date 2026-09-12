"""relay(도구 중계)를 **진짜 asyncio 루프 위에서 실제로 돌려** 붙든다.

붙드는 것: (1) 실행기 스레드에서 적기() 한 것이 루프의 편집기로 건너간다(스레드->루프
다리), (2) 편집을 몰아서 한다 -- 적기 N번에 편집 N번이 아니다(레이트리밋 회피),
(3) 상한을 넘으면 앞을 줄이고 뒤를 남긴다, (4) 판이 안 묶인 스레드의 적기는 아무 일도
안 한다(중계는 부수 기능 -- 도구를 죽이면 안 된다), (5) 마무리가 '도구 호출 없음' 을
말한다, (6) `!중계` 는 관리 채널만 켜고 끈다, (7) 봇 배선(도구 세 자리 · 서버의 판 생성과
마무리 · `import time`) -- 봇은 여기서 임포트 못 하므로 원문을 본다.

LLM·디스코드 없이 돈다. 실행: python3 tests/test_relay.py
"""
from __future__ import annotations

import asyncio
import sys
import threading
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import relay  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


# 루프를 딴 스레드에서 돌린다 -- 봇에서 도구는 실행기 스레드, 편집은 이벤트 루프다.
loop = asyncio.new_event_loop()
루프스레드 = threading.Thread(target=loop.run_forever, daemon=True)
루프스레드.start()

편집기록: list = []


async def 가짜편집(text: str) -> None:
    편집기록.append(text)


try:
    print("== 스레드에서 적은 것이 루프의 편집기로 건너간다 ==")
    판 = relay.중계판(가짜편집, loop, 최소간격=0.3, 상한=400)

    def 도구스레드():
        relay.등록(판)
        try:
            for i in range(6):
                relay.적기(relay.줄(f"python3 일{i}.py", 0, 0.1 * i))
                time.sleep(0.02)
        finally:
            relay.해제()

    t = threading.Thread(target=도구스레드)
    t.start()
    t.join()
    time.sleep(0.8)                                 # 몰아둔 편집이 돌 시간
    ok(편집기록 and "일5.py" in 편집기록[-1], f"마지막 편집에 마지막 줄이 있다 ({len(편집기록)}회 편집)")
    ok(len(편집기록) < 6, f"**적기 6번에 편집 {len(편집기록)}번 -- 몰아서 한다**")
    ok("도구 6개" in 편집기록[-1], "머리에 도구 수가 적힌다")

    print("\n== 상한을 넘으면 앞을 줄이고 뒤를 남긴다 ==")
    for i in range(30):
        판.적기(relay.줄("x" * 100 + f"_{i}", 0, 1.0))
    time.sleep(0.6)
    본 = 판.본문()
    ok(len(본) <= 400 + 40 and "앞을 줄였다" in 본 and "_29" in 본,
       f"상한 안에서 뒤가 남는다 ({len(본)}자)")

    print("\n== 마무리 ==")
    asyncio.run_coroutine_threadsafe(판.마무리(), loop).result(timeout=2)
    ok(편집기록[-1].startswith("✅ 끝"), "마무리가 마지막 편집을 한다")
    빈판 = relay.중계판(가짜편집, loop)
    asyncio.run_coroutine_threadsafe(빈판.마무리(), loop).result(timeout=2)
    ok("도구 호출 없음" in 편집기록[-1] and "의심" in 편집기록[-1],
       "**도구 없이 끝나면 그렇다고 말한다** -- 실측 없는 답을 의심하게")

    print("\n== 판이 안 묶인 스레드의 적기는 아무 일도 안 한다 ==")
    앞 = len(편집기록)
    relay.적기("이건 어디에도 안 간다")
    time.sleep(0.4)
    ok(len(편집기록) == 앞, "묶이지 않았으면 조용하다 (도구를 죽이지 않는다)")

    print("\n== 편집이 죽어도 답은 산다 ==")

    async def 죽는편집(text):
        raise RuntimeError("메시지가 삭제됐다")

    죽판 = relay.중계판(죽는편집, loop, 최소간격=0.0)
    죽판.적기("x")
    time.sleep(0.3)
    asyncio.run_coroutine_threadsafe(죽판.마무리(), loop).result(timeout=2)
    ok(True, "편집 실패가 예외로 안 올라온다")
finally:
    loop.call_soon_threadsafe(loop.stop)

print("\n== !중계 명령 ==")
relay.상태["켜짐"] = False
ok(relay.run("!중계 켜기", None, False) is not None and "관리 채널" in relay.run("!중계 켜기", None, False),
   "공개 채널은 못 켠다")
ok(not relay.상태["켜짐"], "그래서 안 켜졌다")
ok("켜짐" in relay.run("!중계 켜기", None, True) and relay.상태["켜짐"], "관리 채널은 켠다")
ok("켜짐" in relay.run("!중계 상태", None, False), "상태는 공개도 본다")
ok("꺼짐" in relay.run("!중계 끄기", None, True) and not relay.상태["켜짐"], "끈다")
ok(relay.run("!중계방송 해줘", None, True) is None, "붙여 쓴 `!중계방송` 은 명령이 아니다")
ok(relay.run("아무 말", None, True) is None, "모르는 말은 None")

print("\n== 봇 배선 (원문으로 본다 -- 봇은 여기서 임포트 못 한다) ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("import time" in _도구.split("def ", 1)[0], "**bot_tools 가 time 을 들인다** -- 없으면 첫 run_shell 에서 NameError 로 봇이 죽는다")
_런셸 = _도구.split("def run_shell", 1)[-1].split("\n@tool", 1)[0]
ok("relay.적기(relay.줄(" in _런셸, "run_shell 이 중계에 적는다")
_실험 = _도구.split("def run_experiment", 1)[-1].split("\n@tool", 1)[0]
ok("relay.적기(relay.줄(" in _실험, "run_experiment 이 중계에 적는다")
ok("모델 전환" in _도구, "모델 전환도 중계에 적는다")
ok('relay.상태["켜짐"]' in _서버 and "relay.중계판(" in _서버, "서버가 켜짐이면 판을 만든다")
ok("run_admin_agent, content, thread_id, 중계판" in _서버, "판을 실행기 스레드로 넘긴다")
ok("await 중계판.마무리()" in _서버, "답이 오면 마무리한다")
ok("relay.등록(중계판)" in _서버 and "relay.해제()" in _서버, "실행기 스레드에서 묶고 푼다")
import dispatch  # noqa: E402
ok(relay in dispatch.명령들, "dispatch 에 걸려 있다")

print("\n== 배경 보고가 **어느 판인지** 말한다 ==")
# 실측 2026-09-11: 같은 오류가 두 번 왔을 때 '고침이 아직 안 왔나' 인지 '고침이 틀렸나'
# 인지 로그만으로 못 갈랐다. 트레이스백 줄번호를 옛 커밋과 맞춰 보고서야 알았다.
_판 = relay.어느판()
ok(_판 and len(_판) >= 7 and " " not in _판, f"지금 도는 판의 커밋을 안다 ({_판!r})")
ok(relay.어느판("/tmp") == "", "저장소가 아니면 빈 말 -- 지어내지 않는다")
import time as _t
_보 = relay.배경보고({"무엇": "improve.run", "로그": "/tmp/없는로그", "시작": _t.monotonic() - 9,
                    "명령": "python3 -m improve.run"})
ok(f"판 {_판}" in _보.splitlines()[0], f"끝났다는 줄에 판이 적힌다 ({_보.splitlines()[0][:70]})")

print("\n== 배경 로그는 **이 실행이 쓴 부분만** 읽는다 (덧쓰기의 옛 트레이스백을 안 본다) ==")
# 실측 2026-09-12: 새 실행은 멀쩡히 끝났는데 옛 트레이스백을 읽고 "터졌다" 고 했고, 진단은
# 그 옛 줄번호로 "도는 코드가 낡았다" 고 했다. 전부 옛 글이었다.
import tempfile as _tf, os as _os
_d = _tf.mkdtemp(prefix="test-bg-")
_log = _os.path.join(_d, "x.log")
with open(_log, "w", encoding="utf-8") as _f:
    _f.write('Traceback (most recent call last):\n  File "improve/run.py", line 410, in 사용자개선\n'
             "ModuleNotFoundError: No module named 'plan'\n")
_e = relay.배경등록("x", _log, "python3 x", 시작바이트=_os.path.getsize(_log))   # 띄우는 쪽이 열기 전에 잰 자리
relay.배경꺼내기()
with open(_log, "a", encoding="utf-8") as _f:
    _f.write("개선 부탁: 핸드폰\n  판정: **판열림**\n")
ok(relay.배경로그(_e).startswith("개선 부탁"), "배경로그 는 이 실행이 쓴 부분만 돌려준다")
ok(relay.터졌나(_e) == (False, ""), "**옛 트레이스백으로 '터졌다' 고 하지 않는다**")
ok("ModuleNotFoundError" not in relay.배경보고(_e) and "판열림" in relay.배경보고(_e), "끝 보고도 이 실행의 줄만")
_e2 = relay.배경등록("y", _log, "python3 y")
relay.배경꺼내기()
ok(_e2["시작바이트"] == 0 and relay.터졌나(_e2)[0] is True,
   "**안 주면 0 -- 전부 본다.** 등록 시점에 재면 자식이 이미 쓴 줄이 잘린다(띄운 뒤 등록하므로)")
import shutil as _sh; _sh.rmtree(_d, ignore_errors=True)
# 실측 2026-09-12(VM): `-m improve.run` 으로 바꾸자 pgrep 이 "improve/run.py" 를 못 찾아 20초 만에 '끝'.
_e3 = relay.배경등록("improve/run.py", _log if False else "/tmp/x.log", "python3 -m improve.run", 0, 찾을말="improve.run")
relay.배경꺼내기()
ok(_e3["찾을말"] == "improve.run" and _e3["무엇"] == "improve/run.py", "보이는 이름과 pgrep 으로 찾는 이름을 가른다")
import subprocess as _sp
_pr = _sp.Popen([sys.executable, "-c", "import time; time.sleep(8)  # improve.run 흉내"], stdout=_sp.DEVNULL)
try:
    ok(relay.배경끝났나({"무엇": "improve/run.py", "찾을말": "improve.run 흉내"}) is False,
       "**찾을말로 살아 있는지 본다** -- 보이는 이름으로 보면 살아 있는 일을 죽었다고 한다")
    ok(relay.배경끝났나("improve/run.py") is True, "(견줌) 보이는 이름으로는 못 찾는다 -- 그것이 사고였다")
finally:
    _pr.kill(); _pr.wait()
_bot4 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("relay.배경끝났나, 배경)" in _bot4, "봇이 등록 사전(찾을말)으로 본다")
_ed = (뿌리 / "eval" / "discord_cmd.py").read_text(encoding="utf-8")
ok("찾을말=찾을것" in _ed, "띄우는 쪽이 모듈 꼴 이름을 찾을말로 넘긴다")
ok("시작바이트 = 로그파일.stat().st_size" in _ed and ", 시작바이트, " in _ed, "띄우는 쪽이 열기 전 크기를 재서 넘긴다")
_bot2 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("relay.배경로그, 배경" in _bot2, "봇이 증거로 **이 실행의 출력**을 넘긴다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("relay: 스레드->루프 · 몰아서 편집 · 꼬리 유지 · 마무리 · 명령 경계 · 봇 배선 -- 통과")
