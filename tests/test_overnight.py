"""야간 러너의 red-green -- **실패가 밤을 죽이지 않는가.**

drive_novel 은 에피소드가 실패하면 break 한다. 사람이 볼 때는 맞지만 자는 동안에는 그
break 하나가 남은 시간을 통째로 날린다. 여기서 검증하는 것은 문장이 아니라 그 성질이다.

LLM 없이 돈다. 실행: python3 tests/test_overnight.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import drive as D                                          # noqa: E402
from novel.overnight import Director                                  # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[폴백] claude -p 가 죽으면 Gemini 로 내려가는가")
calls = {"primary": 0, "fallback": 0}


class Boom:
    def __call__(self, prompt):
        calls["primary"] += 1
        raise RuntimeError("claude -p 실패(구독 한도 소진 가능)")


def fake_default(prompt):
    calls["fallback"] += 1
    return '{"ok": true}'


d = Director.__new__(Director)
d.primary = Boom()
d.fall_after, d.retry_after = 3, 1800.0
d.streak, d.demoted_at = 0, None
d.stats = {"primary": 0, "fallback": 0, "fail": 0}
orig = D.default_llm
D.default_llm = fake_default
try:
    for _ in range(5):
        d("프롬프트")
finally:
    D.default_llm = orig

ok(calls["primary"] == 3, f"3회 연속 실패까지만 위를 두드린다 (얻은 값 {calls['primary']})")
ok(calls["fallback"] == 5, f"그 뒤로는 전부 폴백 (얻은 값 {calls['fallback']})")
ok(d.demoted_at is not None, "강등 시각이 기록된다")
ok(d.stats["fail"] == 3, f"실패 횟수가 집계된다 ({d.stats})")

print("[복귀] 시간이 지나면 위를 다시 두드리는가")
d.demoted_at = time.time() - 2000        # retry_after(1800) 를 넘긴 과거
calls["primary"] = 0
D.default_llm = fake_default
try:
    d("프롬프트")
finally:
    D.default_llm = orig
ok(calls["primary"] == 1,
   "강등 뒤에도 주기적으로 재시도한다 -- 구독 한도는 리셋될 수 있다")

print("[생존] 에피소드가 터져도 다음으로 넘어가는가")
work = Path(tempfile.mkdtemp())
runner = work / "boom_runner.py"
runner.write_text(f'''
import sys
sys.path.insert(0, {str(REPO)!r})
from novel import drive as D
from novel import overnight

seen = []
def boom_build(novel, spec, llm, max_repairs=3, log=None):
    seen.append(spec["eps"][0])
    if len(seen) <= 2:
        raise RuntimeError("일부러 터뜨린다")
    return []

D.build_episode = boom_build
overnight.D.build_episode = boom_build
overnight.D.drive = lambda *a, **k: {{"status": "done", "verified": 0,
                                     "failed": 0, "remaining": 0}}
sys.argv = ["x", "--hours", "0.05", "--path", {str(work / "n.json")!r},
            "--gemini-director"]
rc = overnight.main()
print("SEEN", len(seen))
''', encoding="utf-8")
r = subprocess.run([sys.executable, str(runner)], capture_output=True, text=True, timeout=120)
seen = int(next((l.split()[1] for l in r.stdout.splitlines() if l.startswith("SEEN")), "0"))
ok(seen > 2, f"앞의 두 에피소드가 터져도 계속 돈다 (시도 {seen}개)")
ok(r.returncode == 0, f"러너 자체는 정상 종료한다 (rc={r.returncode})")

rep = Path(work / "n.overnight.json")
ok(rep.exists(), "아침에 읽을 요약 파일을 남긴다")
if rep.exists():
    j = json.loads(rep.read_text(encoding="utf-8"))
    ok(len(j["episodes_failed"]) >= 2, f"실패한 에피소드가 기록된다 ({len(j['episodes_failed'])}건)")
    ok("error" in json.dumps(j, ensure_ascii=False), "무엇 때문에 터졌는지 남는다")

print("[예산] 벽시계를 넘기면 멈추는가")
ok("--hours" in Path(REPO / "novel/overnight.py").read_text(encoding="utf-8"),
   "시간 예산 인자가 있다")

print()
if fails:
    print(f"야간 러너: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("야간 러너: 폴백·복귀·에피소드 생존·요약·예산 -- 통과")


# ==================================================== Discord 알림
print()
print("[Discord] 켜고 끄기")
from novel.overnight import Discord                                   # noqa: E402
import os                                                             # noqa: E402

d0 = Discord(token="", channel_id="", webhook="")
ok(not d0.on, "토큰도 웹훅도 없으면 꺼진다")
ok(d0.send("무시됨") is False, "꺼진 상태에서 보내면 조용히 False")

d1 = Discord(token="tok", channel_id="123", webhook="")
ok(d1.on, "봇 토큰 + 채널이면 켜진다")
d2 = Discord(token="", channel_id="", webhook="https://discord.com/api/webhooks/x/y")
ok(d2.on, "웹훅만 있어도 켜진다")

print("[Discord] 실패해도 런을 죽이지 않는가")
d3 = Discord(token="bad-token-value", channel_id="000000000000000000", webhook="")
sent = d3.send("이 호출은 실패해야 한다")
ok(sent is False, "실패하면 False 를 돌려줄 뿐 예외를 올리지 않는다")
ok(d3.failed == 1, f"실패가 집계된다 ({d3.failed})")

print("[Discord] **토큰이 로그에 새지 않는가** -- 이 저장소의 G004 가 존재하는 이유")
import io, contextlib                                                 # noqa: E402
# 자리표시자 표식(placeholder)을 넣어 G004 의 _LIVE_SECRET 오탐을 피한다. 진짜처럼
# 생긴 문자열을 테스트에 박으면 자격증명 스캐너가 그것을 유출로 잡는다 -- 실제로 잡혔다.
FAKE_CRED = "placeholder-not-a-real-bot-credential-0000"
buf = io.StringIO()
d4 = Discord(token=FAKE_CRED, channel_id="000000000000000000", webhook="")
with contextlib.redirect_stderr(buf):
    d4.send("실패를 유도한다")
leaked = buf.getvalue()
ok(FAKE_CRED not in leaked, f"실패 로그에 토큰이 없다 (로그: {leaked.strip()[:70]})")
ok("Discord 전송 실패" in leaked, "대신 에러 종류와 코드만 남는다")

print("[Discord] 하트비트는 조용할 때만")
d5 = Discord(token="t", channel_id="1", webhook="", heartbeat=10_000)
d5.send = lambda text: (beats.append(text), True)[1]
beats = []
d5.last = time.time()
d5.beat("살아있다")
ok(not beats, "최근에 보냈으면 하트비트를 내지 않는다")
d5.last = time.time() - 20_000
d5.beat("살아있다")
ok(len(beats) == 1, "오래 조용하면 한 번 낸다 -- 밤새 수백 개가 쌓이지 않게")

print()
if fails:
    print(f"Discord 알림: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("Discord 알림: 켜기·실패 격리·토큰 비노출·하트비트 -- 통과")
