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

## 표본 색인 표를 얹은 것 -- 실측 2026-09-16 (iCE40 HX8K, 목표 50 MHz)

    설계                          곱셈    LC     Fmax      BER(선형 대비)
    FFE 11탭 W7 DW7 (홀로)         11   2,237  52.38 PASS       --
    선형 FFE11+DFE8   민판         11   2,999  22.63 FAIL      1.00배
    선형 FFE11+DFE8   파이프        11   2,999  34.73 FAIL      1.00배
    NN 5->2 Q2.4      민판         12   2,368  30.58 FAIL      2.55배
    NN 5->2 Q2.4      파이프        12   2,336  47.87 FAIL      2.55배
    **FFE11+표2x4     민판**       11   3,047  26.62 FAIL    **7.98배**
    **FFE11+표2x4     파이프**      11   3,037  41.38 FAIL    **7.98배**
    FFE11+표2x5       파이프        11   5,497    --           6.86배
    MLP 창11은닉8                  96  ~19,000  칩 밖          5.80배

(BER 은 압축 1.0 · 압축뒤대역 0.35 · 30만 비트 · 씨 8개. 파이프판은 민판과 같은
판정을 한 칸 늦게 내므로 BER 이 같다 -- 검사가 그것을 붙든다.)

**읽히는 것 셋.**

*하나 -- 선형 기준선과 거의 같은 면적에 BER 8배다.* 3,037 대 2,999 LC 로 **+1.3%**
이고 클럭은 41.4 대 34.7 로 **1.19배 빠르다.** 되먹임 고리가 없어서다.

*둘 -- 면적을 맞춘 신경망보다 BER 이 3.1배 좋다.* NN 5->2(2,336 LC · 2.55배) 대
표(3,037 LC · 7.98배). 표가 30% 크고 클럭은 0.86배지만 BER 이 3.1배다. 그리고
**5.80배를 내는 곱셈 96개짜리 망은 이 칩에 안 들어간다**(약 19,000 LC).

*셋 -- 표는 공짜가 아니다.* 칸당 약 3.2 LC 라 256칸이 810 LC 다(DFE 8탭 762 LC 와
비슷하다). 칸을 늘리면 면적이 선형으로 늘고 BER 은 오히려 나빠진다(1,024칸 6.86배 ·
4,096칸 2.01배) -- **천장이 학습 데이터라서** 칸을 늘려도 안 찬다.

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

## 파이프라인 -- 재 봤다 (실측 2026-09-16)

앞 판은 "층 사이에 레지스터를 한 단 넣으면 풀린다" 를 **가설로** 적어 뒀다. 넣고 쟀다.

    설계                        민판              한 단 넣은 것        Fmax 변화
    NN 5->2  Q2.4    2,368 LC · 30.58 MHz   2,336 LC · 47.87 MHz   +56.5%
    NN 5->4  Q2.4    4,636 LC · 26.73 MHz   4,736 LC · 45.42 MHz   +69.9%
    선형 FFE11+DFE8  2,999 LC · 22.63 MHz   2,999 LC · 34.73 MHz   +53.5%

**방향은 맞았고 크기도 컸다.** 그런데 가설이 안 말한 것이 셋 나왔다.

*하나 -- 50 MHz 를 여전히 못 넘는다.* 제일 좋은 것이 47.87 이라 목표에 **4% 모자란다.**
"파이프라인하면 목표를 만족한다" 는 여전히 거짓이다. 한 단 더 넣어야 한다(안 쟀다).

*둘 -- 면적이 늘지 않았다. 5->2 는 오히려 32 LC 줄었다(-1.4%).* 레지스터를 더 넣었는데
작아진 것은, 조합 경로가 짧아지면서 배치·배선이 더 촘촘히 채웠기 때문으로 보인다.
**보인다까지가 이 측정이 받치는 말이다** -- 넷리스트를 뜯어 확인하지 않았다.

*셋 -- 선형 쪽도 같은 만큼 빨라진다(+53.5%).* 되먹임 고리 **밖**인 FFE 누산은 자를 수
있어서다. 고리 안(acc -> d -> hist)은 못 자른다. 그래서 두 설계의 간격은 그대로다:

    민판    30.58 / 22.63 = 1.35배
    파이프  47.87 / 34.73 = **1.38배**

*판정은 안 바뀐다.* `tests/test_nnfix.py` 가 파이프판이 민판과 **같은 판정을 한 칸 늦게**
내는지 본다. 그리고 **실제로 한 칸 늦은지도** 본다 -- 민판 정렬로 다 맞으면 레지스터가
안 들어간 것이므로, 그 검사가 없으면 `파이프=True` 가 무시돼도 초록이 난다.

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
{은닉레지선언}
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
            y = y + $signed({은닉원}[j]) * $signed(coef[L*H+H+j]);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < L; k = k + 1) sr[k] <= 0;
            for (k = 0; k < {NCO}; k = k + 1) coef[k] <= 0;
{은닉리셋}            d <= 1'b0;
        end else begin
            if (cw_we) coef[cw_addr] <= cw_data;
            for (k = L-1; k > 0; k = k - 1) sr[k] <= sr[k-1];
            sr[0] <= x;
{은닉갱신}            d <= ~y[YW-1];
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
       FRAC: int = 4, 파이프: bool = False) -> str:
    """등화기 Verilog 한 벌. `top` 은 `nneq_eq`.

    `파이프` 가 참이면 **은닉층 뒤에 레지스터를 한 단** 넣는다. 조합 경로가
    `sr -> 곱셈 L개 -> 덧셈 -> 시프트·클립` 과 `hq -> 곱셈 H개 -> 덧셈` 둘로 갈린다.
    지연이 한 사이클 늘지만 심볼당 한 결정이라 처리율은 안 준다. **판정 순서는
    그대로이므로 비트 일치 검사가 그대로 붙든다**(한 칸 더 늦을 뿐이다).
    """
    창, 은닉 = int(창), int(은닉)
    nco = 계수수(창, 은닉)
    HW = int(FRAC) + 2
    ZW = int(XW) + int(WW) + 주소폭(창 + 1)
    YW = HW + int(WW) + 주소폭(은닉 + 1)
    if 파이프:
        은닉레지선언 = f"    reg signed [{HW}-1:0] hq [0:{은닉}-1];\n"
        은닉리셋 = f"            for (k = 0; k < {은닉}; k = k + 1) hq[k] <= 0;\n"
        은닉갱신 = f"            for (k = 0; k < {은닉}; k = k + 1) hq[k] <= h[k];\n"
        은닉원 = "hq"
    else:
        은닉레지선언 = 은닉리셋 = 은닉갱신 = ""
        은닉원 = "h"
    return NN.format(L=창, H=은닉, XW=int(XW), WW=int(WW), FRAC=int(FRAC),
                     LIM=1 << int(FRAC), ZW=ZW, YW=YW, HW=HW,
                     NCO=nco, AW=주소폭(nco), B2=창 * 은닉 + 2 * 은닉,
                     은닉레지선언=은닉레지선언, 은닉리셋=은닉리셋,
                     은닉갱신=은닉갱신, 은닉원=은닉원)


def 계수싣기(정수모: dict) -> "list[int]":
    """`nnfix.굳히기` 가 낸 정수 모델을 **RTL 의 addr 차례**로 편다.

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
    // **계수가 한 addr 공간에 있다.** 0..L-1 이 FFE, L..L+NT-1 이 DFE 다.
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
{누산레지선언}
    always @* begin
        accf = 0;
        for (k = 0; k < L; k = k + 1)
            accf = accf + $signed({{{{(FW-CW-DW){{prod[k][CW+DW-1]}}}}, prod[k]}});
        acc = $signed({{{{(TW-FW){{{누산원}[FW-1]}}}}, {누산원}}});
{합산}
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < L; k = k + 1) sr[k] <= 0;
            for (k = 0; k < DEPTH; k = k + 1) hist[k] <= 1'b0;
            for (k = 0; k < {NCO}; k = k + 1) coef[k] <= 0;
{누산리셋}            d <= 1'b0;
        end else begin
            if (cw_we) coef[cw_addr] <= cw_data;
            sr[0] <= x;
            for (k = 1; k < L; k = k + 1) sr[k] <= sr[k-1];
            for (k = DEPTH-1; k > 0; k = k - 1) hist[k] <= hist[k-1];
{누산갱신}            hist[0] <= d;
            d <= ~acc[TW-1];
        end
    end
endmodule
"""


def ffe_dfe(ffe탭: int = 11, dfe자리=(1, 2, 3, 4, 5, 6, 7, 8), W: int = 7,
            DW: int = 6, WD: int = 8, 파이프: bool = False) -> str:
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
    # **되먹임 고리 밖만 자를 수 있다.** accf 는 sr 와 계수에만 달려 있어 자를 수 있고,
    # acc -> d -> hist -> acc 고리는 못 자른다(자르면 되먹임 자체가 늦는다).
    if 파이프:
        누산레지선언 = f"    reg signed [{FW}-1:0] accq;\n"
        누산리셋 = "            accq <= 0;\n"
        누산갱신 = "            accq <= accf;\n"
        누산원 = "accq"
    else:
        누산레지선언 = 누산리셋 = 누산갱신 = ""
        누산원 = "accf"
    return FFEDFE.format(L=L, NT=NT, DEPTH=깊이, DW=int(DW), CW=cw,
                         AW=주소폭(L + NT), FW=FW, TW=TW,
                         NCO=L + NT, 합산=합산,
                         누산레지선언=누산레지선언, 누산리셋=누산리셋,
                         누산갱신=누산갱신, 누산원=누산원)


FFETBL = r"""
module ffe_tbl (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire signed [{DW}-1:0] x,
    input  wire                   cw_we,      // FFE 계수 쓰기
    input  wire [{AW}-1:0]        cw_addr,
    input  wire signed [{W}-1:0]  cw_data,
    input  wire                   tw_we,      // 표 쓰기
    input  wire [{TA}-1:0]        tw_addr,
    input  wire                   tw_data,
    output reg                    d
);
    localparam L    = {L};
    localparam W    = {W};
    localparam DW   = {DW};
    localparam FW   = {FW};     // FFE 누산기
    localparam SH   = {SH};     // 양자화 시프트
    localparam QB   = {QB};     // 표본 하나의 색인 비트
    localparam WIN  = {WIN};    // 색인에 쓰는 표본 수

    reg signed [DW-1:0] sr   [0:L-1];
    reg signed [W-1:0]  coef [0:L-1];
    // **표는 판정 한 비트만 담는다** -- 2^(WIN*QB) 비트짜리 ROM 하나다.
    reg                 tbl  [0:{NT}-1];

    wire signed [W+DW-1:0] prod [0:L-1];
    genvar i;
    generate
        for (i = 0; i < L; i = i + 1) begin : taps
            assign prod[i] = coef[i] * sr[i];
        end
    endgenerate

    integer k;
    reg signed [FW-1:0] accf;
    always @* begin
        accf = 0;
        for (k = 0; k < L; k = k + 1)
            accf = accf + $signed({{{{(FW-W-DW){{prod[k][W+DW-1]}}}}, prod[k]}});
    end

    // **양자화는 자르기와 죔쇠뿐이다.** 늘이고 줄이는 것(곱셈)이 없다.
    wire signed [FW-1:0] shifted = accf >>> SH;
    wire signed [QB:0]   hi_lim  = {{1'b0, {{(QB-1){{1'b1}}}}}};   //  2^(QB-1) - 1
    wire [QB-1:0] qcode =
        (shifted >  $signed({{{{(FW-QB){{1'b0}}}}, hi_lim[QB-1:0]}})) ? {{QB{{1'b1}}}} :
        (shifted < -$signed({{{{(FW-QB-1){{1'b0}}}}, 1'b1, {{(QB-1){{1'b0}}}}}})) ? {{QB{{1'b0}}}} :
        (shifted[QB-1:0] + {{1'b1, {{(QB-1){{1'b0}}}}}});   // 가운데로 옮긴다

    // 지난 표본의 qcode (WIN-1 개)
    reg [QB-1:0] pcode [0:{WINM1}-1];
{PIPEDECL}    reg [{TA}-1:0] addr;
    always @* begin
        addr = {{{{({TA}-QB){{1'b0}}}}, {QNOW}}};
        for (k = 0; k < {WINM1}; k = k + 1)
            addr = addr | ({{{{({TA}-QB){{1'b0}}}}, pcode[k]}} << (QB * (k + 1)));
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < L; k = k + 1) begin sr[k] <= 0; coef[k] <= 0; end
            for (k = 0; k < {WINM1}; k = k + 1) pcode[k] <= 0;
{PIPERST}
            for (k = 0; k < {NT}; k = k + 1) tbl[k] <= 1'b0;
            d <= 1'b0;
        end else begin
            if (cw_we) coef[cw_addr] <= cw_data;
            if (tw_we) tbl[tw_addr] <= tw_data;
            sr[0] <= x;
            for (k = 1; k < L; k = k + 1) sr[k] <= sr[k-1];
{PIPEUPD}            pcode[0] <= {QNOW};
            for (k = 1; k < {WINM1}; k = k + 1) pcode[k] <= pcode[k-1];
            d <= tbl[addr];
        end
    end
endmodule
"""


def ffe_tbl(ffe탭: int = 11, 창: int = 2, 색인비트: int = 4, 시프트: int = 6,
            W: int = 7, DW: int = 7, 파이프: bool = False) -> str:
    """FFE + **표본 코드로 색인하는 표.** `top` 은 `ffe_tbl`.

    ## 뒷단에 곱셈기가 하나도 없다

    FFE 는 그대로 곱셈 `ffe탭`개를 쓴다 -- **FFE 없이는 표가 완전히 실패한다**
    (실측: 0.26~0.63배, 0/6 씨). 표가 대신하는 것은 **DFE 또는 신경망**이고,
    그 자리에 곱셈기도 덧셈기도 안 든다: 자르기 · 죔쇠 · 이어붙이기 · ROM 읽기뿐이다.

    표가 **담는 것**은 판정 한 비트라 2^(창·색인비트) 비트다 -- 창 2 · 4비트면 256비트.
    그런데 **면적은 그 비트 수가 아니다.** 실측(iCE40 HX8K, FFE 를 뺀 표 단계만):

        256칸    810 LC     3.17 LC/칸
        1,024칸  3,283 LC   3.21 LC/칸
        4,096칸  12,698 LC  3.10 LC/칸

    **칸당 약 3.2 LC 로 칸 수에 선형이다.** 저장은 256비트인데 면적을 먹는 것은
    **읽어 내는 먹스**(주소 해독)와 쓰기 포트다. "곱셈기가 없다" 는 맞지만
    "공짜" 는 아니다 -- 256칸이 DFE 8탭(762 LC)과 비슷한 값이다.

    ## 양자화가 하드웨어가 할 수 있는 것이어야 한다

    백분위로 늘이고 줄이는 것은 곱셈이다. 여기서는 누산기를 `시프트`만큼 산술
    우시프트하고 죔쇠를 걸어 `색인비트` 만 쓴다. **재 보니 오히려 더 좋았다**
    (백분위 7.80배 vs 시프트 7.98배) -- 2의 거듭제곱 눈금이 손해가 아니었다.

    ## Verilog 식별자에도 한글을 쓰지 마라

    처음에 `코드` · `주소` 같은 이름을 그대로 썼더니 iverilog 가 `syntax error` 를
    냈다. CLAUDE.md 가 셸에 대해 적어 둔 것과 **같은 부류**다 -- 언어가 식별자로
    ASCII 만 받는다. 파이썬은 받고 셸과 Verilog 는 안 받는다.

    ## 되먹임이 없다

    지난 **코드**를 들고 있을 뿐 지난 **판정**을 되먹이지 않는다. 그래서 오류 번짐이
    없고 파이프라인도 자유롭다 -- DFE 의 되먹임 고리가 Fmax 를 먹던 자리가 사라진다.
    """
    L, 창, qb = int(ffe탭), int(창), int(색인비트)
    FW = int(W) + int(DW) + 주소폭(L + 1)
    TA = qb * 창
    # **되먹임이 없어 파이프라인이 자유롭다** -- 양자화 뒤를 자르면 조합 경로가
    # `곱셈 -> 덧셈 트리 -> 시프트·죔쇠` 와 `ROM 읽기` 둘로 갈린다.
    if 파이프:
        PIPEDECL = f"    reg [{qb}-1:0] qreg;\n"
        PIPERST = "            qreg <= 0;\n"
        PIPEUPD = "            qreg <= qcode;\n"
        QNOW = "qreg"
    else:
        PIPEDECL = PIPERST = PIPEUPD = ""
        QNOW = "qcode"
    return FFETBL.format(L=L, W=int(W), DW=int(DW), FW=FW, SH=int(시프트),
                         QB=qb, WIN=창, WINM1=max(창 - 1, 1),
                         NT=1 << TA, TA=TA, AW=주소폭(L),
                         PIPEDECL=PIPEDECL, PIPERST=PIPERST, PIPEUPD=PIPEUPD,
                         QNOW=QNOW)
