"""**압축에 맞춘 ADC 사다리 -- 이득은 진짜인데 칼날이라 못 쓴다.**

이 검사가 붙드는 것은 "된다" 가 아니라 **"왜 못 쓰는가"** 다. 신탁 조건(압축 세기를
정확히 앎)에서는 ADC 두 비트어치를 벌지만, 그 이득은 사다리 파라미터의 +-5% 창에만
있고 밖에서는 균일 ADC 보다 나쁘다. **이득과 취약성이 같은 현상**이라(포화 근처에서
역함수가 악조건이다) 정칙화로 떼어낼 수도 없다.

누가 이 코드를 보고 "좋아 보이는데 켜자" 하지 않도록, 칼날 자체를 검사로 박아 둔다.

    (가) 대조: 압축이 없으면 **정확히 아무 일도 안 한다**
    (나) 신탁 조건에서는 정말 이긴다 (이득이 헛것이 아니다)
    (다) **+-10% 어긋나면 균일 기준선보다 나쁘다** -- 이것이 못 쓰는 까닭이다
    (라) AFE 선형성과 ADC 비트의 교환비: κ 가 오르면 필요한 비트가 는다
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import serdes

FAIL = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL.append(말)


공 = dict(심볼수=60000, 손실dB=20.0, FFE탭=11, DFE탭=8, ADC비트=7, 레벨=4, 씨=1)
p = lambda r: r["BER"] if r["오류수"] > 0 else 3.0 / max(r["잰비트"], 1)

print("[가 -- 압축이 없으면 아무 일도 안 한다]")
같 = True
for snr in (34.0, 38.0):
    a = serdes.링크(**공, SNRdB=snr, 압축=0.0)
    b = serdes.링크(**공, SNRdB=snr, 압축=0.0, ADC맞춤=True)
    같 &= a["오류수"] == b["오류수"]
ok(같, "κ=0 이면 압축맞춤 ADC 가 균일 ADC 와 **오류 수까지 같다**")

print("[나 -- 신탁 조건에서는 이득이 진짜다]")
기준 = p(serdes.링크(**공, SNRdB=42.0, 압축=1.0, 역압축=True))
신탁 = p(serdes.링크(**공, SNRdB=42.0, 압축=1.0, ADC맞춤=True))
ok(신탁 < 기준 / 5.0,
   f"κ=1.0 에서 압축맞춤 {신탁:.2e} 가 균일+역압축표 {기준:.2e} 보다 "
   f"{기준/신탁:.0f}배 낫다 -- **이득은 헛것이 아니다**")

print("[다 -- 그런데 +-10% 어긋나면 기준선보다 나쁘다]")
원래 = serdes.ADC압축맞춤
본 = {}


def 엿(x, b, fs, se, a, h, 람다=1.0):
    본["a"] = a
    return 원래(x, b, fs, se, a, h, 람다)


serdes.ADC압축맞춤 = 엿
try:
    serdes.링크(**공, SNRdB=42.0, 압축=1.0, ADC맞춤=True)
finally:
    serdes.ADC압축맞춤 = 원래
A = 본["a"]


def 고정(v):
    def g(x, b, fs, se, a, h, 람다=1.0):
        return 원래(x, b, fs, 1.0, v, h, 람다)
    return g


나쁨 = {}
for q in (0.9, 1.1):
    serdes.ADC압축맞춤 = 고정(A * q)
    try:
        나쁨[q] = p(serdes.링크(**공, SNRdB=42.0, 압축=1.0, ADC맞춤=True))
    finally:
        serdes.ADC압축맞춤 = 원래
ok(all(v > 기준 for v in 나쁨.values()),
   f"사다리가 10% 어긋나면 0.9배 {나쁨[0.9]:.2e} · 1.1배 {나쁨[1.1]:.2e} 로 "
   f"**둘 다 균일 기준선 {기준:.2e} 보다 나쁘다** -- 그래서 기본값이 꺼져 있다")
ok(나쁨[1.1] > 나쁨[0.9],
   f"과대추정이 과소추정보다 더 나쁘다 ({나쁨[1.1]/나쁨[0.9]:.1f}배) -- "
   f"`atanh` 가 포화 근처에서 발산하기 때문이다(물리이지 우연이 아니다)")

print("[라 -- AFE 선형성과 ADC 비트의 교환비]")
def 필요비트(k, 목표=2.262e-4):
    for b in range(5, 13):
        r = serdes.링크(**{**공, "ADC비트": b}, SNRdB=55.0, 압축=k, 역압축=True)
        if p(r) < 목표:
            return b
    return 99
b0, b1 = 필요비트(0.0), 필요비트(1.0)
ok(b1 > b0,
   f"KP4 문턱을 넘는 데 κ=0 이면 {b0}비트, κ=1.0 이면 {b1}비트 -- "
   f"**압축을 허용한 대가가 ADC {b1-b0}비트**다 (고속 ADC 전력은 대략 비트당 2배)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for m in FAIL:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
