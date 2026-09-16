"""`nnfix.py` · `eqrtl.py` -- 고정소수점 기준모델과 그것을 그대로 옮긴 Verilog.

주제의 5단계(FPGA 구현). **이 자리의 거짓 초록은 면적을 보고하고 정답을 안 보는
것**이다 -- 틀린 회로가 제일 작다. 그래서 여기서는 LC 를 한 줄도 안 센다. 재는 것은
**RTL 이 기준모델과 같은 값을 내는가** 하나뿐이고, 면적은 그것이 맞은 다음에야 뜻을
갖는다.

## 자릿수는 정수부가 갈랐다 -- 실측 2026-09-16, 씨 6개

`가중치비트`(부호 포함 전체 폭)와 `프랙비트`를 따로 흔들어 float 대비 BER 배수를 쟀다.

    폭  프랙  정수부   배     퍼짐
     7    6     0    7.86  [5.74,10.84]   <- 스케일이 2 로 밀려난다
     8    6     1    1.84  [1.62, 2.05]
    10    8     1    1.86  [1.66, 2.10]   <- 폭이 10 이어도 정수부가 1 이면 같다
     9    6     2    0.98  [0.92, 1.08]
     8    5     2    0.99  [0.79, 1.36]
     7    4     2    1.00  [0.85, 1.24]
    10    4     5    1.00  [0.85, 1.24]

**같은 정수부면 전체 폭이 달라도 같은 값이 나온다.** 그러니 갈린 것은 소수 해상도가
아니라 **가중치가 담기는 범위**다. 바닥은 정수부 2(가중치 ±4)다.

소수부에도 바닥이 따로 있다: 프랙 3 은 1.21배인데 퍼짐이 [0.60, 2.15] 로 1 을
가로지른다 -- **더 나쁘다고 말할 수 없고 같다고도 말할 수 없다(미해결).** 그래서
안전한 바닥으로 프랙 4 를 쓴다.

두 바닥을 합치면 **부호 1 + 정수부 2 + 소수부 4 = 7비트(Q2.4)** 다.

### 앞 판의 내 진단이 틀렸었다

여기 처음 적었던 것은 "Q1.6 8비트가 2.6배 나쁜데, 원인은 W1 이 안 들어가 스케일
`s=8` 로 나눠 담은 것" 이었다. **둘 다 틀렸다.** 8비트에서 `고를스케일` 은 1 을
내놓는다(나누지 않는다) -- 스케일이 밀려나는 것은 7비트부터다. 그리고 배수는 2.6 이
아니라 1.84 다. 한 번 돌린 한 씨의 값을 원인까지 붙여 적어 둔 것이었다.

## RTL 은 부호가 아니라 **누산기 정수값**으로 맞춘다

결정만 보면 약 절반은 우연히 맞는다 -- 어긋난 회로가 50% 언저리로 초록처럼 보인다.
실제로 첫 두 판이 52% · 91% 였고 둘 다 정렬 문제였다(`eqrtl.계수싣기` 머리말).
그래서 `y` 를 그대로 찍어 **정수까지** 견준다.

한 칸 어긋남에 주의: 표시 시점의 `y` 는 색인 i 인데 `d` 는 레지스터라 i-1 이다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import nnfix
import nneq
import eqrtl

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


print("[재기 -- 폭 밖을 자른다]")
# 10비트 부호 있는 범위는 [-512, 511] 이다. **대칭이 아니다.**
ok(nnfix.재기([100.0, -100.0, 0.0], 프랙비트=6, 비트=10).tolist() == [511, -512, 0],
   "폭 밖이 [-512, 511] 로 잘린다 (대칭이 아니다)")
ok(nnfix.재기([1.0], 프랙비트=6, 비트=10).tolist() == [64], "1.0 -> Q6 에서 64")
ok(nnfix.재기([-0.5], 프랙비트=4, 비트=10).tolist() == [-8], "-0.5 -> Q4 에서 -8")

print("\n[고를스케일 -- 담기는 제일 작은 2의 거듭제곱]")
모 = {"W1": np.array([[3.9]]), "b1": np.array([0.0])}
ok(nnfix.고를스케일(모, 프랙비트=4, 비트=7) == 1.0,
   "폭 7 Q2.4 면 3.9 가 그대로 담긴다 (62 <= 63)")
ok(nnfix.고를스케일(모, 프랙비트=6, 비트=7) == 4.0,
   "폭 7 Q0.6 이면 249 > 63 이라 4 로 나눈다 (249/4 = 62 <= 63)")
ok(nnfix.고를스케일(모, 프랙비트=6, 비트=6) == 16.0,
   "폭이 한 비트 더 좁으면(끝 31) 16 으로 나눈다 -- 2의 거듭제곱 중 **제일 작은 것**")

print("\n[앞먹임 -- 손으로 센 값]")
# W1=[[2]], x=64(=1.0) -> 128, b1=32 -> 160, >>6 = 2, 클립 안. y = 2*64 = 128 >= 0
정 = {"W1": np.array([[2]]), "b1": np.array([32]),
     "W2": np.array([[64]]), "b2": np.array([0])}
ok(nnfix.앞먹임(정, np.array([[64]]), 프랙비트=6, 반올림=False).tolist() == [1],
   "z=160 >>6 =2, y=128 -> +1")
정2 = dict(정, W2=np.array([[-64]]))
ok(nnfix.앞먹임(정2, np.array([[64]]), 프랙비트=6, 반올림=False).tolist() == [-1],
   "W2 부호를 뒤집으면 결정이 뒤집힌다 -- 마지막이 부호뿐이라는 확인")


def _y(x):
    z = (np.array([[x]]) @ np.array([[64]]) + np.array([0]) * 64) >> 6
    h = np.clip(z, -64, 64)
    return int(np.ravel(h @ np.array([[64]]))[0])


print("\n[동점 -- y 가 0 이면 +1 이다]")
# RTL 은 `d <= ~y[YW-1]` 이라 y=0 을 양수로 본다. 기준모델도 `>=` 여야 같다.
영 = {"W1": np.array([[0]]), "b1": np.array([0]),
     "W2": np.array([[0]]), "b2": np.array([0])}
ok(nnfix.앞먹임(영, np.array([[0]]), 프랙비트=4, 반올림=False).tolist() == [1],
   "y == 0 은 +1 이다 (`~y[MSB]` 와 같은 규칙)")

print("\n[hardtanh -- 실제로 자른다]")
ok(_y(64) == _y(6400), "클립 밖에서는 더 밀어도 y 가 안 커진다")
ok(_y(32) < _y(64), "클립 안에서는 선형이다")

print("\n[자릿수 -- 갈린 것은 정수부다]")


def 배수(비트, 프랙, 씨수=4):
    f, m = [], []
    for 씨 in range(씨수):
        r = nnfix.링크(비트수=40000, 앞뒤=2, 은닉수=2, 에폭=10, 씨=씨,
                     가중치비트=비트, 프랙비트=프랙)
        f.append(r["부동"]["BER"]); m.append(r["정수"]["BER"])
    return float(np.mean(m) / np.mean(f))


정수부1 = 배수(8, 6)
정수부2 = 배수(9, 6)
좁지만정수부2 = 배수(7, 4)
print(f"    폭8 Q1.6(정수부 1) {정수부1:.2f}배 · 폭9 Q2.6(정수부 2) {정수부2:.2f}배 · "
      f"폭7 Q2.4(정수부 2) {좁지만정수부2:.2f}배")
ok(정수부1 > 1.3, f"정수부 1 은 float 보다 나쁘다 ({정수부1:.2f}배)")
ok(정수부2 < 1.15, f"정수부 2 는 float 을 따라잡는다 ({정수부2:.2f}배)")
# **여기가 핵심**: 폭은 더 좁은데 정수부가 2 라서 더 좋다.
ok(좁지만정수부2 < 정수부1,
   f"7비트 Q2.4({좁지만정수부2:.2f}배)가 8비트 Q1.6({정수부1:.2f}배)보다 좋다 "
   "-- 갈린 것이 폭이 아니라 정수부다")

print("\n[계수싣기 -- 창을 뒤집는다]")
정3 = {"W1": np.arange(6).reshape(3, 2), "b1": np.array([9, 9]),
      "W2": np.array([[7], [7]]), "b2": np.array([5])}
난것 = eqrtl.계수싣기(정3)
ok(난것[:6] == [4, 5, 2, 3, 0, 1], "마지막 행(최신)이 먼저 실린다")
ok(난것[6:] == [9, 9, 7, 7, 5], "b1 · W2 · b2 가 그 뒤에 온다")
ok(len(난것) == eqrtl.계수수(3, 2), "계수 개수가 맞는다")
X = nneq.창만들기(np.arange(10.0), 2)
ok(X[5, -1] == 7.0 and X[5, 0] == 3.0,
   "**창만들기의 마지막 열이 제일 최신이다** -- 뒤집기가 이 약속 위에 선다")

print("\n[RTL -- 기준모델과 누산기까지 같은가]")
if not all(shutil.which(t) for t in ("iverilog", "vvp")):
    ok(True, "건너뜀: iverilog/vvp 가 없다")
else:
    창, 은닉, 프랙, 폭 = 5, 2, 4, 7
    r = nnfix.링크(비트수=40000, 앞뒤=(창 - 1) // 2, 은닉수=은닉, 에폭=10, 씨=0,
                 프랙비트=프랙, 가중치비트=폭)
    정수모, X정수 = r["정수모"], r["X정수"]
    N = 220
    Xn = X정수[:N]
    기준 = nnfix.앞먹임(정수모, Xn, 프랙, 반올림=False)   # RTL 은 >>> 내림이다
    ok(len(set(기준.tolist())) == 2,
       "**기준 판정이 양쪽으로 다 난다** -- 한쪽뿐이면 검사가 헛돈다")
    # RTL 의 sr[k] = 표본[t-k], X[i,j] = 표본[i+j-앞뒤] -> 스트림은 X 의 마지막 열이다
    스트림 = [int(v) for v in Xn[:, 창 - 1]]
    계수 = eqrtl.계수싣기(정수모)
    주소폭 = eqrtl.주소폭(eqrtl.계수수(창, 은닉))
    판 = tempfile.mkdtemp(prefix="nnrtl-")
    try:
        (Path(판) / "dut.v").write_text(
            eqrtl.nn(창, 은닉, XW=폭, WW=폭, FRAC=프랙), encoding="utf-8")
        tb = ["`timescale 1ns/1ps", "module tb;",
              "  reg clk=0, rst_n=0, cw_we=0;",
              f"  reg [{주소폭 - 1}:0] cw_addr=0;",
              f"  reg signed [{폭 - 1}:0] cw_data=0;",
              f"  reg signed [{폭 - 1}:0] x=0;",
              "  wire d;",
              "  nneq_eq dut(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),"
              ".cw_addr(cw_addr),.cw_data(cw_data),.d(d));",
              "  always #5 clk = ~clk;",
              "  initial begin",
              "    @(negedge clk); rst_n = 1;"]
        for a, v in enumerate(계수):
            tb.append(f"    @(negedge clk); cw_we=1; cw_addr={a}; cw_data={v};")
        tb.append("    @(negedge clk); cw_we=0;")
        for v in 스트림:
            tb.append(f"    @(negedge clk); x = {v};")
            tb.append('    @(posedge clk); #1 $display("D %0d %0d", dut.y, d);')
        tb += ["    $finish;", "  end", "endmodule"]
        (Path(판) / "tb.v").write_text("\n".join(tb), encoding="utf-8")
        쨈 = subprocess.run(["iverilog", "-g2012", "-o", "a.out", "dut.v", "tb.v"],
                           cwd=판, capture_output=True, text=True, timeout=180)
        ok(쨈.returncode == 0, f"iverilog 가 컴파일한다 {쨈.stderr[-200:]}")
        난줄 = subprocess.run(["vvp", "a.out"], cwd=판, capture_output=True,
                            text=True, timeout=180).stdout
    finally:
        shutil.rmtree(판, ignore_errors=True)
    찍힌 = [ln.split()[1:] for ln in 난줄.splitlines() if ln.startswith("D ")]
    ok(len(찍힌) >= N - 2, f"RTL 이 {len(찍힌)} 줄 냈다 (기대 {N})")

    # **기준을 다시 쓰지 않는다.** 처음에는 여기에 같은 식을 손으로 옮겨 놓았는데,
    # 그러면 `nnfix` 쪽 산술을 고쳐도 검사가 초록이었다(hardtanh 한계를 두 배로
    # 바꿔 봐도 안 걸렸다). 산술은 `nnfix.누산기` 한 군데에만 있어야 한다.
    y기준 = nnfix.누산기(정수모, Xn, 프랙, 반올림=False)

    틀린y, 틀린d, 센것 = [], [], 0
    for i in range(창 - 1, min(len(찍힌), len(기준)) - 1):
        센것 += 1
        if int(찍힌[i][0]) != int(y기준[i]):
            틀린y.append((i, int(찍힌[i][0]), int(y기준[i])))
        if (1 if int(찍힌[i][1]) else -1) != 기준[i - 1]:   # d 는 레지스터라 한 칸 늦다
            틀린d.append((i, int(찍힌[i][1]), int(기준[i - 1])))
    ok(센것 > 150, f"견준 것이 {센것} 개다")
    # **부호가 아니라 정수값이다.** 부호만 보면 어긋난 회로도 절반은 맞는다.
    ok(not 틀린y, f"누산기 y 가 {센것}개 다 같다" if not 틀린y
       else f"누산기가 {len(틀린y)}/{센것} 어긋났다: {틀린y[:3]}")
    ok(not 틀린d, f"결정 d 가 {센것}개 다 같다" if not 틀린d
       else f"결정이 {len(틀린d)}/{센것} 어긋났다: {틀린d[:3]}")

print("\n[선형 쪽 -- 견줄 상대도 맞는 답을 내야 한다]")
# 면적 표의 왼쪽 절반이 이 두 모듈에서 나온다. **그것이 맞는 답을 내는지 안 보면
# 거짓 초록이 표의 절반을 차지한다** -- 신경망 쪽만 붙들어 놓고 넘어갈 수 없다.
if not all(shutil.which(t) for t in ("iverilog", "vvp")):
    ok(True, "건너뜀: iverilog/vvp 가 없다")
else:
    def 돌리기(설계, top, 줄들, 찍을것):
        판3 = tempfile.mkdtemp(prefix="eqrtl-")
        try:
            (Path(판3) / "dut.v").write_text(설계, encoding="utf-8")
            (Path(판3) / "tb.v").write_text("\n".join(줄들), encoding="utf-8")
            쨈3 = subprocess.run(["iverilog", "-g2012", "-o", "a.out", "dut.v", "tb.v"],
                                cwd=판3, capture_output=True, text=True, timeout=180)
            ok(쨈3.returncode == 0, f"{top} 이 컴파일된다 {쨈3.stderr[-200:]}")
            return subprocess.run(["vvp", "a.out"], cwd=판3, capture_output=True,
                                  text=True, timeout=180).stdout
        finally:
            shutil.rmtree(판3, ignore_errors=True)

    탭 = 5
    계 = [3, -7, 21, -5, 2]
    입력 = [((i * 11) % 63) - 31 for i in range(40)]
    줄 = ["`timescale 1ns/1ps", "module tb;",
         "  reg clk=0, rst_n=0, cw_we=0;",
         f"  reg [{eqrtl.주소폭(탭) - 1}:0] cw_addr=0;",
         "  reg signed [6:0] cw_data=0;  reg signed [5:0] x=0;",
         "  wire signed [15:0] y;",
         "  ffe dut(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),"
         ".cw_addr(cw_addr),.cw_data(cw_data),.y(y));",
         "  always #5 clk = ~clk;", "  initial begin",
         "    @(negedge clk); rst_n = 1;"]
    for a, v in enumerate(계):
        줄.append(f"    @(negedge clk); cw_we=1; cw_addr={a}; cw_data={v};")
    줄.append("    @(negedge clk); cw_we=0;")
    for v in 입력:
        줄.append(f"    @(negedge clk); x = {v};")
        줄.append('    @(posedge clk); #1 $display("D %0d", y);')
    줄 += ["    $finish;", "  end", "endmodule"]
    찍 = [int(ln.split()[1]) for ln in
         돌리기(eqrtl.ffe(탭, W=7, DW=6), "ffe", 줄, "y").splitlines()
         if ln.startswith("D ")]
    # RTL 의 sr[0] 이 최신이므로 y[t] = sum_k 계[k] * x[t-k] 인데, y 는 레지스터라
    # t 번째 표시 줄에는 x[t-1] 까지만 들어간 값이 나온다(한 칸 늦다).
    기대 = [sum(계[k] * 입력[i - k] for k in range(탭) if i - k >= 0)
          for i in range(len(입력))]
    어긋3 = [(i, 찍[i], 기대[i - 1]) for i in range(탭, min(len(찍), len(기대)))
            if 찍[i] != 기대[i - 1]]
    ok(not 어긋3, f"FFE 가 합성곱과 같다 ({len(찍)}개)" if not 어긋3
       else f"FFE 가 {len(어긋3)}개 어긋났다: {어긋3[:3]}")
    ok(len(set(기대[탭:])) > 10, "기대값이 여러 가지다 -- 한 값뿐이면 검사가 헛돈다")

    # DFE: 곱셈 없이 계수를 더하고 뺀다. 결정 되먹임이라 파이썬도 같은 고리를 돈다.
    자리 = [1, 2, 3]
    # **끝까지 민다.** 작은 계수로만 재면 누산기 폭을 XW 로 좁혀도 통과한다(실측) --
    # acc 가 x 폭 안에 머물러 감기는 자리를 안 지나기 때문이다. 계수를 8비트 끝값에
    # 두고 x 를 12비트 끝까지 훑어, 되먹임이 acc 를 x 폭 밖으로 밀어내게 한다.
    계2 = [127, -127, 120]
    입력2 = [((i * 331) % 4095) - 2047 for i in range(60)]
    줄2 = ["`timescale 1ns/1ps", "module tb;",
          "  reg clk=0, rst_n=0, cw_we=0;",
          f"  reg [{eqrtl.주소폭(len(자리)) - 1}:0] cw_addr=0;",
          "  reg signed [7:0] cw_data=0;  reg signed [11:0] x=0;",
          "  wire d;",
          "  dfe_pos dut(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),"
          ".cw_addr(cw_addr),.cw_data(cw_data),.d(d));",
          "  always #5 clk = ~clk;", "  initial begin",
          "    @(negedge clk); rst_n = 1;"]
    for a, v in enumerate(계2):
        줄2.append(f"    @(negedge clk); cw_we=1; cw_addr={a}; cw_data={v};")
    줄2.append("    @(negedge clk); cw_we=0;")
    for v in 입력2:
        줄2.append(f"    @(negedge clk); x = {v};")
        줄2.append('    @(posedge clk); #1 $display("D %0d", d);')
    줄2 += ["    $finish;", "  end", "endmodule"]
    찍2 = [int(ln.split()[1]) for ln in
          돌리기(eqrtl.dfe(자리, W=8, XW=12), "dfe_pos", 줄2, "d").splitlines()
          if ln.startswith("D ")]
    이력 = [0] * (max(자리) + 1)      # 1 이면 '지난 결정이 1'
    기대2, acc들 = [], []
    for v in 입력2:
        acc = v
        for i, p in enumerate(자리):
            acc += -계2[i] if 이력[p - 1] else 계2[i]
        acc들.append(acc)
        결 = 1 if acc >= 0 else 0
        기대2.append(결)
        이력 = [결] + 이력[:-1]
    # **FFE 와 달리 한 칸 늦지 않다.** FFE 는 x 가 시프트 레지스터를 거쳐 y 가
    # 레지스터에 담기지만, DFE 의 acc 는 x 를 바로 쓴다 -- d 는 그 사이클 것이다.
    어긋4 = [(i, 찍2[i], 기대2[i]) for i in range(len(자리) + 1,
                                              min(len(찍2), len(기대2)))
            if 찍2[i] != 기대2[i]]
    ok(not 어긋4, f"DFE 가 되먹임 모델과 같다 ({len(찍2)}개)" if not 어긋4
       else f"DFE 가 {len(어긋4)}개 어긋났다: {어긋4[:3]}")
    ok(0 < sum(기대2) < len(기대2), "기대 결정이 양쪽으로 다 난다")

    # ---- 합친 FFE+DFE: 면적을 '따로 재서 더한 값' 으로 말하지 않으려면 이것이 맞아야 한다
    Lf, 자리3 = 5, [1, 2, 3]
    # **계수를 끝값에 둔다.** 작은 계수로는 누산기가 CW+DW 안에 머물러, 폭을 좁혀도
    # 검사가 통과한다(실측: |acc| 최대 4,270 < 2^14).
    계f = [127, -127, 120, -110, 100]
    계d = [127, -127, 120]
    # 부호를 교대로 줘야 탭 부호와 맞아 누산기가 끝까지 간다(37,139). 램프만 주면
    # 13,924 에 그쳐 CW+DW 를 못 넘는다. 일곱 번마다 램프 값을 끼워 결정을 흔든다.
    입력3 = [(63 if i % 2 == 0 else -64) if i % 7 else ((i * 37) % 127) - 63
            for i in range(80)]
    줄3 = ["`timescale 1ns/1ps", "module tb;",
          "  reg clk=0, rst_n=0, cw_we=0;",
          f"  reg [{eqrtl.주소폭(Lf + len(자리3)) - 1}:0] cw_addr=0;",
          "  reg signed [7:0] cw_data=0;  reg signed [6:0] x=0;",
          "  wire d;",
          "  ffe_dfe dut(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),"
          ".cw_addr(cw_addr),.cw_data(cw_data),.d(d));",
          "  always #5 clk = ~clk;", "  initial begin",
          "    @(negedge clk); rst_n = 1;"]
    for a, v in enumerate(계f + 계d):
        줄3.append(f"    @(negedge clk); cw_we=1; cw_addr={a}; cw_data={v};")
    줄3.append("    @(negedge clk); cw_we=0;")
    for v in 입력3:
        줄3.append(f"    @(negedge clk); x = {v};")
        줄3.append('    @(posedge clk); #1 $display("D %0d", d);')
    줄3 += ["    $finish;", "  end", "endmodule"]
    찍3 = [int(ln.split()[1]) for ln in
          돌리기(eqrtl.ffe_dfe(Lf, 자리3, W=8, DW=7, WD=8), "ffe_dfe", 줄3, "d").splitlines()
          if ln.startswith("D ")]
    # 파이썬 쪽도 같은 흐름: sr[0]=최신이고 acc 는 x 를 시프트 레지스터로 받는다.
    이력3 = [0] * (max(자리3) + 1)
    기대3, acc3들 = [], []
    for i in range(len(입력3)):
        accf = sum(계f[k] * 입력3[i - k] for k in range(Lf) if i - k >= 0)
        acc = accf
        for j, pp in enumerate(자리3):
            acc += -계d[j] if 이력3[pp - 1] else 계d[j]
        acc3들.append(acc)
        결 = 1 if acc >= 0 else 0
        기대3.append(결)
        이력3 = [결] + 이력3[:-1]
    # y 는 sr 를 거치므로 한 칸 늦고, 되먹임은 같은 사이클이다 -- RTL 의 sr[0] <= x 때문에
    어긋5 = [(i, 찍3[i], 기대3[i - 1]) for i in range(Lf + 1, min(len(찍3), len(기대3)))
            if 찍3[i] != 기대3[i - 1]]
    ok(not 어긋5, f"합친 FFE+DFE 가 모델과 같다 ({len(찍3)}개)" if not 어긋5
       else f"합친 FFE+DFE 가 {len(어긋5)}개 어긋났다: {어긋5[:3]}")
    ok(0 < sum(기대3) < len(기대3), "합친 것의 결정도 양쪽으로 다 난다")
    ok(max(abs(a) for a in acc3들) > (1 << (8 + 7 - 1)),
       f"**합친 누산기가 CW+DW 를 넘긴다** (|acc| 최대 {max(abs(a) for a in acc3들)})")

    # ---- 되먹임은 **따로** 재야 한다. 위 자극은 폭을 재려고 FFE 계수를 끝값에 뒀는데,
    # 그러면 accf 가 ~37,000 이고 DFE 항은 최대 381 이라 **되먹임이 판정에 안 닿는다**.
    # 실제로 그 상태에서 되먹임을 한 칸 밀어 봐도 검사가 통과했다(실측). 폭을 재는 자극과
    # 되먹임을 재는 자극은 요구가 반대라서 한 자극으로는 둘 다 못 잰다.
    계f2 = [8, -3, 2, -1, 1]
    계d2 = [60, -28, 14]
    입력4 = [((i * 29) % 41) - 20 for i in range(80)]
    줄4 = 줄3[:10]                      # 머리말은 같다 (rst 까지)
    for a, v in enumerate(계f2 + 계d2):
        줄4.append(f"    @(negedge clk); cw_we=1; cw_addr={a}; cw_data={v};")
    줄4.append("    @(negedge clk); cw_we=0;")
    for v in 입력4:
        줄4.append(f"    @(negedge clk); x = {v};")
        줄4.append('    @(posedge clk); #1 $display("D %0d", d);')
    줄4 += ["    $finish;", "  end", "endmodule"]
    찍4 = [int(ln.split()[1]) for ln in
          돌리기(eqrtl.ffe_dfe(Lf, 자리3, W=8, DW=7, WD=8), "ffe_dfe", 줄4, "d").splitlines()
          if ln.startswith("D ")]
    이력4 = [0] * (max(자리3) + 1)
    기대4, 되먹임몫 = [], []
    for i in range(len(입력4)):
        accf = sum(계f2[k] * 입력4[i - k] for k in range(Lf) if i - k >= 0)
        되 = sum(-계d2[j] if 이력4[pp - 1] else 계d2[j] for j, pp in enumerate(자리3))
        되먹임몫.append(abs(되) / max(abs(accf) + abs(되), 1))
        결 = 1 if accf + 되 >= 0 else 0
        기대4.append(결)
        이력4 = [결] + 이력4[:-1]
    어긋6 = [(i, 찍4[i], 기대4[i - 1]) for i in range(Lf + 1, min(len(찍4), len(기대4)))
            if 찍4[i] != 기대4[i - 1]]
    몫 = sum(되먹임몫) / len(되먹임몫)
    ok(몫 > 0.25,
       f"**되먹임이 판정에 실제로 닿는다** (누산기 크기의 평균 {100*몫:.0f}%) "
       "-- 안 닿으면 되먹임을 재는 것이 아니다")
    ok(not 어긋6, f"되먹임이 지배적일 때도 합친 것이 모델과 같다 ({len(찍4)}개)"
       if not 어긋6 else f"되먹임 자극에서 {len(어긋6)}개 어긋났다: {어긋6[:3]}")
    ok(0 < sum(기대4) < len(기대4), "되먹임 자극의 결정도 양쪽으로 다 난다")

    # ---- 파이프라인: **판정 순서가 그대로여야 한다.** 한 칸 더 늦을 뿐이다.
    # 이것이 맞아야 "파이프라인이 Fmax 를 올린다" 는 말이 뜻을 갖는다 -- 안 그러면
    # 더 빠른 대신 다른 답을 내는 회로를 재는 것이 된다.
    def 줄바꿔(줄들, 설계이름):
        난 = list(줄들)
        return [l.replace("ffe_dfe dut", f"{설계이름} dut") for l in 난]

    찍5 = [int(ln.split()[1]) for ln in
          돌리기(eqrtl.ffe_dfe(Lf, 자리3, W=8, DW=7, WD=8, 파이프=True),
               "ffe_dfe", 줄4, "d").splitlines() if ln.startswith("D ")]
    # 민판은 기대4[i-1] 과 맞았다 -> 파이프는 기대4[i-2] 와 맞아야 한다
    어긋7 = [(i, 찍5[i], 기대4[i - 2]) for i in range(Lf + 2, min(len(찍5), len(기대4)))
            if 찍5[i] != 기대4[i - 2]]
    ok(not 어긋7, f"파이프라인 선형이 **같은 판정을 한 칸 늦게** 낸다 ({len(찍5)}개)"
       if not 어긋7 else f"파이프라인 선형이 {len(어긋7)}개 어긋났다: {어긋7[:3]}")
    # **한 칸 늦은 것이 맞는지도 확인한다** -- 안 늦었으면 레지스터가 안 들어간 것이다
    같은칸 = sum(1 for i in range(Lf + 2, min(len(찍5), len(기대4)))
                if 찍5[i] == 기대4[i - 1])
    센칸 = len(range(Lf + 2, min(len(찍5), len(기대4))))
    ok(같은칸 < 센칸,
       f"**실제로 한 칸 늦다** (민판 정렬로는 {같은칸}/{센칸} 만 맞는다) "
       "-- 다 맞으면 레지스터가 안 들어간 것이다")

    # 신경망 쪽도 같은 것을 본다
    찍6 = [ln.split()[1:] for ln in
          돌리기(eqrtl.nn(창, 은닉, XW=폭, WW=폭, FRAC=프랙, 파이프=True),
               "nneq_eq", tb, "y d").splitlines() if ln.startswith("D ")]
    어긋8 = [(i, 찍6[i][1], int(기준[i - 2]))
            for i in range(창, min(len(찍6), len(기준)))
            if (1 if int(찍6[i][1]) else -1) != 기준[i - 2]]
    ok(not 어긋8, f"파이프라인 신경망이 **같은 판정을 한 칸 늦게** 낸다 ({len(찍6)}개)"
       if not 어긋8 else f"파이프라인 신경망이 {len(어긋8)}개 어긋났다: {어긋8[:3]}")

    # ---- FFE + 표본 색인 표: 뒷단에 곱셈기가 없는 구조. **면적을 재기 전에 맞는지 본다.**
    # 시프트는 **표본 대부분이 범위 안에 들어오게** 고른다. 처음에 5 로 뒀더니
    # 90/90 이 죔쇠에 걸려 범위 안 산술을 하나도 안 재고 있었다. 9 로 올리니 이번엔
    # 0/90 이라 죔쇠를 안 쟀다. 8 에서 26/90 -- 양쪽 길이 다 돈다(A.12 와 같은 결손).
    Lt, 창t, qb, sh = 5, 2, 4, 8
    계t = [40, -18, 7, -3, 2]
    입력t = [((i * 53) % 127) - 63 for i in range(90)]
    표t = [(i * 37) % 2 for i in range(1 << (qb * 창t))]   # 아무 표나 -- 배선을 본다
    줄t = ["`timescale 1ns/1ps", "module tb;",
          "  reg clk=0, rst_n=0, cw_we=0, tw_we=0, tw_data=0;",
          f"  reg [{eqrtl.주소폭(Lt) - 1}:0] cw_addr=0;",
          f"  reg [{qb * 창t - 1}:0] tw_addr=0;",
          "  reg signed [6:0] cw_data=0;  reg signed [6:0] x=0;",
          "  wire d;",
          "  ffe_tbl dut(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),.cw_addr(cw_addr),"
          ".cw_data(cw_data),.tw_we(tw_we),.tw_addr(tw_addr),.tw_data(tw_data),.d(d));",
          "  always #5 clk = ~clk;", "  initial begin",
          "    @(negedge clk); rst_n = 1;"]
    for a, v in enumerate(계t):
        줄t.append(f"    @(negedge clk); cw_we=1; cw_addr={a}; cw_data={v};")
    줄t.append("    @(negedge clk); cw_we=0;")
    for a, v in enumerate(표t):
        줄t.append(f"    @(negedge clk); tw_we=1; tw_addr={a}; tw_data={v};")
    줄t.append("    @(negedge clk); tw_we=0;")
    for v in 입력t:
        줄t.append(f"    @(negedge clk); x = {v};")
        줄t.append('    @(posedge clk); #1 $display("D %0d", d);')
    줄t += ["    $finish;", "  end", "endmodule"]
    찍t = [int(ln.split()[1]) for ln in
          돌리기(eqrtl.ffe_tbl(Lt, 창t, qb, sh, W=7, DW=7), "ffe_tbl", 줄t, "d").splitlines()
          if ln.startswith("D ")]

    # 정수 기준모델: RTL 의 흐름 그대로 (sr[0]=최신, 자르기+죔쇠, 코드 이어붙이기)
    def 코드내기(acc):
        옮 = acc >> sh                       # 산술 우시프트 = 내림
        큰, 작 = (1 << (qb - 1)) - 1, -(1 << (qb - 1))
        if 옮 > 큰: return (1 << qb) - 1
        if 옮 < 작: return 0
        return (옮 + (1 << (qb - 1))) & ((1 << qb) - 1)
    기대t, 지난c = [], [0] * max(창t - 1, 1)
    for i in range(len(입력t)):
        acc = sum(계t[k] * 입력t[i - k] for k in range(Lt) if i - k >= 0)
        c = 코드내기(acc)
        주소 = c
        for k in range(창t - 1):
            주소 |= 지난c[k] << (qb * (k + 1))
        기대t.append(표t[주소])
        지난c = [c] + 지난c[:-1]
    # sr 를 거치므로 한 칸 늦다
    어긋t = [(i, 찍t[i], 기대t[i - 1]) for i in range(Lt + 2, min(len(찍t), len(기대t)))
            if 찍t[i] != 기대t[i - 1]]
    ok(not 어긋t, f"**FFE+표 RTL 이 정수 기준모델과 같다** ({len(찍t)}개)"
       if not 어긋t else f"FFE+표가 {len(어긋t)}개 어긋났다: {어긋t[:3]}")
    ok(0 < sum(기대t) < len(기대t), "기대 판정이 양쪽으로 다 난다")
    # 죔쇠가 실제로 걸리는가 -- 안 걸리면 죔쇠 논리를 재는 것이 아니다
    accs = [sum(계t[k] * 입력t[i - k] for k in range(Lt) if i - k >= 0)
            for i in range(len(입력t))]
    걸린 = sum(1 for a in accs if not (-(1 << (qb - 1)) <= (a >> sh) <= (1 << (qb - 1)) - 1))
    # 파이프판은 **같은 판정을 한 칸 늦게** 내야 한다 (되먹임이 없어 자를 수 있다)
    찍tp = [int(ln.split()[1]) for ln in
           돌리기(eqrtl.ffe_tbl(Lt, 창t, qb, sh, W=7, DW=7, 파이프=True),
                "ffe_tbl", 줄t, "d").splitlines() if ln.startswith("D ")]
    어긋tp = [(i, 찍tp[i], 기대t[i - 2]) for i in range(Lt + 3, min(len(찍tp), len(기대t)))
             if 찍tp[i] != 기대t[i - 2]]
    ok(not 어긋tp, f"**파이프 FFE+표가 같은 판정을 한 칸 늦게 낸다** ({len(찍tp)}개)"
       if not 어긋tp else f"파이프 FFE+표가 {len(어긋tp)}개 어긋났다: {어긋tp[:3]}")
    같은칸t = sum(1 for i in range(Lt + 3, min(len(찍tp), len(기대t)))
                 if 찍tp[i] == 기대t[i - 1])
    센칸t = len(range(Lt + 3, min(len(찍tp), len(기대t))))
    ok(같은칸t < 센칸t,
       f"**실제로 한 칸 늦다** (민판 정렬로는 {같은칸t}/{센칸t}) -- 다 맞으면 "
       "레지스터가 안 들어간 것이다")

    ok(len(accs) // 10 < 걸린 < len(accs) * 9 // 10,
       f"**죔쇠가 걸리기도 하고 안 걸리기도 한다** ({걸린}/{len(accs)}) -- 전부 걸리면 "
       "범위 안 산술을 안 재는 것이고, 하나도 안 걸리면 죔쇠를 안 재는 것이다")
    최대acc = max(abs(a) for a in acc들)
    ok(최대acc > (1 << 11) - 1,
       f"**되먹임이 acc 를 x 폭 밖으로 민다** (|acc| 최대 {최대acc} > 2047) "
       "-- 안 밀면 누산기 폭을 재는 것이 아니다")

print("\n[누산기 폭 -- 학습된 계수는 구석에 안 간다]")
# **여기가 조용히 초록이던 자리다.** `ZW` 를 XW+WW 로 좁혀도 위 검사는 다 통과했다 --
# 학습된 가중치가 작아서 자극이 넘칠 만큼 안 갔기 때문이다. 폭 주장은 최악값에 대한
# 것이므로 **최악값을 직접 먹여야** 재는 것이 된다.
if not all(shutil.which(t) for t in ("iverilog", "vvp")):
    ok(True, "건너뜀: iverilog/vvp 가 없다")
else:
    창2, 은닉2, 프랙2, 폭2 = 5, 2, 4, 7
    큰 = (1 << (폭2 - 1)) - 1                       # 63
    극 = {"W1": np.full((창2, 은닉2), 큰, dtype=np.int64),
         "b1": np.full(은닉2, 큰, dtype=np.int64),
         "W2": np.full((은닉2, 1), 큰, dtype=np.int64),
         "b2": np.array([큰], dtype=np.int64)}
    # **끝값만 번갈아 넣으면 안 걸린다.** 처음에는 ±큰 만 넣었는데, z 가 20853 까지
    # 가도 `ZW` 를 좁힌 회로가 통과했다 -- 14비트로 감긴 값(+4469)이 여전히 양수라
    # hardtanh 가 어차피 +한계로 눌러 같은 답이 나왔기 때문이다. **감기가 부호를
    # 뒤집는 자리**를 지나야 한다. 그러려면 z 가 구석이 아니라 그 사이를 훑어야 한다.
    스트림2 = [((i * 7) % (2 * 큰 + 1)) - 큰 for i in range(120)]
    X극 = np.array([[스트림2[max(0, i - (창2 - 1 - j))] for j in range(창2)]
                   for i in range(len(스트림2))], dtype=np.int64)
    기준2 = nnfix.누산기(극, X극, 프랙2, 반올림=False)
    판2 = tempfile.mkdtemp(prefix="nnrtl-극-")
    try:
        (Path(판2) / "dut.v").write_text(
            eqrtl.nn(창2, 은닉2, XW=폭2, WW=폭2, FRAC=프랙2), encoding="utf-8")
        주소폭2 = eqrtl.주소폭(eqrtl.계수수(창2, 은닉2))
        tb2 = ["`timescale 1ns/1ps", "module tb;",
               "  reg clk=0, rst_n=0, cw_we=0;",
               f"  reg [{주소폭2 - 1}:0] cw_addr=0;",
               f"  reg signed [{폭2 - 1}:0] cw_data=0;",
               f"  reg signed [{폭2 - 1}:0] x=0;",
               "  wire d;",
               "  nneq_eq dut(.clk(clk),.rst_n(rst_n),.x(x),.cw_we(cw_we),"
               ".cw_addr(cw_addr),.cw_data(cw_data),.d(d));",
               "  always #5 clk = ~clk;", "  initial begin",
               "    @(negedge clk); rst_n = 1;"]
        for a, v in enumerate(eqrtl.계수싣기(극)):
            tb2.append(f"    @(negedge clk); cw_we=1; cw_addr={a}; cw_data={v};")
        tb2.append("    @(negedge clk); cw_we=0;")
        for v in 스트림2:
            tb2.append(f"    @(negedge clk); x = {v};")
            tb2.append('    @(posedge clk); #1 $display("D %0d", dut.y);')
        tb2 += ["    $finish;", "  end", "endmodule"]
        (Path(판2) / "tb.v").write_text("\n".join(tb2), encoding="utf-8")
        subprocess.run(["iverilog", "-g2012", "-o", "a.out", "dut.v", "tb.v"],
                       cwd=판2, capture_output=True, text=True, timeout=180)
        난줄2 = subprocess.run(["vvp", "a.out"], cwd=판2, capture_output=True,
                             text=True, timeout=180).stdout
    finally:
        shutil.rmtree(판2, ignore_errors=True)
    찍힌2 = [int(ln.split()[1]) for ln in 난줄2.splitlines() if ln.startswith("D ")]
    어긋2 = [(i, 찍힌2[i], int(기준2[i]))
            for i in range(창2 - 1, min(len(찍힌2), len(기준2)))
            if 찍힌2[i] != int(기준2[i])]
    ok(len(찍힌2) > 100, f"극단 자극에서 RTL 이 {len(찍힌2)} 줄 냈다")
    # **y 가 아니라 z 를 본다.** hardtanh 가 y 를 눌러 놓으므로 y 는 극단을 먹여도
    # 안 넘친다 -- y 만 보고 "구석을 훑었다" 고 하면 그것이 거짓 초록이다.
    z극 = nnfix.속내(극, X극, 프랙2, 반올림=False)[0]
    ok(int(np.abs(z극).max()) > (1 << (폭2 + 폭2 - 1)),
       f"**자극이 실제로 XW+WW 를 넘긴다** (|z| 최대 {int(np.abs(z극).max())} > "
       f"{1 << (폭2 + 폭2 - 1)}) -- 안 넘으면 누산기 폭을 재는 것이 아니다")
    ok(not 어긋2, f"극단 계수에서도 누산기가 같다 ({len(찍힌2)}개)" if not 어긋2
       else f"극단에서 {len(어긋2)}개 어긋났다: {어긋2[:3]}")

print("\n[배선 -- 물려 놓고 쓰라고 안 하면 안 쓴다]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok("def eq_area(" in 도구글, "bot_tools 에 eq_area")
ok("eq_area" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], "ADMIN_TOOLS 에")
ok("eq_area" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0], "PUBLIC_TOOLS 에")
ok("eq_area" in (뿌리 / "eda_prompt.py").read_text(encoding="utf-8"), "갈래규칙에 있다")
ok('- "nnfix.py"' in 배포 and '- "eqrtl.py"' in 배포,
   "**nnfix.py · eqrtl.py 가 배포 paths 에 있다**")
# 도구 설명이 **왜 비트 일치가 먼저인지**를 말하는가 -- 그것이 이 도구의 존재 이유다
잘린 = 도구글[도구글.index("def eq_area("):도구글.index("def ip_signoff(")]
ok("bit-exact" in 잘린, "도구 설명이 비트 일치를 말한다")
ok("smallest" in 잘린, "제일 작은 회로가 틀린 회로라는 것을 적는다")
ok("2,368" in 잘린 and "1,835" in 잘린, "잰 숫자를 든다")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개 -- {FAIL_목록}")
    sys.exit(1)
print("nnfix/eqrtl: 정수부 2 · 소수부 4 가 바닥이고 · RTL 이 기준모델과 "
      "누산기까지 같고 · 견줄 선형 쪽도 맞는 답을 낸다 -- 통과")
