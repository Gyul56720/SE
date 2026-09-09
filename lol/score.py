"""**심판.** 이 모델이 동전던지기보다 나은가. LLM 호출 0회.

    python3 lol/score.py                  # 백테스트 -- 브라이어 · 로그손실 · 보정
    python3 lol/score.py --K 32           # 다른 K 로
    python3 lol/score.py --몸풀기 10      # 팀마다 이만큼 치른 뒤부터 채점한다

## 왜 이 파일이 예측기보다 먼저 있어야 하나

`law/exam.py` 가 적어 둔 그대로다 -- 자기가 만든 자로 자기를 재면 자가 놓친 것은
영영 안 보인다. 승률 예측에서 이게 더 나쁘다: **어떤 숫자를 내놓아도 그럴듯해 보인다.**
55% 라고 하면 55% 같고 62% 라고 하면 62% 같다. 지어낸 숫자와 계산한 숫자가 화면에서
똑같이 생겼다는 것이 이 문제의 전부다.

그래서 **기준선과 나란히 적는다.** 기준선을 못 이기면 못 이겼다고 적는다.

    항상 0.5      아무것도 모르는 자      브라이어 0.250
    진영 기저율   원장의 블루 승률만 아는 자
    Elo           우리 모델

## 브라이어 점수

    B = mean((p - y)^2)      낮을수록 좋다. 0 이 완벽, 0.25 가 동전던지기

정답률(맞혔나)이 아니라 **확신까지 같이 재는** 자다. 55% 로 맞힌 것과 95% 로 맞힌
것을 정답률은 똑같이 세지만 브라이어는 가른다. 승률을 내놓는 모델에는 이쪽이 맞다.

## 보정 -- 60% 라고 한 경기의 60% 를 이기는가

정확도와 다른 축이다. 늘 60% 라고 말하면서 실제로 90% 를 이기면 그 모델은 **맞히지만
거짓말한다.** 승률을 숫자로 내놓는 이상 이 축이 있어야 한다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lol import corpus as CP                                       # noqa: E402
from lol import elo as EL                                          # noqa: E402

# 팀마다 이만큼 치르기 전 경기는 채점에서 뺀다. 전부 1500 에서 시작하므로 그 구간의
# 예측은 동전던지기이고, 넣으면 우리 자가 흐려진다. **뺐다는 것을 화면에 적는다.**
BURN = 5


def brier(rows) -> float:
    return sum((r["p_blue"] - (1.0 if r["blue_won"] else 0.0)) ** 2 for r in rows) / len(rows)


def logloss(rows) -> float:
    import math
    t = 0.0
    for r in rows:
        p = min(max(r["p_blue"], 1e-9), 1 - 1e-9)
        t += -(math.log(p) if r["blue_won"] else math.log(1 - p))
    return t / len(rows)


def accuracy(rows) -> float:
    """0.5 를 넘으면 블루라고 본 것으로 친다. 정확히 0.5 는 안 맞힌 것으로 센다 --
    반올림 방향으로 점수를 벌지 않는다."""
    hit = sum(1 for r in rows
              if (r["p_blue"] > 0.5) == r["blue_won"] and r["p_blue"] != 0.5)
    return hit / len(rows)


def constant(rows, p: float) -> float:
    """무엇을 물어도 늘 p 라고 답하는 자의 브라이어."""
    return sum((p - (1.0 if r["blue_won"] else 0.0)) ** 2 for r in rows) / len(rows)


def calibration(rows, bins: int = 5) -> list:
    """예측 구간마다 (구간, 경기 수, 평균 예측, 실제 승률)."""
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        part = [r for r in rows if (lo <= r["p_blue"] < hi or (i == bins - 1 and r["p_blue"] == 1.0))]
        if not part:
            continue
        out.append((f"{lo:.1f}~{hi:.1f}", len(part),
                    sum(r["p_blue"] for r in part) / len(part),
                    sum(1 for r in part if r["blue_won"]) / len(part)))
    return out


def backtest(games, k: float = EL.K, burn: int = BURN) -> dict:
    """걸음을 만들고 몸풀기를 뺀 뒤 채점한다. **예측은 elo.walk 가 만든 것 그대로다.**

    여기서 예측을 다시 만들지 않는다 -- 두 자리에서 만들면 언젠가 갈라지고, 갈라지면
    채점기가 예측기와 다른 것을 재게 된다.
    """
    _, rows, bias = EL.walk(games, k=k)
    scored = [r for r in rows if r["n_blue"] >= burn and r["n_red"] >= burn]
    if not scored:
        return {"n": 0, "뺀것": len(rows), "진영이점": bias}
    base_rate = sum(1 for r in scored if r["blue_won"]) / len(scored)
    return {
        "n": len(scored), "뺀것": len(rows) - len(scored), "진영이점": bias,
        "브라이어": brier(scored), "로그손실": logloss(scored), "정확도": accuracy(scored),
        "기준_반반": constant(scored, 0.5),
        "기준_기저율": constant(scored, base_rate), "기저율": base_rate,
        "보정": calibration(scored),
    }


def report(s: dict) -> None:
    if not s.get("n"):
        print(f"채점할 경기가 없다 (몸풀기로 {s.get('뺀것', 0)}개를 뺐다).")
        print("  원장이 작으면 --몸풀기 를 낮추되, 낮춘 만큼 자가 흐려진다는 것을 알고 낮춰라.")
        return
    print(f"채점 {s['n']}경기 (몸풀기로 {s['뺀것']}개 뺐다) · "
          f"잰 진영 이점 {s['진영이점']:+.1f} Elo · 블루 승률 {s['기저율']:.3f}")
    print()
    print(f"  브라이어   {s['브라이어']:.4f}   <- 낮을수록 좋다")
    print(f"  기준 반반  {s['기준_반반']:.4f}   (늘 0.5 라고 답하는 자)")
    print(f"  기준 기저  {s['기준_기저율']:.4f}   (원장의 블루 승률만 아는 자)")
    print(f"  로그손실   {s['로그손실']:.4f}")
    print(f"  정확도     {s['정확도']:.3f}")
    print()
    best = min(s["기준_반반"], s["기준_기저율"])
    if s["브라이어"] < best:
        print(f"  **기준선을 이겼다** ({best - s['브라이어']:+.4f}). 이 모델의 승률은 "
              f"기준선보다 나은 정보를 담고 있다.")
    else:
        print(f"  **기준선을 못 이겼다** ({s['브라이어'] - best:+.4f}). 이 모델이 내는 "
              f"승률은 지금 원장에서 동전던지기보다 낫다고 말할 수 없다.")
        print("  숫자를 그럴듯하게 고치지 말고, 원장을 늘리거나 K 를 바꿔서 다시 재라.")
    print()
    print("  보정 -- p 라고 한 경기를 실제로 얼마나 이겼나")
    for label, n, mean_p, actual in s["보정"]:
        gap = actual - mean_p
        flag = "  <- 어긋남" if abs(gap) > 0.15 and n >= 20 else ""
        print(f"    {label}  {n:>4}경기  말한 것 {mean_p:.3f}  실제 {actual:.3f}  "
              f"({gap:+.3f}){flag}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="승률 모델을 기준선과 견준다 (호출 0회)")
    ap.add_argument("--경로", dest="path", default=str(CP.CORPUS_DIR))
    ap.add_argument("--K", dest="k", type=float, default=EL.K)
    ap.add_argument("--몸풀기", dest="burn", type=int, default=BURN)
    a = ap.parse_args(argv)

    c = CP.load(a.path)
    if not c.games:
        print(f"원장이 비어 있다: {a.path}")
        print("  python3 lol/fetch.py --대회 'LCK/2026 Season' 로 먼저 받아라")
        return 3
    print(f"원장: 경기 {len(c)}개 · {c.first_date[:10]} ~ {c.last_date[:10]}")
    print()
    report(backtest(c.games, k=a.k, burn=a.burn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
