"""**손계산을 진짜 소자 모델로 친다** -- sky130 + ngspice.

`afe.py` 는 닫힌 꼴이다. 그 값이 맞는지는 소자가 답한다. 이 모듈은 블록마다 sky130
넷리스트를 짓고 ngspice 로 돌려 **같은 양을 다시 잰다.**

    차동쌍 V_lim      `afe.압축세기` 가 쓴 2nV_T 가 맞나        -> afe.spice차동쌍
    CTLE 응답         `serdes.CTLE` 가 진짜 CTLE 를 표현하나
    비교기 오프셋      바닥의 또 다른 원인 (미스매치 몬테카를로)
    CML 에지          `serdes.슬루` 의 S 가 진짜 드라이버에서 얼마인가   -> cml
    StrongARM 재생     `afe.strongarm` 의 tau = C_L/gm 이 맞나            -> strongarm

## 재고 나서 **다섯** 을 고쳤다

이 모듈을 돌리기 전에 `afe.py` 가 적어 둔 것 중 다섯이 정확하지 않았다.

    적었던 것                              소자가 말한 것
    V_lim = 2nV_T = 67 mV (상수)           78~297 mV, 바이어스에 따라 움직인다
    serdes.CTLE 는 3.73 dB 어긋난다         **자유 맞춤**이면 1.56 dB. 못 쓰는 것은
                                           회로값 -> 파라미터 **매핑**이지 꼴이 아니다
    제대로 된 CML 은 S=6.25               S=2.45~2.70 -- 꼴은 맞고 **스위칭 바닥**을 뺐다
    StrongARM tau = C_L/gm = 2.4 ps        **16.85 ps** -- 꼴은 맞고 넣은 C 가 6.7배 작았다
    Pelgrom 면적 = W·L·nf                  sky130 의 `W` 는 **총폭**이다. 면적 = W·L

다섯 다 "닫힌 꼴이 틀렸다" 가 아니라 **"닫힌 꼴이 어느 극한의, 어느 양의 값인지 안
적었다"** 였다. 그것을 안 적으면 숫자가 혼자 걸어 다닌다.

## 못 하던 두 칸을 채웠다 -- `W` 는 총폭이다

앞판에는 "CML 에지는 못 했다" 가 적혀 있었다. 세 번 지어 세 번 다 못 믿을 값이
나왔다 -- 꼬리 노드가 **-0.337 V** 로 내려가거나(이상적 전류원이 실현 불가능한
전류를 강요한다는 뜻) 스윙이 이상적 한계를 넘었다.

**원인은 회로가 아니라 내가 소자 크기를 20~40배 작게 썼다는 것이었다.** sky130 에서
`W` 는 핑거 하나의 폭이 아니라 **총폭**이고 `nf` 는 그것을 나누는 수다. 실측:

    W=1  nf=1          149 uA        W=10 nf=10     1,672 uA
    W=10 nf=1        1,784 uA        W=1 nf=1 m=10  1,489 uA

크기를 제대로 잡으니 자기모순이 사라졌고, 두 칸이 다 채워졌다(`cml`, `strongarm`).
**"못 믿을 숫자를 싣는 것이 안 싣는 것보다 나쁘다" 는 그대로다** -- 다만 이번에는
못 믿을 이유를 찾아서 고쳤다.
"""
from __future__ import annotations

import math
import re
import subprocess

import numpy as np

import afe
import pdk
import serdes
import spice


def 됐나(왜: str = "") -> bool:
    return spice.있나() and (pdk.있나() or pdk.받기()["됐나"])


def _표뽑기(로그: str, 열: int = 3) -> np.ndarray:
    """ngspice `print` 표에서 숫자 줄만 건진다. 열 수가 맞는 줄만."""
    줄 = []
    for 한 in 로그.splitlines():
        c = 한.split()
        if len(c) == 열 + 1 and c[0].isdigit():
            try:
                줄.append([float(x) for x in c[1:]])
            except ValueError:
                pass
    return np.array(줄) if 줄 else np.zeros((0, 열))


def ctle(ID: float = 200e-6, RD: float = 3e3, RS: float = 2e3,
         CS: float = 200e-15, CL: float = 30e-15, W: float = 50.0,
         L: float = 0.5, nf: int = 10, 보드율: float = 20e9,
         초: int = 300) -> dict:
    """**진짜 소스 축퇴 CTLE 의 AC 응답**, 그리고 두 모형이 그것을 얼마나 잘 맞추나.

    `serdes.CTLE` 의 세 파라미터(피킹·영점비·극점비)를 **자유롭게 최적화해서** 맞춘
    잔차를 낸다. `afe.ctle환산` 이 낸 매핑 값으로 맞춘 것과 구분해야 한다 --

        매핑으로 맞춤    3.73 dB 어긋난다  (회로값을 그대로 넣었을 때)
        자유 맞춤        1.56 dB           (세 파라미터를 최적화했을 때)

    **그러니까 못 쓰는 것은 꼴이 아니라 매핑이다.** 1영점 2극점 꼴 자체는 실제 CTLE 를
    1.6 dB 안에서 흉내 낸다. 남는 1.6 dB 는 C_gd 앞먹임·출력 컨덕턴스 같은, 어느
    3-파라미터 모형도 못 담는 것이다(내 닫힌 꼴도 1.27 dB 남는다).
    """
    if not 됐나():
        return {"판정": serdes.못잼, "왜": "ngspice 나 sky130 이 없다"}
    net = f"""* sky130 source-degenerated CTLE
{pdk.lib줄('tt')}
VDD vdd 0 1.8
VCM vcm 0 0.85
VID vid 0 dc 0 ac 1
Eip ip 0 vol='v(vcm) + 0.5*v(vid)'
Eim im 0 vol='v(vcm) - 0.5*v(vid)'
RD1 vdd d1 {RD}
RD2 vdd d2 {RD}
XM1 d1 ip s1 0 sky130_fd_pr__nfet_01v8 L={L} W={W} nf={nf} m=1
XM2 d2 im s2 0 sky130_fd_pr__nfet_01v8 L={L} W={W} nf={nf} m=1
RS1 s1 s2 {RS}
CS1 s1 s2 {CS}
I1 s1 0 {ID}
I2 s2 0 {ID}
CL1 d1 0 {CL}
CL2 d2 0 {CL}
.control
save v(d1) v(d2)
ac dec 40 1e6 1e11
let g = db(v(d2) - v(d1))
print g
.endc
.end
"""
    r = spice.돌리기(net, 초=초)
    a = _표뽑기(r["로그"], 2)
    if len(a) < 50:
        return {"판정": serdes.못잼, "왜": f"AC 곡선을 못 읽었다({len(a)}점) -- {r['왜']}"}
    f, g = a[:, 0], a[:, 1]
    f_nyq = float(보드율) / 2.0
    안 = (f >= 1e7) & (f <= 1.2 * f_nyq)
    f, g = f[안], g[안] - g[안][0]
    i0, ip = 0, int(np.argmax(g))

    def 시뮬(피킹dB, wz, wp):
        s = 1j * (f / f_nyq)
        A = 10.0 ** (피킹dB / 20.0)
        H = (1 + s / wz) / ((1 + s / (wp * A)) * (1 + s / (wp * 2.0)))
        return 20.0 * np.log10(np.abs(H / H[0]))

    최선 = None
    for pk in np.arange(1.0, 14.1, 0.25):
        for wz in np.geomspace(0.01, 1.0, 45):
            for wp in np.geomspace(0.02, 3.0, 45):
                e = float(np.max(np.abs(시뮬(pk, wz, wp) - g)))
                if 최선 is None or e < 최선[0]:
                    최선 = (e, float(pk), float(wz), float(wp))
    return {"판정": serdes.PASS, "왜": "",
            "DC이득dB": float(g[i0]), "피크dB": float(g[ip]),
            "피킹dB": float(g[ip] - g[i0]), "피크Hz": float(f[ip]),
            "자유맞춤_최대잔차dB": 최선[0],
            "자유맞춤_피킹dB": 최선[1], "자유맞춤_영점비": 최선[2],
            "자유맞춤_극점비": 최선[3], "점수": int(len(f))}


def 오프셋(씨수: int = 30, W: float = 20.0, L: float = 0.5, nf: int = 4,
        ID: float = 100e-6, 코너: str = "tt_mm", 초: int = 120) -> dict:
    """**입력쌍 오프셋을 미스매치 몬테카를로로 잰다** -- 바닥의 또 다른 원인.

    sky130 은 `tt_mm` 코너에 미스매치를 담고 있다. 씨앗을 바꿔 가며 돌려, 출력
    전류 차가 0 이 되는 입력 전압(= 오프셋)의 분포를 낸다.

    **ngspice 제어어 안의 되돌이로는 안 된다** -- `reset` 을 해도 `agauss` 가 새로
    안 뽑혀 60회가 전부 같은 값이었다(실측). 씨앗을 바꿔 **프로세스를 따로 띄운다.**

    ## 왜 이것이 §17.2 의 바닥과 이어지나

    `afe.바닥원인()` 은 비교기의 **재생 감도**(41 uV)를 ADC LSB(2,617 uV)와 견주고
    "양자화가 지배한다" 고 했다. 맞는데, **오프셋은 다른 이야기다** -- 실측 sigma 가
    W=20u·L=0.5u·nf=4 에서 **1.44 mV** 로 LSB 의 0.55배다. 즉 바닥에는 기여자가
    **둘**이고 둘의 크기가 비슷하다. 오프셋은 면적으로 줄일 수 있다(Pelgrom).
    """
    if not 됐나():
        return {"판정": serdes.못잼, "왜": "ngspice 나 sky130 이 없다"}
    본 = f"""* sky130 input-pair offset, one MC draw
{pdk.lib줄('%s')}
VDD vdd 0 1.8
VCM vcm 0 0.85
VOS vos 0 0
Eip ip 0 vol='v(vcm) + 0.5*v(vos)'
Eim im 0 vol='v(vcm) - 0.5*v(vos)'
RD1 vdd d1 2k
RD2 vdd d2 2k
XM1 d1 ip s 0 sky130_fd_pr__nfet_01v8 L={L} W={W} nf={nf} m=1
XM2 d2 im s 0 sky130_fd_pr__nfet_01v8 L={L} W={W} nf={nf} m=1
ITAIL s 0 {2 * ID}
.control
set rndseed = %d
save v(d1) v(d2)
dc VOS -30m 30m 0.5m
print v(d1) v(d2)
.endc
.end
"""

    def 한번(씨, 코): 
        r = spice.돌리기(본 % (코, 씨), 초=초)
        a = _표뽑기(r["로그"], 3)
        if len(a) < 10:
            return None
        v, dd = a[:, 0], a[:, 1] - a[:, 2]
        i = np.where(np.sign(dd[:-1]) != np.sign(dd[1:]))[0]
        if not len(i):
            return None
        k = int(i[0])
        return float(v[k] - dd[k] * (v[k + 1] - v[k]) / (dd[k + 1] - dd[k]))

    없음 = 한번(1, "tt")                      # 대조: 미스매치 없으면 0 이라야 한다
    값 = [x for x in (한번(s, 코너) for s in range(1, int(씨수) + 1)) if x is not None]
    if len(값) < 5:
        return {"판정": serdes.못잼, "왜": f"{len(값)}회밖에 못 잰다"}
    v = np.array(값) * 1e3
    return {"판정": serdes.PASS, "왜": "", "회수": len(v),
            "대조_미스매치없음_mV": (None if 없음 is None else 없음 * 1e3),
            "평균mV": float(v.mean()), "시그마mV": float(v.std(ddof=1)),
            "최대절대mV": float(np.abs(v).max()),
            "면적um2": float(W) * float(L)}


def 면적별오프셋(짝들=((20.0, 0.5, 4), (80.0, 0.5, 4), (20.0, 2.0, 4)),
           씨수: int = 25) -> dict:
    """**Pelgrom**: `sigma_Vos ∝ 1/sqrt(W·L)` 이 실제로 성립하나.

    실측(sky130 tt_mm, ID=100uA, 씨 30):

        면적 10 um2   sigma 1.392 mV      (기준)
        면적 40       0.740 · 0.789 mV    예측 0.696 -- **W 로 키우든 L 로 키우든 같다**
        면적 160      0.447 mV            예측 0.348

    면적 법칙이 선다(같은 면적이면 W·L 배분이 달라도 sigma 가 거의 같다). 큰 면적에서
    조금 얕은 것은 BSIM 미스매치에 면적 말고도 항이 더 있기 때문이다.

    ## 면적을 **네 배로 잘못 적었었다** -- sky130 의 `W` 는 총폭이다

    처음에는 `면적 = W·L·nf` 로 적었다. sky130 소자에서 `W` 는 **핑거 하나의 폭이
    아니라 총폭**이고 `nf` 는 그것을 몇 조각으로 나누는지다(실측으로 확인했다:
    W=10/nf=1 과 W=10/nf=10 이 같은 전류를 낸다. W=1/nf=1/m=10 도 거의 같다).
    그러니 면적은 `W·L` 이다. **비(比)는 안 바뀌므로 위의 결론은 그대로**이고,
    절대 면적만 네 배 작아진다.
    """
    난다 = []
    기준 = None
    for W, L, nf in 짝들:
        r = 오프셋(씨수=씨수, W=W, L=L, nf=nf)
        if r["판정"] != serdes.PASS:
            return {"판정": serdes.못잼, "왜": r["왜"], "줄": 난다}
        면적 = r["면적um2"]
        if 기준 is None:
            기준 = (r["시그마mV"], 면적)
        난다.append({**r, "W": W, "L": L, "nf": nf,
                    "예측시그마mV": 기준[0] * math.sqrt(기준[1] / 면적)})
    return {"판정": serdes.PASS, "왜": "", "줄": 난다}


_CML본 = """* sky130 CML 드라이버 -- 제대로 크기를 잡은 것
{lib}
VDD vdd 0 1.8
Vip ip 0 PULSE({lo} {hi} 0 {에지}p {에지}p {폭}p {주기}p)
Vim im 0 PULSE({hi} {lo} 0 {에지}p {에지}p {폭}p {주기}p)
VB  b  0 {VB}
RD1 vdd o1 {RD}
RD2 vdd o2 {RD}
RT1 o1 vdd {RD}
RT2 o2 vdd {RD}
CL1 o1 0 {CL}f
CL2 o2 0 {CL}f
XM1 o1 ip t 0 sky130_fd_pr__nfet_01v8 L={Ls} W={Ws} nf={nfs} m=1
XM2 o2 im t 0 sky130_fd_pr__nfet_01v8 L={Ls} W={Ws} nf={nfs} m=1
XM3 t   b  s 0 sky130_fd_pr__nfet_01v8 L={Lt} W={Wt} nf={nft} m=1
Vsense s 0 0
.control
save v(o1) v(o2) v(t) i(Vsense)
tran {걸음}p {끝}p
let vod = v(o1) - v(o2)
meas tran vhi FIND vod AT={잼A}p
meas tran vlo FIND vod AT={잼B}p
meas tran ttail MIN v(t) from={창0}p to={끝}p
meas tran o1lo MIN v(o1) from={창0}p to={끝}p
meas tran itail MAX i(Vsense) from={창0}p to={끝}p
meas tran itaillo MIN i(Vsense) from={창0}p to={끝}p
meas tran itailav AVG i(Vsense) from={창0}p to={끝}p
meas tran o1hi MAX v(o1) from={창0}p to={끝}p
{에지잼}
.endc
.end
"""


def cml(CL: float = 60.0, 보드율: float = 20e9, sps: int = 8, VB: float = 1.0, RD: float = 50.0,
        Ws: float = 100.0, nfs: int = 50, Ls: float = 0.15,
        Wt: float = 300.0, nft: int = 60, Lt: float = 0.5,
        스윙: float = 0.6, 공통: float = 1.5, 에지: float = 8.0,
        코너: str = "tt", 초: int = 300) -> dict:
    """**제대로 설계한 CML 드라이버의 에지를 잰다** -- `serdes.슬루` 의 `S` 가 얼마인가.

    `serdes.슬루` 는 기울기 한계를 `S = T_s/(R_eff·C_L)` 한 숫자로 넣는다. 논문은 그
    숫자를 0.05~0.015 로 쓸었는데, **진짜 드라이버가 그 값 근처인지 잰 적이 없었다.**

    ## 세 번 못 잰 뒤에 무엇이 틀렸는지 알았다 -- `W` 는 총폭이다

    처음 세 번은 꼬리 노드가 **-0.337 V** 로 내려가거나(이상적 전류원이 실현 불가능한
    전류를 강요하고 있다는 뜻이다) 스윙이 이상적 한계를 넘었다. 원인은 소자 크기였다.
    sky130 에서 `W` 는 **핑거 하나가 아니라 총폭**이고 `nf` 는 그것을 나누는 수다.
    실측으로 붙들었다:

        W=1  nf=1          149 uA
        W=10 nf=1        1,784 uA        -- W 를 열 배 하면 열 배
        W=10 nf=10       1,672 uA        -- nf 를 바꿔도 거의 같다
        W=1  nf=1 m=10   1,489 uA        -- m 열 배도 거의 같다

    그래서 내 소자는 **20~40배 작았다.** 꼬리가 낼 수 없는 전류를 요구받으니 노드가
    접지 밑으로 내려간 것이다. 크기를 제대로 잡으니 자기모순이 사라졌다.

    ## 스윙을 두 번 잘못 읽었다 -- 창 전체의 MAX/MIN 은 스파이크를 잡는다

    처음에는 `.meas MAX/MIN` 으로 창 전체에서 스윙을 읽었다. 684 mVppd 가 나왔는데
    이상적 한계 `2·I·R_eff` 는 524 mV 다 -- **30% 넘친다.** 앞판 세 번을 못 믿게 만든
    바로 그 증상이다. 원인은 이번엔 회로가 아니라 **읽는 자리**였다: 입력 에지가
    스위치의 `C_gd` 를 통해 출력 노드로 밀어 넣는 스파이크를 MAX 가 잡는다.

    **가라앉은 자리**(다음 에지 3 ps 전)에서 읽으니

        단일단 스윙 261.8 mV     I_꼬리·R_eff = 10.47 mA × 25 Ω = 261.8 mV
        비                       **1.000**

    네 자리까지 맞는다. 꼬리 전류는 출력이 아니라 **꼬리에 따로 단 0 V 원**으로
    쟀으니 이 일치는 정의가 아니라 검사다(KCL 이 다른 길로 한 번 더 닫힌다).

    ## 실측 (20 GBd · 스위치 W=100u · 꼬리 W=300u · R_eff=25 Ω · 입력 600 mVppd)

        C_L(fF)     0      30      60     200     500    1000
        상승 20-80% 3.22    3.21    3.54    6.90   17.30   34.26  ps
        tau         2.33    2.32    2.55    4.98   12.48   24.71  ps
        R_eff·C_L   0       1.50    1.50    5.00   12.50   25.00  ps
        S           2.69    2.70    2.45    1.26    0.50    0.25

    꼬리 노드는 0.580 V 로 접지 위에 얌전히 있다 -- 자기모순이 사라졌다.

    ## 닫힌 꼴 `tau = R_eff·C_L` 은 **자기 영역에서 정확하다**

    C_L 이 지배하면 실측이 `R_eff·C_L` 과 **0.2~1.2% 안에서** 만난다(200 fF 에서
    4.98 vs 5.00, 500 fF 에서 12.48 vs 12.50, 1 pF 에서 24.71 vs 25.00). 작은 C_L
    에서는 **2.33 ps 의 바닥**이 남는데, 그것은 RC 가 아니라 **차동쌍이 스위칭하는
    속도**다(입력 에지 8 ps 에 V_lim 이 작아 입력보다 빨리 갈린다).

    `afe.cml드라이버` 의 기본값(C_L=100 fF)이 낸 S=6.25 는 그 바닥을 안 세어 낙관적이고,
    바닥까지 세면 **S=2.5~2.7** 이다. 꼴은 맞고 **바닥 항을 안 적었다.**

    ## 그래서 논문의 S 는 물리적으로 무엇인가 -- **5~17 pF 의 부하**다

    `S = T_s/(R_eff·C_L)` 을 C_L 로 풀면

        S=0.05  ->  tau=125 ps  ->  C_L =  **5.0 pF**
        S=0.015 ->  tau=417 ps  ->  C_L = **16.7 pF**

    20 GBd 드라이버의 패드·ESD·패키지는 다 합쳐 100~300 fF 다. **20~170배 어긋난다.**
    그러니 논문의 S 쓸기는 "이 드라이버가 그렇다" 가 아니라 **"표를 깨려면 이만큼
    가야 한다"** 는 뜻이고, 실제로 `eqsweep` 에서 슬루는 표를 못 깼다. 두 사실이
    서로 맞는다.
    """
    if not 됐나():
        return {"판정": serdes.못잼, "왜": "ngspice 나 sky130 이 없다"}
    UI = 1.0 / float(보드율)
    주기 = 5.0 * UI * 1e12
    폭 = 주기 / 2.0 - 에지
    끝 = 5.0 * 주기
    창0 = 3.0 * 주기
    본 = dict(lib=pdk.lib줄(코너), lo=공통 - 스윙 / 2, hi=공통 + 스윙 / 2,
             에지=에지, 폭=폭, 주기=주기, VB=VB, RD=RD, CL=CL,
             Ls=Ls, Ws=Ws, nfs=nfs, Lt=Lt, Wt=Wt, nft=nft,
             걸음=0.05, 끝=끝, 창0=창0,
             잼A=창0 + 주기 / 2 - 3.0, 잼B=창0 + 주기 - 3.0)

    r = spice.돌리기(_CML본.format(에지잼="", **본), 초=초)
    잰 = spice.잰것뽑기(r["로그"])
    if "vhi" not in 잰 or "vlo" not in 잰:
        return {"판정": serdes.못잼, "왜": "스윙을 못 읽었다", "로그": r["로그"][-800:]}
    # **가라앉은 자리에서 읽는다.** 창 전체의 MAX/MIN 을 쓰면 입력 에지가 Cgd 로
    # 밀어 넣는 스파이크를 스윙으로 읽어 I·R_eff 보다 30% 큰 값이 나온다(실측).
    vhi, vlo = max(잰["vhi"], 잰["vlo"]), min(잰["vhi"], 잰["vlo"])
    # 두 벌로 재는 이유: ngspice 42 의 `.meas ... VAL='식'` 이 조용히 실패한다(실측).
    낮 = vlo + 0.2 * (vhi - vlo)
    높 = vlo + 0.8 * (vhi - vlo)
    에지잼 = (f"meas tran trise TRIG vod VAL={낮:.6f} RISE=2 "
            f"TARG vod VAL={높:.6f} RISE=2")
    r2 = spice.돌리기(_CML본.format(에지잼=에지잼, **본), 초=초)
    잰2 = spice.잰것뽑기(r2["로그"])
    상승 = 잰2.get("trise")
    if 상승 is None or not (0 < 상승 < 주기 * 1e-12):
        return {"판정": serdes.못잼, "왜": f"상승시간을 못 읽었다 ({상승})",
                "로그": r2["로그"][-800:]}
    # **자기모순 검사**: 꼬리를 흐르는 전류(따로 단 0V 원으로 잰 것)와 출력 스윙이
    # `V_single = I·R_eff` 로 맞아야 한다. 앞판 세 번은 여기가 안 맞았다.
    R_eff = float(RD) / 2.0                   # RD1 과 RT1 이 둘 다 vdd 로 가므로 병렬
    I꼬리 = abs(잰.get("itail", float("nan")))
    I꼬리최소 = abs(잰.get("itaillo", float("nan")))
    I꼬리평균 = abs(잰.get("itailav", float("nan")))
    단일 = (vhi - vlo) / 2.0
    tau = 상승 / math.log(0.8 / 0.2)          # 한 극점이면 t_2080 = tau·ln4
    T_s = UI / int(sps)                        # `serdes.슬루` 의 S 는 **표본**당이다
    return {"판정": serdes.PASS, "왜": "",
            "차동mVppd": (vhi - vlo) * 1e3, "꼬리최소V": 잰.get("ttail"),
            "상승s": 상승, "상승UI": 상승 / UI, "tau_s": tau, "tau_UI": tau / UI,
            "S": T_s / tau, "표본s": T_s, "UI_s": UI, "CL_fF": CL,
            "꼬리전류A": I꼬리, "꼬리전류최소A": I꼬리최소, "꼬리전류평균A": I꼬리평균,
            "R_eff옴": R_eff, "단일단스윙V": 단일,
            "스윙_IR비": 단일 / max(I꼬리평균 * R_eff, 1e-12)}


_SA본 = """* sky130 StrongARM 래치 -- dV={dv}
{lib}
Vdd vdd 0 1.8
Vclk clk 0 PULSE(0 1.8 {t0}p 5p 5p {hi}p {주기}p)
Vip ip 0 {vip}
Vim im 0 {vim}
XMT t clk 0 0 sky130_fd_pr__nfet_01v8 L=0.15 W={Wt} nf={nft} m=1
XM1 dp ip t 0 sky130_fd_pr__nfet_01v8 L=0.15 W={Wi} nf={nfi} m=1
XM2 dm im t 0 sky130_fd_pr__nfet_01v8 L=0.15 W={Wi} nf={nfi} m=1
XM3 op om dm 0 sky130_fd_pr__nfet_01v8 L=0.15 W={Wn} nf={nfn} m=1
XM4 om op dp 0 sky130_fd_pr__nfet_01v8 L=0.15 W={Wn} nf={nfn} m=1
XM5 op om vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wp} nf={nfp} m=1
XM6 om op vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wp} nf={nfp} m=1
XM7 op clk vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wr} nf={nfr} m=1
XM8 om clk vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wr} nf={nfr} m=1
XM9  dp clk vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wr} nf={nfr} m=1
XM10 dm clk vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wr} nf={nfr} m=1
CP op 0 {CL}f
CM om 0 {CL}f
CDP dp 0 {Cd}f
CDM dm 0 {Cd}f
.control
save v(op) v(om) v(clk)
tran {걸음}p {끝}p
let vod = v(op) - v(om)
meas tran tres TRIG v(clk) VAL=0.9 RISE=1 TARG vod VAL={목표:.4f} RISE=1
meas tran vend FIND vod AT={끝잼}p
.endc
.end
"""


def strongarm(dV들=(0.4, 0.2, 0.1, 0.05, 0.02, 0.01, 5e-3, 2e-3, 1e-3, 5e-4, 2e-4),
              공통: float = 1.2, CL: float = 2.0, Cd: float = 1.0,
              Wi: float = 20.0, nfi: int = 10, Wt: float = 40.0, nft: int = 20,
              Wn: float = 10.0, nfn: int = 5, Wp: float = 20.0, nfp: int = 10,
              Wr: float = 6.0, nfr: int = 3, VDD: float = 1.8,
              보드율: float = 20e9, 코너: str = "tt", 초: int = 300) -> dict:
    """**StrongARM 래치의 재생 시상수를 입력 크기 쓸기로 잰다.**

    재생이 지수면 해결 시간은 입력 크기의 **로그**다.

        t_해결 = t_0 + tau · ln(1/ΔV_in)

    그러니 `t_해결` 을 `ln(1/ΔV_in)` 에 대해 그으면 **기울기가 tau** 다. 파형에서
    `ln|vod|` 의 기울기로 직접 재는 길과 **따로** 재서 서로 맞는지 본다.

    ## 첫 판은 거짓 값을 냈다 -- 공통모드 하강을 해결로 읽었다

    처음에는 `v(om)` 이 VDD/2 를 지나는 때로 쟀다. 작은 ΔV 에서 **47.3 ps 로 평평**
    해졌고 "감도 바닥이 50 uV" 로 읽힐 뻔했다. 공차를 1000배 조여도 안 움직였으니
    수치 문제도 아니었다. **ΔV=0 으로 돌려 보니 답이 나왔다** -- 래치는 안 풀리고
    (op=om=0.867 V 메타스테이블) 그런데도 `tres` 가 47.3 ps 를 냈다. 두 출력이
    **함께** 내려가는 공통모드 하강이 문턱을 지난 것이었다.

    차동 `vod = v(op)-v(om)` 로 바꾸니 **ΔV 를 40,000배 쓸어도 로그 법칙이 곧게**
    선다(잔차 rms 1.38 ps). 한 노드로 재면 안 된다.

    ## 실측 (sky130 tt, VDD=1.8V, 공통 1.2V, 위 크기)

        ΔV       400mV   100mV    10mV     1mV    0.2mV   0.01mV
        t_해결   61.5ps  78.9ps  118.3ps  157.1ps 184.2ps 234.6ps

        맞춤:  t_해결 = 42.3 ps + tau·ln(1/ΔV),  **tau = 16.59 ps**  (기본 쓸기 2,000배)
        ΔV 를 0.01 mV 까지 넓히면(40,000배)      tau = 16.68 ps, 잔차 rms 1.38 ps
        파형의 ln|vod| 기울기(따로 잰 것):       **tau = 16.85~17.17 ps**

    세 길이 3% 안에서 만난다. 지수 구간을 셋으로 쪼개도 tau 가 16.85 · 16.84 · 16.90 ps
    로 **안 움직인다** -- 재생이 정말 한 지수다.

    ## `afe.strongarm` 의 닫힌 꼴은 **꼴이 맞고 넣은 값이 틀렸다**

    `tau = C_L/gm` 이다. 반전점에 세운 교차결합단을 재니 `gm = 4.699 mS`(nmos 2.754 +
    pmos 1.945), 고리를 끊고 다음단 게이트까지 단 노드 용량이 **80.2 fF** 였다.

        tau = 80.2 fF / 4.699 mS = 17.07 ps      vs  실측 16.85 ps   -- 1.3% 차

    **닫힌 꼴은 맞다.** 틀린 것은 `afe.strongarm` 의 기본값 `C_L=12 fF` 였다 -- 그것은
    **밖에 단 짐**이고, 고리가 지는 것은 교차결합쌍의 **게이트 용량까지 포함한** 80 fF
    다. 6.7배 차이다. V_lim 과 CTLE 때와 같은 부류의 잘못이다: 꼴이 아니라 **그 꼴이
    어느 값을 가리키는지**를 안 적었다.

    ## 그래서 감도가 nV 가 아니다 -- 20 GBd 한 UI 로는 못 푼다

    tau=16.85 ps 면 한 UI(50 ps)는 **2.97 tau** 뿐이다.

        감도 = VDD·e^(-UI/tau) = 1.8·e^-2.97 = **92 mV**       -- ADC LSB 의 35배
        `afe.strongarm` 기본값(tau=2.4ps)이 낸 값                  0.8 nV

    ADC LSB(7비트, 2,617 uV)보다 작아지려면 `ln(1.8/2.617e-3)=6.53 tau` = 110 ps 가
    든다. **위 쓸기에서 직접 읽으면** ΔV=2.6 mV 를 푸는 데 141 ps 다 -- 2.8 UI,
    즉 `필요인터리빙 = 3`.

    **결론은 살아남되 조건이 붙는다.** "비교기 감도가 아니라 양자화가 바닥을 정한다"
    는 맞는데, 그것은 **3-way 이상으로 인터리빙했을 때**다. 한 래치를 20 GBd 로 그냥
    돌리면 비교기가 바닥을 정한다. 130 nm 공정이라 그렇고, 실제 112G SerDes 의 5~7 nm
    에서는 tau 가 한 자릿수 작다 -- 그러니 이것은 **이 공정에 대한 진술**이지 제품에
    대한 진술이 아니다.
    """
    if not 됐나():
        return {"판정": serdes.못잼, "왜": "ngspice 나 sky130 이 없다"}
    UI = 1.0 / float(보드율)
    t0, hi, 끝 = 50.0, 400.0, 500.0
    공 = dict(lib=pdk.lib줄(코너), t0=t0, hi=hi, 주기=2 * 끝, CL=CL, Cd=Cd,
             Wt=Wt, nft=nft, Wi=Wi, nfi=nfi, Wn=Wn, nfn=nfn, Wp=Wp, nfp=nfp,
             Wr=Wr, nfr=nfr, 걸음=0.05, 끝=끝, 끝잼=끝 - 5,
             목표=0.9 * VDD)
    줄 = []
    for dv in dV들:
        본 = _SA본.format(dv=dv, vip=공통 + dv / 2, vim=공통 - dv / 2, **공)
        r = spice.돌리기(본, 초=초)
        잰 = spice.잰것뽑기(r["로그"])
        t = 잰.get("tres")
        if t is None or not (0 < t < 끝 * 1e-12):
            continue
        줄.append((float(dv), float(t), float(잰.get("vend", float("nan")))))
    if len(줄) < 5:
        return {"판정": serdes.못잼, "왜": f"{len(줄)}점밖에 못 잰다"}
    a = np.array(줄)
    기울기, 절편 = np.polyfit(-np.log(a[:, 0]), a[:, 1], 1)
    잔 = a[:, 1] - (기울기 * (-np.log(a[:, 0])) + 절편)
    tau = float(기울기)
    return {"판정": serdes.PASS, "왜": "", "줄": [tuple(x) for x in a.tolist()],
            "tau_s": tau, "절편_s": float(절편),
            "잔차rms_s": float(잔.std()), "쓸기배수": float(a[:, 0].max() / a[:, 0].min()),
            "해결폭_s": float(a[:, 1].max() - a[:, 1].min()),
            "잔차비": float(잔.std() / max(a[:, 1].max() - a[:, 1].min(), 1e-15)),
            "UI_s": UI, "UI당tau수": UI / tau,
            "감도V": VDD * math.exp(-UI / tau),
            "필요인터리빙": int(math.ceil(
                (절편 + tau * math.log(1.0 / 2.617e-3)) / UI))}


_극점본 = """* 교차결합쌍의 고리를 끊고, 노드가 실제로 지는 짐을 잰다
{lib}
Vdd vdd 0 1.8
Lfb  gA oA 1T
Cin  gin gA 1T
Vin  gin 0 DC 0 AC 1
XMNA oA gA 0   0   sky130_fd_pr__nfet_01v8 L=0.15 W={Wn} nf={nfn} m=1
XMPA oA gA vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wp} nf={nfp} m=1
CLA  oA 0 {CL}f
XMNB oB oA 0   0   sky130_fd_pr__nfet_01v8 L=0.15 W={Wn} nf={nfn} m=1
XMPB oB oA vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wp} nf={nfp} m=1
CLB  oB 0 {CL}f
XMNC oC oB 0   0   sky130_fd_pr__nfet_01v8 L=0.15 W={Wn} nf={nfn} m=1
XMPC oC oB vdd vdd sky130_fd_pr__pfet_01v8 L=0.15 W={Wp} nf={nfp} m=1
CLC  oC 0 {CL}f
.control
op
print @m.xmna.msky130_fd_pr__nfet_01v8[gm]
print @m.xmpa.msky130_fd_pr__pfet_01v8[gm]
print @m.xmna.msky130_fd_pr__nfet_01v8[gds]
print @m.xmpa.msky130_fd_pr__pfet_01v8[gds]
ac dec 60 1e6 1e13
let m1 = db(v(oA))
meas ac a0 FIND m1 AT=1e6
meas ac f3db WHEN m1={f3:.4f} FALL=1
.endc
.end
"""


def 래치극점(Wn: float = 10.0, nfn: int = 5, Wp: float = 20.0, nfp: int = 10,
         CL: float = 2.0, 코너: str = "tt", 초: int = 300) -> dict:
    """**`tau = C/gm` 에 넣을 `C` 와 `gm` 을 소자에서 직접 뽑는다.**

    교차결합쌍을 반전점에 세우면 그 한쪽은 그냥 인버터다. 고리를 끊고(DC 되먹임은
    1 TH 인덕터로, AC 입력은 1 TF 커패시터로) 재면

        gm = gm_n + gm_p,  gds = gds_n + gds_p,  극점 f3dB = gds/(2·pi·C)

    가 나오고 `C = gds/(2·pi·f3dB)` 다. 중요한 것은 **다음단 게이트를 달아야** 한다는
    것 -- 고리가 지는 짐에는 교차결합쌍의 게이트 용량이 들어 있다. 이것을 빼면 C 가
    9.8 fF 로 나오고(`tau` 2.3 ps), 달면 **80.2 fF**(`tau` 17.1 ps)다. 실측 재생
    시상수 16.85 ps 와 맞는 쪽은 **단 쪽**이다.
    """
    if not 됐나():
        return {"판정": serdes.못잼, "왜": "ngspice 나 sky130 이 없다"}
    공 = dict(lib=pdk.lib줄(코너), Wn=Wn, nfn=nfn, Wp=Wp, nfp=nfp, CL=CL)
    r = spice.돌리기(_극점본.format(f3=-1e9, **공), 초=초)
    잰 = spice.잰것뽑기(r["로그"])
    if "a0" not in 잰:
        return {"판정": serdes.못잼, "왜": "DC 이득을 못 읽었다"}
    r2 = spice.돌리기(_극점본.format(f3=잰["a0"] - 3.0, **공), 초=초)
    잰2 = spice.잰것뽑기(r2["로그"])
    f3 = 잰2.get("f3db")
    if not f3 or f3 <= 0:
        return {"판정": serdes.못잼, "왜": "극점을 못 읽었다"}
    본로그 = r["로그"]
    def 값(이름):
        for 한 in 본로그.splitlines():
            if 이름 in 한 and "=" in 한:
                try:
                    return float(한.split("=")[-1].strip())
                except ValueError:
                    pass
        return float("nan")
    gm = 값("xmna.msky130_fd_pr__nfet_01v8[gm]") + 값("xmpa.msky130_fd_pr__pfet_01v8[gm]")
    gds = 값("xmna.msky130_fd_pr__nfet_01v8[gds]") + 값("xmpa.msky130_fd_pr__pfet_01v8[gds]")
    C = gds / (2 * math.pi * f3)
    return {"판정": serdes.PASS, "왜": "", "gm_S": gm, "gds_S": gds,
            "DC이득": gm / gds, "f3dB_Hz": f3, "C_F": C,
            "tau_C_gm_s": C / gm, "tau_C_gm말고_s": C / max(gm - gds, 1e-9)}


def 래치오프셋(씨수: int = 20, 공통: float = 1.2, 걸음: int = 12,
          범위: float = 0.05, 코너: str = "tt_mm",
          Wi: float = 20.0, nfi: int = 10, Wt: float = 40.0, nft: int = 20,
          Wn: float = 10.0, nfn: int = 5, Wp: float = 20.0, nfp: int = 10,
          Wr: float = 6.0, nfr: int = 3, 초: int = 300) -> dict:
    """**래치 통째의 입력환산 오프셋** -- 입력쌍만 잰 것과 다르다.

    `오프셋()` 은 **차동쌍 하나**의 오프셋을 잰다(sigma 1.4~2.0 mV). 그런데 판정을
    하는 것은 래치 통째이고, 교차결합쌍·리셋 소자의 미스매치도 **작은 앞단 이득을
    거쳐** 입력으로 환산된다. 그래서 씨앗마다 래치를 돌려 **답이 뒤집히는 ΔV** 를
    이분법으로 찾는다 -- 그것이 그 씨앗의 오프셋이다.

    ## 실측 (sky130 tt_mm, 씨 20, 이분법 12걸음 = 25 uV 해상도)

        평균 -1.342 mV      sigma **4.059 mV**      최대 절대 12.5 mV

    **입력쌍만 잰 1.4~2.0 mV 의 두 배가 넘고, ADC LSB(2,617 uV)의 1.55배다.** 즉
    §17.2 바닥의 기여자 셋 중 **이것이 가장 크다**:

        비교기 재생 감도    8-way 인터리빙에서 1e-4 uV      -- 무시할 만하다
        ADC LSB(7비트)      2,617 uV
        **래치 오프셋 sigma  4,059 uV**                     -- 가장 크다

    둘이 큰 이유는 (가) 이 래치의 입력쌍이 `L=0.15u`(면적 3 um2)로 `오프셋()` 이 쓴
    `L=0.5u`(면적 10 um2)보다 작고 -- Pelgrom 만으로도 1.8배 -- (나) 교차결합쌍과
    리셋 소자가 더해지기 때문이다. **면적으로 살 수 있는 몫**이고, 실제 수신기는
    여기에 오프셋 보정을 단다.
    """
    if not 됐나():
        return {"판정": serdes.못잼, "왜": "ngspice 나 sky130 이 없다"}
    공 = dict(lib=pdk.lib줄(코너), t0=50.0, hi=400.0, 주기=900.0, CL=2.0, Cd=1.0,
             Wt=Wt, nft=nft, Wi=Wi, nfi=nfi, Wn=Wn, nfn=nfn, Wp=Wp, nfp=nfp,
             Wr=Wr, nfr=nfr, 걸음=0.2, 끝=400.0, 끝잼=395.0, 목표=1.62)

    def vod(씨, dv):
        본 = _SA본.format(dv=dv, vip=공통 + dv / 2, vim=공통 - dv / 2, **공)
        본 = 본.replace(".control\n", f".control\nset rndseed = {int(씨)}\n")
        잰 = spice.잰것뽑기(spice.돌리기(본, 초=초)["로그"])
        return 잰.get("vend")

    def 한씨(씨):
        lo, hi = -abs(범위), abs(범위)
        a, b = vod(씨, lo), vod(씨, hi)
        if a is None or b is None or not (a < 0 < b):
            return None
        for _ in range(int(걸음)):
            m = 0.5 * (lo + hi)
            v = vod(씨, m)
            if v is None:
                return None
            if v < 0:
                lo = m
            else:
                hi = m
        return -0.5 * (lo + hi)

    값 = [x for x in (한씨(s) for s in range(1, int(씨수) + 1)) if x is not None]
    if not 값:
        return {"판정": serdes.못잼, "왜": "한 씨앗도 못 쟀다"}
    v = np.array(값) * 1e3
    return {"판정": serdes.PASS, "왜": "", "회수": len(v),
            "평균mV": float(v.mean()),
            "시그마mV": float(v.std(ddof=1)) if len(v) > 1 else float("nan"),
            "최대절대mV": float(np.abs(v).max()),
            "해상도uV": abs(범위) * 2e6 / (1 << int(걸음))}
