# -*- coding: utf-8 -*-
"""house/syn/pvt -- PVT 코너와 OCV 를 셈한다.

**왜 직접 지었나.** OpenSTA·PrimeTime 이 없고, `lab/lib/nsw10.lib` 은 공칭 코너
하나뿐이다(PDK 가 아니라 RC 모형에서 만든 것이므로 코너별 .lib 이 없다). 코너를
말만 하고 넘어가는 대신, **소자 모형에서 지연 배수를 셈해** 공칭 STA 결과에 건다.

모형 (T1/T20 의 α 제곱 법칙):
    I_d  ∝ μ(T) · (V − V_th(T))^α           α ≈ 1.3
    μ(T) ∝ T^(−1.5)                          포논 산란
    V_th(T) = V_th0 + dVth/dT · (T − 25)     dVth/dT ≈ −0.8 mV/K
    지연 ∝ C·V / I_d

그래서 지연 배수 = [V / (V−V_th(T))^α] · T^1.5 를 공칭으로 정규화한 값이다.
**이것은 파운드리 특성화가 아니다.** 코너 <i>사이의 비</i>는 물리에서 나오고,
절댓값은 라이브러리의 공칭값에 묶여 있다. 보고서에 그대로 적는다.

온도 반전(temperature inversion)이 이 모형에서 실제로 나온다 -- 오버드라이브가
작으면 V_th 가 내려가는 효과가 이동도 효과를 이겨서 **차가울 때 더 느려진다**.
"""
from __future__ import annotations

import math

# 공정 코너: 문턱과 구동의 전역 이동
공정 = {
    "ss": {"이름": "slow-slow", "Vth0": 0.52, "구동배수": 1.22, "누설배수": 0.45},
    "tt": {"이름": "typical", "Vth0": 0.45, "구동배수": 1.00, "누설배수": 1.00},
    "ff": {"이름": "fast-fast", "Vth0": 0.38, "구동배수": 0.82, "누설배수": 2.60},
}
알파 = 1.3
dVth_dT = -0.0008        # V/K
공칭 = {"V": 1.8, "T": 25.0, "P": "tt"}


def vth(P: str, T: float) -> float:
    return 공정[P]["Vth0"] + dVth_dT * (T - 25.0)


def 지연배수(P: str, V: float, T: float) -> float:
    """공칭(tt, 1.8 V, 25 °C) 대비 지연 배수.  1보다 크면 느리다."""
    def raw(P_, V_, T_):
        ov = V_ - vth(P_, T_)
        if ov <= 0.02:
            return float("inf")
        TK = T_ + 273.15
        return (V_ / (ov ** 알파)) * (TK ** 1.5)
    기준 = raw(공칭["P"], 공칭["V"], 공칭["T"])
    v = raw(P, V, T)
    if v == float("inf"):
        return float("inf")
    return (v / 기준) * 공정[P]["구동배수"]


def 누설배수(P: str, V: float, T: float) -> float:
    """누설은 문턱에 지수로, 온도에 지수로 붙는다."""
    n, kT = 1.35, 0.0259 * (T + 273.15) / 298.15
    return (공정[P]["누설배수"]
            * math.exp((vth("tt", 25.0) - vth(P, T)) / (n * kT))
            * (V / 공칭["V"]) ** 2)


def 코너표(공정들=("ss", "tt", "ff"), 전압들=(1.62, 1.80, 1.98),
         온도들=(-40.0, 25.0, 125.0)) -> list:
    out = []
    for P in 공정들:
        for V in 전압들:
            for T in 온도들:
                d = 지연배수(P, V, T)
                out.append({"P": P, "V": V, "T": T,
                           "지연배수": (None if d == float("inf") else round(d, 4)),
                           "누설배수": round(누설배수(P, V, T), 3)})
    return out


def 온도반전점(P="tt", V들=None) -> list:
    """전압을 쓸어 '차가울 때 더 느린' 자리를 찾는다.  이것이 코너 목록을 정한다."""
    V들 = V들 or [0.60, 0.70, 0.80, 0.90, 1.10, 1.30, 1.50, 1.80, 1.98]
    out = []
    for V in V들:
        d냉 = 지연배수(P, V, -40.0)
        d열 = 지연배수(P, V, 125.0)
        if d냉 == float("inf") or d열 == float("inf"):
            out.append({"V": V, "cold": None, "hot": None, "반전": None})
            continue
        out.append({"V": V, "cold": round(d냉, 4), "hot": round(d열, 4),
                   "반전": bool(d냉 > d열)})
    return out


def 반전전압_닫힌꼴(P="tt", T=25.0) -> float:
    """d(ln 지연)/dT = 0 -> V − V_th = α·|dVth/dT|·(T+273.15)/1.5."""
    TK = T + 273.15
    ov = 알파 * abs(dVth_dT) * TK / 1.5
    return vth(P, T) + ov


def 반전전압_수치(P="tt", T=25.0, lo=0.4, hi=3.0) -> float:
    """같은 값을 **다른 길로** 구한다 -- 수치 미분의 부호를 이분법으로 좁힌다."""
    def dlnd_dT(V):
        h = 0.5
        a, b = 지연배수(P, V, T - h), 지연배수(P, V, T + h)
        if a == float("inf") or b == float("inf") or a <= 0 or b <= 0:
            return -1.0
        return (math.log(b) - math.log(a)) / (2 * h)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if dlnd_dT(mid) < 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def ocv스큐(삽입지연_ns: float, 공통몫=0.98, 늦은=1.07, 이른=0.93) -> dict:
    """공통 경로가 지워지지 않는 몫.  실효 스큐 = (1.00·늦은 − 공통몫·이른)·삽입지연."""
    비 = 1.00 * 늦은 - 공통몫 * 이른
    return {"공통몫": 공통몫, "늦은배수": 늦은, "이른배수": 이른,
            "실효비": round(비, 6), "실효스큐_ps": round(비 * 삽입지연_ns * 1e3, 2)}
