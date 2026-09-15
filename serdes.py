"""와이어라인 SerDes 링크를 **실제로 돌려 BER 을 잰다** -- 채널·CTLE·FFE·DFE·CDR.

사용자(2026-09-15)가 고른 연구 주제:
"경량화(양자화·프루닝) 신경망 기반 wireline SerDes 등화기의 FPGA 실시간 구현".
그 방법론의 1~2 단계(채널 모델링, CTLE+DFE(LMS) 기준선, BER)가 여기다. 4 단계
(비트폭 대비 BER 곡선)도 여기서 재고, 5 단계(FPGA 자원·Fmax)는 `pnr.py` 가 받는다.

교안(2026 VLSI ch0)의 **Eye Diagram** 과 ch4 의 **CDR/PLL** 이 같은 자리에서 만난다.

## 이 판에는 거짓 초록이 넷이다 -- 전부 실측으로 확인했다

    1. 오류 0 을 BER 0 이라 부르는 것
    2. 학습에 쓴 비트로 BER 을 재는 것
    3. DFE 에 **진짜 판정 대신 정답 비트**를 먹이는 것
    4. LMS 가 발산했는데 마지막 MSE 만 보는 것

셋째가 제일 조용하다. DFE 는 제가 방금 내린 판정을 되먹이므로 한 번 틀리면 그 오류가
뒤로 번진다(error propagation). 정답 비트를 먹이면 그 번짐이 통째로 사라져서 BER 이
실제보다 몇 자릿수 좋게 나온다. 하드웨어는 정답을 모른다.

## SNR 의 정의를 못 박는다

`SNRdB` 는 **손실 없는 이상적 링크의 메인 커서(=1)에 견준** 잡음이다.
    sigma = 10 ** (-SNRdB / 20)
그래서 손실 0 · 등화 없음이면 닫힌 꼴 `BER = Q(10^(SNRdB/20))` 이 나와야 한다.
`tests/test_serdes.py` 가 그것으로 이 시뮬레이터를 **교정**한다 -- 정의가 없는
SNR 은 아무 숫자나 된다.
"""
from __future__ import annotations

import math

import numpy as np

PASS, FAIL, 못잼 = "PASS", "FAIL", "못잼"


def Q(x: float) -> float:
    """가우시안 꼬리 확률. `BER = Q(A/sigma)` 의 그 Q."""
    return 0.5 * math.erfc(x / math.sqrt(2.0))


# ---------------------------------------------------------------- 채널

def 채널(손실dB: float = 20.0, sps: int = 16, 길이심볼: int = 64) -> np.ndarray:
    """Nyquist 에서 `손실dB` 만큼 죽는 **최소위상** 채널의 임펄스 응답.

    스킨이펙트꼴로 `|H(f)| = 10^(-(손실dB/20)·sqrt(f/f_nyq))` 을 세우고, 로그 크기의
    켑스트럼으로 최소위상을 붙인다. **선형위상으로 두면 안 된다** -- 그러면 커서가
    앞뒤로 대칭이 되어 후행 커서만 지우는 DFE 가 뜻을 잃는다. 진짜 채널의 꼬리는
    뒤로 끌린다.
    """
    N = int(sps * 길이심볼)
    f = np.fft.rfftfreq(N, 1.0)          # 0 .. 0.5 (심볼률 sps 배 기준)
    f_nyq = 0.5 / sps                    # 심볼률의 절반
    크기 = 10.0 ** (-(손실dB / 20.0) * np.sqrt(np.maximum(f, 0.0) / f_nyq))
    크기 = np.maximum(크기, 1e-9)
    # 최소위상 재구성(실켑스트럼 접기)
    전체 = np.concatenate([크기, 크기[-2:0:-1]])
    c = np.fft.ifft(np.log(전체)).real
    m = np.zeros(N)
    m[0] = c[0]
    m[1:N // 2] = 2.0 * c[1:N // 2]
    m[N // 2] = c[N // 2]
    h = np.fft.ifft(np.exp(np.fft.fft(m))).real
    return h


def 펄스응답(h: np.ndarray, sps: int) -> np.ndarray:
    """한 심볼(NRZ 사각 펄스)이 채널을 지나 나온 꼴."""
    return np.convolve(h, np.ones(sps), mode="full")


def 커서들(h: np.ndarray, sps: int) -> dict:
    """메인 커서와 앞뒤 커서. **ISI 가 여기서 보인다.**

    메인 커서는 펄스응답에서 제일 큰 표본이고, 나머지 심볼 간격 표본이 전부 ISI 다.
    `아이높이_ISI` 는 잡음이 없어도 최악 데이터 패턴에서 남는 눈높이다(peak distortion).
    """
    p = 펄스응답(h, sps)
    k = int(np.argmax(np.abs(p)))
    앞 = list(range(k - sps * 8, k, sps))
    뒤 = list(range(k + sps, k + sps * 25, sps))
    선행 = [float(p[i]) for i in 앞 if 0 <= i < len(p)]
    후행 = [float(p[i]) for i in 뒤 if 0 <= i < len(p)]
    메인 = float(p[k])
    ISI = sum(abs(x) for x in 선행) + sum(abs(x) for x in 후행)
    return {"메인": 메인, "선행": 선행, "후행": 후행, "ISI": ISI,
            "아이높이_ISI": 2.0 * (abs(메인) - ISI), "표본자리": k}


# ---------------------------------------------------------------- CTLE

def CTLE(x: np.ndarray, sps: int, 피킹dB: float = 6.0,
         영점비: float = 0.25, 극점비: float = 1.0) -> np.ndarray:
    """연속시간 선형 등화기. **고주파를 들어 올려 채널 손실을 되돌린다.**

    1영점 2극점 꼴이다. 영점/극점은 Nyquist 에 견준 비율로 준다. CTLE 는 선형이므로
    **잡음도 같이 들어 올린다** -- 그래서 피킹을 올린다고 BER 이 계속 좋아지지 않는다.
    이 시뮬레이터가 그것을 실제로 보여 준다.
    """
    N = len(x)
    f = np.fft.rfftfreq(N, 1.0)
    f_nyq = 0.5 / sps
    s = 1j * (f / f_nyq)
    wz, wp = 영점비, 극점비
    A = 10.0 ** (피킹dB / 20.0)
    H = (1.0 + s / wz) / ((1.0 + s / (wp * A)) * (1.0 + s / (wp * 2.0)))
    H = H / abs(H[0]) if abs(H[0]) > 0 else H     # DC 이득 1 로 못 박는다
    return np.fft.irfft(np.fft.rfft(x) * H, n=N)


# ---------------------------------------------------------------- 등화기

def 양자화(탭: np.ndarray, 비트: int) -> np.ndarray:
    """대칭 고정소수점으로 자른다. `비트` 는 부호를 포함한 전체 폭.

    연구 기여 2번(비트폭 대비 BER 곡선)이 이 함수 위에 선다. 스케일은 최댓값 기준이다 --
    **0 비트는 없다**: 부호 하나만 남으면 비트 1 이고, 그때 탭은 ±최댓값뿐이다.
    """
    탭 = np.asarray(탭, dtype=float)
    if 비트 <= 0:
        raise ValueError("비트는 1 이상이어야 한다")
    큰것 = float(np.max(np.abs(탭))) if 탭.size else 0.0
    if 큰것 == 0.0:
        return 탭.copy()
    단계 = 2 ** (비트 - 1) - 1
    if 단계 < 1:                       # 비트=1 -> 부호만 남는다
        return np.sign(탭) * 큰것
    return np.round(탭 / 큰것 * 단계) / 단계 * 큰것


def 프루닝(탭: np.ndarray, 남길비율: float) -> np.ndarray:
    """작은 탭부터 0 으로. 남는 것의 비율을 `남길비율`(0~1) 로 준다."""
    탭 = np.asarray(탭, dtype=float).copy()
    남길 = max(1, int(round(남길비율 * 탭.size)))
    if 남길 >= 탭.size:
        return 탭
    문턱 = np.sort(np.abs(탭))[::-1][남길 - 1]
    탭[np.abs(탭) < 문턱] = 0.0
    return 탭


def ADC(x: np.ndarray, 비트: int, 풀스케일: float) -> "tuple[np.ndarray, float]":
    """균일 ADC. **분해능만이 아니라 자르기(클리핑)까지 모형에 넣는다.**

    ADC 는 두 숫자로 정해진다 -- 몇 비트인가(분해능)와 어디까지 받나(풀스케일).
    풀스케일을 좁히면 큰 표본이 잘리고, 넓히면 같은 비트로 더 성긴 눈금을 쓴다.
    **그 맞바꿈이 진짜 설계 결정이라 둘을 따로 못 쓴다** -- 비트만 쓸면 풀스케일을
    이미 최적이라 가정한 것이고, 그 가정은 잰 적이 없다.

    돌려주는 것: (양자화된 표본, 잘린 비율). 잘린 비율을 같이 내는 까닭은 링크가
    5% 를 자르고도 BER 이 그럭저럭 나올 수 있어서다 -- 그 BER 은 분해능의 성적이
    아니라 범위 부족의 성적이다.
    """
    if 비트 <= 0:
        return x, 0.0
    단계수 = 2 ** (비트 - 1)
    if 풀스케일 <= 0:
        return x, 0.0
    눈금 = 풀스케일 / 단계수
    코드 = np.round(x / 눈금)
    잘린 = np.clip(코드, -단계수, 단계수 - 1)
    클립 = float(np.mean(코드 != 잘린)) if 코드.size else 0.0
    return 잘린 * 눈금, 클립


def LMS_FFE(받은것: np.ndarray, 정답: np.ndarray, 탭수: int, 지연: int,
            걸음: float = 0.01) -> dict:
    """FFE 탭을 LMS 로 맞춘다. **발산했는지 본다.**

    LMS 는 걸음이 크면 발산하는데, 발산한 탭으로도 BER 은 그냥 나쁘게 나올 뿐이라
    "등화가 잘 안 되네" 로 읽히기 쉽다. 여기서는 탭이 터졌으면 터졌다고 말한다.
    """
    w = np.zeros(탭수)
    w[지연] = 1.0
    오차기록 = []
    for n in range(탭수, len(받은것)):
        x = 받은것[n - 탭수 + 1:n + 1][::-1]
        k = n - 지연
        if k < 0 or k >= len(정답):
            continue
        e = 정답[k] - float(w @ x)
        w = w + 걸음 * e * x
        오차기록.append(e * e)
        if not np.all(np.isfinite(w)) or np.max(np.abs(w)) > 1e6:
            return {"탭": w, "발산": True, "MSE": float("inf"),
                    "왜": (f"**LMS 가 발산했다** -- 걸음 {걸음} 이 크다. 탭이 "
                          f"{np.max(np.abs(w)):.3g} 까지 갔다. 걸음을 10배 줄여라")}
    꼬리 = 오차기록[-max(1, len(오차기록) // 10):] or [float("inf")]
    return {"탭": w, "발산": False, "MSE": float(np.mean(꼬리)),
            "왜": f"수렴했다 -- 마지막 10% 구간 MSE {np.mean(꼬리):.4g}"}


# ---------------------------------------------------------------- 링크

def 링크(비트수: int = 20000, 손실dB: float = 20.0, SNRdB: float = 20.0,
       sps: int = 8, CTLE피킹dB: float = 0.0, FFE탭: int = 0, DFE탭: int = 0,
       탭비트: int = 0, 남길비율: float = 1.0, 이상적판정: bool = False,
       ADC비트: int = 0, ADC풀스케일시그마: float = 3.0,
       학습비율: float = 0.3, 씨: int = 0) -> dict:
    """PRBS -> 채널 -> 잡음 -> CTLE -> FFE -> DFE -> 슬라이서. {BER, 오류수, ...}.

    **학습 구간과 측정 구간을 가른다.** 탭은 앞 `학습비율` 만큼으로 맞추고 BER 은
    나머지에서만 센다. 같은 비트로 맞추고 재면 그 BER 은 등화기 성능이 아니라 암기다.

    **정렬을 재서 한다.** 채널은 지연을 낳으므로 `표본[i]` 에 실린 것은 `b[i]` 가
    아니라 `b[i-지연]` 이다. 첫 판은 이 밀기를 안 해서 **BER 이 전부 0.5 로 나왔다**
    (동전 던지기) -- 등화기가 나쁜 것처럼 보였지만 실은 정답을 엉뚱한 데 대고 있었다.
    """
    rng = np.random.default_rng(씨)
    b = rng.integers(0, 2, 비트수) * 2 - 1        # ±1 NRZ
    h = 채널(손실dB, sps, 64)

    보낸것 = np.repeat(b, sps).astype(float)
    y = np.convolve(보낸것, h, mode="full")[:len(보낸것)]
    # SNR 정의: **손실 없는 이상적 메인 커서(=1)** 에 견준다. 머리말 참조.
    sigma = 10.0 ** (-SNRdB / 20.0)
    y = y + rng.normal(0.0, sigma, len(y))
    if CTLE피킹dB:
        y = CTLE(y, sps, CTLE피킹dB)

    # 표본 위상·지연을 **펄스응답에서 재서** 고른다
    p = 펄스응답(h, sps)
    꼭대기 = int(np.argmax(np.abs(p)))
    위상, 지연심볼 = 꼭대기 % sps, 꼭대기 // sps
    표본 = y[위상::sps]
    if 지연심볼:
        표본 = 표본[지연심볼:]
    맞춘것 = b[:len(표본)]
    표본 = 표본[:len(맞춘것)]
    학습끝 = int(np.clip(len(표본) * 학습비율, 0, len(표본) - 1))
    학습 = slice(0, max(학습끝, 1))

    # ADC -- **아날로그 AGC 가 풀스케일을 잡고 그 다음에 양자화된다.** 여기 뒤로는
    # 전부 디지털이므로 FFE·DFE 는 양자화된 표본만 본다.
    클립비율 = 0.0
    if ADC비트 and ADC비트 > 0:
        rms = float(np.sqrt(np.mean(표본[학습] ** 2))) or 1.0
        표본, 클립비율 = ADC(표본, int(ADC비트), ADC풀스케일시그마 * rms)

    # AGC: 메인 커서 이득을 **학습 구간의 상관으로 잰다**(수신기가 아는 것만 쓴다)
    g = float(np.mean(표본[학습] * 맞춘것[학습])) or 1.0
    표본 = 표본 / g

    적응 = {"왜": "FFE 를 안 썼다", "발산": False, "MSE": float("nan"), "탭": None}
    if FFE탭 > 0:
        지연 = FFE탭 // 2
        힘 = float(np.mean(표본[학습] ** 2)) or 1.0
        적응 = LMS_FFE(표본[학습], 맞춘것[학습], FFE탭, 지연, 걸음=0.02 / 힘)
        if 적응["발산"]:
            return {"BER": float("nan"), "오류수": -1, "잰비트": 0, "표본": 표본,
                    "비트": 맞춘것, "판정": 못잼, "왜": 적응["왜"], "적응": 적응,
                    "DFE탭": None, "이상적판정": 이상적판정,
                    "ADC비트": int(ADC비트), "클립비율": 클립비율,
                    "ADC풀스케일시그마": ADC풀스케일시그마}
        w = 적응["탭"]
        if 탭비트:
            w = 양자화(w, 탭비트)
        if 남길비율 < 1.0:
            w = 프루닝(w, 남길비율)
        적응["쓴탭"] = list(map(float, w))
        나온것 = np.convolve(표본, w, mode="full")
        표본 = 나온것[지연:지연 + len(맞춘것)]
        g2 = float(np.mean(표본[학습] * 맞춘것[학습])) or 1.0
        표본 = 표본 / g2

    # DFE 탭을 **지금 이 파형의 후행 커서로 잰다** -- 채널 h 의 커서가 아니다.
    # CTLE·FFE 를 지난 뒤 남은 ISI 라야 DFE 가 지울 것이 맞는다.
    dfe탭값 = None
    if DFE탭 > 0:
        탭 = []
        for m in range(1, DFE탭 + 1):
            앞 = 표본[학습][m:]
            뒤 = 맞춘것[학습][:-m] if m else 맞춘것[학습]
            n = min(len(앞), len(뒤))
            탭.append(float(np.mean(앞[:n] * 뒤[:n])) if n else 0.0)
        dfe탭값 = np.array(탭)
        if 탭비트:
            dfe탭값 = 양자화(dfe탭값, 탭비트)
        if 남길비율 < 1.0:
            dfe탭값 = 프루닝(dfe탭값, 남길비율)

    판정 = _슬라이스(표본, dfe탭값, 맞춘것 if 이상적판정 else None)

    잰것 = slice(학습끝, len(판정))
    오류 = int(np.sum(판정[잰것] != 맞춘것[잰것]))
    잰비트 = int(잰것.stop - 잰것.start)
    return {"BER": (오류 / 잰비트) if 잰비트 else float("nan"),
            "오류수": 오류, "잰비트": 잰비트, "표본": 표본, "비트": 맞춘것,
            "위상": 위상, "지연심볼": 지연심볼, "sigma": sigma, "적응": 적응,
            "ADC비트": int(ADC비트), "클립비율": 클립비율,
            "ADC풀스케일시그마": ADC풀스케일시그마,
            "DFE탭": None if dfe탭값 is None else list(map(float, dfe탭값)),
            "이상적판정": 이상적판정, "판정": PASS,
            "왜": BER말(오류, 잰비트)}


def 받은파형(비트수: int = 4000, 손실dB: float = 20.0, SNRdB: float = 26.0,
         sps: int = 8, CTLE피킹dB: float = 0.0, 씨: int = 0) -> np.ndarray:
    """채널(과 CTLE)까지만 지난 **오버샘플 파형**. 아이 다이어그램용.

    `링크()` 가 돌려주는 `표본` 은 심볼률로 이미 뽑은 것이라 접을 수가 없다 --
    눈을 그리려면 심볼 안을 여러 점으로 본 파형이 있어야 한다.
    """
    rng = np.random.default_rng(씨)
    b = rng.integers(0, 2, int(비트수)) * 2 - 1
    y = np.convolve(np.repeat(b, sps).astype(float), 채널(손실dB, sps, 64),
                    mode="full")[:int(비트수) * sps]
    y = y + rng.normal(0.0, 10.0 ** (-SNRdB / 20.0), len(y))
    return CTLE(y, sps, CTLE피킹dB) if CTLE피킹dB else y


def _슬라이스(표본: np.ndarray, dfe탭, 정답) -> np.ndarray:
    """문턱 0 슬라이서. DFE 가 있으면 **한 심볼씩 순차로** 돈다(되먹임이라 벡터화 못 한다)."""
    if dfe탭 is None or len(dfe탭) == 0:
        return np.where(표본 >= 0, 1, -1)
    n마디 = len(dfe탭)
    난것 = np.zeros(len(표본), dtype=int)
    지난판정 = np.zeros(n마디)
    for i in range(len(표본)):
        v = 표본[i] - float(dfe탭 @ 지난판정)
        난것[i] = 1 if v >= 0 else -1
        # **되먹이는 것은 판정이다.** `정답` 을 먹이면 오류 번짐이 사라져 BER 이
        # 실제보다 좋게 나온다 -- 하드웨어는 정답을 모른다.
        먹일것 = float(정답[i]) if 정답 is not None and i < len(정답) else float(난것[i])
        지난판정 = np.concatenate([[먹일것], 지난판정[:-1]])
    return 난것


def BER말(오류: int, 잰비트: int) -> str:
    """**오류 0 은 BER 0 이 아니다.** 3의 규칙으로 위쪽 한계를 같이 말한다."""
    if 잰비트 <= 0:
        return "**잰 비트가 없다** -- 측정이 아니다"
    if 오류 == 0:
        return (f"{잰비트:,}비트에 오류 0. 그래도 참 BER 은 {3.0 / 잰비트:.2e} 까지 갈 수 "
                f"있다(3의 규칙). **오류 0 은 BER 0 이 아니다** -- 더 세려면 비트를 늘려라")
    ber = 오류 / 잰비트
    상대 = 1.0 / math.sqrt(오류)
    return (f"BER {ber:.3e} ({오류:,}/{잰비트:,}). 오류 {오류}개면 상대오차가 "
            f"±{100 * 상대:.0f}% 다(1/sqrt(N))")


# ---------------------------------------------------------------- 아이

def 눈한가운데(높이: np.ndarray) -> int:
    """틀을 다시 자를 위상 -- **눈이 제일 크게 열린 곳**을 한가운데로 둔다.

    `argmax` 로 잡으면 안 된다 -- 이상적인 NRZ 는 모든 위상의 눈높이가 같아서 argmax
    가 0 번을 집고, 그러면 틀이 심볼 경계에 걸려 **한가운데에 천이가 놓인다**.
    실측 2026-09-15: 그래서 완벽히 열린 눈의 너비가 0.50 UI 로 나왔다(1.00 이어야 한다).
    """
    n = len(높이)
    높이 = np.asarray(높이, dtype=float)
    쓸것 = 높이[np.isfinite(높이)]
    if 쓸것.size and float(쓸것.max() - 쓸것.min()) <= 1e-9 * max(1.0, abs(float(쓸것.max()))):
        # 높이가 **평평하다** = 이상적인 NRZ. argmax 는 0 번을 집고, 그러면 틀이 심볼
        # 경계에 걸려 한가운데에 천이가 놓인다(실측: 완전히 열린 눈이 0.50 UI 로 나왔다).
        #
        # 첫 판은 "모든 위상이 열렸나(`높이 > 0`)" 로 갈랐는데 **너무 헐거웠다** --
        # 6dB 채널의 1e-5 짜리 실눈도 '열림' 으로 세어 평평한 것으로 잘못 보았고,
        # 그래서 틀이 안 돌아가 최적 표본점이 +0.44 UI 에 찍혔다(실측 2026-09-15).
        return n // 2
    return int(np.argmax(높이))


def 아이재기(표본파형: np.ndarray, sps: int, 버릴앞: int = 64) -> dict:
    """아이 다이어그램을 **접어서 잰다** -- 눈높이(V)와 눈너비(UI).

    교안(2026 VLSI ch0): "if we fold the voltage move in each period into one frame".

    눈높이는 눈이 제일 크게 열린 위상에서 위쪽 무리의 최솟값과 아래쪽 무리의 최댓값
    차이다. **눈너비는 영교차의 산포로 잰다** -- 계측기가 쓰는 정의다. 첫 판은
    "높이가 0 보다 큰 위상의 수" 로 셌는데, 그러면 **20dB 손실로 눈높이가 0.001 V
    까지 닫힌 파형이 눈너비 1.00 UI 로 나왔다**(실측). 세로로 닫힌 눈을 가로로는
    활짝 열렸다고 말한 셈이다.

    ## 잰 눈은 **본 데이터의 눈**이다

    여기 나오는 값은 준 비트열에서 실제로 나타난 최악 패턴의 눈이다. 최악 **가능**
    패턴의 눈은 `커서들()['아이높이_ISI']`(peak distortion) 이고 그쪽이 더 나쁘다 --
    무작위 4천 비트로는 최악 패턴이 안 나온다. 둘을 같은 것으로 말하지 않는다.
    """
    x = np.asarray(표본파형, dtype=float)
    x = x[버릴앞 * sps:] if len(x) > 버릴앞 * sps * 2 else x
    n = (len(x) // sps) * sps
    if n < sps * 4:
        return {"눈높이": float("-inf"), "눈너비UI": 0.0, "위상별높이": [],
                "틀": np.zeros((0, sps)), "sps": sps, "왜": "**잰 표본이 너무 적다**"}
    def 틀짓기(오프셋):
        잘린 = x[오프셋:]
        m = (len(잘린) // sps) * sps
        return 잘린[:m].reshape(-1, sps)

    def 높이재기(틀):
        난것 = []
        for j in range(틀.shape[1]):
            칸 = 틀[:, j]
            위, 아래 = 칸[칸 >= 0], 칸[칸 < 0]
            난것.append(float(위.min() - 아래.max()) if len(위) and len(아래)
                      else float("-inf"))
        return np.array(난것)

    중심 = 눈한가운데(높이재기(틀짓기(0)))
    # **다시 자른다 -- 굴리지 않는다.** `np.roll` 은 한 심볼의 끝을 제 앞머리에 이어
    # 붙여 가짜 이음매를 만든다(실측 2026-09-15: 그 이음매가 t=0 에 세로 다발로
    # 그려져 눈이 엉뚱한 데 있는 것처럼 보였다). 계측기는 트리거 위상을 옮긴다.
    틀 = 틀짓기((중심 - sps // 2) % sps)
    높이 = 높이재기(틀)
    if 틀.shape[0] < 4:
        return {"눈높이": float("-inf"), "눈너비UI": 0.0, "위상별높이": [],
                "틀": 틀, "sps": sps, "왜": "**잰 표본이 너무 적다**"}
    가운데 = sps // 2
    왼끝, 오른끝 = 0.0, float(sps)
    for 줄 in 틀:
        부호 = np.sign(줄)
        바뀜 = np.nonzero(np.diff(부호) != 0)[0]      # j 와 j+1 사이에서 교차
        왼 = 바뀜[바뀜 < 가운데]
        오 = 바뀜[바뀜 >= 가운데]
        if len(왼):
            왼끝 = max(왼끝, float(왼.max()) + 1.0)
        if len(오):
            오른끝 = min(오른끝, float(오.min()))
    너비 = max(0.0, (오른끝 - 왼끝) / sps)
    # **높이는 눈이 제일 크게 열린 위상에서 잰다**(최적 표본 위상 = CDR 이 맞추려는 곳),
    # **너비는 영교차 산포로 잰다.** 둘은 다른 위상의 물음이다 -- 최소위상 채널은
    # 앞뒤가 안 대칭이라 한가운데가 곧 최적 표본점이 아니다(실측: 6dB 에서 0.54 대 0.90).
    # 같은 높이가 여럿이면(이상적인 NRZ 는 전부 같다) **한가운데에 제일 가까운 것**을
    # 고른다. 그냥 argmax 면 0 번을 집어 최적 표본점이 -0.50 UI 로 찍힌다.
    유한 = 높이[np.isfinite(높이)]
    꼭대기 = float(유한.max()) if 유한.size else float("-inf")
    후보 = [j for j in range(sps)
          if np.isfinite(높이[j]) and 높이[j] >= 꼭대기 - 1e-12 * max(1.0, abs(꼭대기))]
    최고자리 = min(후보, key=lambda j: abs(j - sps / 2.0)) if 후보 else int(np.argmax(높이))
    최고 = float(높이[최고자리])
    return {"눈높이": 최고, "눈너비UI": 너비, "위상별높이": list(map(float, 높이)),
            "최적표본위상UI": (최고자리 - sps / 2.0) / sps,
            "틀": 틀, "sps": sps,
            "왜": ("**눈이 닫혔다** -- 어느 위상에서도 위아래 무리가 겹친다"
                  if not np.isfinite(최고) or 최고 <= 0 else
                  f"eye height {최고:.3f} V at {(최고자리 - sps / 2.0) / sps:+.2f} UI · "
                  f"eye width {너비:.2f} UI "
                  f"(worst pattern **seen in this data**, not worst possible)")}


def 아이그리기(표본파형: np.ndarray, sps: int, 낼곳: str, 제목: str = "") -> dict:
    """아이 다이어그램 PNG. 라벨은 영어로 쓴다(한글은 글꼴이 없으면 두부가 된다)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = 아이재기(표본파형, sps)
    틀 = r["틀"]
    보일것 = 틀[: min(len(틀), 2000)]
    t = np.linspace(-0.5, 0.5, sps, endpoint=False)
    fig, ax = plt.subplots(figsize=(6.0, 3.6), dpi=140)
    for 줄 in 보일것:
        ax.plot(t, 줄, color="#2b6cb0", alpha=0.05, linewidth=0.8)
    ax.axhline(0.0, color="#c53030", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Time (UI)")
    ax.set_ylabel("Amplitude (V)")
    ax.set_title(제목 or f"Eye diagram — height {r['눈높이']:.3f} V, "
                        f"width {r['눈너비UI']:.2f} UI")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(낼곳)
    plt.close(fig)
    r.pop("틀", None)
    r["경로"] = 낼곳
    return r


# ---------------------------------------------------------------- 비트폭 쓸기

def 구별되나(오류1: int, 비트1: int, 오류2: int, 비트2: int) -> "tuple[bool, str]":
    """두 BER 측정이 **오차막대 밖에서** 다른가. 포아송 2시그마.

    이것이 없으면 "4비트가 float 와 같다" 를 오류 11개 대 8개로 말하게 된다 --
    그 차이는 셈의 흔들림이다. **구별 안 되는 것을 같다고 말하지 않는다**: 같다고
    말하려면 비트를 늘려 오차막대를 좁혀야 한다.
    """
    if 비트1 <= 0 or 비트2 <= 0:
        return False, "잰 비트가 없다"
    p1, p2 = 오류1 / 비트1, 오류2 / 비트2
    시그마 = math.sqrt(오류1) / 비트1 + math.sqrt(오류2) / 비트2
    if 시그마 <= 0:
        시그마 = 3.0 / min(비트1, 비트2)
    if abs(p1 - p2) > 2.0 * 시그마:
        return True, f"{p1:.2e} vs {p2:.2e} -- 2시그마 밖이다"
    return False, (f"{p1:.2e} vs {p2:.2e} -- **구별 안 된다**(오류 {오류1} 대 {오류2}, "
                   f"2시그마 ±{2 * 시그마:.1e}). 같다고 말하려면 비트를 더 세라")


def 가르려면몇비트(p1: float, p2: float) -> float:
    """두 BER 을 2시그마로 **가르려면** 측정 구간이 몇 비트여야 하나.

        |p1-p2| > 2(sigma1+sigma2),  sigma_i = sqrt(p_i/N)
        => N > [ 2(sqrt(p1)+sqrt(p2)) / |p1-p2| ]^2

    이 숫자가 없으면 "구별 안 된다" 가 "같다" 로 읽힌다. 실측 2026-09-15: 25dB 채널
    SNR 30dB 에서 6비트가 35만 비트로는 '구별 안 됨' 이었는데, 필요한 것이 **35.1만**
    이었다 -- 경계에 걸쳐 있었다. 140만으로 다시 재니 **구별됐다**(BER 31% 상승).
    그 한 줄이 없어서 '6비트면 열화 없음' 이라는 결론이 나왔다.
    """
    if p1 <= 0 or p2 <= 0 or p1 == p2:
        return float("inf")
    import math as _m
    return (2.0 * (_m.sqrt(p1) + _m.sqrt(p2)) / abs(p1 - p2)) ** 2


def 비트폭쓸기(비트들=(2, 3, 4, 5, 6, 8, 10, 12), **인자) -> dict:
    """**연구 기여 2번**: 탭 비트폭 대비 BER. 부동소수점 기준선과 나란히 놓는다.

    각 비트폭이 기준선과 **구별되는지**까지 같이 낸다. 오차막대 안에서 같은 것을
    "열화 없음" 이라 적으면 그것이 이 저장소가 내내 쫓은 거짓 초록이다.
    """
    기준 = 링크(탭비트=0, **인자)
    줄 = []
    for b in 비트들:
        r = 링크(탭비트=int(b), **인자)
        다른가, 말 = 구별되나(r["오류수"], r["잰비트"], 기준["오류수"], 기준["잰비트"])
        필요 = 가르려면몇비트(r["BER"], 기준["BER"])
        줄.append({"비트": int(b), "BER": r["BER"], "오류수": r["오류수"],
                  "잰비트": r["잰비트"], "기준선과다름": 다른가, "견줌": 말,
                  "가르려면": 필요, "왜": r["왜"]})
    열화없는최소 = next((x["비트"] for x in 줄 if not x["기준선과다름"]), None)
    return {"기준선": {"BER": 기준["BER"], "오류수": 기준["오류수"],
                    "잰비트": 기준["잰비트"], "왜": 기준["왜"]},
            "줄": 줄, "열화없는최소비트": 열화없는최소}


def ADC쓸기(비트들=(4, 5, 6, 7, 8), 풀스케일들=(2.0, 2.5, 3.0, 4.0),
         고르기씨: int = 12345, **인자) -> dict:
    """**ADC 분해능과 풀스케일을 함께 쓴다.** 둘은 따로 고를 수 없다.

    비트만 쓸면 풀스케일이 이미 최적이라고 가정한 것이고, 그 가정은 잰 적이 없다.
    실측 2026-09-15(25dB · SNR 30dB · FFE 11 + DFE 8): 어느 분해능에서나 바닥이
    **2.5 시그마**에 있었고, 그때 클립률이 0% 가 아니라 **0.45%** 였다 --
    잘 맞춘 ADC 는 일부러 조금 자른다. 3.0 시그마(옛 기본값)는 조금 넓었다.

    ## 고른 자리의 BER 은 낙관적이다 -- 그래서 다시 잰다

    여러 풀스케일 중 **제일 좋은 것을 고르면** 그 값은 셈의 흔들림까지 같이 고른 것이라
    실제보다 좋게 나온다(승자의 저주). 그래서 고른 풀스케일을 **다른 씨**로 한 번 더
    돌려 그 숫자를 따로 낸다. 고를 때 쓴 숫자와 말할 때 쓰는 숫자를 가른다.
    """
    if int(고르기씨) == int(인자.get("씨", 0)):
        # **같은 씨로 다시 재면 다시 잰 것이 아니다.** 고를 때 쓴 바로 그 숫자를
        # '독립 측정' 이라고 내놓게 되고, 승자의 저주가 그대로 남은 채 이름만 바뀐다.
        raise ValueError(
            f"고르기씨({고르기씨})가 쓸기 씨({인자.get('씨', 0)})와 같다 -- "
            "다시 재려면 다른 씨라야 한다")
    기준 = 링크(ADC비트=0, **인자)
    줄 = []
    for B in 비트들:
        칸 = []
        for k in 풀스케일들:
            r = 링크(ADC비트=int(B), ADC풀스케일시그마=float(k), **인자)
            다름, _ = 구별되나(r["오류수"], r["잰비트"], 기준["오류수"], 기준["잰비트"])
            칸.append({"풀스케일": float(k), "BER": r["BER"], "오류수": r["오류수"],
                      "잰비트": r["잰비트"], "클립비율": r["클립비율"],
                      "기준선과다름": 다름,
                      "가르려면": 가르려면몇비트(r["BER"], 기준["BER"])})
        제일 = min(칸, key=lambda c: c["오류수"])
        다시인자 = dict(인자)
        다시인자["씨"] = 고르기씨
        다시 = 링크(ADC비트=int(B), ADC풀스케일시그마=제일["풀스케일"], **다시인자)
        기준다시 = 링크(ADC비트=0, **다시인자)
        다름2, _ = 구별되나(다시["오류수"], 다시["잰비트"],
                        기준다시["오류수"], 기준다시["잰비트"])
        줄.append({"비트": int(B), "칸": 칸, "최적풀스케일": 제일["풀스케일"],
                  "고를때BER": 제일["BER"], "다시잰BER": 다시["BER"],
                  "다시잰오류수": 다시["오류수"], "다시잰잰비트": 다시["잰비트"],
                  "다시잰클립": 다시["클립비율"], "기준선과다름": 다름2,
                  "가르려면": 가르려면몇비트(다시["BER"], 기준다시["BER"])})
    최소 = next((x["비트"] for x in 줄 if not x["기준선과다름"]), None)
    return {"기준선": {"BER": 기준["BER"], "오류수": 기준["오류수"],
                    "잰비트": 기준["잰비트"], "왜": 기준["왜"]},
            "줄": 줄, "열화없는최소비트": 최소, "고르기씨": 고르기씨}


def ADC쓸기말로(s: dict) -> str:
    줄 = [f"float (no ADC) baseline: {s['기준선']['왜']}", "",
         "ADC resolution x full scale (full scale in sigma of the sampled signal):", ""]
    머리 = "  bit " + "".join(f"{k['풀스케일']:>10.1f}s" for k in s["줄"][0]["칸"])
    줄.append(머리)
    for x in s["줄"]:
        줄.append(f"  {x['비트']:3d} " + "".join(f"{c['BER']:>11.2e}" for c in x["칸"]))
        줄.append("      " + "".join(f"{100 * c['클립비율']:>10.2f}%" for c in x["칸"])
                  + "   <- clipped")
    줄.append("")
    for x in s["줄"]:
        표 = ("differs from float"
              if x["기준선과다름"] else
              ("NOT YET separated -- would need >= "
               f"{x['가르려면']:,.0f} evaluation bits to settle"
               if x["가르려면"] < float("inf") else "identical to float"))
        줄.append(f"  {x['비트']:2d} bit  best full scale {x['최적풀스케일']:.1f} sigma  "
                  f"(clips {100 * x['다시잰클립']:.2f}%)  "
                  f"re-measured BER {x['다시잰BER']:.3e}  {표}")
    줄.append("")
    b = s.get("열화없는최소비트")
    줄.append(f"**smallest ADC width NOT YET separated from float: {b} bit**"
              if b else "**every ADC width tested is distinguishable from float**")
    줄.append("Each row's full scale was **chosen** by the lowest BER, so that BER is "
              "optimistically biased (winner's curse). The `re-measured BER` re-runs the "
              "chosen full scale on a different seed -- quote that one, not the grid.")
    줄.append("`NOT YET separated` does NOT mean equal. **Absence of a measured "
              "difference is not evidence of no degradation.**")
    return "\n".join(줄)


def 쓸기말로(s: dict) -> str:
    줄 = [f"float baseline: {s['기준선']['왜']}", ""]
    for x in s["줄"]:
        if x["기준선과다름"]:
            표 = "differs"
        else:
            # **'구별 안 됨' 옆에 곧바로 조건을 붙인다.** 맨 아래 한 줄로만 적었더니
            # 옮겨 적히는 동안 떨어져 나가고 "no degradation" 이 되었다(실측).
            n = x["가르려면"]
            표 = ("NOT YET separated -- would need >= "
                  f"{n:,.0f} evaluation bits to settle (ran {x['잰비트']:,})"
                  if n < float("inf") else "identical to float")
        줄.append(f"  {x['비트']:2d} bit   BER {x['BER']:.3e}  "
                  f"({x['오류수']:,} errors)  {표}")
    줄.append("")
    b = s.get("열화없는최소비트")
    if not b:
        줄.append("**every width tested is distinguishable from float**")
        return "\n".join(줄)
    그줄 = next(x for x in s["줄"] if x["비트"] == b)
    모자란가 = 그줄["가르려면"] > 그줄["잰비트"]
    줄.append(f"**smallest width NOT YET separated from float: {b} bit**"
              + ("  <- PROVISIONAL: this run cannot settle it"
                 if 모자란가 else ""))
    줄.append("`NOT YET separated` does NOT mean equal. **Absence of a measured "
              "difference is not evidence of no degradation** -- it means the error "
              "bars are wider than the gap. Re-run at the bit count each row names "
              "before quoting a word length as safe for hardware.")
    if 모자란가:
        줄.append(f"Measured 2026-09-15: a {b}-bit row that read `same` at 350,000 bits "
                  "separated cleanly at 1,400,000 (BER +31%). The width that survived "
                  "was one bit wider.")
    return "\n".join(줄)


# 개념 목록(`concepts.py`)이 가리키는 본보기. **가리키는 데가 실제로 돌아야 한다** --
# `tests/test_concepts.py` 가 전부 돌려 본다. 비트 수는 검사가 빨리 끝나게 잡았다.
본보기 = {
    "awgn_calibration": dict(비트수=200000, 손실dB=0.0, SNRdB=9.0, sps=4, 학습비율=0.0),
    "isi_closed_eye":   dict(비트수=40000, 손실dB=20.0, SNRdB=30.0, sps=8),
    "ctle_only":        dict(비트수=40000, 손실dB=20.0, SNRdB=28.0, sps=8, CTLE피킹dB=6.0),
    "ffe_dfe":          dict(비트수=40000, 손실dB=20.0, SNRdB=28.0, sps=8, FFE탭=11, DFE탭=8),
    "dfe_only":         dict(비트수=40000, 손실dB=14.0, SNRdB=26.0, sps=8, DFE탭=8),
    "ideal_decision_dfe": dict(비트수=40000, 손실dB=22.0, SNRdB=22.0, sps=8, DFE탭=10,
                               이상적판정=True),
    "quantized_4bit":   dict(비트수=40000, 손실dB=20.0, SNRdB=26.0, sps=8, FFE탭=11,
                             DFE탭=8, 탭비트=4),
    "pruned_half":      dict(비트수=40000, 손실dB=20.0, SNRdB=26.0, sps=8, FFE탭=11,
                             DFE탭=8, 남길비율=0.5),
}


def 본보기돌리기(이름: str) -> dict:
    if 이름 not in 본보기:
        return {"판정": 못잼, "왜": f"모르는 본보기 {이름!r} -- {' · '.join(본보기)}",
                "오류수": -1, "잰비트": 0, "BER": float("nan")}
    return 링크(**본보기[이름])


def 말로(r: dict) -> str:
    줄 = [f"BER: {r['왜']}"]
    적 = r.get("적응") or {}
    if 적.get("탭") is not None:
        줄.append(f"FFE: {적['왜']}")
    if r.get("DFE탭"):
        줄.append("DFE taps: " + " · ".join(f"{t:+.3f}" for t in r["DFE탭"]))
    if r.get("ADC비트"):
        c = r.get("클립비율", 0.0)
        줄.append(f"ADC: {r['ADC비트']}-bit, full scale "
                  f"{r.get('ADC풀스케일시그마', 0):.1f} sigma, clipped {100 * c:.2f}% "
                  + ("of samples" if c < 0.01 else
                     "of samples -- **this BER is a range failure, not a resolution "
                     "result. Widen the full scale before reading it.**"))
    if r.get("이상적판정"):
        줄.append("**ideal-decision DFE — this hides error propagation; hardware "
                  "does not know the answer**")
    return "\n".join(줄)
