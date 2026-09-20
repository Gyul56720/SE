"""**LDPC 검사노드(CNU) Verilog.** `nrldpcfix` 와 비트까지 같아야 한다.

계층 min-sum 의 알맹이다. 층 하나를 도는 비용의 대부분이 여기 있다.

    들어오는 것   Q_0 .. Q_{D-1}   (부호 W 비트)
    나가는 것     R_i = alpha * (prod_j sign(Q_j)) * sign(Q_i) * (i 가 최소면 min2, 아니면 min1)

## 동점은 답을 안 바꾼다 -- 확인하고 나서 간단히 썼다

`a_i <= min1` 인 자리를 전부 "최소" 로 쳐도 된다. 동점이면 `min2 == min1` 이라
어느 쪽을 골라도 같은 값이 나오기 때문이다. 그래서 골든의 `argsort` 가 동점에서
무엇을 고르든 RTL 과 안 어긋난다. (안 그랬으면 정렬의 안정성까지 맞춰야 했다.)

## 이 판의 거짓 초록

**합성해서 LC 를 보고하고는 그것이 맞는 답을 내는지 안 보는 것.** 면적은 아무
회로나 내놓을 수 있다 -- 틀린 회로가 제일 작다. 그래서 `tests/test_ldpcrtl.py` 가
`nrldpcfix` 의 정수값과 **한 값씩** 맞춰 본다(부호만 보지 않는다).
"""
from __future__ import annotations

import numpy as np

import nrldpcfix as X


def cnu(D: int = 4, W: int = 6, 분자: int = 3, 분모비트: int = 2) -> str:
    """검사노드 하나. 조합회로 -- 층 파이프라인은 이것을 감싼다."""
    나 = "\n"
    입력 = ", ".join(f"q{i}" for i in range(D))
    출력 = ", ".join(f"r{i}" for i in range(D))
    줄 = [
        f"// CNU  D={D} W={W} alpha={분자}/{1<<분모비트}   nrldpcfix 와 비트일치",
        f"module cnu #(parameter W={W}) (",
        f"  input  signed [W-1:0] {입력},",
        f"  output signed [W-1:0] {출력}",
        ");",
    ]
    for i in range(D):
        줄.append(f"  wire signed [W-1:0] a{i} = q{i}[W-1] ? -q{i} : q{i};   // |Q|")
    줄.append(f"  wire s_all = " + " ^ ".join(f"q{i}[W-1]" for i in range(D)) + ";")
    # 최소 1 · 2 를 비교기 나무로
    줄.append("  // 최소 두 개 -- 짝지어 올린다")
    cur = [f"a{i}" for i in range(D)]
    단 = 0
    lo, hi = [], []
    while len(cur) > 1:
        새 = []
        for k in range(0, len(cur) - 1, 2):
            x, y = cur[k], cur[k + 1]
            L, H = f"lo{단}_{k}", f"hi{단}_{k}"
            줄.append(f"  wire signed [W-1:0] {L} = ({x} < {y}) ? {x} : {y};")
            줄.append(f"  wire signed [W-1:0] {H} = ({x} < {y}) ? {y} : {x};")
            새.append(L)
            hi.append(H)
        if len(cur) % 2:
            새.append(cur[-1])
        lo = 새
        cur = 새
        단 += 1
    줄.append(f"  wire signed [W-1:0] min1 = {cur[0]};")
    # min2 = 후보들(탈락한 hi 들과 마지막까지 안 뽑힌 lo 들) 중 최소
    후보 = hi[:]
    if len(후보) == 0:
        줄.append("  wire signed [W-1:0] min2 = min1;")
    else:
        앞 = 후보[0]
        for n, c in enumerate(후보[1:], 1):
            줄.append(f"  wire signed [W-1:0] m2_{n} = ({앞} < {c}) ? {앞} : {c};")
            앞 = f"m2_{n}"
        줄.append(f"  wire signed [W-1:0] min2 = {앞};")
    for i in range(D):
        줄.append(f"  wire [W-1:0] mag{i} = (a{i} <= min1) ? min2 : min1;")
        # mag 는 비음수다. 곱은 W+분모비트 비트면 넘치지 않는다 -- 남는 비트를 안 만든다
        줄.append(f"  wire [W+{분모비트-1}:0] pr{i} = mag{i} * {분자};")
        줄.append(f"  wire signed [W-1:0] sc{i} = pr{i}[W+{분모비트-1}:{분모비트}];")
        줄.append(f"  wire neg{i} = s_all ^ q{i}[W-1];")
        줄.append(f"  assign r{i} = neg{i} ? -sc{i} : sc{i};")
    줄.append("endmodule")
    return 나.join(줄) + 나


def 골든CNU(q: np.ndarray, 분자: int = 3, 분모비트: int = 2) -> np.ndarray:
    """`nrldpcfix.복호` 안의 검사노드와 **같은 식**. 여기만 떼어 쓴다."""
    q = np.asarray(q, dtype=np.int64)
    a = np.abs(q)
    순 = np.argsort(a)
    최소1, 최소2 = a[순[0]], (a[순[1]] if len(q) > 1 else a[순[0]])
    부호 = np.where(q >= 0, 1, -1)
    부호곱 = int(np.prod(부호))
    크기 = np.where(np.arange(len(q)) == 순[0], 최소2, 최소1)
    return X.정규화(부호곱 * 부호 * 크기, 분자, 분모비트)


def 테스트벤치(D: int = 4, W: int = 6, 벡터수: int = 300, 씨: int = 0,
           분자: int = 3, 분모비트: int = 2) -> "tuple[str,int]":
    """골든이 낸 값을 그대로 박은 벤치. **틀리면 어느 벡터에서 무엇이 달랐는지 찍는다.**"""
    rng = np.random.default_rng(씨)
    한계 = (1 << (W - 1)) - 1
    벡 = rng.integers(-한계, 한계 + 1, size=(벡터수, D))
    기대 = np.array([골든CNU(v, 분자, 분모비트) for v in 벡])
    나 = "\n"
    줄 = ["`timescale 1ns/1ps", "module tb;", f"  localparam integer W = {W};",
          f"  localparam integer D = {D};", f"  localparam integer N = {벡터수};"]
    for i in range(D):
        줄.append(f"  reg  signed [W-1:0] q{i};")
        줄.append(f"  wire signed [W-1:0] r{i};")
        줄.append(f"  reg  signed [W-1:0] e{i};")
    줄.append(f"  cnu #(.W(W)) dut ({', '.join(f'.q{i}(q{i})' for i in range(D))}, "
              f"{', '.join(f'.r{i}(r{i})' for i in range(D))});")
    줄.append("  integer k; integer bad = 0;")
    줄.append(f"  reg signed [W-1:0] QV [0:N*D-1];")
    줄.append(f"  reg signed [W-1:0] EV [0:N*D-1];")
    줄.append("  initial begin")
    for n in range(벡터수):
        for i in range(D):
            줄.append(f"    QV[{n*D+i}] = {int(벡[n][i])}; EV[{n*D+i}] = {int(기대[n][i])};")
    줄.append("    for (k = 0; k < N; k = k + 1) begin")
    for i in range(D):
        줄.append(f"      q{i} = QV[k*D+{i}]; e{i} = EV[k*D+{i}];")
    줄.append("      #1;")
    for i in range(D):
        줄.append(f"      if (r{i} !== e{i}) begin bad = bad + 1;")
        줄.append(f'        $display("FAIL vec=%0d out=%0d got=%0d exp=%0d", k, {i}, r{i}, e{i}); end')
    줄.append("    end")
    줄.append('    if (bad == 0) $display("PASS %0d vectors x %0d outputs", N, D);')
    줄.append('    else $display("FAIL %0d mismatches", bad);')
    줄.append("    $finish;")
    줄.append("  end", )
    줄.append("endmodule")
    return 나.join(줄) + 나, 벡터수
