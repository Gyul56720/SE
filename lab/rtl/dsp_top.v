// ---------------------------------------------------------------------------
// dsp_top -- 실습용 블록 하나.
//
// **작지만 모든 단계를 물어야 한다.**  이 블록 하나로 뒤의 열 단계를 전부
// 돌린다. 그래서 일부러 다음을 한 덩이에 넣었다.
//
//   곱셈누산기(MAC)  -> 조합 깊이. STA 의 임계경로가 여기서 난다
//   제어 FSM         -> 커버리지의 상태/전이 칸. DV 실습의 과녁
//   2단 동기화기     -> CDC. 비동기 start 를 이 클럭으로 들인다
//   클럭 게이팅      -> 누산기의 인에이블. T19 의 CGIC 가 여기 꽂힌다
//   비동기 리셋      -> 동기 해제. T3/X42 가 말한 그 꼴
//
// 합성 가능한 Verilog-2001 만 쓴다 -- iverilog 와 yosys 양쪽이 받아야 한다.
// ---------------------------------------------------------------------------
module dsp_top #(
    parameter W = 8
) (
    input              clk,
    input              rst_n,        // 비동기 어서트, 동기 디어서트
    input              start_async,  // 다른 클럭에서 온다 -- CDC
    input      [W-1:0] a,
    input      [W-1:0] b,
    output reg [2*W+1:0] acc,
    output reg         done,
    output     [1:0]   state_o
);
    // ---- 리셋 동기화 (비동기 어서트 / 동기 디어서트) ----------------------
    reg r1, r2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) {r2, r1} <= 2'b00;
        else        {r2, r1} <= {r1, 1'b1};
    wire rst_sync_n = r2;

    // ---- CDC: 2단 동기화기 + 펄스 만들기 ----------------------------------
    reg s1, s2, s3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) {s3, s2, s1} <= 3'b000;
        else        {s3, s2, s1} <= {s2, s1, start_async};
    wire start_pulse = s2 & ~s3;      // 한 클럭 펄스

    // ---- 제어 FSM ---------------------------------------------------------
    localparam S_IDLE = 2'd0, S_LOAD = 2'd1, S_RUN = 2'd2, S_DONE = 2'd3;
    reg [1:0] st;
    reg [2:0] cnt;
    assign state_o = st;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st   <= S_IDLE;
            cnt  <= 3'd0;
            done <= 1'b0;
        end else if (!rst_sync_n) begin
            st   <= S_IDLE;
            cnt  <= 3'd0;
            done <= 1'b0;
        end else begin
            done <= 1'b0;
            case (st)
                S_IDLE: if (start_pulse) begin st <= S_LOAD; cnt <= 3'd0; end
                S_LOAD:                        st <= S_RUN;
                S_RUN:  if (cnt == 3'd7)       st <= S_DONE;
                        else                   cnt <= cnt + 3'd1;
                S_DONE: begin done <= 1'b1;    st <= S_IDLE; end
            endcase
        end
    end

    // ---- 누산기.  en 이 곧 클럭 게이팅의 인에이블이다 ---------------------
    wire en = (st == S_RUN) || (st == S_LOAD);
    wire [2*W-1:0] prod = a * b;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)            acc <= {(2*W+2){1'b0}};
        else if (!rst_sync_n)  acc <= {(2*W+2){1'b0}};
        else if (st == S_LOAD) acc <= {{2{1'b0}}, prod};
        else if (en)           acc <= acc + {{2{1'b0}}, prod};
    end
endmodule
