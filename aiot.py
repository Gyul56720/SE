"""**3GPP 앰비언트 IoT (Rel-19/20) 의 R2D 링크** -- 1 uW 봉투검출 수신기.

## 왜 이 도메인인가 -- 우리 자가 이 자에 맞는다

이 저장소는 유선 SerDes 를 오래 팠다. 거기서는 sky130(130 nm)이 **우스운 대역**이었다 --
224G/448G 는 3~5 nm 로 만든다. 그래서 면적 숫자가 "그 공정에 대한 진술" 이상이 못 됐다.

**앰비언트 IoT 태그는 실제로 130~180 nm 로 만든다.** 싸야 하고, 누설이 속도보다 중요하고,
RF 정류기가 필요하기 때문이다. 이 도메인에서는 sky130 면적이 **제품 면적과 같은 자리**다.

## 이 판의 병목은 이름이 붙어 있다

    태그 수신 감도   -20 ~ -30 dBm      (Type-A ~ Type-B 는 -50 dBm)
    리더 수신 감도   -90 dBm
                    ------------------
    비대칭           **60 ~ 70 dB**

커버리지를 정하는 것은 둘 중 나쁜 쪽이므로, 이 비대칭이 곧 앰비언트 IoT 의 사거리다.

까닭은 소자에 있다. Rel-19 'device 1' 은 **~1 uW 첨두 전력**, **RF 봉투검출기**(제곱 + LPF),
**증폭 없음**(R2D·D2R 양쪽 다), 초기 SFO **최대 ~10^5 ppm(=10%)**, R2D 는 OOK 만.

증폭기가 없으면 코히런트 처리가 없고, 코히런트 처리가 없으면 제곱법 검출이다. 그리고
제곱법은 약신호에서 **출력 SNR 이 입력 SNR 의 제곱에 비례한다**(signal suppression) --
즉 **입력에서 1 dB 를 잃으면 출력에서 2 dB 를 잃는다.** 감도가 나쁜 자리에서 하필 손실이
두 배로 걸린다.

## 이 모듈이 하는 일

재는 자를 먼저 짓는다. `검증()` 이 시늉이 아니라 **닫힌 꼴과 대조**한다 --
비코히런트 OOK 의 오류율은 지수분포와 비중심 카이제곱으로 정확히 적히므로, 시늉이 그것을
못 맞추면 시늉이 틀린 것이다.

    표기:  r = A + n,  n ~ CN(0, sigma^2)   (실/허수 각각 sigma^2/2)
           z = |r|^2                         (제곱법 봉투검출)
           2z/sigma^2 ~ 비중심카이제곱(자유도 2, 비중심 lambda = 2A^2/sigma^2)

           '0' 이면 A=0 이라 z 는 평균 sigma^2 의 **지수분포**
           P(z > T | 0) = exp(-T/sigma^2)
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import ncx2, expon


# ---------------------------------------------------------------- 규격 상수

규격 = {
    # Rel-19 'device 1' (3GPP). 출처는 표준 문서 -- 우리가 잰 것이 아니다.
    "첨두전력W": 1e-6,
    "SFO_ppm최대": 1e5,          # **10^5 ppm = 10%**. 105 ppm 이 아니다.
    "R2D변조": "OOK",
    "D2R변조": ("OOK", "BPSK", "BFSK"),
    "증폭": False,
    "감도dBm": {"태그(현행)": -20.0, "TypeA": -30.0, "TypeB": -50.0, "리더": -90.0},
}


def 감도비대칭dB() -> float:
    """리더와 태그의 감도 차. **이것이 커버리지를 정한다.**"""
    s = 규격["감도dBm"]
    return float(s["TypeA"] - s["리더"])


# ---------------------------------------------------------------- 검출 통계

def 입력SNR(A: float, sigma: float) -> float:
    """봉투검출기 **입력**의 SNR (선형). A 는 신호 진폭, sigma^2 는 복소 잡음 전력."""
    return float(A * A / (sigma * sigma))


def 출력SNR(A: float, sigma: float, N: int = 1) -> float:
    """제곱법 검출기 **출력**의 SNR. `N` 은 비코히런트 누적 표본 수.

    z = |r|^2 이고 Z = sum_{i<N} z_i 라 하면

        E[Z|1] - E[Z|0] = N*A^2
        Var(Z|0)        = N*sigma^4

    이므로 출력 SNR = (N A^2)^2 / (N sigma^4) = **N * (입력SNR)^2**.

    **이것이 감도 벽의 정체다.** 입력에서 1 dB 를 잃으면 출력에서 2 dB 가 빠진다.
    코히런트 수신기는 이 제곱이 없다 -- 그래서 리더가 -90 dBm 을 하고 태그가 -20 dBm 을 한다.
    """
    s = 입력SNR(A, sigma)
    return float(int(N) * s * s)


def 이론BER(A: float, sigma: float, 문턱: float, N: int = 1) -> float:
    """비코히런트 OOK 의 **닫힌 꼴** 오류율. 등확률 0/1.

    Z = sum |r_i|^2 에 대해 2Z/sigma^2 는 자유도 2N 의 카이제곱이고,
    '1' 이면 비중심 lambda = 2*N*A^2/sigma^2 다.
    """
    N = int(N)
    s2 = sigma * sigma
    x = 2.0 * 문턱 / s2
    거짓경보 = float(ncx2.sf(x, 2 * N, 0.0))          # A=0 이면 중심 카이제곱
    놓침 = float(ncx2.cdf(x, 2 * N, 2.0 * N * A * A / s2))
    return 0.5 * (거짓경보 + 놓침)


def 최적문턱(A: float, sigma: float, N: int = 1, 칸: int = 4000) -> "tuple[float, float]":
    """`이론BER` 을 최소로 만드는 문턱을 훑어 찾는다. (문턱, 그때 BER) 을 돌려준다.

    **중간값이 최적이 아니다.** '0' 은 지수분포(꼬리가 길다)이고 '1' 은 비중심
    카이제곱이라 두 분포가 비대칭이다. 그래서 문턱은 가운데보다 아래로 내려간다.
    """
    s2 = sigma * sigma
    높 = (A * A + s2) * N * 3.0 + 1e-18
    후보 = np.linspace(1e-12, 높, int(칸))
    값 = np.array([이론BER(A, sigma, float(t), N) for t in 후보])
    i = int(np.argmin(값))
    return float(후보[i]), float(값[i])


# ---------------------------------------------------------------- 시늉

def 받기(비트: np.ndarray, A: float, sigma: float, sps: int, rng) -> np.ndarray:
    """OOK 를 보내고 **제곱법 봉투검출**을 통과시킨다. 증폭도 AGC 도 없다.

    복소 잡음을 쓴다 -- 태그에는 반송파 위상 정보가 없으므로 위상은 미지이고,
    검출기가 보는 것은 |r|^2 뿐이다.
    """
    sps = int(sps)
    보낸것 = np.repeat(비트.astype(float), sps) * float(A)
    n = (rng.normal(0.0, sigma / math.sqrt(2.0), 보낸것.shape)
         + 1j * rng.normal(0.0, sigma / math.sqrt(2.0), 보낸것.shape))
    return np.abs(보낸것 + n) ** 2


def 모아서판정(z: np.ndarray, sps: int, 문턱: float, 창: int = None) -> np.ndarray:
    """**integrate-and-dump**: 심볼마다 `창`개 표본을 더해 문턱과 견준다.

    `창` 을 `sps` 보다 작게 주면 심볼의 일부만 쓰는 것이다 -- SFO 로 창이 어긋났을 때
    무슨 일이 나는지 보려고 둔 손잡이다.
    """
    sps = int(sps)
    창 = int(창 or sps)
    n = len(z) // sps
    Z = z[: n * sps].reshape(n, sps)[:, :창].sum(axis=1)
    return (Z > float(문턱)).astype(int)


def SFO주기(z: np.ndarray, ppm: float) -> np.ndarray:
    """표본 클럭이 `ppm` 만큼 틀어진 것을 **다시 샘플링**으로 흉내 낸다.

    10^5 ppm = 10% 면 심볼 열 개마다 한 심볼이 통째로 밀린다. 그래서 3GPP 는 R2D
    파형이 **에지를 실어 나르게** 하고 기기가 그것으로 계속 맞춘다.
    """
    ppm = float(ppm)
    if ppm == 0.0:
        return z
    n = len(z)
    t = np.arange(n) * (1.0 + ppm * 1e-6)
    t = t[t <= n - 1]
    return np.interp(t, np.arange(n), z)


# ---------------------------------------------------------------- 검증

def 검증(씨: int = 0) -> dict:
    """**시늉이 닫힌 꼴을 맞추나.** 못 맞추면 시늉이 틀린 것이다."""
    난것 = {"통과": [], "실패": []}

    def 본다(참, 말):
        (난것["통과"] if 참 else 난것["실패"]).append(말)

    rng = np.random.default_rng(씨)

    # (가) 제곱 법칙 -- 출력 SNR 이 입력 SNR 의 제곱을 따라가나
    sigma = 1.0
    기울기들 = []
    for N in (1, 4, 16):
        SNR입 = np.array([0.03, 0.1, 0.3])          # 약신호 영역
        SNR출 = np.array([출력SNR(math.sqrt(s) * sigma, sigma, N) for s in SNR입])
        기울기 = float(np.polyfit(np.log10(SNR입), np.log10(SNR출), 1)[0])
        기울기들.append(기울기)
    본다(all(abs(g - 2.0) < 1e-9 for g in 기울기들),
       f"약신호에서 출력SNR 의 기울기가 **정확히 2** 다 (잰 것 {기울기들[0]:.6f}) "
       f"-- 입력 1 dB 가 출력 2 dB 다")

    # (나) 시늉 BER 이 닫힌 꼴과 맞나
    맞춤 = []
    for SNRdB in (6.0, 9.0, 12.0):
        s = 10 ** (SNRdB / 10.0)
        A = math.sqrt(s) * sigma
        T, 이론 = 최적문턱(A, sigma, N=1)
        비트 = rng.integers(0, 2, 400000)
        z = 받기(비트, A, sigma, sps=1, rng=rng)
        잰것 = float(np.mean(모아서판정(z, 1, T) != 비트))
        비 = 잰것 / 이론 if 이론 > 0 else float("inf")
        맞춤.append((SNRdB, 이론, 잰것, 비))
    본다(all(0.94 <= b <= 1.06 for *_, b in 맞춤),
       "시늉 BER 이 닫힌 꼴의 6% 안에 든다: "
       + ", ".join(f"{d:.0f}dB {m:.2e}/{t:.2e}={b:.3f}" for d, t, m, b in 맞춤))

    # (다) 최적 문턱이 **가운데가 아니다**
    A = math.sqrt(10 ** 0.9) * sigma
    T, _ = 최적문턱(A, sigma, N=1)
    가운데 = (0.0 + (A * A + sigma * sigma)) / 2.0
    본다(T < 가운데 * 0.98,
       f"최적 문턱 {T:.3f} 이 두 평균의 가운데 {가운데:.3f} 보다 **아래**다 "
       f"({T/가운데:.3f}배) -- '0' 의 지수 꼬리가 길기 때문이다")

    # (라) 누적이 감도를 사 준다 -- 다만 **비코히런트라 sqrt(N) 만**
    s = 10 ** 0.6
    A = math.sqrt(s) * sigma
    b1 = 최적문턱(A, sigma, N=1)[1]
    b16 = 최적문턱(A, sigma, N=16)[1]
    본다(b16 < b1, f"N=16 누적이 BER 을 {b1:.2e} -> {b16:.2e} 로 내린다")

    # (마) 감도 비대칭이 규격대로 읽히나
    본다(abs(감도비대칭dB() - 60.0) < 1e-9,
       f"규격이 말하는 태그-리더 감도 비대칭 = **{감도비대칭dB():.0f} dB**")

    return 난것


def 말로(난것: dict) -> str:
    줄 = [f"  통과 {t}" for t in 난것["통과"]] + [f"  실패 {t}" for t in 난것["실패"]]
    줄.append("전부 통과" if not 난것["실패"] else f"{len(난것['실패'])}개 실패")
    return "\n".join(줄)


if __name__ == "__main__":
    print(말로(검증()))
