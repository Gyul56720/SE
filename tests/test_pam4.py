"""**PAM4 원단이 교과서와 맞나, 그리고 NRZ 를 안 건드렸나.**

이 검사가 붙드는 것 넷:

    (가) 페널티 9.54 dB · 그레이 이웃 한 비트 · 잡음만일 때 SER 닫힌 꼴
    (나) **NRZ 가 비트 하나 안 바뀐다** -- 같은 씨앗에서 난수 소비까지 같다
    (다) PAM4 BER 이 SNR 에 따라 **단조로 내려간다** (안 내려가면 등화기가 깨진 것)
    (라) 같은 링크에서 PAM4 가 NRZ 보다 **대략 9.5 dB 더 든다**
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import pam
import serdes

FAIL = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL.append(말)


print("[가 -- 교과서 값 셋]")
v = pam.검증()
ok(abs(v["페널티dB"] - 9.542425) < 1e-4,
   f"PAM4 페널티 {v['페널티dB']:.4f} dB = 20log10(3)")
ok(v["그레이_이웃한비트"], "그레이: 이웃 레벨은 한 비트만 다르다")
ok(0.9 < v["SER비"] < 1.1,
   f"잡음만일 때 SER 실측 {v['SER실측']:.3e} / 닫힌 꼴 {v['SER예측']:.3e} = "
   f"{v['SER비']:.3f} ({v['오류수']}개 오류 -- 상대오차 "
   f"{1/np.sqrt(max(v['오류수'],1)):.3f} 안)")
ok(abs(v["BER_over_SER"] - 0.5) < 1e-9,
   f"그레이라서 BER = SER/2 (심볼당 2비트, 오류는 전부 이웃: "
   f"이웃비율 {v['이웃비율']:.3f})")

print("[나 -- NRZ 를 안 건드렸다]")
같음, 난수같음 = True, True
for 씨 in (0, 1, 7, 99):
    r1 = np.random.default_rng(씨)
    옛 = r1.integers(0, 2, 5000) * 2 - 1
    옛뒤 = r1.normal(0, 1, 8)
    r2 = np.random.default_rng(씨)
    새, _, _ = pam.심볼만들기(r2, 5000, 2)
    새뒤 = r2.normal(0, 1, 8)
    같음 &= bool(np.array_equal(옛, 새))
    난수같음 &= bool(np.allclose(옛뒤, 새뒤))
ok(같음 and 난수같음,
   "M=2 심볼 만들기가 `rng.integers(0,2,N)*2-1` 과 **값도 난수 소비도 같다** -- "
   "그래서 예전 결과가 한 비트도 안 바뀐다")
# 레벨을 안 주면 NRZ 이고, 명시해도 같아야 한다
a = serdes.링크(비트수=20000, 손실dB=20, SNRdB=18, FFE탭=11, DFE탭=4, 압축=1.5,
             ADC비트=7, 씨=3)
b = serdes.링크(비트수=20000, 손실dB=20, SNRdB=18, FFE탭=11, DFE탭=4, 압축=1.5,
             ADC비트=7, 씨=3, 레벨=2)
ok(a["오류수"] == b["오류수"] and a["잰비트"] == b["잰비트"],
   f"`레벨` 을 안 줘도 줘도 NRZ 는 같다 ({a['오류수']} 오류)")

print("[다 -- PAM4 가 SNR 에 따라 단조로 내려간다]")
BER = []
for snr in (28, 31, 34, 37):
    r = serdes.링크(심볼수=120000, 손실dB=20, SNRdB=snr, FFE탭=11, DFE탭=8,
                 레벨=4, 씨=1)
    BER.append(r["BER"])
ok(all(BER[i] > BER[i + 1] for i in range(len(BER) - 1)),
   "28->37 dB 에서 BER 이 " + " > ".join(f"{x:.2e}" for x in BER))
# **이것이 없으면 AGC 버그를 못 잡는다**: E[b^2] 로 안 나누면 55 dB 에서도 5e-2 에
# 눌러앉는다(실측). 아주 높은 SNR 에서 바닥이 없어야 한다.
높 = serdes.링크(심볼수=120000, 손실dB=20, SNRdB=50, FFE탭=11, DFE탭=8, 레벨=4, 씨=1)
ok(높["오류수"] == 0,
   f"SNR 50 dB 에서 오류 0 -- 눈금이 안 어긋난다 (AGC 를 E[b^2] 로 안 나누면 "
   f"여기가 5e-2 에서 안 내려간다)")

print("[라 -- PAM4 가 NRZ 보다 ~9.5 dB 더 든다]")
def 필요(레벨, 목표=1e-3):
    낮, 높 = 10.0, 50.0
    for _ in range(13):
        가 = 0.5 * (낮 + 높)
        r = serdes.링크(심볼수=120000, 손실dB=20, SNRdB=가, FFE탭=11, DFE탭=8,
                     레벨=레벨, 씨=2)
        p = r["BER"] if r["오류수"] > 0 else 3.0 / max(r["잰비트"], 1)
        낮, 높 = (가, 높) if p > 목표 else (낮, 가)
    return 0.5 * (낮 + 높)
n2, n4 = 필요(2), 필요(4)
ok(6.0 < (n4 - n2) < 13.0,
   f"BER 1e-3 에 NRZ {n2:.2f} dB · PAM4 {n4:.2f} dB -- 차 {n4-n2:.2f} dB "
   f"(이론 9.54 dB. ISI·등화가 있어 정확히 같지는 않다)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for m in FAIL:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
