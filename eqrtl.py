"""등화기 **Verilog** -- 신경망과, 견줄 상대인 선형 FFE·DFE.

신경망 쪽은 `nnfix.누산기` 와 비트까지 같아야 한다.

주제의 5단계. 여기서 제일 큰 거짓 초록은 **합성해서 LC 를 보고하고는 그것이 맞는 답을
내는지 안 보는 것**이다. 면적은 아무 회로나 내놓을 수 있다 -- 틀린 회로가 제일 작다.
그래서 `tests/test_nnfix.py` 가 이 모듈이 낸 Verilog 를 실제로 돌려 `nnfix` 의
누산기 정수값과 **한 값씩** 맞춰 본다(부호만 보지 않는다).

## 곱셈기 폭을 안 맞추면 면적이 거짓말을 한다 -- 실측 2026-09-16

첫 판은 모든 항을 32비트로 부호확장해 곱했다. **비트까지는 맞았다.** 그런데
"곱셈 12개가 FFE 의 11개보다 2.8배 크다" 가 나왔다 -- 망 때문이 아니라 10x10
짜리 곱을 32x32 로 시킨 때문이다. **맞는 답을 내는 회로도 면적은 틀릴 수 있다.**
비트 일치는 면적이 뜻을 갖기 위한 필요조건이지 충분조건이 아니다.

누산기는 넘치지 않을 만큼만 잡으므로 **잘리는 자리가 없고 결과가 안 바뀐다** --
그것도 비트 일치로 확인한다(`tests/test_nnfix.py`).

    prod = XW + WW                  7x7 -> 14
    z    = prod + ceil(log2(L+1))   L 개를 더해도 안 넘친다
    h    = FRAC + 2                 +-(1<<FRAC) 가 들어가는 제일 좁은 부호 폭
    y    = HW + WW + ceil(log2(H+1))

## 재 놓은 면적과 Fmax -- iCE40 HX8K, 목표 50 MHz, yosys + nextpnr

    설계                     곱셈      LC     Fmax      판정
    DFE 4탭 W8                0      210   69.82 MHz  PASS
    DFE 8탭 W8                0      438   36.54 MHz  FAIL
    FFE 5탭 W7                5      802   69.24 MHz  PASS
    FFE 11탭 W7              11    1,835   56.11 MHz  PASS
    NN 5->2  Q2.4  7비트     12    2,368   30.58 MHz  FAIL
    NN 5->2  Q2.5  8비트     12    3,011   28.08 MHz  FAIL
    NN 5->2  Q3.6 10비트     12    4,498   26.20 MHz  FAIL
    NN 5->4  Q2.4  7비트     24    4,636   26.73 MHz  FAIL
    NN 11->2 Q2.4  7비트     24    4,762   26.01 MHz  FAIL
    NN 9->4  Q2.4  7비트     40    7,915       --     칩 밖 (103%)

네 가지가 읽힌다.

*하나 -- 자릿수가 면적의 절반이다.* 같은 망이 Q3.6 10비트에서 4,498 LC, Q2.4
7비트에서 2,368 LC 다. BER 은 float 대비 0.98 배와 1.00 배로 **같다**(nnfix 머리말).
자릿수를 안 재고 넉넉히 잡는 것만으로 면적이 1.9배가 된다.

*둘 -- 곱셈 하나당 값은 선형과 거의 같다.* NN 은 2,368/12 = 197 LC, FFE 는
1,835/11 = 167 LC. iCE40 에는 곱셈기가 없어 LUT 로 짓고, 그 값은 폭의 제곱을
따른다(7 -> 8비트에서 2,368 -> 3,011, +27%; 8²/7² = 1.31). **망이라서 비싼 것이
아니라 곱셈이 비싸다.** 그래서 곱셈 수가 곧 면적이다 -- 12 · 24 · 40 개가
2,368 · 4,7xx · 7,915 LC 다.

*셋 -- 판정 되먹임은 곱셈이 하나도 없다.* NRZ 판정이 ±1 뿐이라 되먹임은 계수를
더하거나 빼는 것이다. 그래서 DFE 8탭이 438 LC 로 FFE 5탭(802 LC)보다 작다.
**등화기에서 제일 싼 탭은 DFE 탭이다.**

*넷 -- 지는 자리는 면적이 아니라 조합 경로다.* 50 MHz 에서 떨어지는 것이 NN 만이
아니다. **DFE 8탭도 36.5 MHz 로 떨어진다** -- 여덟 단 더하기가 한 사이클에 줄줄이
들어 있어서다. NN 은 곱셈 -> 시프트·클립 -> 곱셈 두 층이 한 경로에 있다. 둘 다
같은 병이고 고치는 법도 같다.

**층 사이에 레지스터를 한 단 넣으면(파이프라인) 풀린다** -- 등화기는 한 심볼에 한
결정을 내면 되므로 지연이 한 사이클 늘어도 처리율은 안 준다. 다만 DFE 는 다르다:
되먹임 고리라 지연을 넣으면 **되먹임 자체가 늦어져** 풀리지 않는다(unrolled DFE 가
현업의 답이다). 여기서는 둘 다 안 했다. **재지 않은 것을 됐다고 말하지 않는다.**

## 그래서 맞바꿈은 이렇다 -- 25dB · SNR 30dB · 압축 1.0 · 30만 비트 · 씨 6개

    선형 FFE11 + DFE8   BER 2.34e-02 [2.21, 2.47]   ~2,273 LC   36.5 MHz
    NN 5->2 Q2.4        BER 3.69e-03 [2.30, 5.47]    2,368 LC   30.6 MHz
    이득                6.96배 [4.21, 10.10]        면적 +4%    클럭 0.84배

**거의 같은 면적에 BER 7배, 대신 클럭 0.84배.** 둘 다 파이프라인 전이다.

선형 쪽 LC 는 두 모듈을 **따로 재서 더한 값**이다(2,273 = 1,835 + 438). 한 모듈로
합성하면 슬라이서가 붙고 배선이 공유되므로 그대로는 안 나온다 -- 더한 값이라고
적어 둔다.

## 선형 쪽도 여기 있다 -- 안 그러면 위 표를 아무도 다시 못 잰다

견줄 상대를 임시 디렉터리에만 두면, 표의 왼쪽 절반이 저장소에 없는 파일에서
나온 숫자가 된다. 이 저장소가 다섯 번 앓은 병이 바로 그것이다(#62 `law/bench.py`
없음). `ffe` · `dfe` 도 같이 둔다.

## 계수는 핀이 아니라 내부 레지스터다

계수를 최상위 포트로 빼면 iCE40 의 핀에 먼저 걸려 "칩에 안 들어간다" 가 나온다
(실측: FFE 29탭 x 7비트 = 203핀, SB_IO 90% 인데 LUT 는 61%). 실제 설계는 적응
엔진이 계수를 레지스터에 쓴다. 레지스터 면적까지 같이 세는 쪽이 정직하다.
"""
from __future__ import annotations

import numpy as np

NN = r'''
module nneq_eq (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire signed [{XW}-1:0]   x,
    input  wire                     cw_we,
    input  wire [{AW}-1:0]          cw_addr,
    input  wire signed [{WW}-1:0]   cw_data,
    output reg                      d
);
    localparam L    = {L};
    localparam H    = {H};
    localparam XW   = {XW};
    localparam WW   = {WW};
    localparam FRAC = {FRAC};
    localparam ZW   = {ZW};
    localparam YW   = {YW};
    localparam HW   = {HW};

    reg signed [XW-1:0] sr   [0:L-1];          // sr[0] 이 최신
    reg signed [WW-1:0] coef [0:{NCO}-1];

    integer k, j;
    reg signed [ZW-1:0] z  [0:H-1];
    reg signed [HW-1:0] h  [0:H-1];
    reg signed [YW-1:0] y;
    reg signed [ZW-1:0] zs;

    always @* begin
        for (j = 0; j < H; j = j + 1) begin
            z[j] = $signed({{{{(ZW-WW-FRAC){{coef[L*H+j][WW-1]}}}},
                           coef[L*H+j], {{FRAC{{1'b0}}}}}});
            for (k = 0; k < L; k = k + 1)
                z[j] = z[j] + $signed(sr[k]) * $signed(coef[k*H+j]);
            zs   = z[j] >>> FRAC;                       // 산술 우시프트(내림)
            h[j] = (zs >  {LIM}) ?  {LIM} :             // hardtanh
                   (zs < -{LIM}) ? -{LIM} : zs[HW-1:0];
        end
        y = $signed({{{{(YW-WW-FRAC){{coef[{B2}][WW-1]}}}},
                    coef[{B2}], {{FRAC{{1'b0}}}}}});
        for (j = 0; j < H; j = j + 1)
            y = y + $signed(h[j]) * $signed(coef[L*H+H+j]);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < L; k = k + 1) sr[k] <= 0;
            for (k = 0; k < {NCO}; k = k + 1) coef[k] <= 0;
            d <= 1'b0;
        end else begin
            if (cw_we) coef[cw_addr] <= cw_data;
            for (k = L-1; k > 0; k = k - 1) sr[k] <= sr[k-1];
            sr[0] <= x;
            d <= ~y[YW-1];
        end
    end
endmodule
'''


def 주소폭(n: int) -> int:
    b = 1
    while (1 << b) < max(int(n), 2):
        b += 1
    return b


def 계수수(창: int, 은닉: int) -> int:
    return 창 * 은닉 + 은닉 + 은닉 + 1


def nn(창: int = 5, 은닉: int = 2, XW: int = 7, WW: int = 7,
       FRAC: int = 4) -> str:
    """등화기 Verilog 한 벌. `top` 은 `nneq_eq`."""
    창, 은닉 = int(창), int(은닉)
    nco = 계수수(창, 은닉)
    HW = int(FRAC) + 2
    ZW = int(XW) + int(WW) + 주소폭(창 + 1)
    YW = HW + int(WW) + 주소폭(은닉 + 1)
    return NN.format(L=창, H=은닉, XW=int(XW), WW=int(WW), FRAC=int(FRAC),
                     LIM=1 << int(FRAC), ZW=ZW, YW=YW, HW=HW,
                     NCO=nco, AW=주소폭(nco), B2=창 * 은닉 + 2 * 은닉)


def 계수싣기(정수모: dict) -> "list[int]":
    """`nnfix.굳히기` 가 낸 정수 모델을 **RTL 의 주소 차례**로 편다.

    RTL 은 `sr[0]` 이 최신이고 `nneq.창만들기` 의 X 는 **0번 열이 제일 오래된 것**이다
    (`X[i,j] = 표본[i+j-앞뒤]`). 그러니 `sr[k]` 는 `X[i, L-1-k]` 에 해당하고,
    W1 의 행을 **뒤집어** 실어야 같은 값을 곱한다. 이 한 줄을 빠뜨려 처음 두 판이
    52% · 91% 로 어긋났다 -- 51% 도 100% 도 아닌 값이 나오면 대개 정렬 문제다.
    """
    W1 = np.asarray(정수모["W1"]); 창, 은닉 = W1.shape
    난것 = [int(W1[창 - 1 - k, j]) for k in range(창) for j in range(은닉)]
    난것 += [int(v) for v in np.ravel(정수모["b1"])]
    난것 += [int(v) for v in np.ravel(정수모["W2"])]
    난것 += [int(np.ravel(정수모["b2"])[0])]
    return 난것


FFE = r"""
module ffe (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire signed [{DW}-1:0] x,
    input  wire                   cw_we,
    input  wire [{AW}-1:0]        cw_addr,
    input  wire signed [{W}-1:0]  cw_data,
    output reg  signed [{YW}-1:0] y
);
    localparam L  = {L};
    localparam W  = {W};
    localparam DW = {DW};
    localparam YW = {YW};
    reg signed [DW-1:0] sr   [0:L-1];
    reg signed [W-1:0]  coef [0:L-1];
    wire signed [W+DW-1:0] prod [0:L-1];
    wire signed [YW-1:0]   ext  [0:L-1];
    genvar i;
    generate
        for (i = 0; i < L; i = i + 1) begin : taps
            assign prod[i] = coef[i] * sr[i];
            assign ext[i]  = {{{{(YW-W-DW){{prod[i][W+DW-1]}}}}, prod[i]}};
        end
    endgenerate
    integer k;
    reg signed [YW-1:0] acc;
    always @* begin
        acc = 0;
        for (k = 0; k < L; k = k + 1) acc = acc + ext[k];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < L; k = k + 1) begin sr[k] <= 0; coef[k] <= 0; end
            y <= 0;
        end else begin
            if (cw_we) coef[cw_addr] <= cw_data;
            sr[0] <= x;
            for (k = 1; k < L; k = k + 1) sr[k] <= sr[k-1];
            y <= acc;
        end
    end
endmodule
"""

DFE = r"""
module dfe_pos (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire signed [{XW}-1:0] x,
    input  wire                  cw_we,
    input  wire [{AW}-1:0]       cw_addr,
    input  wire signed [{W}-1:0] cw_data,
    output reg                   d
);
    localparam DEPTH = {DEPTH};
    localparam NT    = {NT};
    localparam W     = {W};
    localparam XW    = {XW};
    // **곱셈기가 없다.** NRZ 판정은 +-1 뿐이라 되먹임은 계수를 더하거나 빼는 것이다.
    // 지연 1 은 `d` 자신이다. `hist[0] <= d` 는 비봉쇄 대입이라 **한 박자 전** 것을
    // 담으므로, hist[0] 은 지연 2 다. 처음에 이것을 지연 1 로 읽어 되먹임이 통째로
    // 한 칸 밀렸다 -- 면적은 그대로였고 답만 틀렸다(검사로 잡았다).
    reg        hist [0:DEPTH-1];
    reg signed [W-1:0] coef [0:NT-1];
    integer k;
    // **누산기를 x 폭 + 계수 합만큼만 잡는다.** 넉넉히 잡으면 여덟 단 더하기가
    // 그만큼 긴 캐리 사슬이 되어 Fmax 가 그대로 깎인다 (실측: 23비트 33.3 MHz).
    reg signed [{TW}-1:0] acc;
    always @* begin
        acc = $signed(x);
{합산}
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < DEPTH; k = k + 1) hist[k] <= 1'b0;
            for (k = 0; k < NT; k = k + 1) coef[k] <= 0;
            d <= 1'b0;
        end else begin
            if (cw_we) coef[cw_addr] <= cw_data;
            for (k = DEPTH-1; k > 0; k = k - 1) hist[k] <= hist[k-1];
            hist[0] <= d;
            d <= ~acc[{TW}-1];
        end
    end
endmodule
"""


def ffe(탭: int = 11, W: int = 7, DW: int = 6) -> str:
    """선형 FFE. `top` 은 `ffe`. 곱셈 `탭` 개."""
    탭, W, DW = int(탭), int(W), int(DW)
    YW = W + DW + 주소폭(탭 + 1)
    return FFE.format(L=탭, W=W, DW=DW, YW=YW, AW=주소폭(탭))


def dfe(자리들=(1, 2, 3, 4, 5, 6, 7, 8), W: int = 8, XW: int = 12) -> str:
    """판정 되먹임. `top` 은 `dfe_pos`. **곱셈이 하나도 없다** -- ±1 이라 더하기·빼기다."""
    자리들 = [int(p) for p in 자리들]
    깊이 = max(자리들)
    # x 와 "계수 NT 개의 합" 을 둘 다 담는 제일 좁은 폭. 한 비트는 부호 자리다.
    TW = max(int(XW), int(W) + 주소폭(len(자리들) + 1)) + 1
    def 어디(p):
        return "d" if p == 1 else f"hist[{p - 2}]"
    합산 = "\n".join(
        f"        acc = {어디(p)} ? (acc - $signed(coef[{i}]))"
        f" : (acc + $signed(coef[{i}]));"
        for i, p in enumerate(자리들))
    return DFE.format(DEPTH=max(깊이 - 1, 1), NT=len(자리들), W=W, XW=XW, TW=TW,
                      AW=주소폭(len(자리들)), 합산=합산)
