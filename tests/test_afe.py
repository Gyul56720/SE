"""**회로와 시뮬레이터를 맞댄다.** 그림은 검사가 아니다.

`afe.py` 는 블록마다 소자 파라미터에서 논문의 손잡이를 닫힌 꼴로 낸다. 그 대응이
맞는지는 **재 봐야** 안다 -- 회로도를 그려 놓고 "이렇게 동작한다" 고 적는 것은 이
저장소가 쫓아온 거짓 초록과 같은 부류다.

    (가) 약반전 차동쌍의 전달이 `serdes.압축하기` 와 **정확히 같은 함수**인가
    (나) `S = T_s/(R_eff·C_L)` 이 `serdes.슬루` 가 실제로 하는 것과 맞나
    (다) `serdes.CTLE` 는 소스 축퇴쌍과 **다르다** -- 그 차이가 남아 있나
    (라) 바닥을 정하는 것이 비교기가 아니라 양자화인가 (ADC 눈금을 **재서**)
    (마) DFE 되먹임 예산이 보드율에 따라 닫히고 안 닫히나

(다)가 중요하다. "같다" 가 아니라 **"다르다"를 붙드는 검사**다 -- 나중에 누가
회로값으로 시뮬레이터를 몰려고 하면 여기서 걸려야 한다.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import afe
import serdes

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


print("[가 -- 약반전 차동쌍 = serdes.압축하기]")
for kappa in (0.5, 1.0, 2.0):
    rng = np.random.default_rng(3)
    y = rng.normal(0.0, 1.0, 20000)
    rms = float(np.sqrt(np.mean(y ** 2)))
    n = 1.3
    V_lim = 2.0 * n * afe.V_T
    v = y * (V_lim * kappa / rms)                 # rms 가 κ·V_lim 이 되게
    회로 = afe.차동쌍전달(v, "약반전", n=n)
    # serdes 쪽: tanh(a y)/a. 같은 모양인지 보려면 스케일만 맞춘다.
    시뮬 = serdes.압축하기(y, kappa)
    a = kappa / rms
    겹 = np.tanh(a * y)                            # = 회로의 I_od/I_SS 여야 한다
    ok(float(np.max(np.abs(회로 - 겹))) < 1e-12,
       f"κ={kappa}: 회로 전달 = tanh(a·y), 최대차 {np.max(np.abs(회로 - 겹)):.1e} "
       f"(입력 rms {1000 * np.sqrt(np.mean(v ** 2)):.1f} mV)")
    ok(float(np.max(np.abs(시뮬 * a - 겹))) < 1e-12,
       f"κ={kappa}: serdes.압축하기 는 그것을 a 로 나눈 것이다(소신호 이득 1)")
# κ 환산이 되돌아오나
m = afe.압축세기(0.134, "약반전")
ok(abs(m["kappa"] - 2.0) < 0.01,
   f"입력 134 mV rms -> κ={m['kappa']:.2f} (약반전 V_lim {1000 * m['V_lim_V']:.1f} mV)")

print("[나 -- 슬루 정규화가 serdes.슬루 와 맞나]")
sps, baud = 8, 20e9
for S in (0.05, 0.02):
    x = np.concatenate([np.zeros(40), np.ones(4000)])
    v = serdes.슬루(x, S)
    걸음 = float(np.max(np.abs(np.diff(v))))
    ok(abs(걸음 - S) < 1e-12, f"S={S}: 한 표본 최대 걸음이 정확히 S 다 ({걸음:.6f})")
    tau = afe.S를시상수로(S, baud, sps)
    T_s = 1.0 / (baud * sps)
    ok(abs(tau - T_s / S) < 1e-24,
       f"S={S} -> tau {tau * 1e12:.0f} ps = {tau * baud:.1f} UI")
# **논문이 쓴 S 는 20 GBd 드라이버로 닿을 수 없다** -- 그 사실을 붙든다
r = afe.슬루_검증(baud, sps)
ok(r["제대로된드라이버의S"] > 1.0,
   f"제대로 된 CML 은 S={r['제대로된드라이버의S']:.2f} -- 1 보다 커서 "
   f"**슬루 제한이 안 걸린다**(tau {r['제대로된드라이버tau_ps']:.2f} ps)")
ok(all(x["tau_UI"] > 2.0 for x in r["논문의S"]),
   "논문이 쓴 S 는 전부 tau > 2 UI -- " +
   " · ".join(f"S={x['S']}:{x['tau_UI']:.1f}UI" for x in r["논문의S"]))

print("[다 -- serdes.CTLE 는 소스 축퇴쌍이 아니다]")
c = afe.ctle_검증()
ok(not c["같은가"] and c["최대차dB"] > 1.0,
   f"피킹 {c['피킹dB']:.1f} dB 로 맞춰도 대역 안에서 최대 {c['최대차dB']:.2f} dB "
   f"어긋난다 -- 회로값으로 시뮬레이터를 몰 수 없다")
# 회로 전달함수는 저주파/고주파 이득이 닫힌 꼴과 맞아야 한다
f = np.array([1e3, 1e14])
H = afe.ctle전달(f, gm=20e-3, R_D=500.0, R_S=400.0, C_S=80e-15, C_L=40e-15)
env = afe.ctle환산(gm=20e-3, R_D=500.0, R_S=400.0, C_S=80e-15, C_L=40e-15)
ok(abs(abs(H[0]) - env["저주파이득"]) / env["저주파이득"] < 0.01,
   f"DC 이득 {abs(H[0]):.3f} = g_m R_D/(1+g_m R_S/2) = {env['저주파이득']:.3f}")

print("[라 -- 바닥을 정하는 것: 비교기인가 양자화인가]")
# **ADC 눈금을 serdes.ADC 에서 재서** 가져온다(식을 검사 안에 베껴 적지 않는다).
램프 = np.linspace(-2.5, 2.5, 20001)
양자, _ = serdes.ADC(램프, 7, 2.5)
계단 = np.unique(np.round(np.diff(np.unique(양자)), 12))
LSB = float(계단[계단 > 0].min())
b = afe.바닥원인(ADC비트=7, 풀스케일시그마=2.5, AFE입력rmsV=0.067)
ok(abs(b["ADC_LSB정규"] - LSB) / LSB < 0.02,
   f"ADC 눈금: afe 가 쓴 {b['ADC_LSB정규']:.4f} = serdes.ADC 에서 잰 {LSB:.4f}")
ok(b["지배"] == "양자화" and b["비"] > 10,
   f"LSB {b['ADC_LSB_uV']:.0f} µV 가 비교기 감도 {b['비교기감도uV']:.0f} µV 의 "
   f"{b['비']:.0f}배 -- **바닥은 양자화가 정한다**")
# 비교기를 아주 느리게 만들면 뒤집혀야 한다(검사가 살아 있는지)
느린 = afe.바닥원인(gm=1e-3, C_L=60e-15, ADC비트=12)
ok(느린["지배"] == "비교기 재생",
   f"대조: 느린 비교기(gm 1 mS · C 60 fF) + 12비트 ADC 에서는 "
   f"비교기가 지배한다 -- 검사가 한쪽으로 고정돼 있지 않다")

print("[마 -- DFE 1탭 예산]")
닫 = [afe.dfe1탭예산(보드율=b)["닫히나"] for b in (10e9, 20e9, 28e9, 56e9)]
ok(닫 == [True, True, True, False],
   f"10/20/28 GBd 는 닫히고 56 GBd 는 안 닫힌다 -- 한계 "
   f"{afe.dfe1탭예산()['최대보드율_GBd']:.1f} GBd")
빠 = afe.dfe1탭예산(보드율=20e9, 래치ps=6.0, 합산ps=4.0, 배선ps=3.0, 준비ps=2.0)
ok(빠["최대보드율_GBd"] > afe.dfe1탭예산()["최대보드율_GBd"],
   f"고리를 빠르게 하면 한계가 올라간다 ({빠['최대보드율_GBd']:.0f} GBd)")

print("[바 -- CDR 잔류 지터]")
j = afe.지터_검증()
낮, 높 = j["실현범위UI"]
ok(낮 < 0.05 < 높 * 1.2,
   f"논문이 쓴 0.05 UI 가 실현 범위 [{낮:.3f}, {높:.3f}] 안이다")
좁 = afe.cdr잔류지터(루프BW_Hz=2e6)["잔류rjUI"]
넓 = afe.cdr잔류지터(루프BW_Hz=30e6)["잔류rjUI"]
ok(좁 > 넓, f"루프를 넓히면 잔류가 준다 ({좁:.3f} -> {넓:.3f} UI)")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for m in FAIL_목록:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
