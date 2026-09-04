"""llm_pool 의 429 구분 -- **1분이면 풀릴 키를 하루 종일 봉인하지 않는가.**

quota_tracker 가 RPD 와 RPM 을 일부러 갈라놨고 그 이유를 독스트링에 적어뒀다:
"둘을 합쳐 놓으면 ... 1분이면 풀릴 키를 하루 종일 봉인하게 된다."
bot_tools 는 그 구분을 지키는데 orchestrator/llm_pool 은 안 지키고 있었다 -- 모든 429 를
record_exhausted 로 보내 자정까지 확정 소진 처리했다.

야간 런에서 치명적이다. 후보가 넷뿐인데 몇 초 안에 여러 번 호출하다 RPM 에 걸리면 멀쩡한
조합이 차례로 봉인되고, 몇 분 만에 풀이 비어 남은 밤이 통째로 날아간다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_llm_pool_rpm.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ["QUOTA_STATE_PATH"] = tempfile.mktemp()
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "orchestrator"))

import llm_pool                                                       # noqa: E402
import quota_tracker as q                                             # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


class Err(Exception):
    pass


RPM = Err("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerMinutePerProjectPerModel")
RPD = Err("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel")
VAGUE = Err("429 RESOURCE_EXHAUSTED")


def cand(label, exc=None, reply="ok"):
    class L:
        def invoke(self, prompt):
            if exc:
                raise exc
            return reply
    return (label, L())


print("[판정] 분당 한도를 알아보는가")
ok(llm_pool._is_rpm(RPM), "PerMinute 를 RPM 으로")
ok(not llm_pool._is_rpm(RPD), "PerDay 는 RPM 이 아니다")
ok(not llm_pool._is_rpm(VAGUE),
   "quotaId 가 없으면 False -- 모르는 것은 보수적으로 일일 소진 취급")

print("[RPM] 60초만 쉬고 자정까지 봉인되지 않는가")
pool = [cand("a:m", RPM), cand("b:m")]
txt, lbl = llm_pool.call(pool, "p", verbose=False)
ok(lbl == "b:m", f"다음 후보로 넘어간다 ({lbl})")
ok(q.is_rpm_cooling("a:m"), "RPM 을 맞은 후보는 쿨다운에 들어간다")
ok(0 < q.rpm_cooldown_remaining("a:m") <= 60, "쿨다운은 60초 안쪽")
ok(not q.is_dead("a:m"), "영구 사망 목록에 올라가지 않는다")

print("[복귀] 쿨다운이 끝나면 저절로 돌아오는가")
q.record_rpm_cooldown("a:m", seconds=-1)          # 이미 지난 시각
ok(not q.is_rpm_cooling("a:m"), "쿨다운이 지나면 풀린다")
ok(q.remaining("a:m") > 0,
   "잔량이 원래대로 돌아온다 -- 별도 해제 작업 없이")

print("[RPD] 일일 소진은 여전히 자정까지 확정되는가")
pool2 = [cand("c:m", RPD), cand("d:m")]
llm_pool.call(pool2, "p", verbose=False)
ok(q.remaining("c:m") == 0, "PerDay 는 오늘 소진 처리")
ok(not q.is_rpm_cooling("c:m"), "쿨다운이 아니라 소진이다 -- 1분마다 다시 두드리지 않는다")

print("[야간] 후보 넷이 RPM 을 맞아도 풀이 마르지 않는가")
for lab in ("e1:m", "e2:m", "e3:m", "e4:m"):
    q.record_rpm_cooldown(lab, seconds=-1)
pool3 = [cand("e1:m", RPM), cand("e2:m", RPM), cand("e3:m", RPM), cand("e4:m")]
txt, lbl = llm_pool.call(pool3, "p", verbose=False)
ok(lbl == "e4:m", "셋이 RPM 이어도 넷째로 성공")
ok(all(not q.is_dead(x) for x in ("e1:m", "e2:m", "e3:m")),
   "**아무도 봉인되지 않는다** -- 1분 뒤 전부 돌아온다")

print("[건너뛰기] 잔량 0 인 후보는 **시도조차 하지 않는가**")
print("      ← 2026-09-04 실측: 12번 시도가 전부 429 였는데 절반은 이미 소진을 알던 조합")
calls = []


def counting(label, err=None):
    c = cand(label, err)
    inner = c[1]

    class Counting:
        def invoke(self, prompt):
            calls.append(label)
            return inner.invoke(prompt)
    return (label, Counting())


for lab in ("z1:m", "z2:m", "z3:m"):
    q.record_rpm_cooldown(lab, seconds=-1)
q.record_exhausted("z1:m")
q.record_exhausted("z2:m")
pool4 = [counting("z1:m", RPD), counting("z2:m", RPD), counting("z3:m")]
txt, lbl = llm_pool.call(pool4, "p", verbose=False)
ok(lbl == "z3:m", f"잔량 있는 후보로 성공 ({lbl})")
ok(calls == ["z3:m"],
   f"소진된 둘은 아예 호출되지 않는다 (실제 호출: {calls})  "
   "← 이게 안 되면 상한이 죽은 후보로 채워져 멀쩡한 것에 닿지 못한다")

print("[안전] 전부 잔량 0 이면 그때는 거르지 않는가")
calls.clear()
for lab in ("y1:m", "y2:m"):
    q.record_rpm_cooldown(lab, seconds=-1)
    q.record_exhausted(lab)
pool5 = [counting("y1:m", RPD), counting("y2:m")]
txt, lbl = llm_pool.call(pool5, "p", verbose=False)
ok(lbl == "y2:m", f"그래도 시도해서 성공한다 ({lbl})  ← 카운터는 추정이라 틀릴 수 있다")
ok(len(calls) >= 1, f"아무것도 시도하지 않고 실패하지는 않는다 ({calls})")

print()
if fails:
    print(f"llm_pool RPM: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("llm_pool RPM: 판정·쿨다운·복귀·일일소진 구분·야간 생존 -- 통과")
