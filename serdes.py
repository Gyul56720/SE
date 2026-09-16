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

def 반사읽기(글: str):
    """`"0.35@11, 0.2@4"` 를 `[(0.35, 11.0), (0.2, 4.0)]` 로. 빈 글은 빈 것."""
    난것 = []
    for 조각 in str(글 or "").replace(" ", "").split(","):
        if not 조각:
            continue
        if "@" not in 조각:
            raise ValueError(f"반사는 `계수@지연심볼` 꼴이라야 한다: {조각!r}")
        계, 지 = 조각.split("@", 1)
        try:
            계수, 지연 = float(계), float(지)
        except ValueError:
            raise ValueError(f"반사의 숫자를 못 읽었다: {조각!r}")
        if not (0.0 < abs(계수) < 1.0):
            raise ValueError(f"반사 계수는 0 과 1 사이라야 한다(수동적 채널): {계수}")
        if 지연 <= 0:
            raise ValueError(f"반사 지연은 0보다 커야 한다: {지연}")
        난것.append((계수, 지연))
    return 난것


def 반사붙이기(h: np.ndarray, sps: int, 반사) -> np.ndarray:
    """스킨이펙트 응답에 **반사(에코)** 를 얹는다. `반사` 는 `[(계수, 지연심볼), ...]`.

    실제 백플레인은 매끄러운 손실만 있지 않다 -- 커넥터·비아 스터브·임피던스 불연속이
    신호 일부를 되돌려 보내고, 그것이 τ 만큼 늦게 다시 도착한다.

        H_total(f) = H_skin(f) · (1 + Σ Γ_k e^{-j2πfτ_k})

    그래서 |H| 에 **노치**가 생긴다: Γ 하나면 f·τ = 1/2 인 데서 합이 (1-|Γ|) 로 꺼지고,
    깊이가 20log10(1-|Γ|) 다. 스킨이펙트는 주파수에 대해 단조롭게 죽지만 **노치는
    특정 주파수만 파낸다** -- 그래서 CTLE 처럼 매끄러운 부스트로는 못 메운다.

    시간 영역에서는 이것이 **τ 만큼 떨어진 자리에 커서 하나**를 만든다. 짧은 FFE 는
    그 자리에 손이 닿지 않는다 -- 스팬 밖이기 때문이다. 탭 수를 늘리거나, 그 자리에만
    탭을 놓아야(floating tap) 잡힌다.
    """
    if not 반사:
        return h
    긴것 = max(int(round(d * sps)) for _, d in 반사)
    되돌림 = np.zeros(긴것 + 1)
    되돌림[0] = 1.0
    for 계수, 지연심볼 in 반사:
        k = int(round(float(지연심볼) * sps))
        if 0 < k < len(되돌림):
            되돌림[k] += float(계수)
    return np.convolve(h, 되돌림)[:len(h)]


def 채널(손실dB: float = 20.0, sps: int = 16, 길이심볼: int = 64, 반사=()) -> np.ndarray:
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
    return 반사붙이기(h, sps, 반사)


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


def 역압축하기(z: np.ndarray, 세기: float, a: float = 0.0) -> np.ndarray:
    """`압축하기` 의 **정확한 역함수.** 메모리 없는 보정의 상한을 재려고 둔다.

    ## 왜 이것이 필요한가 -- 빠져 있던 대조

    `압축하기` 는 **메모리가 없다**(한 표본만 보고 누른다). 그러면 그 역도 메모리가
    없고, 곧 **ADC 코드 하나를 다른 값으로 바꾸는 표 하나**다 -- 곱셈기 0개,
    7비트 ADC 면 128칸 ROM 이다. 신경망이 압축을 되돌려 이긴다면, 이 표 하나가
    같은 일을 **거의 공짜로** 해야 한다.

    그 대조 없이 "선형 등화기는 압축을 못 되돌린다" 고 적으면, 정확히는
    **"선형 FFE·DFE 는 못 되돌린다"** 이지 "선형 하드웨어로는 못 한다" 가 아니다.
    표는 선형이 아니지만 신경망도 아니다.

    여기서는 세기와 스케일을 **정확히 준다**(수신기가 곡선을 안다고 가정). 실제
    수신기는 그것을 추정해야 하므로 이보다 나쁠 수밖에 없다 -- 그래서 **상한**이다.

    `tanh(a·y)/a` 의 역은 `atanh(a·z)/a` 이고, `|a·z| -> 1` 에서 발산한다. 그 발산이
    물리다 -- 포화 구간에서는 정보가 이미 뭉개져서 되돌리면 잡음만 커진다. 발산을
    막으려고 인자를 잘라 둔다.
    """
    if not 세기 or a <= 0:
        return z
    u = np.clip(np.asarray(z, dtype=float) * a, -0.999, 0.999)
    return np.arctanh(u) / a


def 압축세기(y: np.ndarray, 세기: float) -> float:
    """`압축하기` 가 쓰는 `a` 를 그대로 돌려준다 -- 역함수에 같은 값을 주려고."""
    if not 세기:
        return 0.0
    rms = float(np.sqrt(np.mean(np.asarray(y, dtype=float) ** 2))) or 1.0
    return float(세기) / rms


def 압축하기(y: np.ndarray, 세기: float) -> np.ndarray:
    """수신 앞단 증폭기의 **비선형 압축**. `세기`=0 이면 아무것도 안 한다.

        y_out = tanh(a*y) / a,   a = 세기 / rms(y)

    ## 왜 수신단인가 -- 송신단에 걸면 **아무 일도 안 일어난다**

    NRZ 는 레벨이 ±1 둘뿐이다. 메모리 없는 비선형은 그 둘을 각각 다른 값으로 옮길
    뿐이라 **그냥 이득 변화**이고, 슬라이서 문턱이 0 이면 BER 이 한 톨도 안 변한다.
    비선형이 뜻을 가지려면 신호에 **레벨이 여럿**이어야 하고, 그 자리가 ISI 로
    퍼진 뒤의 수신 파형이다. 실제 링크에서도 압축은 작은 신호를 크게 키우는 RX
    앞단(CTLE·VGA)에서 난다.

    ## 이것이 선형 등화기가 못 푸는 것이다

    FFE·DFE·CTLE 는 전부 선형 연산이다. 선형 채널 + AWGN 에서는 최적 등화기도
    선형이라(MMSE-DFE) 신경망을 얹어도 잘해야 비긴다 -- **이기면 그건 물리가
    아니라 새는 구멍이다.** 압축은 선형 역연산이 존재하지 않으므로 여기서 처음으로
    비선형 사상이 할 일이 생긴다.
    """
    if not 세기 or 세기 <= 0:
        return y
    rms = float(np.sqrt(np.mean(y ** 2))) or 1.0
    a = float(세기) / rms
    return np.tanh(a * y) / a


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
       반사=(), DFE자리=None, 압축: float = 0.0,
       탭비트: int = 0, 남길비율: float = 1.0, 이상적판정: bool = False,
       ADC비트: int = 0, ADC풀스케일시그마: float = 3.0, 역압축: bool = False,
       압축뒤대역: float = 0.0, ROM깊이: int = 0, ROM최소표본: int = 8,
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
    h = 채널(손실dB, sps, 64, 반사)

    보낸것 = np.repeat(b, sps).astype(float)
    y = np.convolve(보낸것, h, mode="full")[:len(보낸것)]
    # SNR 정의: **손실 없는 이상적 메인 커서(=1)** 에 견준다. 머리말 참조.
    sigma = 10.0 ** (-SNRdB / 20.0)
    y = y + rng.normal(0.0, sigma, len(y))
    # **압축은 잡음이 실린 뒤, 등화 앞에서** 난다 -- RX 앞단의 자리가 거기다.
    _압축a = 압축세기(y, 압축)          # 역보정에 같은 값을 주려고 붙든다
    y = 압축하기(y, 압축)
    # **압축 뒤의 대역 제한.** 실제 수신단은 압축이 일어난 뒤에도 필터를 더 지난다
    # (CTLE 부하 · ADC 입력망 · 패키지). 그러면 한 표본이 여러 압축값의 **섞임**이
    # 되어 **표본마다 되돌리는 것(메모리 없는 역함수)이 더는 정확하지 않다.**
    # `압축뒤대역` 은 심볼률 대비 3dB 대역이다(1.0 이면 필터가 없는 것과 같다).
    if 압축뒤대역 and 압축뒤대역 > 0:
        길이 = max(3, int(round(sps / max(압축뒤대역, 1e-3))))
        창 = np.hanning(길이 + 2)[1:-1]
        y = np.convolve(y, 창 / 창.sum(), mode="same")
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

    # **메모리 없는 역보정**(선택). ADC 코드 하나를 다른 값으로 바꾸는 표 하나이고,
    # 곱셈기가 0개다. 신경망 이득이 "압축을 되돌린 것" 이라면 이 표가 같은 일을
    # 거의 공짜로 해야 한다 -- 그 대조가 없으면 신경망에 공을 잘못 돌린다.
    # 세기와 스케일을 정확히 주므로 **모든 메모리 없는 보정의 상한**이다.
    if 역압축 and 압축:
        표본 = 역압축하기(표본, 압축, _압축a)

    # AGC: 메인 커서 이득을 **학습 구간의 상관으로 잰다**(수신기가 아는 것만 쓴다)
    g = float(np.mean(표본[학습] * 맞춘것[학습])) or 1.0
    표본 = 표본 / g

    적응 = {"왜": "FFE 를 안 썼다", "발산": False, "MSE": float("nan"), "탭": None}
    if FFE탭 > 0:
        지연 = FFE탭 // 2
        # **걸음을 탭 수로도 나눈다(NLMS).** 안정 조건이 mu < 2/(L·sigma^2) 라 탭이
        # 길어지면 같은 걸음이 발산한다 -- 실측 2026-09-15: 전력으로만 나눴더니
        # FFE 29탭이 탭 1.08e+06 까지 터졌다. 그 상태로 "탭을 늘려도 안 낫다" 고
        # 말하면 물리가 아니라 내 걸음을 재는 것이다.
        힘 = float(np.mean(표본[학습] ** 2)) or 1.0
        적응 = LMS_FFE(표본[학습], 맞춘것[학습], FFE탭, 지연,
                     걸음=0.2 / (max(1, FFE탭) * 힘))
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
    # DFE 탭 **자리**를 정한다. 이어진 1..N 이 기본이고, `DFE자리` 를 주면 그 자리에만
    # 놓는다 -- 반사가 만든 먼 커서(예: 11심볼 뒤)를 잡는 floating tap 이 그것이다.
    # 이어진 탭으로 11심볼까지 가려면 탭이 11개 필요하지만, 자리를 알면 서너 개면 된다.
    자리들 = ([int(x) for x in DFE자리 if int(x) > 0]
            if DFE자리 else list(range(1, int(DFE탭) + 1)))
    자리들 = sorted(set(자리들))
    dfe탭값 = None
    if 자리들:
        탭 = []
        for m in 자리들:
            앞 = 표본[학습][m:]
            뒤 = 맞춘것[학습][:-m]
            n = min(len(앞), len(뒤))
            탭.append(float(np.mean(앞[:n] * 뒤[:n])) if n else 0.0)
        dfe탭값 = np.array(탭)
        if 탭비트:
            dfe탭값 = 양자화(dfe탭값, 탭비트)
        if 남길비율 < 1.0:
            dfe탭값 = 프루닝(dfe탭값, 남길비율)

    # **판정 색인 ROM**(선택). 같은 과거 판정에 대해 DFE 의 선형 함수를 임의 함수로
    # 넓힌다 -- 곱셈기는 여전히 0개이고 2^깊이 칸 ROM 하나가 는다.
    ROM표, 되돌린칸 = None, 0
    if ROM깊이 and int(ROM깊이) > 0:
        ROM표, 되돌린칸 = 판정ROM학습(표본, 맞춘것, int(ROM깊이), 학습끝,
                                  dfe탭값, 자리들, int(ROM최소표본))
        판정 = _슬라이스ROM(표본, ROM표, int(ROM깊이))
    else:
        판정 = _슬라이스(표본, dfe탭값, 맞춘것 if 이상적판정 else None, 자리들)

    잰것 = slice(학습끝, len(판정))
    오류 = int(np.sum(판정[잰것] != 맞춘것[잰것]))
    잰비트 = int(잰것.stop - 잰것.start)
    return {"BER": (오류 / 잰비트) if 잰비트 else float("nan"),
            "오류수": 오류, "잰비트": 잰비트, "표본": 표본, "비트": 맞춘것,
            "위상": 위상, "지연심볼": 지연심볼, "sigma": sigma, "적응": 적응,
            "ADC비트": int(ADC비트), "클립비율": 클립비율, "압축": float(압축),
            "ADC풀스케일시그마": ADC풀스케일시그마,
            "DFE탭": None if dfe탭값 is None else list(map(float, dfe탭값)),
            "DFE자리": 자리들, "반사": list(반사),
            "ROM깊이": int(ROM깊이), "ROM칸수": (0 if ROM표 is None else len(ROM표)),
            "ROM되돌린칸": 되돌린칸,
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


def 판정ROM학습(표본: np.ndarray, 정답: np.ndarray, 깊이: int, 끝: int,
            dfe탭=None, 자리들=None, 최소표본: int = 8):
    """**과거 `깊이`개 판정으로 색인되는 표**를 학습 구간에서 만든다. 곱셈기 0개.

    ## 왜 이것인가 -- 값이 매겨진 축에서 고른 구조

    이 저장소가 잰 곱셈기 값은 이렇다(표 12).

        메모리 없는 비선형   ADC 코드 표          곱셈 0
        선형 선행커서 ISI    FFE                  탭당 1 (약 197 LC)
        선형 후행커서 ISI    DFE                  곱셈 0 (NRZ 판정이 ±1)
        **비선형 후행커서**  **판정 색인 표**     **곱셈 0**
        표본에 달린 비선형   신경망 · Volterra    많다

    선형 DFE 는 과거 판정의 **선형** 함수 `Σ c_k d_{t-k}` 로 뺄 값을 정한다. 같은
    입력에 대해 **임의의** 함수를 담으면 그것이 2^깊이 칸짜리 표 하나이고, 곱셈기는
    여전히 0개다. 즉 **표는 같은 탭 수의 DFE 를 엄밀히 일반화한다.**

    일반 MLP 가 틀린 도구인 까닭이 여기 있다 -- 곱셈기 0개로 되는 일(판정에 달린
    비선형)에 곱셈기를 낸다. 망이 곱셈기 값을 해야 하는 자리는 **판정이 아니라 표본에
    달린** 비선형뿐이다.

    ## 누수를 막는 두 가지

    *하나.* 표는 **학습 구간에서만** 만든다. 색인에 정답 비트를 쓰는 것은 표준 PHY 의
    학습 프리앰블에 해당하므로 괜찮다. 그러나 **평가 구간에서는 제 판정으로 색인해야**
    하고(`_슬라이스ROM`), 그래야 오류 번짐이 DFE 와 똑같이 산다.

    *둘.* 표본이 모자란 칸은 배우지 않는다 -- `최소표본` 미만이면 **선형 DFE 값으로
    되돌린다.** 그러지 않으면 드문 패턴에서 잡음을 외운 값이 들어가 평가에서 터진다.
    되돌릴 DFE 가 없으면 0 이다.
    """
    깊이 = int(깊이)
    if 깊이 <= 0:
        return None, 0
    끝 = int(max(끝, 1))
    칸수 = 1 << 깊이
    합 = np.zeros(칸수)
    수 = np.zeros(칸수, dtype=np.int64)
    # 색인: 과거 깊이개 판정(정답)을 비트로. d=+1 -> 1, d=-1 -> 0. 최근 것이 최하위.
    쓸것 = min(끝, len(표본), len(정답))
    for t in range(깊이, 쓸것):
        idx = 0
        for k in range(깊이):
            idx |= (1 if 정답[t - 1 - k] > 0 else 0) << k
        합[idx] += 표본[t] - 정답[t]
        수[idx] += 1
    표 = np.zeros(칸수)
    되돌린칸 = 0
    for i in range(칸수):
        if 수[i] >= 최소표본:
            표[i] = 합[i] / 수[i]
        else:
            되돌린칸 += 1
            if dfe탭 is not None and 자리들:
                # 이 칸의 패턴이 뜻하는 지난 판정으로 선형 DFE 값을 낸다
                표[i] = float(sum(c * (1.0 if (i >> (m - 1)) & 1 else -1.0)
                                  for c, m in zip(dfe탭, 자리들) if m <= 깊이))
    return 표, 되돌린칸


def _슬라이스ROM(표본: np.ndarray, 표: np.ndarray, 깊이: int) -> np.ndarray:
    """판정 색인 표로 되먹이는 슬라이서. **되먹이는 것은 제 판정이다.**"""
    깊이 = int(깊이)
    난것 = np.empty(len(표본))
    지난 = np.zeros(깊이)              # 지난[0] 이 한 심볼 전
    for i in range(len(표본)):
        idx = 0
        for k in range(깊이):
            idx |= (1 if 지난[k] > 0 else 0) << k
        v = 표본[i] - 표[idx]
        난것[i] = 1.0 if v >= 0 else -1.0
        지난 = np.concatenate([[난것[i]], 지난[:-1]])
    return 난것


def _슬라이스(표본: np.ndarray, dfe탭, 정답, 자리들=None) -> np.ndarray:
    """문턱 0 슬라이서. DFE 가 있으면 **한 심볼씩 순차로** 돈다(되먹임이라 벡터화 못 한다).

    `자리들` 은 각 탭이 몇 심볼 뒤를 보는가다. 이어진 1..N 이 아니어도 된다 --
    반사가 만든 먼 커서만 골라 잡는 floating tap 을 위해서다.
    """
    if dfe탭 is None or len(dfe탭) == 0:
        return np.where(표본 >= 0, 1, -1)
    자리들 = list(자리들) if 자리들 else list(range(1, len(dfe탭) + 1))
    깊이 = max(자리들)
    난것 = np.zeros(len(표본), dtype=int)
    지난판정 = np.zeros(깊이)          # 지난판정[0] 이 한 심볼 전
    for i in range(len(표본)):
        v = 표본[i] - float(sum(c * 지난판정[m - 1] for c, m in zip(dfe탭, 자리들)))
        난것[i] = 1 if v >= 0 else -1
        # **되먹이는 것은 판정이다.** `정답` 을 먹이면 오류 번짐이 사라져 BER 이
        # 실제보다 좋게 나온다 -- 하드웨어는 정답을 모른다.
        먹일것 = float(정답[i]) if 정답 is not None and i < len(정답) else float(난것[i])
        지난판정 = np.concatenate([[먹일것], 지난판정[:-1]])
    return 난것


def 반사자리찾기(표본: np.ndarray, 비트: np.ndarray, 최대지연: int = 40,
           건너뛸앞: int = 6, 몇개: int = 3) -> "list[int]":
    """**반사가 어디 있나.** 먼 자리의 커서를 상관으로 훑어 큰 것부터 돌려준다.

    하드웨어의 floating-tap DFE 가 실제로 하는 일이다 -- 탭을 이어 붙여 멀리 뻗는
    대신, 어디가 큰지 **찾아서** 그 자리에만 탭을 놓는다. `건너뛸앞` 은 이어진
    탭이 이미 맡는 앞쪽 구간이다.
    """
    n = min(len(표본), len(비트))
    난것 = []
    for m in range(int(건너뛸앞) + 1, int(최대지연) + 1):
        if m >= n:
            break
        난것.append((abs(float(np.mean(표본[m:n] * 비트[:n - m]))), m))
    난것.sort(reverse=True)
    return sorted(m for _, m in 난것[:int(몇개)])


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


def 동작점SNR(손실dB: float, 목표BER: float = 1e-3, 비트수: int = 200000,
          낮게: float = 10.0, 높게: float = 50.0, 되풀이: int = 14, **인자) -> dict:
    """float 기준선 BER 이 `목표BER` 이 되는 SNR 을 이분법으로 찾는다.

    ## 왜 필요한가 -- 고정 SNR 으로는 채널을 못 쓴다

    이 모형의 SNR 은 **손실 없는 이상적 메인 커서(=1)** 에 견준 값이라, 손실을 올리면
    ISI 와 실효 SNR 이 **같이** 나빠진다. 실측 2026-09-15(SNR 30dB 고정, FFE11+DFE8):

        10~20dB  오류 0        <- 견줄 수가 없다(측정 바닥 아래)
        25dB     BER 7.0e-04
        30dB     BER 3.2e-02   <- 이미 깨진 링크
        35dB     BER 1.2e-01

    쓸 수 있는 창이 한 점뿐이다. 손실마다 **같은 BER 자리**로 옮겨 놓아야 "몇 비트가
    필요한가" 를 손실끼리 견줄 수 있다. 그러지 않으면 비트 수 차이인지 동작점 차이인지
    영영 못 가른다.

    돌려주는 것에 **실제로 난 BER 을 같이 싣는다** -- 이분법이 목표에 못 닿을 수도
    있고(측정 바닥·링크 붕괴), 그때 SNR 만 보면 닿은 줄 안다.
    """
    인자 = dict(인자)
    인자.pop("SNRdB", None)
    낮, 높 = float(낮게), float(높게)
    난것 = None
    for _ in range(int(되풀이)):
        가운데 = 0.5 * (낮 + 높)
        r = 링크(비트수=int(비트수), 손실dB=float(손실dB), SNRdB=가운데, **인자)
        난것 = r
        # 오류 0 은 BER 0 이 아니다 -- 3의 규칙 위쪽 한계로 다룬다
        p = r["BER"] if r["오류수"] > 0 else 3.0 / max(r["잰비트"], 1)
        if p > 목표BER:
            낮 = 가운데          # 너무 나쁘다 -> SNR 을 올린다
        else:
            높 = 가운데
    SNR = 0.5 * (낮 + 높)
    끝 = 링크(비트수=int(비트수), 손실dB=float(손실dB), SNRdB=SNR, **인자)
    닿았나 = 끝["오류수"] > 0 and 0.2 * 목표BER < 끝["BER"] < 5.0 * 목표BER
    return {"SNRdB": SNR, "BER": 끝["BER"], "오류수": 끝["오류수"],
            "잰비트": 끝["잰비트"], "닿았나": bool(닿았나),
            "왜": (f"SNR {SNR:.2f} dB 에서 float BER {끝['BER']:.3e} "
                  f"({끝['오류수']:,} 오류) -- 목표 {목표BER:.1e}"
                  + ("" if 닿았나 else "  **목표에 못 닿았다 -- 이 점은 믿지 마라**"))}


def 여러씨(씨들, 만들기) -> dict:
    """같은 물음을 씨 여러 개로 돌려 **평균과 산포**를 낸다.

    ## 왜 이것이 필요한가 -- 실측 2026-09-15, 이 세션에서 세 번째로 같은 병

    손실 30dB 에서 계수 폭을 씨 네 개로 돌렸더니 이랬다(float 대비 BER 올림).

        seed      6b       7b       8b       9b      10b
           7  +24.5%    -4.7%   +30.6%    -2.5%    -1.5%
          11   +6.0%   +26.2%    -6.5%    +2.3%    -2.3%
          23  +81.3%    +5.5%    -3.8%    +6.4%    -0.9%
          42  +40.8%    -0.8%    +6.3%    +1.9%    -2.9%
        산포    27.8     11.9     14.6      3.2      0.8

    **거친 폭에서는 씨끼리의 산포가 재려는 효과보다 크다.** 한 씨로 보면 7비트가
    -4.7% 로도 +26.2% 로도 나온다 -- 어느 쪽을 봤느냐가 결론을 정한다. 거친 폭에서
    LMS 해가 어디로 반올림되는지가 씨마다 달라서이고, 9~10비트에서야 산포가 무너진다.

    그래서 **한 씨로 워드 길이를 말하지 않는다.** 평균과 산포를 같이 낸다.
    """
    값들 = [만들기(int(씨)) for 씨 in 씨들]
    n = len(값들)
    평균 = sum(값들) / n if n else float("nan")
    산포 = (sum((v - 평균) ** 2 for v in 값들) / n) ** 0.5 if n else float("nan")
    return {"값들": 값들, "평균": 평균, "산포": 산포, "씨수": n,
            "낮": min(값들) if 값들 else float("nan"),
            "높": max(값들) if 값들 else float("nan")}


def 충분한가(칸: dict, 넉넉함: float = 1.0) -> bool:
    """이 워드 길이가 **충분한가.** 평균 열화가 작고 **씨 산포도 작아야** 참이다.

    둘 다여야 한다. 평균만 보면 실측 2026-09-15 의 30dB · 7비트가 통과한다 --
    평균 +6.6% 인데 산포가 ±11.9% 라 한 씨에서 -4.7%, 다른 씨에서 +26.2% 였다.
    **어느 씨를 뽑았느냐가 결론을 정하는 폭은 설계 여유가 없는 폭이다.**
    """
    바닥 = 5.0 * 넉넉함
    return abs(칸["올림%"]) <= 바닥 and 칸["산포"] <= 바닥


def 손실쓸기(손실들=(15.0, 20.0, 25.0, 30.0), 비트폭들=(7, 8, 9, 10),
         목표BER: float = 1e-3, 비트수: int = 800000, 찾기비트수: int = 200000,
         찾기되풀이: int = 14, ADC도: bool = True, ADC풀스케일시그마: float = 2.5,
         씨들=(7, 11, 23, 42), 넉넉함: float = 1.0, **인자) -> dict:
    """**손실마다 같은 BER 자리로 옮겨 놓고** 필요한 워드 길이를 잰다.

    `ADC도` 가 참이면 계수와 ADC 를 **같은 폭으로 함께** 자른다(현업에서 둘을 따로
    고르지 않는다). 거짓이면 계수만 자르고 ADC 는 이상적이다.

    **씨를 여러 개 돌린다.** 한 씨로는 워드 길이를 못 말한다 -- `여러씨()` 머리말의
    실측을 보라. 어떤 폭이 '충분하다' 고 말하려면 평균 열화가 작은 것만으로 모자라고
    **씨끼리의 산포도 그 열화만큼 작아야** 한다. 산포가 크면 그 폭에서는 어느 씨를
    뽑았느냐가 결론을 정한다는 뜻이고, 그것은 설계 여유가 없다는 말이다.
    """
    인자 = dict(인자)
    인자.pop("씨", None)
    난것 = []
    for L in 손실들:
        점 = 동작점SNR(L, 목표BER, 찾기비트수, 되풀이=int(찾기되풀이),
                    씨=씨들[0], **인자)
        칸 = []
        for B in 비트폭들:
            더 = {"탭비트": int(B)}
            if ADC도:
                더["ADC비트"] = int(B)
                더["ADC풀스케일시그마"] = ADC풀스케일시그마

            def 한번(씨, B=B, 더=더, L=L, 점=점):
                공통 = dict(비트수=int(비트수), 손실dB=float(L),
                          SNRdB=점["SNRdB"], 씨=씨, **인자)
                기준 = 링크(**공통)
                r = 링크(**공통, **더)
                return (100.0 * (r["BER"] / 기준["BER"] - 1.0)
                        if 기준["BER"] > 0 else float("nan"))

            m = 여러씨(씨들, 한번)
            칸.append({"비트": int(B), "올림%": m["평균"], "산포": m["산포"],
                      "낮": m["낮"], "높": m["높"], "값들": m["값들"],
                      "씨수": m["씨수"]})
        최소 = next((c["비트"] for c in 칸 if 충분한가(c, 넉넉함)), None)
        흔들리는것 = [c["비트"] for c in 칸 if c["산포"] > 5.0 * 넉넉함]
        난것.append({"손실dB": float(L), "동작점": 점, "칸": 칸,
                    "필요비트": 최소, "흔들리는폭": 흔들리는것,
                    "쓸만한가": 점["닿았나"]})
    return {"줄": 난것, "목표BER": 목표BER, "ADC도": bool(ADC도),
            "씨들": list(씨들), "넉넉함": 넉넉함}


def 손실쓸기말로(s: dict) -> str:
    함께 = "coefficients AND ADC at the same width" if s["ADC도"] else "coefficients only"
    줄 = [f"Word length vs channel loss ({함께}), each loss moved to a common "
         f"float BER of {s['목표BER']:.0e}.",
         f"Every cell is the mean BER increase over float across {len(s['씨들'])} seeds, "
         "+- the seed-to-seed spread.", ""]
    줄.append("  loss   SNR  " + "".join(f"{c['비트']:>17d}b" for c in s["줄"][0]["칸"]))
    for x in s["줄"]:
        줄.append(f"  {x['손실dB']:4.0f}dB {x['동작점']['SNRdB']:5.1f}  "
                  + "".join(f"{c['올림%']:>+10.1f}% +-{c['산포']:>4.1f}"
                            for c in x["칸"]))
        if not x["쓸만한가"]:
            줄.append(f"      ** {x['동작점']['왜']} **")
    줄.append("")
    for x in s["줄"]:
        b = x["필요비트"]
        줄.append(f"  {x['손실dB']:4.0f} dB: smallest width that is both small in mean AND "
                  f"stable across seeds = " + (f"**{b} bit**" if b else "none tested"))
        if x["흔들리는폭"]:
            줄.append("          seed-unstable widths (spread larger than the effect): "
                      + " · ".join(f"{w}b" for w in x["흔들리는폭"]))
    줄.append("")
    줄.append("A width is only called sufficient when the mean degradation AND the "
              "seed spread are both small. **A single seed cannot name a word length** "
              "-- measured, 7-bit at 30 dB read -4.7% on one seed and +26.2% on another, "
              "because at coarse widths it is the rounding of that seed's LMS solution "
              "that decides, not the step size. The spread collapses only once the width "
              "is genuinely sufficient.")
    return "\n".join(줄)


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
    if r.get("반사"):
        줄.append("channel reflections: "
                  + " · ".join(f"{g:+.2f} at {d:.0f} UI" for g, d in r["반사"])
                  + "  (notch at f*tau = 1/2, depth 20log10(1-|G|))")
    if r.get("DFE탭"):
        자리 = r.get("DFE자리") or list(range(1, len(r["DFE탭"]) + 1))
        줄.append("DFE taps @" + ",".join(str(m) for m in 자리) + ": "
                  + " · ".join(f"{t:+.3f}" for t in r["DFE탭"]))
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
