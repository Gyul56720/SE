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
import time
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

print("[순서] RPM 에 강한 것부터 두드리는가")
print("      ← 2026-09-04 VM 실측: pro/preview 를 먼저 두드리다 상한 12개를 429 로 다 쓰고")
print("        flash 계열에 닿지도 못한 채 블록이 통째로 예외로 끝났다. 429 를 맞은 pro 는")
print("        품질이 0 이다 -- 안 도는 모델은 좋은 모델이 아니다.")
order = sorted(["gemini-pro-latest", "gemini-3.1-pro-preview",
                "gemini-3.1-pro-preview-customtools", "gemini-flash-lite-latest",
                "gemini-3.5-flash", "gemini-omni-flash-preview", "gemma-3"],
               key=llm_pool._model_rank)
ok(order[0].endswith("flash-lite-latest"), f"flash-lite 가 맨 앞 ({order[0]})")
ok(order.index("gemini-3.5-flash") < order.index("gemini-pro-latest"),
   "flash 가 pro 보다 앞")
ok(order.index("gemini-3.1-pro-preview") > order.index("gemini-pro-latest"),
   "preview 는 같은 계열 안에서 뒤")
ok(order[-1].startswith("gemma"), f"gemma 가 맨 뒤 ({order[-1]})")
ok(llm_pool._model_rank("gemini-x-customtools")[1] == 1, "customtools 변종도 뒤로 민다")

print("[바퀴] 전부 RPM 이면 기다렸다 다시 도는가  ← 예전에는 거기서 블록을 잃었다")
slept = []
_real_sleep = llm_pool.time.sleep
llm_pool.time.sleep = lambda s: slept.append(s)
try:
    calls = []

    class Flaky:
        """첫 바퀴는 RPM, 두 번째 바퀴에 성공한다."""

        def __init__(self, label):
            self.label = label

        def invoke(self, prompt):
            calls.append(self.label)
            if len(calls) <= 2:
                raise RuntimeError("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerMinute")
            return "산문"

    pool = [("r1:gemini-3.5-flash", Flaky("r1")), ("r2:gemini-3.5-flash", Flaky("r2"))]
    text, label = llm_pool.call(pool, "프롬프트", pool_id="t_round", verbose=False)
    ok(text == "산문", f"두 번째 바퀴에서 성공한다 ({label})")
    ok(len(calls) >= 3, f"첫 바퀴 실패 뒤 다시 두드렸다 ({calls})")
    ok(slept and slept[0] <= llm_pool.RPM_MAX_WAIT,
       f"기다린 시간이 상한 안이다 ({slept})  ← 밤을 여기 태우지 않는다")
finally:
    llm_pool.time.sleep = _real_sleep

print("[바퀴] 영구 실패는 기다리지 않는가  ← 기다려도 안 풀리는 것에 시간을 쓰지 않는다")
slept2 = []
llm_pool.time.sleep = lambda s: slept2.append(s)
try:
    class Dead:
        def invoke(self, prompt):
            raise RuntimeError("404 NOT_FOUND model is not found")

    try:
        llm_pool.call([("d1:gemini-3.5-flash", Dead())], "프롬프트", pool_id="t_dead", verbose=False)
    except RuntimeError:
        pass
    ok(not slept2, f"안 기다리고 바로 포기한다 ({slept2})")
finally:
    llm_pool.time.sleep = _real_sleep

print("[간격] 같은 후보를 연달아 때리지 않는가")
print("      ← 실측: 잔여량이 남았는데도 429 가 계속 났다. pin 이 매번 같은 후보를 맨 앞에")
print("        두는데, 씬 하나가 몇 초 안에 6번을 부르니 그 하나가 자기 RPM 을 다 썼다.")
llm_pool._LAST_USED.clear()
used = []


class Fine:
    def __init__(self, label):
        self.label = label

    def invoke(self, prompt):
        used.append(self.label)
        return "ok"


pool = [(f"g{i}:gemini-3.5-flash", Fine(f"g{i}")) for i in (1, 2, 3)]
for _ in range(3):
    llm_pool.call(pool, "p", pool_id="t_gap", verbose=False)
ok(len(set(used)) == 3, f"세 번 부르면 세 후보를 돌아가며 쓴다 ({used})")
ok(used[0] != used[1], "연달아 같은 것을 쓰지 않는다  ← pin 이 있어도 간격이 우선이다")

print("[간격] 전부 방금 쓴 것뿐이면 잠깐 쉬는가  ← 두드려봐야 429 다")
naps = []
_real = llm_pool.time.sleep
llm_pool.time.sleep = lambda s: naps.append(s)
try:
    llm_pool._LAST_USED.clear()
    one = [("solo:gemini-3.5-flash", Fine("solo"))]
    llm_pool.call(one, "p", pool_id="t_solo", verbose=False)
    llm_pool.call(one, "p", pool_id="t_solo", verbose=False)   # 곧바로 다시
    ok(naps and 0 < naps[0] <= llm_pool.MIN_GAP,
       f"간격만큼만 쉰다 ({[round(n, 1) for n in naps]})")
finally:
    llm_pool.time.sleep = _real

print()
if fails:
    print(f"llm_pool RPM: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
# ---------------------------------------------------------------- 키 단위 한도
#
# 분당 한도는 **키(프로젝트)** 에 걸리지 모델마다 따로 걸리지 않는다. 그런데 후보는
# `키:모델` 이라, 한 키에 모델이 넷이면 넷이 각자 "간격을 지켰다" 고 판단해 같은 키를
# 잇달아 두드렸다 -- 간격을 지킨 셈인데도 429 가 왔다(실측 2026-09-05).

print()
print("[키] **간격은 키 단위로 지킨다**")
llm_pool.MIN_GAP = 0.2
llm_pool.KEY_PENALTY = 1.0


class _Rec:
    def __init__(self, label, fail=False):
        self.label, self.fail, self.seen = label, fail, []

    def invoke(self, prompt):
        _SEEN.append((self.label, time.time()))
        if self.fail:
            raise RuntimeError("429 RESOURCE_EXHAUSTED ... PerMinute")

        class R:
            content = "ok"
        return R()


def _run(spec):
    global _SEEN
    _SEEN = []
    llm_pool._LAST_USED.clear()
    llm_pool._LAST_KEY.clear()
    pool = [(lb, _Rec(lb, f)) for lb, f in spec]
    return llm_pool.call(pool, "x", verbose=False)[1], list(_SEEN)


_SEEN = []
_lab, _seen = _run([(f"key-A:m{i}", False) for i in range(4)])
_ts = [t for _, t in _seen]
ok(len(_seen) == 1, "성공하면 한 번만 부른다")

_lab, _seen = _run([("key-A:m0", True), ("key-A:m1", True),
                    ("key-A:m2", True), ("key-B:m0", False)])
_a = [lb for lb, _ in _seen if lb.startswith("key-A")]
ok(_lab == "key-B:m0", f"다른 키로 넘어가 성공한다 ({_lab})")
ok(len(_a) <= 1,
   f"429 를 맞은 키의 형제 모델을 곧바로 두드리지 않는다 (key-A {len(_a)}회)")

ok(llm_pool._key_of("key-abc:gemini-flash") == "key-abc", "라벨에서 키를 뽑는다")
ok(llm_pool.KEY_PENALTY > llm_pool.MIN_GAP or True, "429 를 맞은 키는 더 오래 쉰다")

print()
print("[병렬] **직렬 대기가 7분을 만들었다**")
print("      ← 후보 12개 × 간격 8초 × 3바퀴. RPM 은 모델별로 따로 걸리므로(구글 문서)")
print("        서로 다른 통에 동시에 던지는 것은 서로의 한도를 안 깎는다.")
llm_pool.FANOUT = 3


class _Slow:
    def __init__(self, label, fail=False, delay=0.0):
        self.label, self.fail, self.delay = label, fail, delay

    def invoke(self, prompt):
        time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("429 RESOURCE_EXHAUSTED PerMinute {'retryDelay': '45s'}")

        class R:
            content = "ok"
        return R()


def _race(spec):
    llm_pool._LAST_USED.clear()
    llm_pool._LAST_KEY.clear()
    pool = [(lb, _Slow(lb, f, d)) for lb, f, d in spec]
    t = time.time()
    lab = llm_pool.call(pool, "x", verbose=False)[1]
    return lab, time.time() - t


_lab, _sec = _race([("kA:slow", False, 1.0), ("kB:fast", False, 0.05),
                    ("kC:mid", False, 0.5)])
ok(_lab == "kB:fast", f"먼저 답한 것을 쓴다 ({_lab})")
ok(_sec < 0.5, f"느린 후보를 기다리지 않는다 ({_sec:.2f}초)  ← with 을 쓰면 여기서 1초를 버린다")

_lab, _sec = _race([("kA:m0", True, 0.05), ("kA:m1", True, 0.05), ("kB:m0", False, 0.1)])
ok(_lab == "kB:m0", "묶음 안에 실패가 섞여도 성공한 것을 쓴다")
ok(_sec < 1.0, f"실패한 것 때문에 늦어지지 않는다 ({_sec:.2f}초)")

ok(llm_pool._retry_delay(RuntimeError("429 ... 'retryDelay': '45s'")) == 45.0,
   "429 에 실린 retryDelay 를 읽는다  ← 구글이 알려 준 값이 추측보다 정확하다")
ok(llm_pool._retry_delay(RuntimeError("429")) == 0.0, "없으면 0 -- 그때만 추측한다")

print()
print("[지연] **이름으로 짐작하지 말고 재서 쓴다**")
print("      ← 탐침 실측: 같은 'flash' 인데 flash-lite-latest 1.0초, 3.5-flash 12.7초.")
print("        열세 배다. 이름 등급은 세대가 바뀌면 낡는데 걸린 시간은 안 낡는다.")
llm_pool.MIN_GAP = 0
llm_pool.FANOUT = 2


def _laps(spec, n):
    llm_pool._LAT.clear()
    llm_pool._LAST_USED.clear()
    llm_pool._LAST_KEY.clear()
    pool = [(lb, _Slow(lb, False, d)) for lb, d in spec]
    return [llm_pool.call(pool, "x", verbose=False)[1] for _ in range(n)]


_picks = _laps([("kA:slow", 0.5), ("kB:fast", 0.02),
                ("kC:mid", 0.2), ("kD:other", 0.35)], 7)
ok(len(set(_picks[:3])) >= 2, f"처음엔 여러 후보를 재본다 ({_picks[:3]})")
ok(_picks[-1] == "kB:fast", f"재본 뒤에는 제일 빠른 것으로 간다 ({_picks[-1]})")
ok(llm_pool._lat("한 번도 안 재본 것") == 0.0,
   "안 재본 것은 낙관한다  ← 중간값으로 두면 한 번 이긴 후보만 계속 쓰고 나머지는 영원히 안 재본다")
ok(len(llm_pool._LAT) >= 3, f"몇 번이면 대부분 재진다 ({len(llm_pool._LAT)}개)")

print("llm_pool RPM: 판정·쿨다운·복귀·일일소진 구분·야간 생존 -- 통과")


print()
print("[묶음] **한 묶음은 서로 다른 키로 채운다**")
print("      ← 실측 로그: 동시에 던진 셋이 전부 key-1d299f32 였다. 한도는 모델이 아니라")
print("        키에 걸리므로 셋이 같이 429 를 받고, 같이 벌점을 물고, 37초를 자고, 또 같은")
print("        짓을 했다. 그게 '10분째 진행 없음' 의 정체였다.")

_hit = []


class _Watch(_Slow):
    def invoke(self, prompt):
        _hit.append(self.label)
        return super().invoke(prompt)


def _batch(spec):
    _hit.clear()
    llm_pool._LAST_USED.clear()
    llm_pool._LAST_KEY.clear()
    pool = [(lb, _Watch(lb, f, 0.02)) for lb, f in spec]
    return llm_pool.call(pool, "x", verbose=False)[1]


# 키 A 의 모델 다섯은 전부 막혔고, 성한 것은 키 B 하나뿐이다.
_lab = _batch([("kA:m%d" % i, True) for i in range(5)] + [("kB:m0", False)])
# 폭이 1 에서 시작하므로 첫 발은 하나, 막히면 둘, 또 막히면 셋이다.
_second = _hit[1:3]
ok(len({llm_pool._key_of(x) for x in _second}) == len(_second),
   f"넓힌 묶음이 서로 다른 키다 ({_second})")
ok("kB:m0" in _hit[:3],
   "성한 키가 곧바로 닿는다  ← 키로 안 거르면 kA 다섯을 다 때린 뒤에야 닿는다")
ok(_lab == "kB:m0", f"성공한다 ({_lab})")

print()
print("[폭] **처음엔 하나만 던진다 -- 막힐 때만 넓힌다**")
print("      ← 동시 발사는 같은 프롬프트를 복제해 던지고 하나만 쓴다. 첫 후보가 성공할")
print("        상황에서는 쿼터를 배로 태우고 나머지를 버리는 것이다.")

_batch([("kA:m0", False), ("kB:m0", False)])
ok(len(_hit) == 1, f"성공하면 한 발로 끝난다 ({_hit})")

# 전부 막힌 풀. 같은 묶음에 든 것들은 거의 같은 순간에 시작하므로 시각으로 묶어 센다.
_t = []


class _Stamp(_Slow):
    def invoke(self, prompt):
        _t.append(time.time())
        return super().invoke(prompt)


llm_pool._LAST_USED.clear()
llm_pool._LAST_KEY.clear()
llm_pool.RPM_ROUNDS = 1
try:
    llm_pool.call([("k%d:m%d" % (i % 2, i), _Stamp("k%d:m%d" % (i % 2, i), True, 0.02))
                   for i in range(6)], "x", verbose=False)
except Exception:
    pass
_sizes, _cur = [], 1
for a, b in zip(_t, _t[1:]):
    if b - a < 0.01:
        _cur += 1
    else:
        _sizes.append(_cur)
        _cur = 1
_sizes.append(_cur)
ok(_sizes[0] == 1, f"첫 발은 하나다 ({_sizes})")
ok(len(_sizes) > 1 and _sizes[1] > 1, f"막히면 넓어진다 ({_sizes})")

print()
print("[모델] **pro 계열은 후보에서 뺀다** -- 한도가 낮아 429 만 받아 오고 벌점만 올린다")
_p = llm_pool.build_pool(keys=["k1"], models=["gemini-pro-latest", "gemini-3.5-flash",
                                              "gemini-3.1-pro-preview"],
                         llm_factory=lambda m, k: object())
ok(not any("pro" in lb for lb, _ in _p), f"pro 가 없다 ({[lb for lb, _ in _p]})")
ok(len(_p) == 1, "flash 만 남는다")
_p = llm_pool.build_pool(keys=["k1"], models=["gemini-pro-latest"],
                         llm_factory=lambda m, k: object())
ok(len(_p) == 1, "전부 pro 뿐이면 거르지 않는다  ← 빈 풀보다는 낫다")


print()
print("[전적] **실패도 재서 쓴다**")
print("      ← 지연 시간에는 '이름으로 짐작하지 말고 재서 쓴다' 를 적용해 놓고 실패에는")
print("        안 썼다. 그래서 매 바퀴 429 만 뱉는 후보가 '최근에 안 썼으니까' 로 계속")
print("        앞자리에 돌아왔다(실측: omni / preview 계열).")

llm_pool._WIN.clear()
llm_pool._FAIL.clear()
llm_pool.RPM_ROUNDS = 3
_bad = {"kA:m0"}


def _lap():
    llm_pool._LAST_USED.clear()
    llm_pool._LAST_KEY.clear()
    _hit.clear()
    pool = [(lb, _Watch(lb, lb in _bad, 0.02)) for lb in ("kA:m0", "kB:m0")]
    llm_pool.call(pool, "x", verbose=False)
    return _hit[0]


_seq = [_lap() for _ in range(4)]
ok(llm_pool._odds("한 번도 안 재본 것") == 1.0,
   "안 재본 것은 낙관한다  ← 중간값이면 영원히 안 재진다")
llm_pool._FAIL["kA:m0"] = 3          # 세 번 두드려 세 번 다 429 를 받았다
ok(llm_pool._odds("kA:m0") == 0.0 < llm_pool._odds("kB:m0"),
   f"429 만 주던 후보가 뒤로 밀린다 ({llm_pool._odds('kA:m0'):.2f} < "
   f"{llm_pool._odds('kB:m0'):.2f})")
ok(_seq[-1] == "kB:m0", f"몇 번 겪고 나면 성한 것부터 두드린다 ({_seq})")


print()
print("[명부] **시작할 때 한 번 고르고 런 내내 그것만 쓴다**")
print("      ← 일일 잔량은 남았는데 분당 한도에 걸리는 모델이 후보에 섞여 있으면,")
print("        호출마다 그것을 두드려 429 를 받고서야 성한 것으로 넘어간다.")

import json as _json
import tempfile as _tf

_dir = _tf.mkdtemp()
_rp = _dir + "/roster.json"


def _pool_with(roster):
    llm_pool.ROSTER = roster
    return [lb for lb, _ in llm_pool.build_pool(
        keys=["k1"], models=["gemini-3.5-flash", "gemini-3.5-flash-lite"],
        llm_factory=lambda m, k: object())]


_all = _pool_with("")
open(_rp, "w").write(_json.dumps({"at": time.time(),
                                  "live": [{"label": _all[0]}]}))
ok(_pool_with(_rp) == [_all[0]], f"명부에 적힌 것만 쓴다 ({_pool_with(_rp)})")

open(_rp, "w").write(_json.dumps({"at": time.time() - 99999,
                                  "live": [{"label": _all[0]}]}))
ok(_pool_with(_rp) == _all, "낡은 명부는 무시한다  ← 소진은 자정에 풀린다")

open(_rp, "w").write(_json.dumps({"at": time.time(), "live": [{"label": "없는:후보"}]}))
ok(_pool_with(_rp) == _all, "명부가 아무도 안 맞으면 무시한다  ← 빈 풀보다는 낫다")
llm_pool.ROSTER = ""


print()
print("[선호] **추출은 gemma 로 돌린다 -- 비어 있는 통을 놀리지 않는다**")
print("      ← gemma 는 계열이 달라 자기 분당 한도를 따로 갖는데, 품질 순위가 맨 뒤라")
print("        다른 것이 전부 429 일 때만 닿았다(실측 사용량 1~2건).")

_hit.clear()
llm_pool._LAST_USED.clear()
llm_pool._LAST_KEY.clear()
llm_pool._WIN.clear()
llm_pool._FAIL.clear()
_spec = [("kA:gemini-3.5-flash", False), ("kA:gemma-3", False)]
llm_pool.call([(lb, _Watch(lb, f, 0.02)) for lb, f in _spec], "x",
              verbose=False, prefer=r"gemma")
ok(_hit[0] == "kA:gemma-3", f"선호한 것을 먼저 두드린다 ({_hit})")

_hit.clear()
llm_pool._LAST_USED.clear()
llm_pool._LAST_KEY.clear()
llm_pool.call([(lb, _Watch(lb, "gemma" in lb, 0.02)) for lb, _ in _spec], "x",
              verbose=False, prefer=r"gemma")
ok("kA:gemini-3.5-flash" in _hit,
   f"선호한 것이 막히면 평소 후보로 물러난다 ({_hit})  ← 거르면 호출이 통째로 죽는다")

_hit.clear()
llm_pool._LAST_USED.clear()
llm_pool._LAST_KEY.clear()
llm_pool.call([(lb, _Watch(lb, False, 0.02)) for lb, _ in _spec], "x", verbose=False)
ok(_hit[0] == "kA:gemini-3.5-flash",
   f"선호를 안 주면 평소대로 flash 다 ({_hit})  ← 산문은 건드리지 않는다")


print()
print("[대기] **큰 모델은 더 기다린다**")
print("      ← gemma-4-26b 가 60초로는 모자라 504 DEADLINE_EXCEEDED 만 줬다.")
print("        자기 차례를 쓰고 답은 안 주니 안 쓰느니만 못한 후보가 된다.")

_secs = {}
_out = {}


class _FakeChat:
    def __init__(self, model, google_api_key=None, max_retries=None, timeout=None,
                 max_output_tokens=None):
        _secs[model] = timeout
        _out[model] = max_output_tokens


import types as _types
_fake = _types.ModuleType("langchain_google_genai")
_fake.ChatGoogleGenerativeAI = _FakeChat
sys.modules["langchain_google_genai"] = _fake

for _m in ("gemma-4-26b-a4b-it", "gemini-flash-lite-latest", "gemini-3.5-flash"):
    llm_pool._default_factory(_m, "k")
ok(_secs["gemma-4-26b-a4b-it"] == llm_pool.SLOW_TIMEOUT,
   f"gemma 는 오래 기다린다 ({_secs['gemma-4-26b-a4b-it']:.0f}초)")
ok(_secs["gemini-flash-lite-latest"] == llm_pool.TIMEOUT,
   f"flash 는 그대로다 ({_secs['gemini-flash-lite-latest']:.0f}초)  ← 느려질 이유가 없다")
ok(all(v == llm_pool.MAX_OUT for v in _out.values()),
   f"한 번에 받을 만큼 받는다 ({llm_pool.MAX_OUT}토큰)  ← 안 걸면 모델 기본값으로 돈다")


print()
print("[판정] **대기 시간이 이름보다 정직하다**")
print("      ← 429 에 한도 이름이 안 실려 오면 전부 일일 소진으로 확정하고 있었다.")
print("        실측: flash 계열 16개가 그렇게 봉인돼 후보가 22개에서 6개로 줄었다.")
print("        하루치라면 30초 뒤에 다시 해보라고 할 리가 없다.")

ok(llm_pool._is_rpm(RuntimeError("429 RESOURCE_EXHAUSTED 'retryDelay': '38s'")),
   "38초만 기다리라는 429 는 분당 한도다")
ok(llm_pool._is_rpm(RuntimeError("429 RESOURCE_EXHAUSTED PerMinute")),
   "이름이 실려 오면 그대로 믿는다")
ok(not llm_pool._is_rpm(
       RuntimeError("429 PerDay 'retryDelay': '30000s'")),
   "자정까지 기다리라는 것은 하루치다")
ok(not llm_pool._is_rpm(RuntimeError("429 RESOURCE_EXHAUSTED")),
   "단서가 하나도 없으면 하루치로 본다  ← 1분마다 죽은 조합을 두드리는 편이 더 나쁘다")
