"""**래치 통째의 오프셋이 바닥의 가장 큰 몫이다** -- sky130 tt_mm 몬테카를로.

`tests/test_afespice.py` 와 따로 두는 까닭은 **시간**이다. 이분법 한 씨앗이 열 번
넘게 과도해석을 돌리므로 다른 검사와 한 파일에 두면 300초 문턱을 넘는다.

이 검사가 붙드는 것:

    (가) 대조 -- 미스매치가 **없는** `tt` 코너에서는 오프셋이 거의 0 이다.
         (측정 장치가 살아 있나. 이것이 안 서면 아래 숫자는 아무 뜻이 없다)
    (나) `tt_mm` 에서는 mV 급으로 흩어지고, 그 크기가 **ADC LSB 와 같은 자리** 다.

전체 20씨 실측은 `afespice.래치오프셋` 의 머리말에 적혀 있다(sigma 4.06 mV).
여기서는 씨앗을 줄여 **장치가 사는지**만 본다 -- 적은 씨앗의 sigma 를 그대로
인용하면 안 된다.
"""
from __future__ import annotations

import sys
from pathlib import Path

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

print("[가 -- 대조: 미스매치 없는 tt 코너]")
대 = afespice.래치오프셋(씨수=1, 걸음=8, 코너="tt")
ok(대["판정"] == serdes.PASS, f"이분법이 돈다 ({대.get('왜', '')[:60]})")
if 대["판정"] == serdes.PASS:
    ok(abs(대["평균mV"]) * 1000.0 < 3 * 대["해상도uV"],
       f"미스매치가 없으면 오프셋이 {대['평균mV'] * 1e3:.0f} uV 로 "
       f"이분법 해상도({대['해상도uV']:.0f} uV)의 세 배 안이다 -- **장치가 살아 있다**")

print("[나 -- tt_mm 에서는 mV 급으로 흩어진다]")
m = afespice.래치오프셋(씨수=3, 걸음=8)
ok(m["판정"] == serdes.PASS, f"몬테카를로가 돈다 ({m.get('왜', '')[:60]})")
if m["판정"] == serdes.PASS and 대["판정"] == serdes.PASS:
    # 대조의 **값**과 견주면 안 된다 -- 그것은 이분법 해상도의 반쯤이라 잡음이다.
    # 견줄 자리는 **해상도**다(실측: 대조 195 uV = 해상도 391 uV 의 절반).
    ok(m["최대절대mV"] * 1000.0 > 3 * m["해상도uV"],
       f"tt_mm 최대 절대 {m['최대절대mV']:.2f} mV 가 이분법 해상도"
       f"({m['해상도uV']:.0f} uV)의 {m['최대절대mV'] * 1000.0 / m['해상도uV']:.1f}배 -- "
       f"미스매치가 실제로 보인다 ({m['회수']}씨 -- **sigma 를 인용하기엔 적다**. "
       f"20씨 실측은 4.06 mV)")
    b = afe.바닥원인(ADC비트=7, 풀스케일시그마=2.5, AFE입력rmsV=0.067)
    ok(m["최대절대mV"] * 1000.0 > 0.3 * b["ADC_LSB_uV"],
       f"그 크기가 ADC LSB({b['ADC_LSB_uV']:.0f} uV)와 **같은 자리**다 -- "
       f"바닥의 기여자 셋 중 20씨 sigma 4,059 uV 로 **이것이 가장 크다**")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for x in FAIL_목록:
        print("  - " + x)
    sys.exit(1)
print("전부 통과")
