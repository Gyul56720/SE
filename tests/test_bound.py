"""**이론 한계** -- 구조들을 서로가 아니라 최적에 견준다.

이 저장소는 내내 "선형 대비 7.98배" 처럼 **서로** 견주어 왔다. 그런 숫자에는 바닥이
없다. 7.98배가 최적의 코앞인지 아직 천 배가 남았는지 알 수 없고, 그러면 "신경망이
필요한가" 도 끝내 못 닫는다 -- **비교 대상이 서로뿐이면 둘 다 나쁠 수 있다.**

여기서 붙드는 것은 넷이다.

    (가) 정합필터 한계가 **교정되어 있다**(고립 펄스를 실제로 쏘아 닫힌 꼴과 맞춘다)
    (나) 명제 4 의 **등호**: 잡음 뒤의 가역 메모리없는 비선형은 최적 수신기에 공짜다
    (다) 선형 채널에서 **DDFSE 가 모든 구조보다 훨씬 낫다** -- 남은 간격이 크다
    (라) beta=0.35 에서는 **DDFSE 가 표보다 나쁘다** -- 선형 모형으로 못 잡는 자리다

(라)가 이 논문의 존재 이유다. 거기서만 선형 수열 검출기가 무너지고 256칸 표가 이긴다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import bound
import nneq
import serdes

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


print("[가 -- 정합필터 한계를 교정한다]")
for snr in (8.0, 10.0):
    r = bound.교정(SNRdB=snr, 개수=60000)
    ok(r["판정"] == serdes.PASS,
       f"SNR {snr:.0f}dB: 잰 {r['잰BER']:.3e} vs 닫힌 꼴 {r['이론']:.3e} "
       f"(오류 {r['오류수']}개, 어긋남 {100 * r['어긋남']:.1f}%)")

밑 = dict(손실dB=25.0, SNRdB=30.0, sps=8)
N, 씨수 = 200000, 2


def 합(rs):
    return sum(r["오류수"] for r in rs) / sum(r["잰비트"] for r in rs)


def 구조(더, adc=False):
    a = dict(ADC비트=7) if adc else {}
    선 = [serdes.링크(비트수=N, FFE탭=11, DFE탭=8, 씨=s, **밑, **더, **a) for s in range(씨수)]
    표 = [serdes.링크(비트수=N, FFE탭=11, 표본표창=2, 표본표비트=4, 씨=s, **밑, **더, **a)
         for s in range(씨수)]
    망 = [nneq.링크(비트수=N, 앞뒤=2, 은닉수=2, 에폭=12, 가중치비트=7, 씨=s, **밑, **더, **a)
         for s in range(씨수)]
    return 합(선), 합(표), 합(망)


print("[나 -- 명제 4 의 등호: 가역 압축은 최적 수신기에 공짜다]")
선형 = 구조({})
압축 = 구조(dict(압축=1.0, 역압축=True))
ok(all(abs(a - b) / max(a, 1e-12) < 0.02 for a, b in zip(선형, 압축)),
   f"압축 1.0 + 정확한 역 = 선형 채널과 같은 BER: "
   f"{['%.3e' % x for x in 선형]} vs {['%.3e' % x for x in 압축]}")

print("[다 -- 선형 채널에서 최적은 구조들보다 훨씬 낫다]")
b1 = bound.한계재기(밑, 메모리=8, 비트수=200000, 잴것=120000, 씨=0)
최선구조 = min(선형)
ok(b1["DDFSE이상"]["BER"] < 최선구조 / 5.0,
   f"DDFSE {b1['DDFSE이상']['BER']:.2e}(오류 {b1['DDFSE이상']['오류']}) 가 "
   f"제일 나은 구조 {최선구조:.2e} 보다 5배 넘게 낫다 -- "
   f"구조들이 남겨 둔 몫이 크다")
ok(b1["심볼률정합한계"] < b1["DDFSE이상"]["BER"] or b1["DDFSE이상"]["오류"] == 0,
   f"하한 {b1['심볼률정합한계']:.2e} <= 달성값 {b1['DDFSE이상']['BER']:.2e} -- 차례가 맞다")
ok(b1["MFB"] < b1["심볼률정합한계"],
   f"파형 하한 {b1['MFB']:.2e} < 심볼률 하한 {b1['심볼률정합한계']:.2e} -- "
   f"표본을 하나만 쓰면 잃는 것이 있다")

print("[라 -- beta=0.35 에서는 선형 수열 검출기가 표보다 못하다]")
b2 = bound.한계재기(dict(밑, 압축=1.0, 압축뒤대역=0.35), 메모리=8,
                비트수=200000, 잴것=120000, 씨=0)
베 = 구조(dict(압축=1.0, 압축뒤대역=0.35, 역압축=True))
ok(b2["DDFSE손상"]["BER"] > 베[1] * 2.0,
   f"DDFSE {b2['DDFSE손상']['BER']:.2e} 가 표 {베[1]:.2e} 보다 나쁘다 -- "
   f"이 손상은 **어떤 선형 응답으로도 안 잡힌다**. 논문이 노린 자리가 여기다")
ok(b1["DDFSE손상"]["BER"] <= 선형[1],
   f"대조: 선형 채널에서는 DDFSE({b1['DDFSE손상']['BER']:.2e})가 "
   f"표({선형[1]:.2e})보다 낫다 -- (라)가 손상 탓이지 검출기 탓이 아니다")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for m in FAIL_목록:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
