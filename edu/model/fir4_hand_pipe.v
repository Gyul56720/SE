// fir4_hand_pipe.v -- 손으로 **파이프라인까지 그린** RTL.
//
// 왜 이 파일이 있나 -- 비교가 공정하려면
// ---------------------------------------
// `fir4_hand.v` 는 조합 한 덩이다.  그것만 놓고 "HLS 가 손RTL 보다 빠르다" 고
// 적으면 **허수아비를 세운 것**이다.  사람도 파이프라인을 그릴 수 있고,
// 그리면 당연히 빨라진다.  그래서 사람이 그린 파이프라인도 같이 잰다.
//
// 3단으로 끊었다.  끊은 자리는 임계경로를 보고 골랐다:
//
//     1단  접는 덧셈       x0+x3, x1+x2        (9비트 덧셈 두 번)
//     2단  상수 곱셈+합    a0*h0 + a1*h1       (여기가 제일 길다)
//     3단  시프트+포화     >>7, 클립           (비교기 두 개)
//
// **이것이 손RTL 의 진짜 상한이다.**  HLS 가 이것을 이기면 이긴 것이고,
// 못 이기면 못 이긴 것이다.  `fir4_hand.v` 하나만 재서 이겼다고 하지 않는다.
//
// 지연: start 에서 done 까지 3사이클.  조합판은 1사이클이었다 --
// **빨라진 값은 지연으로 치렀다.**  공짜로 빨라지는 것은 없다.
module fir4_hand_pipe (
    input             clock,
    input             reset,
    input             start_port,
    input      signed [7:0] x0,
    input      signed [7:0] x1,
    input      signed [7:0] x2,
    input      signed [7:0] x3,
    output reg              done_port,
    output reg signed [7:0] return_port
);
    // --- 1단: 접는 덧셈 ---
    reg signed [8:0] a0_q, a1_q;
    reg              v1;
    always @(posedge clock) begin
        if (reset) v1 <= 1'b0;
        else       v1 <= start_port;
        a0_q <= $signed({x0[7], x0}) + $signed({x3[7], x3});
        a1_q <= $signed({x1[7], x1}) + $signed({x2[7], x2});
    end

    // --- 2단: 상수 곱셈과 합 ---
    // 계수가 상수라 합성기가 시프트-덧셈으로 푼다.  포트로 받으면 못 푼다.
    // acc_q[6:0] 은 일부러 안 쓴다 -- 버리는 소수 7비트다 (fir4_hand.v 와 같다).
    // **그 한 줄에만** 좁게 끈다.  종류 전체를 끄면 진짜 배선 실수가 묻힌다.
    /* verilator lint_off UNUSEDSIGNAL */
    reg signed [16:0] acc_q;
    /* verilator lint_on UNUSEDSIGNAL */
    reg               v2;
    always @(posedge clock) begin
        if (reset) v2 <= 1'b0;
        else       v2 <= v1;
        acc_q <= a0_q * $signed(-8'sd18) + a1_q * $signed(8'sd111);
    end

    // --- 3단: 시프트와 포화 ---
    wire signed [9:0] sh = acc_q[16:7];
    always @(posedge clock) begin
        if (reset) begin
            done_port   <= 1'b0;
            return_port <= 8'sd0;
        end else begin
            done_port   <= v2;
            return_port <= (sh >  10'sd127) ?  8'sd127 :
                           (sh < -10'sd128) ? -8'sd128 : sh[7:0];
        end
    end
endmodule
