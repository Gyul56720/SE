"""**ASIC 면적이 라이브러리에서 나오나, 그리고 빠지는 것이 없나.**

    (가) 셀 면적·소자수가 sky130 의 **LEF/SPICE 에서** 나온다 (내가 적은 상수가 아니다)
    (나) 짝 못 지은 게이트가 있으면 **면적을 안 낸다** (빼고 더하면 작게 나온다)
    (다) **항등표를 넣으면 거짓이 나온다** -- 합성기가 배선으로 지운다
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import asic
import eqrtl
import pdk
import serdes

FAIL = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL.append(말)


if not asic.shutil_which("yosys"):
    print("yosys 가 없다 -- 건너뛴다")
    raise SystemExit(0)
if not asic.있나():
    print("sky130 표준셀을 못 구했다 -- 건너뛴다")
    raise SystemExit(0)

print("[가 -- 면적은 라이브러리가 답한다]")
# 값을 여기 베껴 적는 것이 아니라, **LEF 가 말한 것과 서로 맞는지**를 본다.
inv, nand2, dff = asic.셀면적("inv_1"), asic.셀면적("nand2_1"), asic.셀면적("dfxtp_1")
ok(all(np.isfinite([inv, nand2, dff])) and inv > 0,
   f"LEF 에서 면적을 읽는다: inv_1 {inv:.3f} · nand2_1 {nand2:.3f} · "
   f"dfxtp_1 {dff:.3f} um2")
ok(abs(inv - nand2) < 1e-6 and dff > 4 * inv,
   f"sky130 hd 는 높이가 같고 폭만 다르다 -- inv_1 과 nand2_1 이 같은 폭(1그리드)이고 "
   f"플립플롭은 {dff/inv:.1f}배다")
t_inv, t_nand, t_dff = (asic.셀소자수("inv_1"), asic.셀소자수("nand2_1"),
                        asic.셀소자수("dfxtp_1"))
ok(t_inv == 2 and t_nand == 4 and t_dff > 20,
   f"SPICE 넷리스트에서 소자를 센다: inv 2 · nand2 4 · dfxtp {t_dff} "
   f"-- CMOS 가 맞다(인버터 2, 2입력 낸드 4)")

print("[나 -- 빠지는 게이트가 있으면 면적을 안 낸다]")
v, top = eqrtl.ffe_dfe(11, tuple(range(1, 9))), "ffe_dfe"
r = asic.잰것(v, top)
ok(r["판정"] == "PASS", f"선형 baseline 이 합성된다 ({r.get('왜','')[:80]})")
if r["판정"] == "PASS":
    ok(not r["못붙인게이트"],
       f"짝 못 지은 게이트가 0개 -- 면적 {r['셀면적um2']:.0f} um2 에 "
       f"빠진 것이 없다 (게이트 {r['게이트수']:,}, 소자 {r['소자수']:,})")
# 일부러 짝을 지워 **거절하는지** 본다 -- 검사가 한쪽으로 고정돼 있지 않은지
원래 = dict(asic.짝)
try:
    asic.짝.pop("$_DFF_PN0_", None)
    asic.짝.pop("$_DFFE_PN0P_", None)
    나쁨 = asic.잰것(v, top)
finally:
    asic.짝.clear()
    asic.짝.update(원래)
ok(나쁨.get("판정") == "못잼" and "셀면적um2" not in 나쁨,
   f"짝을 지우면 **면적을 안 내고 못잼을 낸다** -- {str(나쁨.get('왜',''))[:80]}")

print("[다 -- 항등표는 거짓 면적을 낸다]")
N, 비트 = 128, 7
코드 = np.arange(N) - N // 2
눈금 = 2.5 / (N / 2)
a = serdes.압축세기(np.random.default_rng(0).normal(0, 1.0, 20000), 0.5)
되 = serdes.역압축하기(코드 * 눈금, 0.5, a)
진짜표 = (np.clip(np.round(되 / 눈금), -N // 2, N // 2 - 1).astype(int)
        + N // 2).tolist()
ok(진짜표 != list(range(N)), "진짜 역압축 표는 항등이 아니다")
r진 = asic.잰것(eqrtl.invrom(비트, 비트, 진짜표), "invrom")
r항 = asic.잰것(eqrtl.invrom(비트, 비트), "invrom")
ok(r진["판정"] == "PASS" and r항["판정"] == "PASS", "둘 다 합성된다")
if r진["판정"] == "PASS" and r항["판정"] == "PASS":
    ok(r진["셀면적um2"] > 3 * r항["셀면적um2"],
       f"진짜 표 {r진['셀면적um2']:.0f} um2({r진['게이트수']} 게이트) vs "
       f"항등표 {r항['셀면적um2']:.0f} um2({r항['게이트수']} 게이트) -- "
       f"**항등표를 넣으면 합성기가 배선으로 지워 면적이 거짓으로 작게 나온다.** "
       f"ROM 비용을 잴 때는 반드시 진짜 내용을 넣어야 한다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for m in FAIL:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
