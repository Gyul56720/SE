"""**규격 문턱으로 판정하는 장치가 살아 있나.**

    (가) 부호 파라미터에서 문턱이 **계산돼 나오나** (상수를 박은 것이 아니다)
    (나) 접은 항등식이 **무식하게 더한 것과 같나**
    (다) 같은 비트오류 수라도 **뭉치면** 코드워드 심볼오류가 준다 (FEC 의 요점)
    (라) 바닥에 걸린 구조를 `comply` 가 **바닥이라고 말하나** (필요 SNR 을 안 낸다)
    (마) 대조: 선형 채널에서 표는 **져야** 한다
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import comply
import fec
import serdes

FAIL = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL.append(말)


print("[가 -- 문턱은 계산해서 나온다]")
ok(fec.고치는수("KP4") == 15 and fec.고치는수("KR4") == 7,
   "KP4 t=15 · KR4 t=7 ((n-k)/2)")
th = fec.문턱(1e-15, "KP4")
ok(1.5e-4 < th < 3.5e-4,
   f"KP4 pre-FEC 문턱 {th:.3e} -- 업계가 인용하는 ~2.4e-4 와 같은 자리")
thk = fec.문턱(1e-15, "KR4")
ok(thk < th,
   f"KR4 는 t 가 작아 문턱이 더 빡빡하다 ({thk:.3e} < {th:.3e}) -- "
   f"**문턱이 부호에 따라 움직인다. 상수를 박은 것이 아니다**")
느 = fec.문턱(1e-9, "KP4")
ok(느 > th, f"목표를 1e-9 로 늦추면 문턱이 {느:.3e} 로 는다")

print("[나 -- 접은 항등식이 무식한 합과 같다]")
# sum_{j>t} (j/n) C(n,j) p^j q^(n-j)  ==  p · P(Bin(n-1,p) >= t)
n, t, p = 20, 3, 0.05
무식 = sum((j / n) * math.comb(n, j) * p ** j * (1 - p) ** (n - j)
         for j in range(t + 1, n + 1))
fec.부호들["_시험"] = {"n": n, "k": n - 2 * t, "심볼비트": 10, "왜": "검사용"}
접은 = fec.남는심볼오류율(p, "_시험")
ok(abs(접은 - 무식) < 1e-12 * max(무식, 1e-300),
   f"접은 꼴 {접은:.6e} == 무식하게 더한 것 {무식:.6e} (n={n}, t={t}, p={p})")

print("[다 -- 뭉치면 심볼오류가 준다]")
총비트 = 544 * 10 * 40                        # 코드워드 40개
rng = np.random.default_rng(0)
흩 = np.sort(rng.choice(총비트, 4000, replace=False))       # 흩어진 4,000 비트오류
뭉 = np.concatenate([np.arange(s, s + 10) for s in
                    np.sort(rng.choice(총비트 // 10, 400, replace=False)) * 10])
a = fec.코드워드분포(흩, 총비트)
b = fec.코드워드분포(뭉, 총비트)
ok(a["나쁜비트수"] == b["나쁜비트수"] == 4000,
   f"두 경우 **비트오류 수가 같다** ({a['나쁜비트수']:,})")
ok(b["나쁜심볼수"] < a["나쁜심볼수"] / 5,
   f"그런데 나쁜 RS 심볼은 흩어지면 {a['나쁜심볼수']:,} · 뭉치면 {b['나쁜심볼수']:,} -- "
   f"**뭉치면 FEC 에 유리하다**. 비트만 세면 이것을 못 본다")
판 = fec.판정(흩, 총비트)
ok(판["판정"] == "PASS" and not 판["통과"],
   f"흩어진 BER {판['pre_FEC_BER']:.3e} 는 문턱을 넘는다 -- {fec.말로(판)[:60]}")

print("[라 -- 바닥을 바닥이라고 말한다]")
# 압축 κ=2 · 7비트 ADC 면 SNR 을 55 dB 로 올려도 안 내려간다
바 = comply.필요SNR(dict(심볼수=60000, 손실dB=20.0, FFE탭=11, DFE탭=8,
                     ADC비트=7, 레벨=4, 압축=2.0))
ok(바.get("결과") == "바닥" and not 바.get("닿나"),
   f"κ=2.0: {바.get('왜','')[:110]}")
ok("SNRdB" not in 바 or not np.isfinite(바.get("SNRdB", float("nan"))),
   "**바닥이면 필요 SNR 숫자를 안 낸다** -- 냈으면 닿은 줄 알았을 것이다")
깨 = comply.필요SNR(dict(심볼수=60000, 손실dB=20.0, FFE탭=11, DFE탭=8, 레벨=4))
ok(깨.get("결과") == "닿는다" and np.isfinite(깨.get("SNRdB", float("nan"))),
   f"손상이 없으면 닿는다 -- {깨.get('SNRdB', float('nan')):.2f} dB")

print("[마 -- 대조: 선형 채널에서 표는 져야 한다]")
바탕 = dict(심볼수=80000, 손실dB=20.0, FFE탭=11, DFE탭=8, ADC비트=7, 레벨=4, 압축=0.0)
r = comply.팔들(바탕, {"선형": {}, "표": dict(표본표창=2, 표본표비트=4)}, 씨들=(0,))
선, 표 = r["팔"]["선형"], r["팔"]["표"]
# 지는 데는 두 가지가 있다: (1) dB 가 더 들거나 (2) 아예 바닥에 걸리거나.
# **둘 다 "졌다" 이므로 둘 다 받는다** -- 하나만 받으면 검사가 씨앗·심볼수에 따라
# 흔들린다(실측: 심볼 8만에서는 표가 바닥에 걸려 dB 가 nan 이었다).
진다 = (표["닿은씨"] == 0) or (표["SNRdB평균"] > 선["SNRdB평균"] + 1.0)
꼴 = ("바닥에 걸렸다" if 표["닿은씨"] == 0
     else f"{표['SNRdB평균']-선['SNRdB평균']:+.2f} dB 더 든다")
ok(선["닿은씨"] > 0 and 진다,
   f"압축 없는 채널: 선형 {선['SNRdB평균']:.2f} dB, 표는 {꼴} -- "
   f"표본 두 개로는 FFE11+DFE8 의 스팬을 못 당한다. 여기서 이기면 새는 것이다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for m in FAIL:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
