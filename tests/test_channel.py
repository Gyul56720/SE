"""**S-파라미터에서 온 채널** -- 기하·재료로 짓거나 측정본을 이어 붙인다.

`채널()` 과 `채널물리()` 는 **dB 숫자를 맞춘 것**이다. 크기 곡선을 내가 손으로
세웠으니, 그 곡선이 진짜 보드와 얼마나 닮았는지는 그 안에서 알 길이 없다. 이번에
둘을 더했다.

    채널선로   선폭·기판·유전율·손실각·거칠기를 주면 `scikit-rf` 가 S 를 낸다
               (Djordjevic-Svensson 인과 유전체 + Kirschning-Jansen 분산)
    채널측정   `skrf.data.ntwk1` -- **실제로 측정된 2포트**를 K 벌 직렬로 잇는다

## 여기서 붙드는 것

*하나 -- 왕복.* `채널S21` 이 입구다. 해석적 H 를 넣으면 그 H 가 그대로 나와야 한다.
안 나오면 그 뒤의 모든 채널이 틀린다.

*둘 -- 물리가 맞는가.* 선로는 길이에 비례해 dB 가 늘어야 하고(로그 눈금에서 직선),
측정본은 K 에 비례해 늘어야 한다. 비례가 안 맞으면 캐스케이딩이나 격자가 틀린 것이다.

*셋 -- 대역 밖으로 안 늘린다.* 측정은 1~10 GHz 다. `채널측정` 이 고르는 보드율이
그 대역 안에 Nyquist 를 두는지 본다. 밖으로 외삽하면 그 숫자는 측정이 아니라 내 외삽이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import serdes

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


try:
    import skrf                                  # noqa: F401
except Exception as e:                           # pragma: no cover
    print(f"scikit-rf 가 없다 -- 건너뛴다 ({e})")
    raise SystemExit(0)

print("[왕복 -- 해석적 H 를 넣으면 그대로 나온다]")
sps, 길이심볼, FFT = 8, 64, 4096
h0 = serdes.채널(20.0, sps, 길이심볼)
H = np.fft.rfft(h0, FFT)
f = np.fft.rfftfreq(FFT, 1.0)
되돌린 = serdes.채널S21(f, H, sps, 길이심볼, 20e9, 앞심볼=0)
k = int(np.argmax(np.abs(h0)))
차 = float(np.max(np.abs(되돌린[:len(h0) - k] - h0[k:])))
ok(차 < 1e-9, f"H -> 임펄스 -> 같은 임펄스: 최대 차 {차:.2e}")

print("[선로 -- 길이에 비례해 dB 가 는다]")
잰것 = {}
for 인치 in (10.0, 20.0, 40.0):
    h = serdes.채널선로(sps=sps, 길이심볼=길이심볼, 보드율=20e9, 인치=인치, FFT=8192)
    c = serdes.커서들(h, sps)
    잰것[인치] = c
    print(f"    {인치:5.0f}인치: 메인 {c['메인']:.4f}  ISI {c['ISI']:.4f}  "
          f"아이 {c['아이높이_ISI']:+.3f}")
ok(잰것[10.0]["메인"] > 잰것[20.0]["메인"] > 잰것[40.0]["메인"],
   "길수록 메인 커서가 작아진다")
# dB 는 길이에 **비례**해야 한다 -- 비율이 맞는지 본다(감쇠 dB 가 선형).
dB = {L: -20 * np.log10(max(v["메인"], 1e-12)) for L, v in 잰것.items()}
비 = (dB[40.0] - dB[10.0]) / max(dB[20.0] - dB[10.0], 1e-9)
ok(2.3 < 비 < 4.0,
   f"dB 가 길이에 거의 비례한다: (40-10)/(20-10) = {비:.2f} (정확히 비례면 3.00)")

print("[선로 -- 불연속이 진짜 반사를 만든다]")
민 = serdes.채널선로(sps=sps, 길이심볼=길이심볼, 인치=30.0, FFT=8192)
울 = serdes.채널선로(sps=sps, 길이심볼=길이심볼, 인치=30.0, FFT=8192,
                 불연속=[(0.45, 1.2e-3, 500e-6), (0.8, 1.2e-3, 500e-6)])
ok(not np.allclose(민, 울) and serdes.커서들(울, sps)["ISI"] > serdes.커서들(민, sps)["ISI"],
   f"불연속을 넣으면 ISI 가 는다: {serdes.커서들(민, sps)['ISI']:.4f} -> "
   f"{serdes.커서들(울, sps)['ISI']:.4f}")

print("[측정 -- K 벌 이으면 손실이 K 배로 는다]")
잼 = {}
for K in (1, 8, 16):
    h, baud = serdes.채널측정(K=K, sps=4, 길이심볼=64, FFT=4096)
    잼[K] = (-20 * np.log10(max(serdes.커서들(h, 4)["메인"], 1e-12)), baud)
    print(f"    K={K:2d}: 메인 손실 {잼[K][0]:6.2f} dB  보드율 {baud / 1e9:.2f} GBd")
증가 = (잼[16][0] - 잼[1][0]) / max(잼[8][0] - 잼[1][0], 1e-9)
ok(1.6 < 증가 < 2.6,
   f"K 에 거의 비례한다: (16-1)/(8-1) = {증가:.2f} (정확히 비례면 2.14)")

print("[측정 -- 대역 밖으로 안 늘린다]")
_, baud = serdes.채널측정(K=1, sps=4)
fmax = float(skrf.data.ntwk1.f[-1])
ok(abs(baud * 4 / 2 - fmax) < 1e-3 * fmax,
   f"표본율의 절반({baud * 4 / 2e9:.2f} GHz)이 측정 상한({fmax / 1e9:.2f} GHz)과 같다 "
   f"-- FFT 격자가 측정 대역 안에만 있다")

print("[링크에 물렸는가]")
r1 = serdes.링크(비트수=40000, sps=8, SNRdB=22, FFE탭=11, ADC비트=7,
             채널지음=dict(꼴="선로", 인치=40.0, sps=8), 씨=0)
r2 = serdes.링크(비트수=40000, sps=4, SNRdB=22, FFE탭=11, ADC비트=7,
             채널지음=dict(꼴="측정", K=16, sps=4), 씨=0)
ok(np.isfinite(r1["BER"]) and np.isfinite(r2["BER"]),
   f"선로 채널 BER {r1['BER']:.2e} · 측정 채널 BER {r2['BER']:.2e}")
쉬운 = serdes.링크(비트수=40000, sps=4, SNRdB=22, FFE탭=11, ADC비트=7,
               채널지음=dict(꼴="측정", K=1, sps=4), 씨=0)
ok(쉬운["BER"] < r2["BER"],
   f"K=1({쉬운['BER']:.2e})이 K=16({r2['BER']:.2e})보다 쉽다")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for m in FAIL_목록:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
