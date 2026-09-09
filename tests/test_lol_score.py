"""**심판이 진짜 가르는가** -- 신호가 있는 원장과 없는 원장을 다르게 판정하는가.

    python3 tests/test_lol_score.py

`law/mutate.py` 가 정한 규율 그대로다: 어긋남 0 은 그 자체로 아무것도 증명하지 않는다.
관문이 잘 만들어져서 0 일 수도 있고, **아무것도 못 잡는 관문이라서** 0 일 수도 있다.

    GREEN  실력차가 진짜 있는 원장에서 -> 기준선을 이겨야 한다
    RED    동전던지기 원장에서        -> 기준선을 **못** 이겨야 한다

둘째가 요점이다. 무엇을 넣어도 "이겼다" 고 말하는 심판은 심판이 아니라 장식이다.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lol import corpus as CP                                       # noqa: E402
from lol import elo as EL                                          # noqa: E402
from lol import score as SC                                        # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def g(date, blue, red, winner):
    return CP.Game(date=date, blue=blue, red=red, winner=winner)


def rows(*pairs):
    """(예측, 블루가 이겼나) 목록을 걸음 꼴로."""
    return [{"p_blue": p, "blue_won": w, "n_blue": 99, "n_red": 99} for p, w in pairs]


def world(strength: dict, n: int, seed: int, coin: bool = False):
    """정답을 아는 원장. coin 이면 실력과 무관하게 반반으로 뽑는다."""
    rng = random.Random(seed)
    teams = list(strength)
    out = []
    for i in range(n):
        x, y = rng.sample(teams, 2)
        p = 0.5 if coin else EL.expect(strength[x], strength[y])
        out.append(g(f"2026-{1 + i // 400:02d}-{1 + i % 28:02d}", x, y,
                     x if rng.random() < p else y))
    return out


print("── 점수 자체가 맞는가 ─────────────────────────────────")
ok(abs(SC.brier(rows((1.0, True), (0.0, False))) - 0.0) < 1e-12,
   "완벽히 맞히면 브라이어 0")
ok(abs(SC.brier(rows((0.0, True), (1.0, False))) - 1.0) < 1e-12,
   "완벽히 틀리면 브라이어 1")
ok(abs(SC.brier(rows((0.5, True), (0.5, False))) - 0.25) < 1e-12,
   "늘 0.5 면 브라이어 0.25 -- 동전던지기의 값")
ok(abs(SC.constant(rows((0.9, True), (0.1, False)), 0.5) - 0.25) < 1e-12,
   "constant 는 예측을 무시하고 상수로만 잰다")
ok(abs(SC.accuracy(rows((0.9, True), (0.8, False), (0.2, False), (0.6, True))) - 0.75) < 1e-12,
   "정확도는 0.5 를 넘겼는지로만 센다")
ok(SC.accuracy(rows((0.5, True), (0.5, False))) == 0.0,
   "**정확히 0.5 는 안 맞힌 것으로 센다** -- 반올림 방향으로 점수를 벌지 않는다")
ok(SC.logloss(rows((0.5, True), (0.5, False))) > 0.69,
   "로그손실도 0.5 에서 ln2 근처다")

print()
print("── 보정 표 ───────────────────────────────────────────")
cal = SC.calibration(rows(*([(0.9, True)] * 9 + [(0.9, False)])), bins=5)
ok(len(cal) == 1 and cal[0][1] == 10, "한 구간에 10경기가 모인다")
ok(abs(cal[0][3] - 0.9) < 1e-9, "0.9 라고 한 경기의 90% 를 이겼으면 실제도 0.9")
ok(abs(SC.calibration(rows((1.0, True)), bins=5)[0][1]) == 1,
   "p=1.0 이 마지막 구간에서 안 새어 나간다 -- 경계 처리")

print()
print("── GREEN: 실력차가 있는 원장 ──────────────────────────")
TRUE = {"S": 1800, "A": 1650, "B": 1500, "C": 1350, "D": 1200}
real = world(TRUE, 1200, seed=20260909)
s = SC.backtest(real, burn=5)
base = min(s["기준_반반"], s["기준_기저율"])
ok(s["n"] > 1000, f"채점한 경기 {s['n']}개 (몸풀기로 {s['뺀것']}개 뺐다)")
ok(s["브라이어"] < base,
   f"**기준선을 이긴다**: 브라이어 {s['브라이어']:.4f} < 기준 {base:.4f} "
   f"({base - s['브라이어']:+.4f})")
ok(s["정확도"] > 0.6, f"정확도 {s['정확도']:.3f} 가 0.6 을 넘는다")
ok(s["로그손실"] < 0.69, f"로그손실 {s['로그손실']:.4f} 가 ln2(0.693) 아래다")
big = [c for c in s["보정"] if c[1] >= 20]
worst = max((abs(c[3] - c[2]) for c in big), default=0.0)
ok(worst < 0.15,
   f"보정이 어긋난 구간이 없다 -- 최대 어긋남 {worst:.3f} (구간 {len(big)}개)")

print()
print("── RED: 동전던지기 원장 -- **못 이겨야 한다** ───────────")
coin = world(TRUE, 1200, seed=777, coin=True)
sc = SC.backtest(coin, burn=5)
base_c = min(sc["기준_반반"], sc["기준_기저율"])
ok(sc["브라이어"] >= base_c - 0.005,
   f"실력차가 없으면 기준선을 못 이긴다: 브라이어 {sc['브라이어']:.4f} vs "
   f"기준 {base_c:.4f} ({sc['브라이어'] - base_c:+.4f})")
ok(abs(sc["정확도"] - 0.5) < 0.05,
   f"정확도도 반반 근처 {sc['정확도']:.3f} -- 없는 신호를 만들어 내지 않는다")

print()
print("── 몸풀기를 빼는가 ───────────────────────────────────")
small = world(TRUE, 40, seed=5)
s0 = SC.backtest(small, burn=0)
s9 = SC.backtest(small, burn=9)
ok(s0["n"] > s9["n"], f"몸풀기를 늘리면 채점 대상이 준다 ({s0['n']} -> {s9['n']})")
ok(s0["뺀것"] == 0, "몸풀기 0 이면 아무것도 안 뺀다")
tiny = SC.backtest(world(TRUE, 6, seed=3), burn=50)
ok(tiny["n"] == 0, "다 빼고 나면 n=0 -- 나눗셈으로 안 죽는다")

print()
print("── 채점기는 예측을 **다시 만들지 않는다** ─────────────")
_, walked, _ = EL.walk(real)
kept = [r for r in walked if r["n_blue"] >= 5 and r["n_red"] >= 5]
ok(len(kept) == s["n"],
   f"백테스트가 센 수({s['n']})와 walk 걸음에서 고른 수({len(kept)})가 같다 -- "
   "두 자리에서 예측을 만들면 언젠가 갈라진다")
ok(abs(SC.brier(kept) - s["브라이어"]) < 1e-12,
   "그 걸음으로 직접 잰 브라이어와도 글자 그대로 같다")

print()
if fails:
    print(f"심판: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print(f"심판 RED/GREEN 통과 -- 신호 있는 원장 {s['브라이어']:.4f} (기준 {base:.4f}) · "
      f"동전던지기 {sc['브라이어']:.4f} (기준 {base_c:.4f})")
