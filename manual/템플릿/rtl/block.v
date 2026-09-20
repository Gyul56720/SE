// block.v -- RTL 뼈대.  스펙(work/스펙.md)을 그대로 옮긴다.
//
// 이름 규칙: **파일 이름 = 모듈 이름**.  verilator 의 DECLFILENAME 이
// 요구하고, 모든 빌드 도구가 이것을 가정한다.  한 파일에 한 모듈.
//
// ── 이 뼈대가 이미 지키고 있는 것 ─────────────────────────────────────
//  * 출력을 레지스터에 담는다      -> 고객 칩에서 타이밍이 예측 가능해진다
//  * 리셋이 동기, active high      -> 스펙 8절과 같아야 한다.  다르면 여기를 고친다
//  * 폭을 전부 적었다              -> 암묵 변환이 없다
//  * valid/ready 가 아니라 valid 만 -> back-pressure 가 없는 스펙일 때.
//                                     필요하면 아래 주석 참고
module block #(
    parameter integer IN_W  = 8,     // TODO 스펙 2절
    parameter integer OUT_W = 8      // TODO 스펙 3절
) (
    input                        clk,
    input                        rst,       // 동기, active high
    input                        in_valid,
    input  signed [IN_W-1:0]     in_data,
    output reg                   out_valid,
    output reg signed [OUT_W-1:0] out_data
);

    // ── 조합 논리: 여기가 알고리즘이다 ───────────────────────────────
    // 지금 들어 있는 것은 **돌아가는 최소 예제**다: y = 포화(2x).
    // 시시하지만 일부러 이렇게 두었다 -- 폭 넓히기와 포화라는 두 함정을
    // 다 보여주면서, 복사하자마자 검증이 통과하기 때문이다.
    // 여기를 스펙 1절의 수식으로 **갈아 끼운다**.
    //
    // 폭을 **한 줄씩** 적는다.  8비트 둘을 더하면 9비트가 필요하다 --
    // 8비트로 자르면 넘칠 때만 조용히 틀린다(자극의 몇 %에서만).
    // 그런 결함이 회귀를 몇 주 먹는다.  그래서 y_wide 가 IN_W+1 비트다.
    wire signed [IN_W:0] y_wide = {in_data[IN_W-1], in_data}
                                + {in_data[IN_W-1], in_data};   // TODO

    // ── 포화 ─────────────────────────────────────────────────────────
    // wrap 하면 큰 양수가 큰 음수로 뒤집혀 뒤 블록이 정반대로 판단한다.
    // 스펙 3절에서 포화를 골랐으면 여기서 한다.
    localparam signed [OUT_W-1:0] HI = {1'b0, {(OUT_W-1){1'b1}}};
    localparam signed [OUT_W-1:0] LO = {1'b1, {(OUT_W-1){1'b0}}};
    wire signed [OUT_W-1:0] y_sat =
        (y_wide > $signed({{(IN_W+1-OUT_W){HI[OUT_W-1]}}, HI})) ? HI :
        (y_wide < $signed({{(IN_W+1-OUT_W){LO[OUT_W-1]}}, LO})) ? LO :
        y_wide[OUT_W-1:0];

    // ── 레지스터 ─────────────────────────────────────────────────────
    // `<=` (non-blocking) 를 쓴다.  순차 논리에 `=` 를 쓰면 다른 블록과의
    // 평가 순서에 따라 결과가 달라진다 -- 시뮬레이터가 정하는 순서이고
    // 명세에 없다.  그것이 경주다.
    always @(posedge clk) begin
        if (rst) begin
            out_valid <= 1'b0;
            out_data  <= {OUT_W{1'b0}};
        end else begin
            out_valid <= in_valid;
            if (in_valid)
                out_data <= y_sat;
        end
    end
endmodule

// ── back-pressure 가 필요하면 ────────────────────────────────────────
// out_ready 를 받고 in_ready 를 내야 한다.  그때 반드시 지킬 규칙:
//
//     in_ready 가 in_valid 에 **조합으로 의존하면 안 된다**
//
// 어기면 두 블록을 이었을 때 조합 고리가 생겨 합성이 안 되거나
// 시뮬이 무한 루프에 빠진다.  해법은 skid buffer 다.
