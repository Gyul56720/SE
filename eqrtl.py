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

    설계                          곱셈      LC     Fmax      판정
    DFE 4탭 W8                     0      210   69.82 MHz  PASS
    DFE 8탭 W8                     0      438   36.54 MHz  FAIL
    FFE 5탭 W7 DW6                 5      802   69.24 MHz  PASS
    FFE 11탭 W7 DW6               11    1,835   56.11 MHz  PASS
    FFE 11탭 W7 DW7               11    2,237   52.38 MHz  PASS
    **FFE11+DFE8 합친 것 DW6**    11    2,559   22.83 MHz  FAIL
    **FFE11+DFE8 합친 것 DW7**    11    2,999   22.63 MHz  FAIL
    NN 5->2  Q2.4  7비트          12    2,368   30.58 MHz  FAIL
    NN 5->2  Q2.5  8비트          12    3,011   28.08 MHz  FAIL
    NN 5->2  Q3.6 10비트          12    4,498   26.20 MHz  FAIL
    NN 5->4  Q2.4  7비트          24    4,636   26.73 MHz  FAIL
    NN 11->2 Q2.4  7비트          24    4,762   26.01 MHz  FAIL
    NN 9->4  Q2.4  7비트          40    7,915       --     칩 밖 (103%)

## 따로 재서 더하면 틀린다 -- 실측 2026-09-16

앞선 판은 FFE(1,835)와 DFE(438)를 따로 재서 **2,273 LC** 라고 적었다. 합쳐서 재니
**2,559 LC (DW6)** 다 -- 더한 값이 **11% 작다.** Fmax 는 더 크게 어긋난다: 따로 재면
56.1 과 36.5 라 "36.5" 로 읽히는데, 합친 것은 **22.8 MHz** 다.

까닭은 구조다. 합치면 FFE 의 17비트 누산과 DFE 의 여덟 단 덧셈이 **한 조합 경로에
직렬로 들어가고**, 누산기도 한 비트 깊어진다. 슬라이서가 하나로 주는 이득보다 이쪽이
크다. **따로 잰 두 수를 더한 값은 과소도 과대도 아닌 다른 물건이다.**

그리고 공정성 문제가 하나 더 있었다. 워드 길이 실측의 결론은 **계수 7비트 · ADC
7비트** 였는데 위 FFE 는 데이터 폭을 6 으로 뒀다 -- 선형 쪽에 제 결론보다 싼 데이터
경로를 준 셈이다. 7 로 맞추면 합친 것이 **2,999 LC · 22.63 MHz** 다.

그래서 같은 조건(둘 다 완결된 단일 모듈, 출력이 판정 한 비트, 데이터 7비트)에서:

    선형 FFE11+DFE8   2,999 LC   22.63 MHz   BER 2.34e-02
    NN 5->2 Q2.4      2,368 LC   30.58 MHz   BER 3.69e-03
                      **21% 작고 · 1.35배 빠르고 · BER 6.96배 좋다**

## 곱셈기 값은 폭의 제곱과 **맞는다** (단정하지는 않는다)

    Q2.4  7비트  2,368 LC      8²/7²  = 1.306   잰 값 3,011/2,368 = 1.272
    Q2.5  8비트  3,011 LC     10²/8²  = 1.563   잰 값 4,498/3,011 = 1.494
    Q3.6 10비트  4,498 LC

세 점 다 제곱 예측보다 3~4% 낮다. 점이 셋뿐이라 지수를 맞춰 정하지는 못하고,
**제곱 축척과 어긋나지 않는다**까지가 이 측정이 받치는 말이다.

## 그 밖에 읽히는 것 둘

*하나 -- 자릿수가 면적의 절반이다.* 같은 망이 Q3.6 10비트에서 4,498 LC, Q2.4
7비트에서 2,368 LC 다. BER 은 float 대비 0.98 배와 1.00 배로 **같다**(nnfix 머리말).

*둘 -- 판정 되먹임은 곱셈이 하나도 없다.* NRZ 판정이 ±1 뿐이라 되먹임은 계수를
더하거나 빼는 것이다. 그래서 DFE 8탭이 438 LC 로 FFE 5탭(802 LC)보다 작다.
**등화기에서 제일 싼 탭은 DFE 탭이다.** 다만 그 여덟 단이 한 사이클에 직렬로 들어가
Fmax 를 36.5 MHz 로 끌어내리고, 합치면 22.6 까지 간다.

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


FFEDFE = r"""
module ffe_dfe (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire signed [{DW}-1:0] x,
    input  wire                   cw_we,
    input  wire [{AW}-1:0]        cw_addr,
    input  wire signed [{CW}-1:0] cw_data,
    output reg                    d
);
    localparam L     = {L};        // FFE 탭
    localparam NT    = {NT};       // DFE 탭
    localparam DEPTH = {DEPTH};
    localparam DW    = {DW};
    localparam CW    = {CW};
    localparam AW    = {AW};
    localparam FW    = {FW};       // FFE 누산기
    localparam TW    = {TW};       // 합친 누산기

    reg signed [DW-1:0] sr   [0:L-1];
    reg                 hist [0:DEPTH-1];
    // **계수가 한 주소 공간에 있다.** 0..L-1 이 FFE, L..L+NT-1 이 DFE 다.
    reg signed [CW-1:0] coef [0:{NCO}-1];

    wire signed [CW+DW-1:0] prod [0:L-1];
    genvar i;
    generate
        for (i = 0; i < L; i = i + 1) begin : taps
            assign prod[i] = coef[i] * sr[i];
        end
    endgenerate

    integer k;
    reg signed [FW-1:0] accf;
    reg signed [TW-1:0] acc;
    always @* begin
        accf = 0;
        for (k = 0; k < L; k = k + 1)
            accf = accf + $signed({{{{(FW-CW-DW){{prod[k][CW+DW-1]}}}}, prod[k]}});
        acc = $signed({{{{(TW-FW){{accf[FW-1]}}}}, accf}});
{합산}
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < L; k = k + 1) sr[k] <= 0;
            for (k = 0; k < DEPTH; k = k + 1) hist[k] <= 1'b0;
            for (k = 0; k < {NCO}; k = k + 1) coef[k] <= 0;
            d <= 1'b0;
        end else begin
            if (cw_we) coef[cw_addr] <= cw_data;
            sr[0] <= x;
            for (k = 1; k < L; k = k + 1) sr[k] <= sr[k-1];
            for (k = DEPTH-1; k > 0; k = k - 1) hist[k] <= hist[k-1];
            hist[0] <= d;
            d <= ~acc[TW-1];
        end
    end
endmodule
"""


def ffe_dfe(ffe탭: int = 11, dfe자리=(1, 2, 3, 4, 5, 6, 7, 8), W: int = 7,
            DW: int = 6, WD: int = 8) -> str:
    """FFE 와 DFE 를 **한 모듈로** 합친 것. `top` 은 `ffe_dfe`.

    ## 왜 따로 잰 것을 더하면 안 되나 -- 실측 2026-09-16

    앞선 판은 FFE(1,835 LC)와 DFE(438 LC)를 따로 재서 2,273 LC 라고 적었다. 그 값은
    **둘 다 과소도 과대도 아닌 다른 물건**이다. 따로 재면 FFE 가 출력 포트 17비트를,
    DFE 가 입력 포트 12비트를 각자 물고 있는데 합치면 그 사이가 **내부 배선**이 되고,
    슬라이서도 하나만 남는다. 반대로 누산기는 한 단 더 깊어진다.

    `W` 와 `WD` 를 따로 두는 것은 실측을 따른 것이다 -- 계수는 7비트, DFE 탭은 8비트가
    바닥이었다(논문 표 3 · 4단계).
    """
    자리 = [int(p) for p in dfe자리]
    L, NT = int(ffe탭), len(자리)
    깊이 = max(max(자리) - 1, 1)
    cw = max(int(W), int(WD))                 # 계수 램 한 칸의 폭
    FW = int(W) + int(DW) + 주소폭(L + 1)
    TW = max(FW, int(WD) + 주소폭(NT + 1)) + 1

    def 어디(p):
        return "d" if p == 1 else f"hist[{p - 2}]"
    합산 = "\n".join(
        f"        acc = {어디(p)} ? (acc - $signed(coef[{L + i}]))"
        f" : (acc + $signed(coef[{L + i}]));"
        for i, p in enumerate(자리))
    return FFEDFE.format(L=L, NT=NT, DEPTH=깊이, DW=int(DW), CW=cw,
                         AW=주소폭(L + NT), FW=FW, TW=TW,
                         NCO=L + NT, 합산=합산)
