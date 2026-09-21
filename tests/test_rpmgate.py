# -*- coding: utf-8 -*-
"""**맞기 전에 간격을 두는가.**

ReAct 루프는 사용자 메시지 하나에 모델을 여러 번 부른다 -- 도구를 부를 때마다 한 번씩
더. 그것이 몇 초 안에 연달아 나가서 **한 메시지가 자기 분당 한도를 혼자 다 쓴다.**
그 뒤에 일어나는 일이 사용자가 본 로그다:

    429 RPM -> 60초 쿨다운 -> 다음 후보로 전환 -> 그 후보도 곧 같은 꼴 -> ...

게다가 후보를 갈아타면 그 대화를 새 모델이 이어받아 **다시 한 바퀴 돈다** -- 한도에
걸릴수록 호출이 더 는다. 되먹임이다.

quota_tracker · poolpick 은 **맞고 난 뒤**를 다룬다(쉬게 하고 · 뒤로 밀고 · 건너뛴다).
여기는 **맞기 전**이다. 시계와 잠을 가짜로 물려 60초를 실제로 기다리지 않고 잰다.

실행: python3 tests/test_rpmgate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import rpmgate as R                                                   # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


class 시계:
    """가짜 시계 -- 잠은 바늘을 돌리는 것으로 갈음한다."""

    def __init__(self):
        self.t = 1000.0
        self.잔것 = []

    def 지금(self):
        return self.t

    def 쉬기(self, 초):
        self.잔것.append(초)
        self.t += 초


print("[한도] 모델마다 다르게 본다 (이름으로 -- API 가 수를 안 준다)")
ok(R.모델한도("key-a:gemini-3.5-flash-lite") == 15, "flash-lite 가 가장 넉넉")
ok(R.모델한도("key-a:gemini-3.5-flash") == 10, "flash")
ok(R.모델한도("key-a:gemini-3.1-pro") == 5, "pro 가 가장 빡빡 -- 여기가 제일 자주 터졌다")
ok(R.모델한도("key-a:듣보모델") == R.기본RPM, "모르는 이름은 보수적으로 기본값")
ok(R.모델한도("flash-lite") == 15, "라벨 없이 모델 이름만 줘도 읽는다")

print()
print("[한가할 때] 한 번도 안 재운다")
c = 시계()
g = R.문(지금=c.지금, 쉬기=c.쉬기)
잔 = [g.지나가기("k:m", 한도=10) for _ in range(10)]
ok(잔 == [0.0] * 10, f"한도까지는 그냥 지나간다 ({sum(잔)}초)")
ok(c.잔것 == [], "**고정 간격이 아니다** -- 놀 때 기다리게 하면 그게 손해다")
ok(g.센것("k:m") == 10, "창 안에 열 번이 남아 있다")

print()
print("[찰 때] 가장 오래된 것이 창 밖으로 나갈 때까지만 기다린다")
잔11 = g.지나가기("k:m", 한도=10)
ok(잔11 > 0, f"열한 번째는 기다린다 ({잔11:.1f}초)")
ok(abs(잔11 - 60.0) < 0.5, f"딱 창 하나만큼 ({잔11:.1f}초) -- 한 바퀴 통째로 쉬지 않는다")
# 가짜 시계에서는 앞의 열 번이 **같은 순간**에 찍혔으므로 창 하나가 지나면 열 개가
# 한꺼번에 빠진다 -- 남는 것은 방금 찍은 하나뿐이다. 진짜 호출은 흩어져 있어 하나씩
# 빠진다. 여기서 재는 것은 "기다린 만큼 자리가 난다" 이지 특정 개수가 아니다.
ok(g.센것("k:m") == 1, f"기다린 뒤 창이 비고 방금 것만 남는다 ({g.센것('k:m')})")

print()
print("[갈라 센다] 모델이 다르면 통도 다르다 (구글이 그렇게 건다)")
c2 = 시계()
g2 = R.문(지금=c2.지금, 쉬기=c2.쉬기)
for _ in range(10):
    g2.지나가기("k:flash", 한도=10)
ok(g2.지나가기("k:flash-lite", 한도=15) == 0.0,
   "**한쪽이 찼다고 다른 쪽을 세우지 않는다** -- 세웠으면 후보를 늘린 뜻이 없다")
ok(g2.지나가기("k2:flash", 한도=10) == 0.0, "키가 다르면 그것도 다른 통이다")

print()
print("[흐르면 풀린다] 시간이 지나면 저절로 자리가 난다")
c3 = 시계()
g3 = R.문(지금=c3.지금, 쉬기=c3.쉬기)
for _ in range(10):
    g3.지나가기("k:m", 한도=10)
c3.t += 61                      # 창 하나가 통째로 지났다
ok(g3.센것("k:m") == 0, "창 밖으로 나간 자국은 지워진다")
ok(g3.지나가기("k:m", 한도=10) == 0.0, "별도 해제 없이 원래대로 -- 이것도 '기다리면 풀린다'")

print()
print("[한 벌] 모듈 수준 문지기가 같은 물건인가")
R.문지기.비우기()
ok(R.센것("x:y") == 0, "비우면 0")
R.지나가기("x:y", 한도=3)
ok(R.센것("x:y") == 1, "모듈 함수가 그 문지기를 쓴다 -- 부르는 쪽마다 따로 세면 뜻이 없다")
R.문지기.비우기()

print()
print("[바퀴] 한 메시지가 도는 길이에도 끝이 있는가")
cfg = R.설정("t-1")
ok(cfg["configurable"]["thread_id"] == "t-1", "thread 를 그대로 싣는다")
ok(cfg["recursion_limit"] == R.바퀴상한, f"바퀴 상한을 함께 싣는다 ({R.바퀴상한})")
ok(R.설정("t", 상한=7)["recursion_limit"] == 7, "부르는 쪽이 상한을 정할 수 있다")


class 넘침(Exception):
    pass


넘침.__name__ = "GraphRecursionError"
ok(R.바퀴넘침(넘침("…")), "LangGraph 의 GraphRecursionError 를 알아본다")
ok(R.바퀴넘침(Exception("Recursion limit of 25 reached")),
   "이름이 아니라 글로 와도 알아본다 -- 판이 바뀌어도 안 놓치게")
ok(not R.바퀴넘침(Exception("503 UNAVAILABLE")),
   "**다른 고장을 바퀴 넘침으로 읽지 않는다** -- 그러면 진짜 장애를 조용히 삼킨다")

말 = R.끊긴말()
ok("대화에 남아 있습니다" in 말,
   "**한 일이 남아 있다고 말한다** ← 이 말이 없으면 사용자가 처음부터 다시 시킨다")
ok("이어서" in 말, "무엇을 치면 이어지는지 알려준다")
ok("나눠" in 말, "왜 나눠 보내는 게 이득인지 말한다(분당 한도)")
# 실측 2026-09-21: 첫 판은 "멈췄습니다" 만 말하고 **한 일을 안 적었다.** 잘린 답에서
# 제일 급한 정보가 그것인데(셸이 돌았나? 파일이 바뀌었나?) 알 길이 없었다.
한일말 = R.끊긴말(한일=["python3 -m eval.run", "git commit -m x"])
ok("eval.run" in 한일말 and "git commit" in 한일말,
   "**여기까지 실제로 돌린 것을 적는다** ← 없으면 사용자가 뭐가 됐는지 모른다")
ok(R.바퀴상한 >= 40,
   f"상한이 평범한 한 턴보다 넉넉하다 ({R.바퀴상한}) -- 25 는 이 봇의 보통 일도 잘랐다")



print()
print("[후보] 429 만 주는 후보는 후보가 아니다")
_ms = ["gemini-3.1-pro-preview-customtools", "gemini-pro-latest",
       "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemma-4-26b"]
남은 = R.usable_models(_ms)
ok("gemini-pro-latest" not in 남은,
   "**사용자 로그에 찍힌 그 모델이 빠진다** (gemini-pro-latest -- 매 바퀴 RPM 초과)")
ok("gemini-3.1-pro-preview-customtools" not in 남은,
   "preview·customtools 꼬리가 붙어도 pro 는 pro 다")
ok("gemini-3.5-flash" in 남은 and "gemini-3.5-flash-lite" in 남은, "flash 계열은 남는다")
ok("gemma-4-26b" in 남은, "pro 가 아닌 것은 안 건드린다")
ok(R.usable_models(["gemini-pro-latest", "gemini-3.1-pro"]) == ["gemini-pro-latest", "gemini-3.1-pro"],
   "**다 걸러지면 거르지 않는다** -- 빈 풀은 느린 답보다 나쁘다(아예 답을 못 한다)")
ok(R.usable_models([]) == [] and R.usable_models(None) == [], "빈 목록은 빈 목록")
ok(R.worth_calling("key-abc:gemini-3.5-flash") and not R.worth_calling("key-abc:gemini-pro-latest"),
   "라벨 꼴(key:model)로 줘도 모델 이름만 본다")
ok(R.모델한도("gemini-pro-latest") == 5,
   "**왜 빼는지가 수로 적혀 있다** -- pro 는 분당 5, flash 는 10, flash-lite 는 15")


print()
if fails:
    print(f"실패 {len(fails)}개: {fails}")
    raise SystemExit(1)
print("rpmgate: 한도 · 한가할 때 · 찰 때 · 갈라 세기 · 흐름 · 후보 거름망 -- 통과")
