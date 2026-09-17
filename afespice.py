"""**손계산을 진짜 소자 모델로 친다** -- sky130 + ngspice.

`afe.py` 는 닫힌 꼴이다. 그 값이 맞는지는 소자가 답한다. 이 모듈은 블록마다 sky130
넷리스트를 짓고 ngspice 로 돌려 **같은 양을 다시 잰다.**

    차동쌍 V_lim      `afe.압축세기` 가 쓴 2nV_T 가 맞나        -> afe.spice차동쌍
    CTLE 응답         `serdes.CTLE` 가 진짜 CTLE 를 표현하나
    비교기 오프셋      바닥의 또 다른 원인 (미스매치 몬테카를로)
    CML 에지          **못 했다** -- 아래

## 재고 나서 세 번 고쳤다

이 모듈을 돌리기 전에 `afe.py` 가 적어 둔 것 중 **셋이 정확하지 않았다.**

    적었던 것                              소자가 말한 것
    V_lim = 2nV_T = 67 mV (상수)           78~297 mV, 바이어스에 따라 움직인다
    serdes.CTLE 는 3.73 dB 어긋난다         **자유 맞춤**이면 1.56 dB. 못 쓰는 것은
                                           회로값 -> 파라미터 **매핑**이지 꼴이 아니다
    제대로 된 CML 은 S=6.25(슬루 없음)      130nm sky130 은 **S=0.30**, 에지가 0.91 UI

셋 다 "닫힌 꼴이 틀렸다" 가 아니라 **"닫힌 꼴이 어느 극한의 값인지 안 적었다"** 였다.
그것을 안 적으면 숫자가 혼자 걸어 다닌다.

## CML 에지는 **못 했다** -- 숫자를 안 싣는다

`serdes.슬루` 의 S 를 실제 드라이버에서 재려고 세 번 지어 봤고 세 번 다 못 믿을
값이 나왔다.

    큰 소자(총 8,000 um)      스윙 1,274 mVppd -- 이상적 2·I·R_eff = 400 mV 를 넘는다
    작은 소자(총 100 um)      스윙 161 mVppd · **꼬리 노드가 -0.337 V** 로 내려간다
    `.meas` 로 에지 재기       창 밖 교차를 잡아 상승 시간이 **음수**로 나온다

꼬리 노드가 접지 아래로 간다는 것은 **이상적 전류원이 그 소자로 실현 불가능한 전류를
강요하고 있다**는 뜻이다 -- 설계가 자기모순이다. 진짜 꼬리 트랜지스터와 헤드룸 예산을
세우고 크기를 제대로 잡아야 하는데, 그것은 이 문서의 범위를 넘는 회로 설계다.

**그래서 S 에 대한 SPICE 값은 내지 않는다.** `afe.슬루_검증()` 의 닫힌 꼴 결론
(논문의 S 는 시상수 2.5~8.3 UI 에 해당한다)은 그대로 두고, "실제 드라이버가 정확히
얼마인지" 는 **안 잰 것으로 남긴다.** 못 믿을 숫자를 싣는 것이 안 싣는 것보다 나쁘다.
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
            "면적um2": float(W) * float(L) * int(nf)}


def 면적별오프셋(짝들=((20.0, 0.5, 4), (80.0, 0.5, 4), (20.0, 2.0, 4)),
           씨수: int = 25) -> dict:
    """**Pelgrom**: `sigma_Vos ∝ 1/sqrt(W·L)` 이 실제로 성립하나.

    실측(sky130 tt_mm, ID=100uA, 씨 30):

        면적 40 um2   sigma 1.392 mV      (기준)
        면적 160      0.740 · 0.789 mV    예측 0.696 -- **W 로 키우든 L 로 키우든 같다**
        면적 640      0.447 mV            예측 0.348

    면적 법칙이 선다(같은 면적이면 W·L 배분이 달라도 sigma 가 거의 같다). 큰 면적에서
    조금 얕은 것은 BSIM 미스매치에 면적 말고도 항이 더 있기 때문이다.
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
