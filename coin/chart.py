"""**차트를 읽는다 -- 예측기가 아니라 상황 서술자로.**

    python3 coin/chart.py --자산 BTC
    python3 coin/chart.py --자산 BTC --간격 1h      시간봉으로

## 왜 지표를 넣나, 그리고 왜 이렇게 넣나

이 파이프라인의 중심은 **지금과 닮은 과거 찾기**다. 그러려면 "지금" 을 잘 적어야
하는데, 뉴스와 백분위 셋(추세·변동·낙폭)만으로는 얇다. 차트 지표가 그 자리를 메운다.

**그런데 예측기로 쓰지 않는다.**

    "RSI 30 아래면 산다"        <- 이런 문턱은 여기 없다. 어디서 온 수인지 못 말한다
    "지금 RSI 가 자기 역사의 8% 자리"  <- 이렇게 넣는다. 닮은 날을 찾는 데 쓰인다

전부 **자기 역사의 백분위**로 바꾼다(`regime.py` · `scenario.py` 와 같은 자).
그러면 자산마다 · 시대마다 다른 값 범위를 안 맞춰도 되고, 무엇보다 **문턱을 안 박는다.**

## 넣은 것

    이격      종가가 이동평균에서 얼마나 떨어졌나 (20 · 60)
    RSI       오른 날과 내린 날의 크기 비 (14)
    변동폭    최근 폭이 자기 역사에서 어디쯤 (ATR 비슷하게, 종가 기준)
    거래량    최근 거래량이 자기 역사에서 어디쯤
    몸통      캔들이 몸통인가 꼬리인가 -- 밀어붙인 날인가 되돌린 날인가
    기울기    최근 회귀 기울기 (추세의 세기)

**이 목록이 정답이라고 주장하지 않는다.** 지표는 얼마든지 더 있고, 어느 것이 닮음을
잘 잡는지는 여기서 못 정한다 -- `similar.py` 가 셋을 따로 보여 주므로, 시장 덩이가
답을 끌고 오는지 아닌지는 화면에서 갈린다.

## 여러 눈금 (분·시간·일)

같은 함수를 어느 봉에나 쓴다. 일봉은 추세, 시간봉은 지금 자리, 분봉은 실시간이다.
**섞지 않는다** -- 눈금마다 따로 내고 이름에 눈금을 붙인다(`RSI@1h`). 섞으면
"어느 눈금에서 과매도인가" 를 못 말하게 된다.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _백분위(값, 모음) -> float:
    쓸것 = [v for v in 모음 if v is not None and v == v]
    if not 쓸것 or 값 is None or 값 != 값:
        return float("nan")
    return sum(1 for v in 쓸것 if v <= 값) / len(쓸것)


def 이평(값들: list, n: int) -> list:
    out, 합 = [], 0.0
    for i, v in enumerate(값들):
        합 += v
        if i >= n:
            합 -= 값들[i - n]
        out.append(합 / min(i + 1, n) if i + 1 >= n else None)
    return out


def 이격들(종가: list, n: int) -> list:
    m = 이평(종가, n)
    return [(c / a - 1.0) if a else None for c, a in zip(종가, m)]


def RSI들(종가: list, n: int = 14) -> list:
    """오른 날과 내린 날의 크기 비. 0~100. **문턱을 안 건다** -- 백분위로 바꾼다."""
    out = [None] * len(종가)
    오름, 내림 = 0.0, 0.0
    for i in range(1, len(종가)):
        d = 종가[i] - 종가[i - 1]
        오름 = (오름 * (n - 1) + max(d, 0.0)) / n
        내림 = (내림 * (n - 1) + max(-d, 0.0)) / n
        if i >= n:
            out[i] = 100.0 if 내림 == 0 else 100 - 100 / (1 + 오름 / 내림)
    return out


def 기울기들(종가: list, n: int = 20) -> list:
    """최근 n봉 회귀 기울기를 값 크기로 나눈 것. 추세의 세기."""
    out = [None] * len(종가)
    for i in range(n, len(종가)):
        y = 종가[i - n + 1:i + 1]
        mx = (n - 1) / 2.0
        my = sum(y) / n
        분자 = sum((k - mx) * (v - my) for k, v in enumerate(y))
        분모 = sum((k - mx) ** 2 for k in range(n))
        out[i] = (분자 / 분모 / my) if 분모 and my else None
    return out


def 몸통들(봉: list) -> list:
    """|종가-시가| / (고가-저가). 1 이면 밀어붙인 날, 0 이면 되돌린 날."""
    out = []
    for r in 봉:
        폭 = (r[2] - r[3])
        out.append((abs(r[4] - r[1]) / 폭) if 폭 else None)
    return out


def 재기(봉: list, 눈금: str = "1d", 끝: int = None) -> dict:
    """**전부 자기 역사의 백분위로.** 끝을 주면 그 자리까지의 자료로만 잰다."""
    if len(봉) < 80:
        return {}
    끝 = len(봉) - 1 if 끝 is None else 끝
    봉 = 봉[:끝 + 1]
    종가 = [r[4] for r in 봉]
    양 = [r[5] for r in 봉]
    잰것 = {
        "이격20": 이격들(종가, 20), "이격60": 이격들(종가, 60),
        "RSI": RSI들(종가, 14), "기울기": 기울기들(종가, 20),
        "몸통": 몸통들(봉),
        "변동폭": [((r[2] - r[3]) / r[4]) if r[4] else None for r in 봉],
        "거래량": [float(v) for v in 양],
    }
    out = {}
    for 이름, 계열 in 잰것.items():
        if 죽은칸(계열):
            continue
        지금 = 계열[-1] if 계열 else None
        p = _백분위(지금, 계열)
        if p == p:
            out[f"{이름}@{눈금}"] = p
    return out


def 죽은칸(값들: list) -> bool:
    """**늘 같은 값이면 지표가 아니다.**

    실측 2026-09-09 (VM): `변동폭@1d 100% · 거래량@1d 100%` 가 찍혔다. 고·저·거래량이
    없는 봉으로 잰 것이라 두 계열이 통째로 0 이었고, 0 만 든 계열의 앞선백분위는
    **모든 자리에서 1.0** 이다. 지표가 아니라 허수인데 화면에는 "역대 최고" 로 보인다.

    그리고 그런 칸은 닮음에서 **모든 날이 완벽히 일치**하므로 시장 닮음을 통째로
    부풀린다(그날 0.94~0.96 이 다 비슷했던 까닭).
    """
    본 = [v for v in 값들 if v is not None and v == v]
    if len(본) < 2:
        return True
    첫 = 본[0]
    return all(abs(v - 첫) < 1e-12 for v in 본)


def 앞선백분위(값들: list) -> list:
    """각 자리에서 **그 자리까지의 자료만으로** 잰 백분위. 미리보기가 안 든다.

    한 자리마다 전체를 다시 세면 O(n^2) 이라 3311일에서 못 쓴다(실측: 사용자가
    Ctrl-C 로 끊었다). 정렬된 목록에 넣어 가며 자리를 찾으면 한 번에 끝난다.
    """
    import bisect
    쌓 = []
    out = []
    for v in 값들:
        if v is None or v != v:
            out.append(float("nan"))
            continue
        bisect.insort(쌓, v)
        out.append(bisect.bisect_right(쌓, v) / len(쌓))
    return out


def 전체(봉: list, 눈금: str = "1d") -> list:
    """**모든 자리의 백분위를 한 번에.** `재기` 를 자리마다 부르면 O(n^2) 이 된다.

    돌려주는 것은 자리마다의 dict 목록이고, `similar.py` 가 그것을 그대로 쓴다.
    """
    if len(봉) < 80:
        return [{} for _ in 봉]
    종가 = [r[4] for r in 봉]
    잰것 = {
        "이격20": 이격들(종가, 20), "이격60": 이격들(종가, 60),
        "RSI": RSI들(종가, 14), "기울기": 기울기들(종가, 20),
        "몸통": 몸통들(봉),
        "변동폭": [((r[2] - r[3]) / r[4]) if r[4] else None for r in 봉],
        "거래량": [float(r[5]) for r in 봉],
    }
    # **죽은 칸은 아예 안 낸다** -- 100% 로 찍히면서 닮음을 부풀린다
    쌓 = {이름: 앞선백분위(계열) for 이름, 계열 in 잰것.items()
          if not 죽은칸(계열)}
    out = []
    for i in range(len(봉)):
        d = {}
        for 이름, p들 in 쌓.items():
            p = p들[i]
            if p == p:
                d[f"{이름}@{눈금}"] = p
        out.append(d)
    return out


def 추세전체(종가: list, 창: int = 60) -> list:
    """`regime.추세` 를 자리마다 -- 한 번에. 앞선 백분위."""
    r = [None] * len(종가)
    for i in range(창, len(종가)):
        a = 종가[i - 창]
        r[i] = (종가[i] / a - 1.0) if a else None
    return 앞선백분위(r)


def 변동전체(종가: list, 창: int = 30) -> list:
    """실현변동성을 자리마다. 하루 수익률의 제곱합을 굴려서 O(n) 으로."""
    import math
    수 = [None] + [(종가[i] / 종가[i - 1] - 1.0) if 종가[i - 1] else None
                   for i in range(1, len(종가))]
    합, 제곱합, 센것 = 0.0, 0.0, 0
    out = [None] * len(종가)
    for i in range(len(종가)):
        v = 수[i]
        if v is not None:
            합 += v
            제곱합 += v * v
            센것 += 1
        if i >= 창 and 수[i - 창] is not None:
            합 -= 수[i - 창]
            제곱합 -= 수[i - 창] ** 2
            센것 -= 1
        if 센것 > 2:
            평 = 합 / 센것
            out[i] = math.sqrt(max(0.0, 제곱합 / 센것 - 평 * 평))
    return 앞선백분위(out)


def 낙폭전체(종가: list, 창: int = 365) -> list:
    """고점 대비 낙폭을 자리마다. 굴리는 최대값으로 O(n)."""
    from collections import deque
    큰 = deque()
    out = [None] * len(종가)
    for i, c in enumerate(종가):
        while 큰 and 종가[큰[-1]] <= c:
            큰.pop()
        큰.append(i)
        if 큰[0] <= i - 창:
            큰.popleft()
        고 = 종가[큰[0]]
        out[i] = (c / 고 - 1.0) if 고 else None
    return 앞선백분위(out)


def 날것(봉: list) -> dict:
    """사람이 읽을 원값. 백분위 옆에 같이 적어야 '8% 자리' 가 얼마인지 안다."""
    if len(봉) < 80:
        return {}
    종가 = [r[4] for r in 봉]
    return {"종가": 종가[-1], "RSI": (RSI들(종가, 14) or [None])[-1],
            "이격20": (이격들(종가, 20) or [None])[-1],
            "기울기": (기울기들(종가, 20) or [None])[-1]}


def 적기(p: dict, 원: dict = None) -> str:
    if not p:
        return "  차트: 봉이 모자란다 (80개는 있어야 백분위가 뜻이 있다)"
    줄 = ["  차트 (전부 **자기 역사의 백분위** -- 문턱이 아니다)"]
    for k in sorted(p):
        v = p[k]
        칸 = int(v * 20)
        줄.append(f"    {k:<14} {v*100:5.1f}%  " + "·" * 칸 + "|")
    if 원:
        줄.append("    (원값: " + " · ".join(
            f"{k} {v:.4g}" for k, v in 원.items() if v is not None) + ")")
    return "\n".join(줄)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--자산", default="BTC")
    ap.add_argument("--간격", default="1d")
    a = ap.parse_args(argv)
    from coin import price as PR
    원 = PR.불러오기(a.자산)
    if not 원 or not 원.get("봉"):
        print(f"가격 원장이 없다: {a.자산} -- python3 coin/price.py --받기 {a.자산}",
              file=sys.stderr)
        return 3
    봉 = 원["봉"]
    print(f"{a.자산} · 봉 {len(봉)}개 · 눈금 {a.간격} "
          f"· 시간대 UTC{원.get('시간대', 0):+g}")
    print(적기(재기(봉, a.간격), 날것(봉)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
