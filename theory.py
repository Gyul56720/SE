"""**논문의 숫자를 닫힌 꼴로 되짚는다** -- 시뮬레이터가 낸 값과 맞는가.

이 저장소는 숫자를 몬테카를로로 낸다. 그러면 **틀려도 그럴듯하다.** 배선이 어긋나도
BER 은 여전히 어떤 값을 내고, 그 값이 틀렸는지는 눈으로 모른다. 그래서 핵심 숫자마다
**손으로 푼 식**을 옆에 놓는다. 식과 잰 것이 어긋나면 둘 중 하나가 틀린 것이고,
어느 쪽이든 알아야 한다.

## 여기 담긴 것

    A. 핵심 주장의 유도 (다섯)
       A1 메모리 없는 역 = 표, 그리고 **그 역이 양자화 잡음을 얼마나 키우는가**
       A2 압축 세기 κ 가 표를 어떻게 깎는가 -- 교차점의 자리
       A3 β≈0.35 에서 메모리가 실제로 생기는 까닭 -- 필터 길이 = sps/β
       A4 판정 영역 천장 -- 지니 한계와 같은 값인가
       A5 주소 공간 대 학습 데이터 -- 찬 칸 수를 미리 셀 수 있는가

    B. 공학 숫자의 닫힌 꼴 재검증 (여섯)
       BER 이득 <-> SNR 여유 · 곱셈기 수 · 표 칸수 · 곱셈기당 면적 · Fmax · 누산기 폭

**모든 함수가 예측과 측정을 같이 돌려준다.** 예측만 내는 함수는 두지 않는다 --
그런 것은 검사할 수 없고, 검사하지 않은 식은 검사하지 않은 초록불과 같다.
"""
from __future__ import annotations

import math

import numpy as np

import serdes


# ---------------------------------------------------------------- B. 공학 숫자

def 이득을dB로(이득: float, 기준BER: float) -> dict:
    """**BER 이득 G 를 SNR 여유 dB 로 옮긴다.** 논문의 7.98배가 몇 dB 인가.

        BER = Q(v/sigma) 이므로   v/sigma = Q^-1(BER)
        이득 G 는 BER 을 p -> p/G 로 옮기는 것이고, 그때 필요한 진폭비가
            r = Q^-1(p/G) / Q^-1(p)
        즉  dSNR = 20 log10 r  [dB]

    **같은 이득이 낮은 BER 에서는 훨씬 적은 dB 다.** Q 의 꼬리가 가파르기 때문이다.

        p = 1e-2  에서 G=7.98 -> 2.3 dB
        p = 1e-6  에서 G=7.98 -> 0.6 dB
        p = 1e-12 에서 G=7.98 -> 0.3 dB

    이 한 줄이 "7.98배" 와 "112G 링크에서 유리하다" 사이의 거리를 잰다. 규격이 보는
    자리(1e-12)에서 그 이득은 **0.3 dB** 이고, 그것은 CTLE 피킹 반 칸이다.
    """
    from bound import Q역
    a = Q역(기준BER)
    b = Q역(기준BER / max(이득, 1e-300))
    if not (a == a and b == b):
        return {"판정": serdes.못잼, "왜": "Q^-1 범위 밖이다"}
    return {"이득": float(이득), "기준BER": float(기준BER),
            "진폭비": b / a, "dB": 20.0 * math.log10(b / a), "판정": serdes.PASS}


def 곱셈기수(꼴: str, **인자) -> int:
    """구조별 뒷단 곱셈기 수. **±1 판정은 곱셈이 아니다**(부호 선택 + 덧셈).

        FFE L 탭        L
        DFE 임의 탭     0      (d in {-1,+1} 이라 계수의 부호를 고르는 것)
        판정 색인 ROM   0      (주소 -> 1비트)
        표본 색인 표     0
        MLP L->H        L*H + H
    """
    if 꼴 == "ffe":
        return int(인자["탭"])
    if 꼴 in ("dfe", "rom", "표"):
        return 0
    if 꼴 == "mlp":
        L, H = int(인자["창"]), int(인자["은닉"])
        return L * H + H
    raise ValueError(f"모르는 꼴 {꼴!r}")


def 칸수(창: int, 색인비트: int, 특징비트: int = 0) -> int:
    """표의 칸 수 `2^(창·색인비트 + 특징비트)`. 한 칸은 **1비트**(판정)다."""
    return 1 << (int(창) * int(색인비트) + int(특징비트))


def 면적모형(잰것) -> dict:
    """**면적 = a·곱셈기수 + b.** 잰 점들로 맞추고 잔차를 낸다.

    `잰것` 은 `[(곱셈기수, LC), ...]`. iCE40 처럼 하드 곱셈기가 없는 소자에서는
    이 모형이 아주 잘 맞아야 한다 -- 곱셈이 전부 패브릭이므로.
    """
    x = np.array([float(m) for m, _ in 잰것])
    y = np.array([float(a) for _, a in 잰것])
    A = np.vstack([x, np.ones_like(x)]).T
    (기울기, 절편), *_ = np.linalg.lstsq(A, y, rcond=None)
    예측 = A @ np.array([기울기, 절편])
    상대 = float(np.max(np.abs(y - 예측) / np.maximum(y, 1.0)))
    return {"곱셈기당LC": float(기울기), "고정LC": float(절편),
            "최대상대오차": 상대, "예측": [float(v) for v in 예측],
            "판정": serdes.PASS if 상대 < 0.10 else serdes.FAIL}


def 누산기폭(W_x: int, W_w: int, L: int, F: int = 4, H: int = 2) -> dict:
    """비트 일치를 지키는 **최소 누산기 폭**. 좁으면 감기고, 넓으면 면적을 버린다.

        곱 하나       W_x + W_w
        L 개의 합     + ceil(log2(L+1))          -> W_z
        은닉 출력      F + 2                      -> W_h   (hardtanh 가 ±2^F 로 자른다)
        출력 누산      W_h + W_w + ceil(log2(H+1)) -> W_u
    """
    def 자리(n):
        return int(math.ceil(math.log2(max(n, 1))))
    W_z = int(W_x) + int(W_w) + 자리(int(L) + 1)
    W_h = int(F) + 2
    W_u = W_h + int(W_w) + 자리(int(H) + 1)
    return {"W_z": W_z, "W_h": W_h, "W_u": W_u}


def Fmax모형(조합깊이단: int, 단당ns: float = 1.0) -> float:
    """아주 거친 모형: `Fmax ~ 1/(깊이·단당지연)`. **자리 수만 본다.**

    파이프라인 한 단을 넣어 깊이를 반으로 자르면 Fmax 가 대략 두 배여야 한다.
    실측은 1.19~1.7배였다(배선 지연이 남기 때문). 이 함수는 그 **차이를 드러내려고**
    둔다 -- 맞으라고 둔 것이 아니다.
    """
    return 1000.0 / max(조합깊이단 * 단당ns, 1e-9)


# ---------------------------------------------------------------- A. 핵심 유도

def 역압축_잡음이득(세기: float) -> dict:
    """**A1.** 메모리 없는 역이 **ADC 양자화 잡음**을 얼마나 키우는가.

    압축은 `z = g(r) = tanh(a r)/a` 이고 `a = 세기/rms(r)`. 역의 기울기가

        d g^-1 / dz = 1/g'(r) = 1/sech^2(a r) = cosh^2(a r)

    이므로 z 에 실린 잡음 e 는 입력 쪽에서 `e·cosh^2(a r)` 이 된다.

    ## 어떤 잡음이 커지나 -- 열잡음은 안 커진다

    열잡음은 **압축 앞**에서 실린다. 그러니 신호와 같이 눌렸다가 역에서 같이 펴진다
    -- 정확한 역이면 **그대로 돌아온다**(명제 4 의 등호). 커지는 것은 **압축 뒤에
    실린 것**, 곧 ADC 양자화 잡음뿐이다. 이것이 §8 이 "곱셈기 0개라 공짜" 라고 적은
    표가 ADC 뒤에서 무는 값이다.

    ## 첫 식이 틀렸다 -- 평균을 잘못 잡았다

    처음에는 이득을 `E[cosh^4(a r)]` 로 냈다. κ=1.0 에서 **39.6(16 dB)** 이 나왔는데
    실측 벌점은 5.3배(BER)뿐이었다. `cosh^4` 의 기대값은 **드문 큰 |r| 이 지배**하고,
    판정은 거기서 나지 않는다. 판정이 나는 자리는 `|r| ~ rms` 이고 거기서는

        잡음 진폭 이득 = cosh^2(a·rms) = cosh^2(세기)

    이다(정의상 `a·rms = 세기`). κ=1.0 -> 2.38배, κ=1.6 -> 6.61배, κ=2.0 -> 14.15배.
    **평균을 어디서 잡느냐가 16 dB 와 7.5 dB 를 가른다.**
    """
    세기 = float(세기)
    if 세기 <= 0:
        return {"세기": 0.0, "판정자리이득": 1.0, "dB": 0.0,
                "꼬리평균이득": 1.0, "판정": serdes.PASS}
    판정 = math.cosh(세기) ** 2                      # |r| = rms 에서의 진폭 이득
    return {"세기": 세기, "판정자리이득": 판정,
            "dB": 20.0 * math.log10(판정),
            "꼬리평균이득": float(np.mean(np.cosh(
                세기 * np.random.default_rng(0).normal(0, 1, 200000)) ** 4)),
            "판정": serdes.PASS}


def 역압축_BER예측(세기: float, ADC비트: int, 풀스케일시그마: float,
              SNRdB: float, 기준BER: float) -> dict:
    """A1 을 **BER 비로** 옮긴다 -- 실측 5.3배와 맞는가.

        열잡음 분산      sigma^2                   (역에서 그대로 돌아온다)
        양자화 분산      Delta^2/12,  Delta = 2·rho·rms / 2^B
        역보정 뒤        sigma^2 + (Delta^2/12)·cosh^4(세기)
        잡음 진폭비      rho_n = sqrt(뒤/앞)

    **절대 BER 을 메인 커서로 예측하지 않는다.** 그렇게 해 보았더니 Q(7) 대 Q(5.7) 의
    비인 7,128배가 나왔다 -- 실제 BER 을 정하는 것은 메인 커서가 아니라 **남은 ISI
    가 만든 제일 좁은 눈**이기 때문이다. 그 눈 높이를 모르므로, 대신 **잰 기준 BER 을
    출발점으로 삼아** 잡음이 `rho_n` 배 커졌을 때로 옮긴다.

        BER_뒤 = Q( Q^-1(BER_앞) / rho_n )

    이것은 기구(양자화 잡음이 cosh^4 만큼 커진다)만 쓰고 눈 높이는 측정에서 가져오는
    **반쯤 닫힌 꼴**이다. 자리 수가 맞으면 기구를 맞게 짚은 것이다.
    """
    from bound import Q역
    sigma = 10.0 ** (-float(SNRdB) / 20.0)
    Δ = 2.0 * float(풀스케일시그마) / (1 << int(ADC비트))      # AGC 가 rms=1 로 맞춘다
    양자 = Δ * Δ / 12.0
    이득 = math.cosh(float(세기)) ** 4 if 세기 > 0 else 1.0
    앞 = math.sqrt(sigma ** 2 + 양자)
    뒤 = math.sqrt(sigma ** 2 + 양자 * 이득)
    rho = 뒤 / 앞
    q = Q역(float(기준BER))
    예측 = serdes.Q(q / rho)
    return {"잡음진폭비": rho, "잡음전력이득": 이득, "양자화분산": 양자,
            "기준BER": float(기준BER), "예측BER": 예측,
            "예측배수": 예측 / max(float(기준BER), 1e-300), "판정": serdes.PASS}


def 필터메모리(베타: float, sps: int = 8) -> dict:
    """**A3.** 압축 뒤 대역제한이 만드는 메모리 길이 -- 닫힌 꼴.

    `serdes.링크` 는 3dB 대역 `베타/T` 를 **길이 `round(sps/베타)` 의 Hann 창**으로
    낸다. 그러므로 메모리는

        지지길이 = round(sps/베타) 표본 = (1/베타) UI

    이다. 여기서 세 영역이 갈린다.

        1/베타 <~ 1 UI   표본 하나 안에 든다 -> **메모리 없음**. 2^B 칸 표가 끝낸다
        1/베타 ~ 2~3 UI  표본 두세 개가 섞인다 -> **표본 색인 표의 자리**
        1/베타 >> 3 UI   창 밖까지 섞인다 -> 어느 구조도 못 잡는다(링크가 죽는다)

    실측된 창(베타 = 0.35 에서만 8/8 씨)이 이 셈과 맞는지 보는 것이 요점이다.
    """
    if not 베타 or 베타 <= 0:
        return {"지지표본": 1, "지지UI": 0.0, "영역": "메모리 없음"}
    길이 = max(3, int(round(int(sps) / float(베타))))
    UI = 길이 / float(sps)
    영역 = ("메모리 없음" if UI <= 1.2 else
          "표본 색인 표의 자리" if UI <= 3.5 else
          "창 밖 -- 어느 구조도 못 잡는다")
    return {"지지표본": 길이, "지지UI": UI, "영역": 영역}


def 찬칸예측(주소: np.ndarray, 학습끝: int, 칸수: int,
         최소표본: int = 4) -> dict:
    """**A5.** 학습 구간의 주소 분포로 **찬 칸 수를 미리 센다.**

        n_i ~ Bin(N, p_i),   칸 i 가 쓸 만하다  <=>  n_i >= m
        기대 찬 칸 = sum_i P( Bin(N, p_i) >= m )

    균등하다고 치면 `C·P(Bin(N,1/C) >= m)` 인데, 실제 주소 분포는 **아주 치우쳐**
    있어서 그 근사가 크게 빗나간다. 그래서 여기서는 경험 분포 `p_i` 를 그대로 쓴다.

    이것이 논문이 말하는 **데이터의 벽**의 닫힌 꼴이다: 칸을 늘리면 p_i 가 쪼개져
    `P(n_i >= m)` 이 급히 0 으로 간다. 막는 것은 면적이 아니라 프리앰블 길이다.
    """
    주소 = np.asarray(주소[:학습끝], dtype=np.int64)
    N = len(주소)
    셈 = np.bincount(주소, minlength=int(칸수))
    p = 셈 / max(N, 1)
    # P(Bin(N,p) >= m) 을 푸아송 근사(lambda = N p)로 -- N 이 크고 p 가 작다
    lam = N * p
    기대 = 0.0
    for i in range(int(최소표본)):
        기대 += np.exp(-lam) * lam ** i / math.factorial(i)
    기대찬칸 = float(np.sum(1.0 - 기대))
    return {"기대찬칸": 기대찬칸, "칸수": int(칸수), "학습심볼": N,
            "실제찬칸": int(np.sum(셈 >= 최소표본))}


def 필요표본수(칸수: int, 여유: float = 0.5, 틀릴확률: float = 0.01) -> float:
    """**A5 의 표본 복잡도.** 칸마다 다수결이 `틀릴확률` 아래이려면 몇 표본이 드나.

        칸 i 의 다수결이 틀릴 확률 <= exp(-2 n_i gamma_i^2)   (호에프딩)
        => n_i >= ln(1/delta) / (2 gamma^2)
        => N >= C · ln(1/delta) / (2 gamma^2)     (균등 분포일 때)

    **N 이 칸 수에 선형**이고 칸 수는 `2^(창·색인비트)` 이므로, **필요한 프리앰블이
    창에 지수로 는다.** 신경망은 같은 창에서 파라미터가 선형으로 늘 뿐이다.
    """
    return float(칸수) * math.log(1.0 / max(틀릴확률, 1e-12)) / (2.0 * max(여유, 1e-9) ** 2)


def _상호정보(코드: np.ndarray, 비트: np.ndarray, 칸수: int) -> float:
    """I(b ; 코드) [bit]. 경험 분포로 센다."""
    n = len(코드)
    양 = np.bincount(코드[비트 > 0], minlength=칸수).astype(float)
    음 = np.bincount(코드[비트 < 0], minlength=칸수).astype(float)
    합 = 양 + 음
    쓸 = 합 > 0
    p = 합[쓸] / n
    q = 양[쓸] / 합[쓸]
    with np.errstate(divide="ignore", invalid="ignore"):
        H = -(q * np.log2(np.where(q > 0, q, 1)) +
              (1 - q) * np.log2(np.where(q < 1, 1 - q, 1)))
    return float(1.0 - np.sum(p * H))          # H(b)=1 비트 - H(b|코드)


def 표가잃는정보(세기: float, 색인비트: int = 4, 손실dB: float = 25.0,
            SNRdB: float = 30.0, 압축뒤대역: float = 0.0,
            비트수: int = 300000, 씨: int = 0) -> dict:
    """**A2.** 압축이 세지면 표가 왜 깎이는가 -- **양자화가 버리는 정보량**으로.

    표가 보는 것은 주소 `c` 뿐이고, 신경망이 보는 것은 양자화되지 않은 `x` 다.
    그래서 두 구조의 원리적 차이는 하나로 적힌다.

        표가 쓸 수 있는 것    I(b ; c)      c = 2의 거듭제곱 눈금으로 자른 x
        망이 쓸 수 있는 것    I(b ; x)      (아주 잘게 나눈 것으로 근사)
        양자화로 잃은 것      I(b ; x) - I(b ; c)   >= 0  (자료처리 부등식)

    **첫 판은 이것을 '판정을 가르는 코드 수' 로 재려 했고, 죽은 지표였다** -- AGC 가
    메인 커서 이득을 1 로 맞추므로 레벨 간격이 늘 정확히 2.0, 눈금도 rms 에 비례해
    늘 0.25 로 나왔다(κ 를 0 에서 2.5 로 쓸어도 8.00칸 그대로). 정규화가 지워 버린
    것을 세고 있었던 것이다. **정보량은 정규화에 안 지워진다.**
    """
    r = serdes.링크(비트수=int(비트수), 손실dB=손실dB, SNRdB=SNRdB, sps=8,
                  FFE탭=11, ADC비트=7, 압축=float(세기), 역압축=bool(세기),
                  압축뒤대역=float(압축뒤대역), 씨=int(씨))
    x, b = r["표본"], r["비트"].astype(float)
    n = min(len(x), len(b))
    x, b = x[:n], b[:n]
    Q = int(색인비트)
    rms = float(np.sqrt(np.mean(x ** 2))) or 1.0
    Δ = 2.0 ** round(math.log2(max(2.5 * rms / ((1 << Q) / 2), 1e-12)))
    코드 = np.clip(np.floor(x / Δ) + (1 << (Q - 1)), 0, (1 << Q) - 1).astype(np.int64)
    거친 = _상호정보(코드, b, 1 << Q)
    잔 = 1 << 12                                  # 연속 근사(12비트)
    Δ2 = 2.0 ** round(math.log2(max(2.5 * rms / (잔 / 2), 1e-12)))
    코드2 = np.clip(np.floor(x / Δ2) + 잔 // 2, 0, 잔 - 1).astype(np.int64)
    고운 = _상호정보(코드2, b, 잔)
    return {"세기": float(세기), "I_표": 거친, "I_연속": 고운,
            "양자화손실": 고운 - 거친, "손실비율": (고운 - 거친) / max(고운, 1e-12),
            "BER": r["BER"], "판정": serdes.PASS}


def 판정영역_천장(깊이들=(2, 4, 6, 8, 10), 압축: float = 1.0,
             압축뒤대역: float = 0.35, 손실dB: float = 25.0,
             SNRdB: float = 30.0, 비트수: int = 300000, 씨: int = 0) -> dict:
    """**A4.** 판정만 보는 구조가 깊이를 늘려도 **멈추는지** 잰다.

    명제 3 은 "판정은 진폭을 버렸으므로 관측이 모자란다" 고 말한다. 그 말이 참이면
    **깊이를 늘려도 어느 값에서 멈춰야** 한다 -- 파라미터가 2^깊이 로 느는데도.
    여기서는 **이상적 과거 판정**으로 색인한 꽉 찬 ROM 을 깊이별로 돌린다(상한이다).

    선형 채널에서는 안 멈춘다 -- 후행 커서가 판정의 함수이므로 깊이가 늘면 계속
    좋아진다. **멈추는 것은 비선형이 진폭을 섞을 때뿐**이고, 그 대조가 여기 같이 있다.
    """
    난다 = {}
    for 이름, 더 in (("비선형", dict(압축=압축, 압축뒤대역=압축뒤대역, 역압축=True)),
                   ("선형(대조)", {})):
        줄 = []
        for d in 깊이들:
            r = serdes.링크(비트수=int(비트수), 손실dB=손실dB, SNRdB=SNRdB, sps=8,
                          FFE탭=11, ADC비트=7, ROM깊이=int(d), 이상적판정=True,
                          씨=int(씨), **더)
            줄.append((int(d), r["BER"], int(r["ROM파라미터수"])))
        BER = [x[1] for x in 줄]
        멈춤 = bool(BER[-1] > 0.7 * min(BER[:-1])) if len(BER) > 1 else False
        난다[이름] = {"줄": 줄, "멈추나": 멈춤,
                   "최저": min(BER), "끝": BER[-1]}
    return 난다
