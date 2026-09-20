"""**층 파이프라인.** 계층 복호가 파이프라인에서 몇 사이클에 도나 -- 그리고 그 회로.

`spec/IP_5G_LDPC복호기.md` 의 병목이 여기 있다. 층 m+1 은 층 m 이 갱신한 L 을 받아
쓰므로, 파이프라인을 깊이 D 로 파면 같은 열을 건드리는 층끼리 읽기-쓰기 해저드가 난다.

## 세 길로 같은 수를 구한다 (독립 대조)

    1. 조합 공식   `멈춤수()`  -- 시뮬 없이 기저행렬에서 센다
    2. 사이클 모형 `사이클모형()` -- 발행 시각을 실제로 굴린다
    3. RTL 시뮬    스톨 제어기를 iverilog 로 돌린다

**1 은 상한이다.** 앞선 멈춤이 이미 간격을 벌려 놓으면 뒤에서는 덜 멈춰도 되는데,
공식은 그것을 안 본다. 그래서 1 >= 2 여야 하고, 2 == 3 이어야 한다.
이 셋이 어긋나면 어느 하나가 틀린 것이다.

## 스톨 제어기가 하는 일

날아다니는 층마다 **어느 열을 건드리는지**를 비트맵으로 들고 있다가, 다음 층의
비트맵과 겹치면 멈춘다. 열 68개(BG1)면 층당 68비트, 깊이 4면 레지스터 3벌.
"""
from __future__ import annotations

import nrldpc as F


def 층비트맵(부: "F.부호 | str") -> "list[int]":
    """층마다 '어느 기저열을 건드리나' 를 비트맵으로."""
    if isinstance(부, str):
        표 = F.기저행렬(부)
        R = max(r for r, _ in 표) + 1
        맵 = [0] * R
        for (r, c) in 표:
            맵[r] |= 1 << c
        return 맵
    return [int(sum(1 << int(j) for j in js)) for js, _ in 부.층]


def 공식멈춤(맵: "list[int]", 깊이: int, 순서=None) -> int:
    """**상한.** 앞선 멈춤이 벌려 놓은 간격을 안 본다."""
    순서 = list(range(len(맵))) if 순서 is None else list(순서)
    s = 0
    for i in range(len(순서)):
        w = 0
        for back in range(1, int(깊이)):
            j = i - back
            if j < 0:
                break
            if 맵[순서[i]] & 맵[순서[j]]:
                w = max(w, int(깊이) - back)
        s += w
    return s


def 사이클모형(맵: "list[int]", 깊이: int, 순서=None) -> dict:
    """발행 시각을 실제로 굴린다. 층 j 를 건드린 층은 `j + 깊이` 전에는 못 나간다."""
    순서 = list(range(len(맵))) if 순서 is None else list(순서)
    n, D = len(순서), int(깊이)
    t = [0] * n
    for i in range(n):
        ti = t[i - 1] + 1 if i else 0
        for j in range(i):
            if 맵[순서[i]] & 맵[순서[j]]:
                ti = max(ti, t[j] + D)
        t[i] = ti
    총 = t[-1] + D
    이상 = (n - 1) + D
    return {"발행시각": t, "총사이클": 총, "이상사이클": 이상,
            "멈춤": t[-1] - (n - 1), "손실%": round((총 - 이상) / 총 * 100, 2)}


# ---------------------------------------------------------------- RTL
def 스톨제어기(열수: int, 깊이: int, 층수: int, 맵: "list[int]") -> str:
    """층 순서를 돌며 해저드가 있으면 멈추는 제어기. 멈춘 사이클을 세어 내보낸다.

    회로가 하는 일은 **비트맵 AND** 하나다 -- 날아다니는 층 (깊이-1) 벌과 견준다.
    """
    나 = "\n"
    W = int(열수)
    줄 = [f"// 층 파이프라인 스톨 제어기  열수={W} 깊이={깊이} 층수={층수}",
          "module stallctl (",
          "  input  wire clk, input wire rst,",
          "  output reg  done,",
          "  output reg  [31:0] cycles,",
          "  output reg  [31:0] stalls",
          ");"]
    줄.append(f"  localparam integer NL = {층수};")
    줄.append(f"  localparam integer D  = {깊이};")
    줄.append(f"  reg [{W-1}:0] MAP [0:NL-1];")
    줄.append("  integer i;")
    줄.append("  initial begin")
    for i, m in enumerate(맵):
        줄.append(f"    MAP[{i}] = {W}'h{m:0{(W+3)//4}x};")
    줄.append("  end")
    # 날아다니는 층의 비트맵 (깊이-1 벌) -- 0 이면 빈 자리
    for k in range(1, int(깊이)):
        줄.append(f"  reg [{W-1}:0] fly{k};")
    줄.append("  reg [31:0] idx;")
    줄.append(f"  wire [{W-1}:0] nxt = (idx < NL) ? MAP[idx] : {W}'b0;")
    겹 = " | ".join(f"|(nxt & fly{k})" for k in range(1, int(깊이)))
    줄.append(f"  wire hazard = (idx < NL) && ({겹});")
    줄.append("  always @(posedge clk) begin")
    줄.append("    if (rst) begin")
    줄.append("      idx <= 0; cycles <= 0; stalls <= 0; done <= 1'b0;")
    for k in range(1, int(깊이)):
        줄.append(f"      fly{k} <= 0;")
    줄.append("    end else if (!done) begin")
    줄.append("      cycles <= cycles + 1;")
    줄.append("      if (hazard) begin")
    줄.append("        stalls <= stalls + 1;")
    for k in range(int(깊이) - 1, 1, -1):
        줄.append(f"        fly{k} <= fly{k-1};")
    if int(깊이) > 1:
        줄.append(f"        fly1 <= 0;                       // 거품")
    줄.append("      end else begin")
    for k in range(int(깊이) - 1, 1, -1):
        줄.append(f"        fly{k} <= fly{k-1};")
    if int(깊이) > 1:
        줄.append("        fly1 <= nxt;")
    줄.append("        idx  <= idx + 1;")
    줄.append("      end")
    줄.append("      if (idx == NL && " + " && ".join(f"fly{k} == 0" for k in range(1, int(깊이))) + ") done <= 1'b1;")
    줄.append("    end")
    줄.append("  end")
    줄.append("endmodule")
    return 나.join(줄) + 나


def 벤치(기대멈춤: int, 기대사이클: int = None) -> str:
    나 = "\n"
    줄 = ["`timescale 1ns/1ps", "module tb;",
          "  reg clk = 0, rst = 1; wire done; wire [31:0] cycles, stalls;",
          "  stallctl dut(.clk(clk), .rst(rst), .done(done), .cycles(cycles), .stalls(stalls));",
          "  always #5 clk = ~clk;",
          "  integer guard = 0;",
          "  initial begin",
          "    @(negedge clk); rst = 0;",
          "    while (!done && guard < 100000) begin @(posedge clk); guard = guard + 1; end",
          f"    if (stalls === {기대멈춤}) $display(\"PASS stalls=%0d cycles=%0d\", stalls, cycles);",
          f"    else $display(\"FAIL stalls=%0d expected={기대멈춤} cycles=%0d\", stalls, cycles);",
          "    $finish;", "  end", "endmodule"]
    return 나.join(줄) + 나
