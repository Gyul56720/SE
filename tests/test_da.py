"""**분산 산술 FFE** -- 선행 사례가 한 일과 이 논문이 하는 일을 갈라 둔다.

사용자가 알려 준 선행 사례: 28 Gb/s PAM-4 수신기에서 **FFE 앞 세 탭을 LUT 로** 짓고,
오프라인에서 계산한 값을 그 LUT 에 싣는다. 고전적으로는 분산 산술(Peled & Liu, 1974)
이다. 이 저장소가 "곱셈기 없는 표" 를 말하고 있으니 **같은 것이냐**는 물음이 먼저다.

    선행 사례의 표   ROM[a] = sum_k c_k a_k   -- 주소의 **선형** 함수. 학습 없음.
                     바꾸는 것은 **구현 비용**이고 계산 결과는 곱셈기 판과 **같다**.
    이 논문의 표     T[i]   = E[b | 주소=i]   -- 주소의 선형 함수가 **아니다**.
                     프리앰블에서 **학습**되고, 어떤 FIR 로도 못 만든다.

**말로 가르지 않고 재서 가른다.** 이 검사가 붙드는 것:

    (가) 분산 산술 판이 곱셈기 판과 **비트까지 같다**(iverilog 로 실제 돌려서)
    (나) ROM 내용이 계수에서 **그대로 셈해 나온다**(학습 데이터가 안 든다)
    (다) 판정 표는 그 성질이 **없다** -- 선형 맞춤의 잔차가 크다

(다)가 없으면 "우리 표는 다르다" 가 주장일 뿐이다.
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import eqrtl
import serdes

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


print("[나 -- ROM 내용은 계수에서 그대로 나온다]")
rng = random.Random(3)
for _ in range(5):
    c = [rng.randrange(-64, 64) for _ in range(4)]
    롬 = eqrtl.da롬(c)
    맞나 = all(롬[a] == sum(v for k, v in enumerate(c) if (a >> k) & 1)
             for a in range(len(롬)))
    if not 맞나:
        break
ok(맞나 and len(롬) == 16, f"계수 4개 -> 16칸, 내용이 sum c_k a_k (학습 데이터가 안 든다)")

print("[가 -- 분산 산술 판이 곱셈기 판과 비트까지 같다]")
if not shutil.which("iverilog"):
    print("  건너뜀 -- iverilog 가 없다")
else:
    탭, N, W, DW = 11, 3, 7, 7
    판 = tempfile.mkdtemp(prefix="da-")
    try:
        open(os.path.join(판, "a.v"), "w").write(eqrtl.ffe(탭=탭, W=W, DW=DW))
        open(os.path.join(판, "b.v"), "w").write(eqrtl.ffe_da(탭=탭, DA탭=N, W=W, DW=DW))
        r2 = random.Random(7)
        계수 = [r2.randrange(-(1 << (W - 1)), 1 << (W - 1)) for _ in range(탭)]
        롬 = eqrtl.da롬(계수[:N])
        자극 = [r2.randrange(-(1 << (DW - 1)), 1 << (DW - 1)) for _ in range(300)]
        RW = W + eqrtl.주소폭(N + 1)
        YW = W + DW + eqrtl.주소폭(탭 + 1)
        AW = eqrtl.주소폭(탭)
        줄 = [f"    @(negedge clk); cw_we=1; cw_addr={i}; cw_data={c};"
             for i, c in enumerate(계수)]
        줄.append("    @(negedge clk); cw_we=0;")
        줄 += [f"    @(negedge clk); rom_we=1; rom_addr={a}; rom_data={v};"
              for a, v in enumerate(롬)]
        줄.append("    @(negedge clk); rom_we=0;")
        줄 += [f"    @(negedge clk); x={v}; @(posedge clk); #1 "
              f"if (ya!==yb) bad=bad+1;" for v in 자극]
        tb = ("module tb;\n"
              f"  reg clk=0, rst_n=0, cw_we=0, rom_we=0;\n"
              f"  reg [{AW}-1:0] cw_addr; reg signed [{W}-1:0] cw_data;\n"
              f"  reg [{N}-1:0] rom_addr; reg signed [{RW}-1:0] rom_data;\n"
              f"  reg signed [{DW}-1:0] x=0;\n"
              f"  wire signed [{YW}-1:0] ya, yb;\n"
              "  ffe    ua(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),"
              ".cw_addr(cw_addr),.cw_data(cw_data),.y(ya));\n"
              "  ffe_da ub(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),"
              ".cw_addr(cw_addr),.cw_data(cw_data),.rom_we(rom_we),"
              ".rom_addr(rom_addr),.rom_data(rom_data),.y(yb));\n"
              "  always #5 clk=~clk;\n  integer bad;\n  initial begin\n"
              "    bad=0; @(negedge clk); rst_n=1;\n"
              + "\n".join(줄) + "\n"
              '    if (bad==0) $display("BITEXACT"); else $display("MISMATCH %0d", bad);\n'
              "    $finish;\n  end\nendmodule\n")
        open(os.path.join(판, "tb.v"), "w").write(tb)
        c1 = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(판, "sim"),
                             os.path.join(판, "a.v"), os.path.join(판, "b.v"),
                             os.path.join(판, "tb.v")],
                            capture_output=True, text=True, timeout=240)
        if c1.returncode != 0:
            ok(False, "iverilog 가 막혔다: " + (c1.stderr or c1.stdout)[-300:])
        else:
            out = subprocess.run(["vvp", os.path.join(판, "sim")],
                                 capture_output=True, text=True, timeout=240).stdout
            ok("BITEXACT" in out,
               f"곱셈기 판과 DA 판이 {len(자극)}개 자극에서 한 비트도 안 다르다 "
               f"({out.strip().splitlines()[0] if out.strip() else '출력 없음'})")
    finally:
        shutil.rmtree(판, ignore_errors=True)

print("[다 -- 판정 표는 주소의 선형 함수가 아니다]")
# 논문의 동작점에서 표를 학습시키고, 그 내용을 **주소 비트의 선형 결합으로** 맞춰 본다.
# 선행 사례의 ROM 이라면 잔차가 0 이어야 한다(정의상 선형이므로).
r = serdes.링크(비트수=300000, 손실dB=25.0, SNRdB=30.0, ADC비트=7,
             압축=1.0, 압축뒤대역=0.35, FFE탭=11,
             표본표창=2, 표본표비트=4, 씨=0)
표, 주소, 찬칸 = serdes.표본색인표학습(r["표본"], r["비트"].astype(float), 2, 4,
                                int(len(r["표본"]) * 0.3))
쓸것 = np.array([i for i in range(len(표)) if 표[i] != 0.0])
값 = 표[쓸것]
비트 = ((쓸것[:, None] >> np.arange(8)[None, :]) & 1).astype(float)
설계 = np.hstack([비트, np.ones((len(쓸것), 1))])
계수, 잔차, *_ = np.linalg.lstsq(설계, 값, rcond=None)
남은 = float(np.linalg.norm(값 - 설계 @ 계수)) / max(float(np.linalg.norm(값)), 1e-12)
# 대조: 같은 크기의 **선형** ROM(분산 산술) 은 같은 맞춤에서 잔차가 0 이어야 한다.
선형롬 = np.array(eqrtl.da롬([3, -5, 2, 7, -1, 6, -4, 2]), dtype=float)
비트2 = ((np.arange(len(선형롬))[:, None] >> np.arange(8)[None, :]) & 1).astype(float)
설계2 = np.hstack([비트2, np.ones((len(선형롬), 1))])
계수2, *_ = np.linalg.lstsq(설계2, 선형롬, rcond=None)
남은2 = float(np.linalg.norm(선형롬 - 설계2 @ 계수2)) / max(float(np.linalg.norm(선형롬)), 1e-12)
ok(남은2 < 1e-9,
   f"대조: 분산 산술 ROM 은 주소 비트의 선형 결합으로 **정확히** 맞는다 (잔차 {남은2:.1e})")
ok(남은 > 0.2,
   f"판정 표는 안 맞는다 -- 상대 잔차 {남은:.2f} ({len(쓸것)}칸). "
   f"어떤 FIR 로도 못 만드는 내용이다")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개")
    for m in FAIL_목록:
        print("  - " + m)
    sys.exit(1)
print("전부 통과")
