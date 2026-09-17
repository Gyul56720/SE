"""**신경망 팔이 PAM4 에서 제대로 도나, 그리고 NRZ 를 안 건드렸나.**

    (가) `레벨` 을 안 줘도 줘도 NRZ 는 같다 (기본값이 옛 동작이다)
    (나) PAM4 가 SNR 따라 단조로 내려가고 **높은 SNR 에서 바닥이 없다**
         -- E[b^2] 로 안 나누면 여기가 눌러앉는다
    (다) 망도 NRZ 대비 ~9.5 dB 더 든다 (PAM4 의 값은 변조가 정하지 등화기가 정하지 않는다)
    (라) `comply` 가 안 받는 인자를 **말없이 떨구지 않고 터뜨린다**
    (마) `comply` 로 망 팔을 실제로 굴릴 수 있다
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import comply
import nneq
import pam
import serdes

FAIL = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL.append(말)


공 = dict(비트수=30000, 손실dB=20.0, 앞뒤=5, 은닉수=8, 에폭=6)

print("[가 -- NRZ 를 안 건드렸다]")
a = nneq.링크(SNRdB=22.0, 씨=3, **공)
b = nneq.링크(SNRdB=22.0, 씨=3, 레벨=2, **공)
ok(a["판정"] == serdes.PASS and a["오류수"] == b["오류수"] and a["잰비트"] == b["잰비트"],
   f"`레벨` 을 안 줘도 줘도 같다 ({a['오류수']} 오류 / {a['잰비트']:,} 비트)")
# E[b^2] 정규화가 NRZ 에서 **항등**이라는 것이 회귀가 도는 까닭이다
L2 = pam.레벨들(2)
ok(abs(float(np.mean(L2 ** 2)) - 1.0) < 1e-12,
   "NRZ 는 E[b^2]=1 이라 새로 넣은 나눗셈이 항등이다 -- 그래서 값이 안 바뀐다")
L4 = pam.레벨들(4)
ok(abs(float(np.mean(L4 ** 2)) - 5.0 / 9.0) < 1e-12,
   f"PAM4 는 E[b^2]={np.mean(L4**2):.4f} = 5/9 -- **안 나누면 이득이 9/5배 어긋난다**")

print("[나 -- PAM4 가 내려가고 바닥이 없다]")
BER = []
for snr in (30.0, 34.0, 38.0):
    r = nneq.링크(SNRdB=snr, 씨=1, 레벨=4, 심볼수=100000,
                **{k: v for k, v in 공.items() if k != "비트수"})
    BER.append((snr, r["BER"], r["판정"]))
ok(all(x[2] == serdes.PASS for x in BER), "세 점 다 학습이 수렴했다")
ok(BER[0][1] > BER[1][1] > BER[2][1],
   "30->38 dB 에서 BER 이 " + " > ".join(f"{x[1]:.2e}" for x in BER))
높 = nneq.링크(SNRdB=48.0, 씨=1, 레벨=4, 심볼수=100000,
            **{k: v for k, v in 공.items() if k != "비트수"})
ok(높["오류수"] == 0,
   f"SNR 48 dB 에서 오류 0 -- 눈금이 안 어긋난다 (E[b^2] 로 안 나누면 여기가 "
   f"1e-2 대에서 안 내려간다)")

print("[다 -- 망도 PAM4 페널티를 그대로 문다]")
def 필요(레벨, 목표=1e-3):
    낮, 높 = 12.0, 50.0
    for _ in range(11):
        가 = 0.5 * (낮 + 높)
        r = nneq.링크(SNRdB=가, 씨=2, 레벨=레벨, 심볼수=100000,
                    **{k: v for k, v in 공.items() if k != "비트수"})
        p = r["BER"] if r["오류수"] > 0 else 3.0 / max(r["잰비트"], 1)
        낮, 높 = (가, 높) if p > 목표 else (낮, 가)
    return 0.5 * (낮 + 높)
n2, n4 = 필요(2), 필요(4)
ok(6.0 < (n4 - n2) < 13.0,
   f"BER 1e-3 에 NRZ {n2:.2f} dB · PAM4 {n4:.2f} dB -- 차 {n4-n2:.2f} dB "
   f"(이론 9.54 dB). **등화기를 바꿔도 이 값은 안 변한다** -- 변조가 정하는 값이다")

print("[라 -- 안 받는 인자를 말없이 떨구지 않는다]")
터졌나 = False
try:
    comply.필요SNR(dict(심볼수=1000, 손실dB=20.0, FFE탭=11, 레벨=4), 돌리기=nneq.링크)
except TypeError as e:
    터졌나 = "FFE탭" in str(e)
ok(터졌나,
   "`nneq.링크` 가 안 받는 `FFE탭` 을 주면 TypeError 를 낸다 -- "
   "말없이 떨구면 **내가 의도한 것과 다른 구성을 견주게 된다**")
안터짐 = comply._인자맞추기(nneq.링크, dict(FFE탭=11, 앞뒤=5, SNRdB=9, 씨=1), 뺄것=("FFE탭",))
ok(안터짐 == {"앞뒤": 5},
   f"`_뺄것` 에 적으면 통과하고 그것만 빠진다 ({안터짐}) -- 검사가 한쪽으로 고정돼 있지 않다")

print("[마 -- comply 로 망 팔을 굴린다]")
r = comply.필요SNR(dict(심볼수=60000, 손실dB=20.0, DFE탭=8, ADC비트=7, 레벨=4,
                     앞뒤=5, 은닉수=8, 에폭=6),
                돌리기=nneq.링크, 되풀이=8)
ok(r.get("판정") == serdes.PASS and r.get("결과") in ("닿는다", "바닥"),
   f"망 팔이 규격 판정을 낸다 -- 결과 `{r.get('결과')}`: {str(r.get('왜',''))[:90]}")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for m in FAIL:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
