"""**sky130 + ngspice 로 손계산을 친다.** 둘이 없으면 건너뛴다.

`afe.py` 는 닫힌 꼴이고 `afespice.py` 는 같은 양을 진짜 소자로 다시 잰다. 이 검사가
붙드는 것은 **두 값이 같다**가 아니라 **어긋나는 자리를 알고 있다**는 것이다 --
어긋남을 숫자로 적어 두면, 나중에 누가 닫힌 꼴을 회로처럼 쓰려 할 때 걸린다.

    (가) CTLE: `serdes.CTLE` 의 꼴은 실제 CTLE 를 ~1.6 dB 안에서 흉내 낸다.
         **못 쓰는 것은 꼴이 아니라 회로값 -> 파라미터 매핑이다**(그쪽은 3.7 dB).
    (나) 오프셋: 미스매치가 없으면 정확히 0, 있으면 mV 급 -- **ADC LSB 와 같은 자리**
    (다) Pelgrom: 면적을 키우면 sigma 가 준다. 같은 면적이면 W·L 배분이 달라도 같다.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import afe
import afespice
import pdk
import serdes
import spice

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


if not spice.있나():
    print("ngspice 가 없다 -- 건너뛴다")
    raise SystemExit(0)
if not (pdk.있나() or pdk.받기()["됐나"]):
    print("sky130 모델을 못 구했다 -- 건너뛴다:", pdk.말로()[:120])
    raise SystemExit(0)

print("[가 -- 실제 CTLE 를 두 모형이 얼마나 맞추나]")
c = afespice.ctle()
ok(c["판정"] == serdes.PASS, f"sky130 CTLE AC 가 돈다 ({c.get('왜', '')[:60]})")
if c["판정"] == serdes.PASS:
    ok(2.0 < c["피킹dB"] < 12.0 and 3e8 < c["피크Hz"] < 1e10,
       f"피킹 {c['피킹dB']:.2f} dB @ {c['피크Hz'] / 1e9:.2f} GHz -- 실제 CTLE 의 자리다")
    ok(c["자유맞춤_최대잔차dB"] < 2.5,
       f"`serdes.CTLE` 의 3파라미터를 **자유 맞춤**하면 최대 잔차 "
       f"{c['자유맞춤_최대잔차dB']:.2f} dB -- 꼴 자체는 쓸 만하다")
    # **매핑은 그만큼 못 한다** -- 그 차이가 이 검사의 요점이다
    매 = afe.ctle_검증()
    ok(매["최대차dB"] > c["자유맞춤_최대잔차dB"],
       f"회로값을 그대로 넣은 매핑은 {매['최대차dB']:.2f} dB 로 더 나쁘다 -- "
       f"**고칠 것은 꼴이 아니라 매핑이다**")

print("[나 -- 비교기 오프셋(미스매치 몬테카를로)]")
o = afespice.오프셋(씨수=12)
ok(o["판정"] == serdes.PASS, f"tt_mm 몬테카를로가 돈다 ({o.get('왜', '')[:60]})")
if o["판정"] == serdes.PASS:
    ok(abs(o["대조_미스매치없음_mV"]) < 1e-6,
       f"대조: 미스매치 없는 tt 코너에서 오프셋이 정확히 0 이다 "
       f"({o['대조_미스매치없음_mV']:.2e} mV) -- 검사가 살아 있다")
    ok(0.3 < o["시그마mV"] < 6.0,
       f"sigma {o['시그마mV']:.2f} mV (면적 {o['면적um2']:.0f} um2, {o['회수']}회)")
    # **ADC LSB 와 같은 자리인가** -- 이것이 §17.2 의 바닥과 이어지는 고리다
    b = afe.바닥원인(ADC비트=7, 풀스케일시그마=2.5, AFE입력rmsV=0.067)
    비 = o["시그마mV"] * 1000.0 / b["ADC_LSB_uV"]
    ok(0.1 < 비 < 3.0,
       f"오프셋 sigma 가 ADC LSB 의 {비:.2f}배 -- **바닥의 기여자가 둘이고 크기가 비슷하다** "
       f"(재생 감도 {b['비교기감도uV']:.0f} uV 는 그 둘보다 훨씬 작다)")

print("[다 -- Pelgrom 면적 법칙]")
p = afespice.면적별오프셋(짝들=((20.0, 0.5, 4), (80.0, 0.5, 4)), 씨수=12)
ok(p["판정"] == serdes.PASS, f"면적 쓸기가 돈다 ({p.get('왜', '')[:60]})")
if p["판정"] == serdes.PASS:
    작, 큰 = p["줄"][0], p["줄"][1]
    ok(큰["시그마mV"] < 작["시그마mV"],
       f"면적 {작['면적um2']:.0f} -> {큰['면적um2']:.0f} um2 에서 "
       f"sigma {작['시그마mV']:.2f} -> {큰['시그마mV']:.2f} mV 로 준다")
    비 = 큰["시그마mV"] / max(큰["예측시그마mV"], 1e-9)
    ok(0.6 < 비 < 1.7,
       f"1/sqrt(면적) 예측 {큰['예측시그마mV']:.2f} mV 대비 {비:.2f}배 -- "
       f"면적 법칙이 선다")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for m in FAIL_목록:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
