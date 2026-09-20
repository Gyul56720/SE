// fir_shell.v -- **타이밍 껍데기.**  Fmax 를 비교하려면 이것이 반드시 필요하다.
//
// 왜 있나 -- 안 쓰면 Fmax 비교가 통째로 거짓이 된다
// --------------------------------------------------
// 실측 2026-09-19.  손RTL 과 HLS RTL 을 그대로 nextpnr 에 넣고 Fmax 를 읽었더니
// 이런 수가 나왔다:
//
//     손RTL          (보고 없음)          <- 레지스터-레지스터 경로가 없다
//     HLS cp=10      324 · 417 · 303 MHz  <- 씨앗마다 35 % 씩 흔들린다
//     HLS cp=6        75 ·  73 ·  72 MHz  <- 레지스터가 **더 많은데 더 느리다**
//
// 레지스터를 더 넣었는데 느려지는 것은 말이 안 된다.  그래서 시시한 설명부터
// 쟀다: **nextpnr 이 내는 "Max frequency" 는 레지스터-레지스터 경로만 본다.**
// 입력 핀에서 첫 레지스터까지의 긴 조합 경로는 제약이 없으면 안 센다.
// cp=10 판은 레지스터가 11개뿐이라 진짜 일은 전부 제약 없는 I/O 경로에서
// 일어났고, 보고된 324 MHz 는 **짧은 곁가지 경로**의 수였다.
//
//     재려던 것: 데이터패스의 임계경로
//     잰 것:     아무 상관 없는 짧은 경로
//
// 이 껍데기는 **모든 입력과 출력을 레지스터로 감싼다.**  그러면 조합 논리가
// 전부 레지스터 사이에 들어가고, nextpnr 이 재는 경로가 곧 우리가 재려던
// 경로가 된다.  업계에서 이것을 타이밍 껍데기(timing shell)라고 부르고,
// 합성 보고를 비교할 때 표준으로 쓴다.
//
//     iverilog/yosys -DDUT=fir4_hand      fir_shell.v fir4_hand.v
//     iverilog/yosys -DDUT=fir_top_tuned  fir_shell.v fir_top_tuned.v
`ifndef DUT
 `define DUT fir4_hand
`endif
module fir_shell (
    input        clock,
    input        reset,
    input        start_i,
    input  [7:0] x0_i, x1_i, x2_i, x3_i,
    output reg       done_o,
    output reg [7:0] y_o
);
    // 입력 레지스터.  핀에서 오는 경로를 여기서 끊는다.
    reg       start_q;
    reg [7:0] x0_q, x1_q, x2_q, x3_q;
    always @(posedge clock) begin
        start_q <= start_i;
        x0_q <= x0_i; x1_q <= x1_i; x2_q <= x2_i; x3_q <= x3_i;
    end

    wire       done_w;
    wire [7:0] y_w;
    `DUT dut (.clock(clock), .reset(reset), .start_port(start_q),
              .x0(x0_q), .x1(x1_q), .x2(x2_q), .x3(x3_q),
              .done_port(done_w), .return_port(y_w));

    // 출력 레지스터.  핀으로 가는 경로를 여기서 끊는다.
    always @(posedge clock) begin
        done_o <= done_w;
        y_o    <= y_w;
    end
endmodule
