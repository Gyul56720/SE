// fir4_hand.v -- 같은 FIR 을 **손으로** 쓴 것.  HLS 와 나란히 재려고 있다.
//
// 인터페이스를 HLS 가 낸 것과 일부러 맞췄다 -- 클럭·리셋·start·done 까지.
// 그래야 **1변수 대조**가 된다.  포트 폭이 다르면 포트 폭 차이를 알고리즘
// 차이로 잘못 읽는다.
//
// 이 파일은 "잘 쓴 손RTL" 이다:
//   * 폭을 전부 적었다 ([7:0] · [8:0] · [16:0])
//   * 계수가 상수라 곱셈이 시프트-덧셈으로 풀린다
//   * 대칭을 접어 곱셈 2번만 한다
//
// 다시 말해 **`fir_top_tuned.cpp` 가 하는 것과 정확히 같은 최적화**를 했다.
// 둘의 면적 차이가 곧 "HLS 도구가 무엇을 더 쓰거나 덜 쓰는가" 다.
module fir4_hand (
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
    // 접기: 8비트 둘을 더하면 9비트다.  8비트로 자르면 넘칠 때만 조용히 틀린다.
    wire signed [8:0] a0 = $signed({x0[7], x0}) + $signed({x3[7], x3});
    wire signed [8:0] a1 = $signed({x1[7], x1}) + $signed({x2[7], x2});

    // 9비트 x 8비트 = 17비트.  계수가 상수이므로 합성기가 곱셈기를 안 쓴다.
    wire signed [16:0] acc = a0 * $signed(-8'sd18) + a1 * $signed(8'sd111);

    // Q3.14 -> Q1.7 : 산술 우시프트 7.  Verilog 의 >>> 는 부호를 끈다.
    wire signed [9:0] sh = acc[16:7];

    // 포화.  wrap 하면 큰 양수가 큰 음수로 뒤집혀 슬라이서가 정반대로 틀린다.
    wire signed [7:0] y = (sh >  10'sd127) ?  8'sd127 :
                          (sh < -10'sd128) ? -8'sd128 : sh[7:0];

    always @(posedge clock) begin
        if (reset) begin
            done_port   <= 1'b0;
            return_port <= 8'sd0;
        end else begin
            done_port   <= start_port;
            return_port <= y;
        end
    end
endmodule
