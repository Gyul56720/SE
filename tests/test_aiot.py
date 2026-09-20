"""**앰비언트 IoT R2D 링크의 자가 살아 있나.**

    (가) 제곱법 검출의 **제곱 법칙** -- 약신호에서 출력SNR 기울기가 정확히 2
    (나) 시늉이 **닫힌 꼴**(비중심 카이제곱)을 맞추나
    (다) 최적 문턱이 **가운데가 아니다** -- '0' 의 지수 꼬리
    (라) 규격 상수를 안 지어냈나 (SFO 는 10^5 ppm 이지 105 ppm 이 아니다)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import aiot

FAIL = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL.append(말)


print("[가~마 -- 모듈 자체 검증]")
난것 = aiot.검증(씨=0)
for t in 난것["통과"]:
    ok(True, t)
for t in 난것["실패"]:
    ok(False, t)

print("[바 -- 규격 상수를 지어내지 않았나]")
ok(aiot.규격["SFO_ppm최대"] == 1e5,
   "SFO 최대가 **10^5 ppm(=10%)** 이다 -- 발췌에서 지수가 날아간 '105 ppm' 이 아니다")
ok(aiot.규격["증폭"] is False,
   "device 1 은 R2D·D2R 어느 쪽도 **증폭하지 않는다**")
ok(aiot.규격["첨두전력W"] == 1e-6,
   "첨두 전력 ~1 uW")

print("[사 -- 제곱 법칙이 dB 로도 맞나]")
sigma = 1.0
d = []
for SNRdB in (-10.0, -5.0, 0.0):
    A = math.sqrt(10 ** (SNRdB / 10.0)) * sigma
    d.append(10 * math.log10(aiot.출력SNR(A, sigma, N=1)))
차 = [d[i + 1] - d[i] for i in range(len(d) - 1)]
ok(all(abs(c - 10.0) < 1e-9 for c in 차),
   f"입력이 5 dB 오르면 출력은 **10 dB** 오른다 (잰 것 {차[0]:.6f} dB) "
   f"-- 거꾸로 말하면 입력 1 dB 손실이 출력 2 dB 손실이다")

print("[아 -- SFO 가 실제로 표본을 민다]")
z = np.arange(1000.0)
민것 = aiot.SFO주기(z, 1e5)          # 10%
ok(len(민것) < len(z) and abs(민것[-1] - z[len(민것) - 1]) > 1.0,
   f"10^5 ppm 이면 1000 표본이 {len(민것)} 로 줄고 끝에서 "
   f"{abs(민것[-1]-z[len(민것)-1]):.1f} 표본만큼 어긋난다")

print()
if FAIL:
    print(f"{len(FAIL)}개 실패")
    sys.exit(1)
print("전부 통과")
