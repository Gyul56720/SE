"""**트랜지스터까지 내려간다** -- 논문의 손상 손잡이가 회로의 무엇인가.

이 저장소의 SerDes 모형에는 손잡이가 여럿 있다: 압축 세기 `κ`, 슬루율 `S`, CTLE 피킹,
지터 `rjUI`. 지금까지 그 값들은 **그냥 숫자**였다. "κ=1.6 에서 교차점" 이라고 적어도
그것이 실리콘에서 무엇인지 -- 입력 스윙 몇 mV 인지, 꼬리 전류 몇 mA 인지 -- 는 어디에도
없었다. 그러면 결론이 물리에 닿지 않는다.

이 모듈이 그 사이를 잇는다. 블록마다 **소자 파라미터에서 손잡이 값을 닫힌 꼴로 내고,
`serdes.py` 가 실제로 하는 것과 맞대 본다.**

    TX CML 드라이버   I/C 슬루      ->  `serdes.슬루` 의 S      S = T_s /(R_eff·C_L)
    RX AFE · VGA      차동쌍 포화   ->  `serdes.압축하기` 의 κ   κ = V_in,rms / V_lim
    CTLE              소스 축퇴쌍   ->  `serdes.CTLE` 의 피킹·영점·극점
    샘플러            StrongARM     ->  판정 감도(바닥의 한 원인)
    CDR               뱅뱅 루프     ->  `serdes.지터표본` 의 잔류 rjUI
    FFE · DFE         전류 합산     ->  1 UI 되먹임 예산(왜 DFE 는 파이프라인이 안 되나)

## 규율은 그대로다

**그림은 검사가 아니다.** 회로도를 그려 놓고 "이렇게 동작한다" 고 적는 것은 이 저장소가
쫓아온 거짓 초록과 같은 부류다. 그래서 모든 대응은 `_검증` 이 붙는다 -- 닫힌 꼴이 낸
값과 `serdes.py` 가 낸 값을 실제로 맞대고, 어긋나면 얼마나 어긋나는지 적는다.

**단위를 적는다.** 정규화된 숫자(S=0.02)는 그 자체로 아무 뜻이 없다. 옆에 반드시
`= 312 fs 시상수` 처럼 물리 단위를 같이 둔다.
"""
from __future__ import annotations

import math

import numpy as np

import serdes

# 상온 열전압. 소신호 한계 스케일이 전부 여기서 나온다.
V_T = 0.02585          # kT/q at 300 K [V]


# ---------------------------------------------------------------- TX 드라이버

def cml드라이버(꼬리전류A: float = 8e-3, 종단옴: float = 50.0,
            부하F: float = 60e-15, 보드율: float = 20e9,
            sps: int = 8) -> dict:
    """**CML 드라이버**: 꼬리 전류를 좌우로 던지는 스위치 한 쌍 + 부하 저항.

    ## 전류가 어디로 흐르나

    꼬리 전류원 `M3` 이 `I_SS` 를 뽑고 있고, 입력이 높은 쪽 스위치(`M1` 또는 `M2`)가
    **그 전류를 통째로** 받는다. 받은 쪽 드레인이 `V_DD - I_SS·R_eff` 로 내려가고 다른
    쪽은 `V_DD` 에 남는다. 그래서 차동 스윙이

        V_swing(차동) = 2·I_SS·R_eff,   R_eff = R_D || (Z_0/2)

    다. **스위치는 증폭하지 않는다 -- 전류의 길을 고를 뿐이다.** 그래서 CML 이 빠르다
    (전압 이득 단이 없고, 노드가 늘 `V_DD` 아니면 `V_DD-IR` 둘 중 하나다).

    ## 왜 꼬리 전류원이 필요한가

    빼 보면 안다. `M3` 이 없으면 스위치 두 개가 그냥 저항 분배기가 되어, 출력 스윙이
    **입력 공통모드에 따라 흔들린다.** 전류원이 스윙을 `I_SS·R` 로 **못 박는 것**이
    그 트랜지스터의 일이다. 대가는 헤드룸 `V_DS,sat` 한 칸이다.

    ## 슬루 -- 이것이 `serdes.슬루` 다

    출력 노드에 `C_L`(패드·ESD·패키지)이 매달려 있다. 전류가 `I_SS` 로 **막혀 있으므로**
    노드가 오를 수 있는 최대 기울기가

        dV/dt|max = I_SS / C_L

    이다. 한 표본 시간 `T_s = 1/(보드율·sps)` 동안 움직일 수 있는 몫을 스윙으로 나누면
    `serdes.슬루` 가 쓰는 정규화된 S 가 나오고, `V_swing = I_SS·R_eff` 를 넣으면
    **전류가 약분된다**:

        S = (I_SS/C_L)·T_s / (I_SS·R_eff) = T_s / (R_eff·C_L)

    **S 는 전류가 아니라 시상수의 문제다.** 꼬리 전류를 키우면 스윙과 슬루가 같이
    커져서 정규화된 S 는 그대로다. S 를 바꾸려면 `R·C` 를 바꿔야 한다.
    """
    R_eff = 1.0 / (1.0 / float(종단옴) + 2.0 / float(종단옴))   # R_D || (Z0/2), R_D=Z0
    스윙 = float(꼬리전류A) * R_eff                                # 단일단 스윙 [V]
    T_s = 1.0 / (float(보드율) * int(sps))
    tau = R_eff * float(부하F)
    return {"R_eff옴": R_eff, "단일단스윙V": 스윙, "차동스윙V": 2 * 스윙,
            "표본시간s": T_s, "시상수s": tau,
            "슬루V_per_s": float(꼬리전류A) / float(부하F),
            "S정규화": T_s / tau,
            "3dB대역Hz": 1.0 / (2 * math.pi * tau)}


def S를시상수로(S: float, 보드율: float = 20e9, sps: int = 8) -> float:
    """정규화된 슬루 `S` 를 **출력 시상수 초** 로 되돌린다. `tau = T_s / S`."""
    return 1.0 / (float(보드율) * int(sps) * float(S))


# ---------------------------------------------------------------- AFE · VGA

def 차동쌍전달(v_id: np.ndarray, 꼴: str = "약반전",
           V_ov: float = 0.1, n: float = 1.3) -> np.ndarray:
    """차동쌍의 **정규화 출력 전류** `I_od/I_SS`, 입력 `v_id` [V].

    ## 두 영역, 두 함수

    *약반전(subthreshold) · BJT.* 전류가 전압의 **지수**라 정확히

        I_od/I_SS = tanh( v_id / (2 n V_T) )

    가 나온다. `serdes.압축하기` 가 쓰는 tanh 가 **근사가 아니라 이 영역의 정확한 답**
    이다. 한계 스케일이 `2nV_T ~ 67 mV`(n=1.3) 로 **온도에만 달렸다**.

    *강반전(square law).* 포화 영역 제곱 법칙에서

        I_od/I_SS = (v_id/(√2·V_ov))·sqrt( 2 - (v_id/(√2·V_ov))^2 ) / √2 ... |v_id| < √2 V_ov
                  = ±1                                                      그 밖

    이고 `|v_id| = √2·V_ov` 에서 **완전히 기울어진다**(한쪽 스위치가 전류를 다 가져간다).
    tanh 보다 **더 급히 꺾인다** -- 무릎이 뾰족하다.

    둘 다 여기 있고, 어느 쪽이 `serdes` 의 tanh 에 얼마나 맞는지는 `압축맞춤()` 이 잰다.
    """
    v = np.asarray(v_id, dtype=float)
    if 꼴 in ("약반전", "subthreshold", "bjt", "BJT"):
        return np.tanh(v / (2.0 * float(n) * V_T))
    if 꼴 in ("강반전", "square"):
        x = v / (math.sqrt(2.0) * float(V_ov))
        안 = np.abs(x) < 1.0
        난다 = np.sign(x).astype(float)
        난다[안] = x[안] * np.sqrt(2.0 - x[안] ** 2) / math.sqrt(1.0)
        # 위 식의 최대가 1 이 되도록 정규화(x=1 에서 1)
        난다[안] = np.clip(난다[안], -1.0, 1.0)
        return 난다
    raise ValueError(f"모르는 꼴 {꼴!r} -- '약반전' 또는 '강반전'")


def 압축세기(입력rmsV: float, 꼴: str = "약반전", V_ov: float = 0.1,
         n: float = 1.3) -> dict:
    """**입력 스윙을 논문의 κ 로 옮긴다.** 이 함수가 이 모듈의 요점이다.

    `serdes.압축하기` 는 `tanh(a·y)/a`, `a = κ/rms(y)` 다. 회로에서는 tanh 의 스케일이
    **소자가 정한다**:

        약반전 · BJT   V_lim = 2 n V_T     ~ 67 mV (n=1.3, 300 K)
        강반전         V_lim = √2 V_ov     ~ 141 mV (V_ov = 100 mV)

    둘을 맞추면

        κ = V_in,rms / V_lim

    이다. 그러므로 논문의 κ 쓸기는 **입력 스윙 쓸기**다.

        κ = 1.0 -> 약반전에서 67 mV rms · 강반전에서 141 mV rms
        κ = 2.0 -> 약반전에서 134 mV rms · 강반전에서 283 mV rms

    ## **그런데 V_lim 은 상수가 아니다** -- SPICE 가 고쳐 준 것

    위 67 mV 는 **전류를 0 으로 보낸 극한**이다. sky130 `nfet_01v8` 로 실제로 돌려
    보니(`spice차동쌍()`, L=1u W=10u, tt) 바이어스에 따라 이렇게 움직인다:

        소자당 ID   0.1 uA    1 uA     10 uA    100 uA
        V_lim       78 mV    87 mV    117 mV   297 mV
        tanh 오차   0.012    0.013    0.034    0.105

    **깊은 약반전으로 갈수록 67 mV 와 tanh 에 수렴하고, 강반전으로 갈수록 둘 다
    멀어진다.** 20 GBd 앞단은 소자당 수백 uA 를 쓰므로 `V_lim ~ 300 mV` 쪽이다.

    그러므로 **κ 를 mV 로 옮길 때는 바이어스를 같이 적어야 한다.** "κ=2.0 = 134 mV"
    는 약반전 극한의 값이고, 실제 앞단에서는 **600 mV 에 가깝다** -- 그만큼 스윙이
    커야 그 압축이 걸린다는 뜻이고, 교차점이 더 먼 자리라는 뜻이다.

    **둘 다 실제 수신기 앞단이 보는 스윙이다.** 25 dB 채널을 지난 800 mVppd 송신이
    수신단에서 대략 45 mVppd 로 남고, AGC 가 그것을 올린다. 즉 논문이 교차점을 잡은
    κ≈2 는 **AFE 입력이 포화 무릎에 닿는 자리**이고, 헤드룸을 더 주거나(V_ov 를 올리거나)
    AGC 를 앞에 두면 그 자리를 옮길 수 있다 -- **설계로 옮길 수 있는 경계**라는 뜻이다.
    """
    V_lim = (2.0 * float(n) * V_T if 꼴 in ("약반전", "subthreshold", "bjt", "BJT")
             else math.sqrt(2.0) * float(V_ov))
    return {"꼴": 꼴, "V_lim_V": V_lim, "입력rmsV": float(입력rmsV),
            "kappa": float(입력rmsV) / V_lim,
            "κ1에필요한rms_mV": 1000.0 * V_lim,
            "κ2에필요한rms_mV": 2000.0 * V_lim}


def 압축맞춤(꼴: str = "강반전", V_ov: float = 0.1, n: float = 1.3,
         범위배: float = 2.0, 점: int = 2001) -> dict:
    """회로의 실제 전달 곡선이 `tanh` 와 얼마나 다른가 -- **재서 낸다.**

    `serdes.압축하기` 가 tanh 를 쓰므로, 강반전 쌍을 쓰는 설계에서는 그 근사가 얼마나
    나쁜지 알아야 한다. 같은 소신호 기울기(원점 기울기)로 맞춘 tanh 와 견준다.
    """
    V_lim = (2.0 * float(n) * V_T if 꼴 in ("약반전", "subthreshold", "bjt", "BJT")
             else math.sqrt(2.0) * float(V_ov))
    v = np.linspace(-범위배 * V_lim, 범위배 * V_lim, int(점))
    실제 = 차동쌍전달(v, 꼴, V_ov, n)
    # 원점 기울기를 맞춘다: tanh(v/s) 의 기울기 1/s = 실제의 원점 기울기
    h = v[1] - v[0]
    기울기 = float((실제[점 // 2 + 1] - 실제[점 // 2 - 1]) / (2 * h))
    근사 = np.tanh(기울기 * v)
    return {"꼴": 꼴, "V_lim_V": V_lim, "원점기울기_perV": 기울기,
            "최대차": float(np.max(np.abs(실제 - 근사))),
            "rms차": float(np.sqrt(np.mean((실제 - 근사) ** 2)))}


# ---------------------------------------------------------------- CTLE

def ctle전달(f: np.ndarray, gm: float = 20e-3, R_D: float = 500.0,
          R_S: float = 400.0, C_S: float = 80e-15,
          C_L: float = 40e-15) -> np.ndarray:
    """**소스 축퇴 차동쌍**의 전달함수 -- 영점 하나, 극점 둘.

    ## 왜 소스에 RC 를 다나

    축퇴 저항 `R_S` 는 저주파 이득을 `gm R_D / (1 + gm R_S/2)` 로 **깎는다.** 그런데
    `C_S` 가 병렬로 있으면 주파수가 오를수록 소스가 **접지로 단락**되어 축퇴가 사라지고
    이득이 `gm R_D` 로 **돌아온다.** 그 차이가 피킹이다.

        영점   ω_z  = 1/(R_S C_S)
        극점1  ω_p1 = (1 + gm R_S/2)/(R_S C_S)
        극점2  ω_p2 = 1/(R_D C_L)
        피킹   = 1 + gm R_S/2   (저주파 대비 고주파 이득비)

    **CTLE 는 신호를 올리는 것이 아니라 저주파를 깎는 것이다.** 그래서 잡음도 같이
    올라가고, 피킹을 계속 올린다고 BER 이 계속 좋아지지 않는다 -- `serdes.CTLE` 의
    머리말이 적은 그 사실의 회로적 까닭이 여기다.

    ## 어떤 트랜지스터가 왜 있나

        M1·M2  입력쌍. gm 이 이득을 만든다
        R_D    부하. 이득 `gm R_D` 와 극점2 `1/(R_D C_L)` 을 같이 정한다
        R_S·C_S 축퇴. **피킹의 양과 자리를 전부 여기서 고른다**
        M3     꼬리 전류원. 없으면 동작점이 공통모드를 따라 떠다닌다
    """
    s = 2j * math.pi * np.asarray(f, dtype=float)
    A_hf = float(gm) * float(R_D)
    분자 = 1.0 + s * float(R_S) * float(C_S)
    분모1 = (1.0 + float(gm) * float(R_S) / 2.0) + s * float(R_S) * float(C_S)
    분모2 = 1.0 + s * float(R_D) * float(C_L)
    return A_hf * 분자 / (분모1 * 분모2)


def ctle환산(gm: float = 20e-3, R_D: float = 500.0, R_S: float = 400.0,
          C_S: float = 80e-15, C_L: float = 40e-15,
          보드율: float = 20e9) -> dict:
    """회로값 -> `serdes.CTLE(피킹dB, 영점비, 극점비)` 의 인자."""
    f_nyq = float(보드율) / 2.0
    피킹 = 1.0 + float(gm) * float(R_S) / 2.0
    f_z = 1.0 / (2 * math.pi * float(R_S) * float(C_S))
    f_p1 = 피킹 / (2 * math.pi * float(R_S) * float(C_S))
    f_p2 = 1.0 / (2 * math.pi * float(R_D) * float(C_L))
    return {"피킹dB": 20.0 * math.log10(피킹), "피킹배": 피킹,
            "f_z_Hz": f_z, "f_p1_Hz": f_p1, "f_p2_Hz": f_p2,
            "영점비": f_z / f_nyq, "극점비": f_p2 / f_nyq,
            "저주파이득": float(gm) * float(R_D) / 피킹,
            "고주파이득": float(gm) * float(R_D)}


# ---------------------------------------------------------------- 샘플러

def strongarm(gm: float = 5e-3, C_L: float = 12e-15, V_DD: float = 0.9,
           UI초: float = 50e-12, 실패목표: float = 1e-12) -> dict:
    """**StrongARM 래치** -- 재생(regeneration)으로 판정한다.

    ## 전류가 어디로 흐르나 (네 단계)

    1. **리셋**(clk 낮음): PMOS 넷이 내부 노드를 `V_DD` 로 올려 놓는다. 꼬리는 꺼진다.
    2. **표본**(clk 오름): 꼬리 NMOS 가 켜지고, 입력쌍이 **입력 차이에 비례해** 두
       노드를 서로 다른 속도로 끌어내린다 -- 여기서 전압 차 `ΔV_0` 가 만들어진다.
    3. **재생**: 노드가 더 내려가 교차결합 인버터가 켜지면 **양의 되먹임**이 걸린다.
       차이가 `ΔV(t) = ΔV_0 · e^{t/τ}`, `τ = C_L/gm` 으로 **지수로 벌어진다.**
    4. **유지**: SR 래치가 결과를 붙든다.

    **증폭기가 없다.** 이 회로는 이득을 만드는 것이 아니라 **작은 차이를 시간으로
    키운다.** 그래서 정적 전력이 0 이고(클럭이 낮으면 전류 경로가 없다) 아주 빠르다.

    ## 왜 이것이 바닥과 이어지나

    한 UI 안에 `V_DD` 까지 벌리려면 초기 차이가

        ΔV_min = V_DD · e^{-UI/τ}

    보다 커야 한다. 그보다 작은 입력은 **메타스테이블**로 남는다. 이것이 판정 감도다.

    ## 기여자가 **둘**이다 -- 재생 감도가 아니라 오프셋

    아래는 **재생 감도**(메타스테이블 한계)를 잰 것이고, 그것은 실제로 작다. 그런데
    비교기에는 다른 한계가 있다 -- **미스매치 오프셋**이다. sky130 `tt_mm` 으로
    몬테카를로를 돌리니(`afespice.오프셋()`, W=20u·L=0.5u·nf=4·ID=100uA)

        비교기 재생 감도    41 uV       -- 무시할 만하다
        비교기 오프셋 sigma  1,400~2,000 uV  -- **ADC LSB 의 0.55~0.75배**
        ADC LSB(7비트)      2,617 uV

    **양자화와 오프셋이 같은 자리에 있고 재생 감도만 멀리 있다.** 오프셋은 면적으로
    줄일 수 있다(Pelgrom, `afespice.면적별오프셋()` 이 확인한다) -- 즉 바닥의 이 몫은
    **설계로 살 수 있는 것**이고, 양자화 몫은 ADC 비트로 사는 것이다.

    ## 실측이 이 tau 를 **7배** 로 고쳤다 -- 꼴은 맞고 `C_L` 이 틀렸다

    `afespice.strongarm()` 이 sky130 래치를 지어 입력 크기를 2,000배 쓸어 재생
    시상수를 쟀다(`t_해결 = t_0 + tau·ln(1/ΔV)` 의 기울기).

        실측 tau = **16.6~17.2 ps**        아래 기본값 gm=5mS·C_L=12fF 가 낸 것 2.4 ps

    닫힌 꼴 `tau = C_L/gm` 은 **맞다.** 틀린 것은 `C_L` 이다. 반전점에 세운
    교차결합단을 재니 `gm = 4.699 mS` 이고, 고리를 끊고 **다음단 게이트까지 단**
    노드 용량이 **80.2 fF** 였다 -- 밖에 단 짐(2 fF)이 아니라 교차결합쌍의 게이트
    용량이 대부분이다.

        tau = 80.2 fF / 4.699 mS = 17.07 ps     vs  실측 16.85 ps   -- 1.3% 차

    그래서 아래 기본값은 **밖에 단 짐만 센 값**이다. `C_L` 에는 고리가 지는 것을
    전부 넣어야 한다.

    ## 그 결과 감도가 nV 가 아니다 -- 20 GBd 한 UI 로는 못 푼다

    tau=16.85 ps 면 한 UI(50 ps)는 2.97 tau 뿐이고 감도는

        VDD·e^(-UI/tau) = 1.8·e^-2.97 = **88 mV**      -- ADC LSB 의 34배

    다. 아래가 낸 0.8 nV 가 아니다. LSB(2,617 uV) 아래로 가려면 141 ps 가 들고,
    그것은 **3-way 이상 인터리빙**이다. `바닥원인()` 의 결론("양자화가 바닥을
    정한다")은 **인터리빙이 3 이상일 때만** 선다. 130 nm 공정이라 그렇고, 실제
    112G SerDes 의 5~7 nm 에서는 tau 가 한 자릿수 작다 -- **이 공정에 대한
    진술**이지 제품에 대한 진술이 아니다.

    ## 여기서 내 예상이 또 틀렸다 -- 바닥의 원인은 이쪽이 아니다

    "§17.2 의 오류 바닥을 이 감도가 정한다" 고 적어 두었다가 **재 보니 아니었다.**
    gm=5 mS · C_L=12 fF 면 tau=2.4 ps 이고 50 ps 안에 e^20.8 ~ 1.1e9 배로 벌어져
    감도가 **0.8 nV** 다. C_L 을 두 배로 늘려도 41 uV 다. 그런데 7비트 ADC 의 LSB 는
    풀스케일 2.5sigma 에서 정규화 **0.039**(AFE 입력 rms 67 mV 면 2.6 mV)다.

        비교기 감도 41 uV  <<  ADC LSB 2,600 uV      -- 64배 차이

    **바닥을 정하는 것은 비교기의 재생 한계가 아니라 양자화 계단이다.** 이것은 실측과도
    맞는다 -- §17.2 의 바닥이 ADC 비트에 따라 1.13e-2 -> 5.7e-3 -> 1.1e-3 으로 내려갔다.
    비교기가 원인이었다면 ADC 비트를 올려도 안 움직였어야 한다. `바닥원인()` 이 이
    비교를 숫자로 낸다.

    **다만 이 단락의 숫자(41 uV, 0.8 nV)는 위에서 고친 `C_L` 을 안 쓴 것이다.** 실측
    `C_L=80.2 fF` 를 넣으면 인터리빙 없이는 96 mV 이고, 결론이 서려면 **3-way 이상
    인터리빙**이 필요하다. `바닥원인()` 은 이제 그것을 인자로 받는다.
    """
    tau = float(C_L) / float(gm)
    N = float(UI초) / tau
    ΔV_min = float(V_DD) * math.exp(-N)
    # 실패 확률 목표에서 필요한 여유(입력이 균등 분포라 치면 P ~ ΔV_min/V_swing)
    return {"tau_s": tau, "재생배수": math.exp(N), "UI당tau수": N,
            "감도V": ΔV_min, "감도uV": ΔV_min * 1e6,
            "실패목표": 실패목표,
            "필요스윙V": ΔV_min / max(실패목표, 1e-30)}


# ---------------------------------------------------------------- CDR

def cdr잔류지터(루프BW_Hz: float = 4e6, 지터PSD목록=None,
            보드율: float = 20e9) -> dict:
    """**뱅뱅 CDR** 이 못 지운 지터가 `serdes.지터표본` 의 `rjUI` 다.

    ## 회로

        Alexander(2x 오버샘플) 위상검출기 -> 전하펌프 -> 루프필터 -> VCO/위상보간기

    위상검출기는 `데이터 뒤집힘` 과 `가운데 표본` 의 부호만 본다 -- **빠른가 늦은가**
    한 비트다. 전하펌프가 그 한 비트로 커패시터에 전하를 넣거나 뺀다. 그 전압이 VCO 를
    민다. **곱셈기가 없다** -- 여기도 부호 한 비트가 전부다.

    ## 무엇이 남나

    루프는 **저역통과로 위상을 따라간다**. 전달이 `H(f)` 면 남는 것은 `1-H(f)` 다.

        residual^2 = ∫ |1 - H(f)|^2 S_φ(f) df

    일차 근사로 `|1-H|^2 ~ f^2/(f^2 + f_c^2)` 를 쓰면, **루프 대역 `f_c` 아래의 지터는
    따라가고 위는 그대로 남는다.** 그래서 잔류 지터는 대역 위 성분만 센 것이다.

    `지터PSD목록` 은 `[(f_Hz, rms_UI), ...]` 꼴의 정현 성분들이다(사인 지터 토막들).
    """
    if 지터PSD목록 is None:
        지터PSD목록 = [(1e5, 0.15), (1e6, 0.08), (1e7, 0.04), (1e8, 0.02)]
    남 = 0.0
    입 = 0.0
    조각 = []
    for f, rms in 지터PSD목록:
        억제 = (f ** 2) / (f ** 2 + float(루프BW_Hz) ** 2)     # |1-H|^2
        조각.append({"f_Hz": f, "입력UI": rms, "억제": 억제,
                    "잔류UI": rms * math.sqrt(억제)})
        남 += rms ** 2 * 억제
        입 += rms ** 2
    return {"루프BW_Hz": float(루프BW_Hz), "입력rjUI": math.sqrt(입),
            "잔류rjUI": math.sqrt(남), "조각": 조각}


# ---------------------------------------------------------------- FFE · DFE

def dfe1탭예산(보드율: float = 20e9, 래치ps: float = 12.0,
           합산ps: float = 8.0, 배선ps: float = 6.0,
           준비ps: float = 5.0) -> dict:
    """**DFE 첫 탭은 1 UI 안에 닫혀야 한다** -- 이 회로가 파이프라인이 안 되는 까닭.

    되먹임 고리가 `표본 -> 래치 판정 -> 레벨 시프트 -> 합산 노드 -> 다음 표본` 이고,
    이 전부가 **한 UI 안**에 끝나야 한다. 레지스터를 하나 끼우면 판정이 한 UI 늦어
    **고리 자체가 깨진다**(빼야 할 심볼이 이미 지나갔다).

        t_latch + t_summer + t_wire + t_setup <= 1 UI

    20 GBd 면 1 UI = 50 ps 다. 위 기본값이 31 ps 를 쓴다.

    **이것이 RTL 쪽에서 본 것과 같은 사실이다.** `eqrtl.ffe_dfe` 의 파이프라인 단을
    FFE 쪽에는 넣을 수 있어도 DFE 되먹임에는 못 넣는다고 적은 그 줄의 회로적 까닭이
    여기다. 그래서 고속 DFE 는 **unrolled(투기적) 구조**로 간다 -- 두 가능한 판정을
    미리 둘 다 계산해 두고 마지막에 먹스로 고른다. 곱셈기는 여전히 0개이고, **면적을
    2배 내서 시간을 사는 것**이다.
    """
    UI_ps = 1e12 / float(보드율)
    합 = float(래치ps) + float(합산ps) + float(배선ps) + float(준비ps)
    return {"UI_ps": UI_ps, "고리지연ps": 합, "여유ps": UI_ps - 합,
            "닫히나": bool(합 <= UI_ps),
            "최대보드율_GBd": 1e3 / 합}


def ffe탭_전류합산(탭수: int = 11, 단위전류A: float = 200e-6,
              부하옴: float = 200.0) -> dict:
    """**아날로그 FFE**: 탭마다 차동쌍 하나, 드레인을 **한 노드에 묶는다.**

    각 탭의 꼬리 전류가 그 탭의 계수다(`w_k ∝ I_k`). 드레인을 같은 부하에 물리면
    **키르히호프가 덧셈을 해 준다** -- 덧셈기가 따로 없다. 부호는 차동 출력을 꼬아서
    (+/- 를 바꿔 물려서) 고른다.

        V_out = R_L · Σ_k ±I_k · tanh(v_k / V_lim)

    **곱셈기가 없다.** 그런데 이것이 §16.4 의 분산 산술과도, 이 논문의 판정 표와도
    다르다 -- 여기서는 계수가 **전류의 크기**이고, 곱셈을 소자의 선형 영역이 해 준다.
    대가는 (ㄱ) 각 탭이 꼬리 전류를 상시로 먹고, (ㄴ) `tanh` 의 선형 구간 안에 있어야
    하므로 **입력 스윙이 제한된다**(κ 가 커지면 탭 자체가 비선형이 된다).
    """
    총전류 = int(탭수) * float(단위전류A)
    return {"탭수": int(탭수), "총꼬리전류A": 총전류,
            "총꼬리전류mA": 총전류 * 1e3,
            "최대출력스윙V": 총전류 * float(부하옴),
            "탭당전류uA": float(단위전류A) * 1e6,
            "곱셈기수": 0}


# ---------------------------------------------------------------- 검증

def 압축_검증(kappa: float = 1.5, 개수: int = 20000, 씨: int = 0) -> dict:
    """**차동쌍의 전달이 `serdes.압축하기` 와 같은 물건인가.**

    약반전 쌍은 정확히 `tanh(v/(2nV_T))` 이고, `serdes.압축하기` 는 `tanh(a y)/a` 다.
    `a = κ/rms(y)` 이므로 `κ = rms/(2nV_T)` 로 맞추면 **모양이 같아야** 한다(진폭
    정규화만 다르다 -- serdes 는 소신호 이득을 1 로 두려고 `a` 로 나눈다).
    """
    rng = np.random.default_rng(씨)
    y = rng.normal(0.0, 1.0, int(개수))
    rms = float(np.sqrt(np.mean(y ** 2)))
    z_sim = serdes.압축하기(y, float(kappa))
    n = 1.3
    V_lim = 2.0 * n * V_T
    v = y * (V_lim * float(kappa) / rms)          # rms 가 κ·V_lim 이 되게 스케일
    i_od = 차동쌍전달(v, "약반전", n=n)
    # 소신호 이득을 맞춰 겹친다
    a = float(kappa) / rms
    z_ckt = i_od / a * (1.0 / (V_lim * float(kappa) / rms)) * (V_lim * float(kappa) / rms)
    z_ckt = np.tanh(a * y) / a                    # 위 두 줄의 결과와 같다(닫힌 꼴로)
    차 = float(np.max(np.abs(z_sim - z_ckt)))
    # **회로 곡선 자체**와 겹치는지도 본다(스케일만 맞춰서)
    겹 = i_od * float(np.max(np.abs(z_sim))) / max(float(np.max(np.abs(i_od))), 1e-12)
    return {"kappa": float(kappa), "V_lim_V": V_lim,
            "입력rms_mV": 1000.0 * float(np.sqrt(np.mean(v ** 2))),
            "닫힌꼴최대차": 차,
            "회로곡선최대차": float(np.max(np.abs(z_sim - 겹))),
            "판정": serdes.PASS if 차 < 1e-12 else serdes.FAIL}


def ctle_검증(gm: float = 20e-3, R_D: float = 500.0, R_S: float = 400.0,
           C_S: float = 80e-15, C_L: float = 40e-15,
           보드율: float = 20e9, sps: int = 8) -> dict:
    """**`serdes.CTLE` 가 소스 축퇴쌍과 같은 모양인가** -- 재 보면 아니다.

    회로는 영점 `1/(R_S C_S)`, 극점 `A/(R_S C_S)` 와 `1/(R_D C_L)` 을 갖는다.
    `serdes.CTLE` 는 같은 1영점 2극점 꼴이지만 **두 극점을 `극점비·A` 와 `극점비·2` 로
    묶어 둔다** -- 둘째 극점이 첫째에 매여 있어서, 부하 극점을 따로 못 준다.

    그래서 대응은 **정확하지 않다.** 얼마나 다른지 대역 안에서 dB 로 재서 낸다.
    이것을 "같다" 고 적으면 회로 파라미터로 시뮬레이터를 몰 수 있다는 뜻이 되는데,
    그것이 참이 아니다.

    ## 정정 -- 못 쓰는 것은 **꼴이 아니라 매핑**이다

    처음에는 이 3.73 dB 를 "`serdes.CTLE` 는 진짜 CTLE 를 못 담는다" 로 읽었다.
    sky130 으로 실제 CTLE 를 돌려 보니(`afespice.ctle()`) 그게 아니었다:

        회로값을 그대로 넣은 매핑      3.73 dB
        세 파라미터를 **자유 맞춤**    **1.56 dB**
        내 닫힌 꼴(구조가 같다)로 맞춤   1.27 dB

    **1영점 2극점 꼴 자체는 실제 CTLE 를 1.6 dB 안에서 흉내 낸다.** 남는 1.3~1.6 dB 는
    C_gd 앞먹임·출력 컨덕턴스처럼 어느 3-파라미터 모형도 못 담는 것이다. 그러므로
    바른 문장은 "꼴이 틀렸다" 가 아니라 **"회로값을 파라미터로 옮기는 식이 틀렸다"** 다
    -- 회로로 시뮬레이터를 몰려면 **맞춤을 해야지 환산을 하면 안 된다.**
    """
    환 = ctle환산(gm, R_D, R_S, C_S, C_L, 보드율)
    f_nyq = 보드율 / 2.0
    f = np.linspace(f_nyq / 200.0, f_nyq * 1.2, 400)
    H_ckt = ctle전달(f, gm, R_D, R_S, C_S, C_L)
    H_ckt = H_ckt / H_ckt[0]
    # serdes.CTLE 와 같은 식(정규화 주파수 s = f/f_nyq)
    s = 1j * (f / f_nyq)
    A = 10.0 ** (환["피킹dB"] / 20.0)
    wz, wp = 환["영점비"], 환["극점비"]
    H_sim = (1.0 + s / wz) / ((1.0 + s / (wp * A)) * (1.0 + s / (wp * 2.0)))
    H_sim = H_sim / H_sim[0]
    d = 20.0 * np.log10(np.abs(H_ckt)) - 20.0 * np.log10(np.abs(H_sim))
    return {**환, "최대차dB": float(np.max(np.abs(d))),
            "Nyquist차dB": float(d[-1]),
            "같은가": bool(np.max(np.abs(d)) < 1.0)}


def ctle적용(x: np.ndarray, sps: int, gm: float = 20e-3, R_D: float = 500.0,
          R_S: float = 400.0, C_S: float = 80e-15, C_L: float = 40e-15,
          보드율: float = 20e9) -> np.ndarray:
    """**회로 그대로의 CTLE** 를 파형에 건다. DC 이득은 1 로 못 박는다."""
    N = len(x)
    fs = float(보드율) * int(sps)
    f = np.fft.rfftfreq(N, 1.0 / fs)
    H = ctle전달(f, gm, R_D, R_S, C_S, C_L)
    H = H / abs(H[0]) if abs(H[0]) > 0 else H
    return np.fft.irfft(np.fft.rfft(x) * H, n=N)


def 슬루_검증(보드율: float = 20e9, sps: int = 8) -> dict:
    """**`serdes.슬루` 의 S 가 회로에서 어떤 시상수인가** -- 그리고 그것이 말이 되나.

    `S = T_s/(R_eff·C_L)` 이므로 `tau = T_s/S` 다. 논문이 쓴 S 값들을 되돌려 본다.
    """
    T_s = 1.0 / (float(보드율) * int(sps))
    UI = 1.0 / float(보드율)
    줄 = []
    for S in (0.05, 0.02, 0.015, 0.01):
        tau = T_s / S
        줄.append({"S": S, "tau_ps": tau * 1e12, "tau_UI": tau / UI,
                  "3dB_GHz": 1.0 / (2 * math.pi * tau) / 1e9})
    쓸만 = cml드라이버(보드율=보드율, sps=sps)
    return {"UI_ps": UI * 1e12, "표본_ps": T_s * 1e12, "논문의S": 줄,
            "제대로된드라이버의S": 쓸만["S정규화"],
            "제대로된드라이버tau_ps": 쓸만["시상수s"] * 1e12}


def 바닥원인(gm: float = 4.699e-3, C_L: float = 80.2e-15, V_DD: float = 1.8,
         UI초: float = 50e-12, ADC비트: int = 7, 풀스케일시그마: float = 2.5,
         AFE입력rmsV: float = 0.067, 인터리빙: int = 8) -> dict:
    """**바닥을 정하는 것이 비교기인가 양자화인가** -- 둘을 같은 단위로 놓고 본다.

    비교기 감도는 `V_DD·e^{-T·gm/C_L}`, ADC 계단은 `2·rho·rms/2^B` 다. 둘을 볼트로
    옮겨 견주면 어느 쪽이 지배하는지 바로 보인다. **더 큰 쪽이 바닥을 정한다.**

    ## 기본값이 **셋** 바뀌었다 -- 실측이 고쳤다

    앞판은 `gm=5 mS · C_L=25 fF · V_DD=0.9 V` 로 41 uV 를 냈다. sky130 으로 실제
    래치를 재니(`afespice.strongarm`, `afespice.래치극점`)

        gm   = 4.699 mS      반전점에 세운 교차결합단
        C_L  = 80.2 fF       **고리가 지는** 용량(교차결합쌍 게이트까지). 밖에 단 2 fF 가 아니다
        V_DD = 1.8 V         sky130 01v8

    이고 `tau = 17.07 ps`(실측 16.85 ps, 1.3% 차)다.

    ## `인터리빙` 이 새로 들어왔다 -- **이것을 안 세면 결론이 뒤집힌다**

    래치가 쓸 수 있는 시간은 한 UI 가 아니라 `인터리빙 x UI` 다. ADC 기반 SerDes 는
    원래 수십 way 로 인터리빙한다.

        인터리빙 1  ->  감도 96,160 uV   **비교기가 바닥을 정한다**
        인터리빙 2  ->  5,137 uV         아직 LSB(2,617 uV)보다 크다
        인터리빙 3  ->  274 uV           여기서부터 양자화가 정한다
        인터리빙 8  ->  1.2e-4 uV        넉넉하다 -- 실제 ADC 기반 수신기의 자리

    그래서 "양자화가 바닥을 정한다" 는 **3-way 이상일 때** 서는 문장이다. 앞판은
    인터리빙을 안 세고 그 결론을 냈는데, 그때 쓴 tau=5 ps 가 실측의 1/3.4 라
    **틀린 값 둘이 서로를 가려** 맞는 결론이 나왔다.
    """
    비교기 = strongarm(gm=gm, C_L=C_L, V_DD=V_DD,
                    UI초=float(UI초) * max(int(인터리빙), 1))["감도V"]
    LSB정규 = 2.0 * float(풀스케일시그마) / (1 << int(ADC비트))
    LSB = LSB정규 * float(AFE입력rmsV)
    return {"비교기감도V": 비교기, "비교기감도uV": 비교기 * 1e6,
            "ADC_LSB정규": LSB정규, "ADC_LSB_V": LSB, "ADC_LSB_uV": LSB * 1e6,
            "비": LSB / max(비교기, 1e-30), "인터리빙": int(인터리빙),
            "쓸수있는시간s": float(UI초) * max(int(인터리빙), 1),
            "지배": "양자화" if LSB > 비교기 else "비교기 재생"}


def 지터_검증(보드율: float = 20e9) -> dict:
    """논문이 쓴 `지터rjUI` 가 실제 CDR 이 남기는 값인가."""
    줄 = []
    for bw in (2e6, 4e6, 10e6, 30e6):
        r = cdr잔류지터(루프BW_Hz=bw, 보드율=보드율)
        줄.append({"루프BW_MHz": bw / 1e6, "입력UI": r["입력rjUI"],
                  "잔류UI": r["잔류rjUI"]})
    쓴것 = [0.05, 0.10, 0.15]
    최소 = min(x["잔류UI"] for x in 줄)
    최대 = max(x["잔류UI"] for x in 줄)
    return {"루프쓸기": 줄, "논문이쓴rjUI": 쓴것,
            "실현범위UI": (최소, 최대),
            "말": (f"논문의 0.05 UI 는 루프 대역 ~2 MHz 에 해당한다(잔류 {최대:.3f} UI). "
                 f"0.15 UI 는 이 프로파일로는 안 나온다 -- **비관적인 값**이고, "
                 f"그 점에서 순서가 안 뒤집힌 것은 여유가 있다는 뜻이다")}


# ---------------------------------------------------------------- SPICE 대조

def spice차동쌍(꼬리전류A: float = 20e-6, W: float = 10.0, L: float = 1.0,
            부하옴: float = 5e3, VDD: float = 1.8, 코너: str = "tt",
            폭V: float = 0.4, 점: int = 161, 초: int = 300) -> dict:
    """**진짜 소자 모델로 차동쌍을 돌린다** -- 손계산이 맞는지 본다.

    sky130 `nfet_01v8`(BSIM4) 로 대신호 전달을 DC 스윕한다. 돌려주는 것은

        V_lim     원점 기울기의 역수 -- `압축세기()` 가 쓰는 그 한계 스케일
        tanh오차   같은 원점 기울기로 맞춘 tanh 와의 최대 차(정규화 출력 -1..+1)

    ## 재고 나서 알게 된 것 -- **V_lim 은 상수가 아니다**

    `압축세기()` 는 약반전 한계 `2nV_T ~ 67 mV` 를 썼다. 그것은 **전류를 0 으로
    보낸 극한**이고, 실제 바이어스에서는 더 크다(실측, L=1u W=10u, tt):

        I_SS      소자당 ID    V_lim      tanh 오차
        0.2 uA    0.1 uA       77.4 mV    0.008
        2   uA    1   uA       87.3 mV    0.013
        20  uA    10  uA      116.8 mV    0.034
        200 uA    100 uA      297.4 mV    0.105

    **깊은 약반전으로 갈수록 67 mV 와 tanh 에 수렴하고, 강반전으로 갈수록 둘 다
    멀어진다.** 20 GBd 앞단은 소자당 수백 uA 를 쓰므로 `V_lim ~ 300 mV` 쪽이다.
    그러므로 논문의 κ 를 mV 로 옮길 때는 **바이어스를 같이 적어야 한다** --
    "κ=2.0 = 134 mV" 는 약반전 극한의 값이고, 실제 앞단에서는 600 mV 에 가깝다.
    """
    import pdk
    import spice
    if not spice.있나():
        return {"판정": serdes.못잼, "왜": "ngspice 가 없다"}
    if not pdk.있나():
        받 = pdk.받기()
        if not 받["됐나"]:
            return {"판정": serdes.못잼, "왜": 받["왜"]}
    net = f"""* sky130 differential pair large-signal transfer
{pdk.lib줄(코너)}
.param ISS={꼬리전류A} VCM={VDD / 2.4:.4f}
VDD vdd 0 {VDD}
VID vid 0 0
Eip ip 0 vol='VCM + 0.5*v(vid)'
Eim im 0 vol='VCM - 0.5*v(vid)'
RD1 vdd d1 {부하옴}
RD2 vdd d2 {부하옴}
XM1 d1 ip tail 0 sky130_fd_pr__nfet_01v8 L={L} W={W} nf=1 m=1
XM2 d2 im tail 0 sky130_fd_pr__nfet_01v8 L={L} W={W} nf=1 m=1
ITAIL tail 0 {{ISS}}
.control
save v(d1) v(d2)
dc VID {-폭V} {폭V} {2 * 폭V / (점 - 1):.6f}
print v(d1) v(d2)
.endc
.end
"""
    r = spice.돌리기(net, 초=초)
    줄 = []
    for 한줄 in r["로그"].splitlines():
        조각 = 한줄.split()
        if len(조각) == 4 and 조각[0].isdigit():
            try:
                줄.append((float(조각[1]), float(조각[2]), float(조각[3])))
            except ValueError:
                pass
    if len(줄) < 20:
        return {"판정": serdes.못잼,
                "왜": f"곡선을 못 읽었다({len(줄)}점) -- {r['왜']}", "로그": r["로그"][-600:]}
    a = np.array(줄)
    vid, v1, v2 = a[:, 0], a[:, 1], a[:, 2]
    iod = (v2 - v1) / (float(꼬리전류A) * float(부하옴))
    k = len(vid) // 2
    기울기 = float((iod[k + 1] - iod[k - 1]) / (vid[k + 1] - vid[k - 1]))
    맞춤 = np.tanh(기울기 * vid)
    return {"판정": serdes.PASS, "왜": "",
            "꼬리전류A": float(꼬리전류A), "소자당ID_uA": 5e5 * float(꼬리전류A),
            "원점기울기_perV": 기울기, "V_lim_mV": 1000.0 / abs(기울기),
            "tanh오차": float(np.max(np.abs(iod - 맞춤))),
            "포화값": float(np.max(np.abs(iod))), "점수": len(vid)}


def spice_검증(꼬리들=(0.2e-6, 2e-6, 20e-6, 200e-6)) -> dict:
    """바이어스를 쓸어 **V_lim 이 약반전 극한으로 수렴하는지** 본다."""
    줄 = []
    for I in 꼬리들:
        r = spice차동쌍(꼬리전류A=I)
        if r["판정"] != serdes.PASS:
            return {"판정": serdes.못잼, "왜": r["왜"], "줄": 줄}
        줄.append(r)
    극한 = 1000.0 * 2 * 1.3 * V_T
    단조 = all(줄[i]["V_lim_mV"] < 줄[i + 1]["V_lim_mV"] for i in range(len(줄) - 1))
    좋아짐 = all(줄[i]["tanh오차"] < 줄[i + 1]["tanh오차"] for i in range(len(줄) - 1))
    return {"판정": serdes.PASS, "약반전극한_mV": 극한, "줄": 줄,
            "V_lim이단조증가": 단조, "tanh오차도단조증가": 좋아짐,
            "제일작은V_lim_mV": 줄[0]["V_lim_mV"],
            "극한에가까운가": 줄[0]["V_lim_mV"] < 1.3 * 극한}
