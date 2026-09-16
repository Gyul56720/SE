"""**여러 계열 합성** -- 곱셈기의 값은 소자가 정한다.

논문의 면적 표는 전부 iCE40 HX8K 에서 났다. 그 소자에는 하드 곱셈기가 없어서 곱셈이
전부 LUT 로 풀린다 -- **곱셈 기반 설계에 가장 불리한 자리**다. 한계로 적어 두기만
하고 재지 않으면, 그 한계가 결론을 얼마나 뒤집는지 아무도 모른다.

## 붙드는 것

    (가) DSP 가 있는 계열에서 신경망의 곱셈이 **DSP 셀로 간다**
    (나) 표(FFE+표)는 어느 계열에서도 **DSP 를 안 쓴다** -- 정의상 패브릭이다
    (다) 못 하는 것을 못 한다고 낸다 -- 모르는 top 이름이나 없는 계열은 '못잼'

(나)가 없으면 (가)가 그냥 "DSP 가 있네" 일 뿐이다. 둘이 같이 있어야 **곱셈기 수가
소자에 따라 다른 값을 갖는다**는 말이 선다.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import eqrtl
import synth

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


if not shutil.which("yosys"):
    print("yosys 가 없다 -- 건너뛴다")
    raise SystemExit(0)

print("[가 -- 신경망의 곱셈이 DSP 로 간다]")
nn = eqrtl.nn(창=5, 은닉=2, 파이프=True)
r5 = synth.재기(nn, "nneq_eq", "ecp5")
ok(r5["판정"] == "PASS" and r5["곱셈기셀"] == 12,
   f"ECP5: 곱셈 12개가 DSP 셀 {r5.get('곱셈기셀')}장으로 (총 셀 {r5.get('합계')})")
rx = synth.재기(nn, "nneq_eq", "xilinx")
ok(rx["판정"] == "PASS" and rx["곱셈기셀"] == 12,
   f"Xilinx: DSP 셀 {rx.get('곱셈기셀')}장 (총 셀 {rx.get('합계')})")
ri = synth.재기(nn, "nneq_eq", "ice40")
ok(ri["판정"] == "PASS" and ri.get("곱셈기셀", 0) == 0 and ri["합계"] > r5["합계"],
   f"iCE40: DSP 가 없어 전부 패브릭 -- 셀 {ri.get('합계')} > ECP5 {r5.get('합계')}")

print("[나 -- 표는 어느 계열에서도 DSP 를 안 쓴다]")
tbl = eqrtl.ffe_tbl(ffe탭=11, 창=2, 색인비트=4, W=7, DW=7, 파이프=True)
for 어디 in ("ecp5", "xilinx"):
    t = synth.재기(tbl, "ffe_tbl", 어디)
    # FFE 의 곱셈 11개는 DSP 로 갈 수 있다. **표 자체가** 안 쓰는 것을 보려면
    # FFE 만 있는 판과 견주어 DSP 수가 같은지 본다.
    f = synth.재기(eqrtl.ffe(탭=11, W=7, DW=7), "ffe", 어디)
    ok(t["판정"] == "PASS" and f["판정"] == "PASS"
       and t.get("곱셈기셀", 0) == f.get("곱셈기셀", 0),
       f"{어디}: FFE+표의 DSP {t.get('곱셈기셀')} = FFE 혼자의 DSP {f.get('곱셈기셀')} "
       f"-- 표는 DSP 를 한 장도 안 쓴다")

print("[다 -- 못 하는 것은 못잼으로 낸다]")
ok(synth.재기(nn, "없는이름", "ecp5")["판정"] == "못잼", "모르는 top 이름 -> 못잼")
ok(synth.재기(nn, "nneq_eq", "없는계열")["판정"] == "못잼", "모르는 계열 -> 못잼")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for m in FAIL_목록:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
