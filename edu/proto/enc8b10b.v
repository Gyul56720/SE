// enc8b10b.v -- 8b/10b 부호기.  PCIe Gen1/2 와 1000BASE-X 가 쓰는 그것.
//
// 이 파일은 **손으로** 썼다.  C++ 모델(`enc8b10b.h`)에서 생성하지 않았다.
// 표를 두 번 적는 것이 낭비처럼 보이지만, 그래야 골든 비교가 **양쪽을 다**
// 검사한다.  한쪽에서 생성하면 비교는 생성기만 검사한다.
//
// ── 회로 구조 ─────────────────────────────────────────────────────────
//
//   data[7:0] ─┬─[4:0]─> 5b/6b 표 ─> six[5:0] ─┐
//              │            ^                   ├─> code[9:0] = {six, four}
//              └─[7:5]─> 3b/4b 표 ─> four[3:0] ─┘
//                           ^
//   rd (플립플롭 1개) ───────┴──> 표의 어느 열을 쓸지 고른다
//                                  그리고 six 의 불균형만큼 갱신된다
//
// **상태는 플립플롭 한 개뿐이다** -- running disparity.  나머지는 전부
// 조합 논리(= 큰 mux 두 개)다.  그래서 이 블록은 작고 빠르다.
//
// ── 왜 rd 가 1비트인가 ────────────────────────────────────────────────
// running disparity 는 -1 또는 +1 만 된다 (`proto_check.cpp` 의 P2 가
// 전수로 확인한다).  두 값뿐이므로 1비트면 된다: 0 = -1, 1 = +1.
// 누산기로 짜면 폭이 늘고 포화를 걱정해야 한다 -- 값이 둘뿐인 것을
// 알면 그 고민이 통째로 사라진다.  **불변식을 알면 하드웨어가 준다.**
module enc8b10b (
    input             clk,
    input             rst,        // 동기, active high
    input             valid,      // data/k 가 유효하다
    input      [7:0]  data,
    input             k,          // 1 = 제어 부호 (K.28.x 만 지원)
    output reg [9:0]  code,
    output reg        code_valid,
    output reg        rd,         // 0 = RD -1,  1 = RD +1
    output reg        err         // K 인데 K.28.x 가 아니다
);
    wire [4:0] lo5 = data[4:0];
    wire [2:0] hi3 = data[7:5];

    // ── 5b/6b 표.  두 열을 다 적는다 ──────────────────────────────────
    // 불균형 0 인데 RD 마다 다른 항목이 있다 (D.07: 111000 / 000111).
    // "불균형 0 이면 같다" 고 압축하면 D7.7 에서 0 이 여섯 개 이어진다.
    reg [5:0] six_m, six_p;
    always @(*) begin
        case (lo5)
            5'd0 : begin six_m=6'b100111; six_p=6'b011000; end
            5'd1 : begin six_m=6'b011101; six_p=6'b100010; end
            5'd2 : begin six_m=6'b101101; six_p=6'b010010; end
            5'd3 : begin six_m=6'b110001; six_p=6'b110001; end
            5'd4 : begin six_m=6'b110101; six_p=6'b001010; end
            5'd5 : begin six_m=6'b101001; six_p=6'b101001; end
            5'd6 : begin six_m=6'b011001; six_p=6'b011001; end
            5'd7 : begin six_m=6'b111000; six_p=6'b000111; end  // 예외
            5'd8 : begin six_m=6'b111001; six_p=6'b000110; end
            5'd9 : begin six_m=6'b100101; six_p=6'b100101; end
            5'd10: begin six_m=6'b010101; six_p=6'b010101; end
            5'd11: begin six_m=6'b110100; six_p=6'b110100; end
            5'd12: begin six_m=6'b001101; six_p=6'b001101; end
            5'd13: begin six_m=6'b101100; six_p=6'b101100; end
            5'd14: begin six_m=6'b011100; six_p=6'b011100; end
            5'd15: begin six_m=6'b010111; six_p=6'b101000; end
            5'd16: begin six_m=6'b011011; six_p=6'b100100; end
            5'd17: begin six_m=6'b100011; six_p=6'b100011; end
            5'd18: begin six_m=6'b010011; six_p=6'b010011; end
            5'd19: begin six_m=6'b110010; six_p=6'b110010; end
            5'd20: begin six_m=6'b001011; six_p=6'b001011; end
            5'd21: begin six_m=6'b101010; six_p=6'b101010; end
            5'd22: begin six_m=6'b011010; six_p=6'b011010; end
            5'd23: begin six_m=6'b111010; six_p=6'b000101; end
            5'd24: begin six_m=6'b110011; six_p=6'b001100; end
            5'd25: begin six_m=6'b100110; six_p=6'b100110; end
            5'd26: begin six_m=6'b010110; six_p=6'b010110; end
            5'd27: begin six_m=6'b110110; six_p=6'b001001; end
            5'd28: begin six_m=6'b001110; six_p=6'b001110; end
            5'd29: begin six_m=6'b101110; six_p=6'b010001; end
            5'd30: begin six_m=6'b011110; six_p=6'b100001; end
            default: begin six_m=6'b101011; six_p=6'b010100; end  // D.31
        endcase
    end

    // K.28 의 5b/6b 는 따로다
    wire [5:0] k28_m = 6'b001111, k28_p = 6'b110000;

    wire [5:0] six = k ? (rd ? k28_p : k28_m)
                       : (rd ? six_p : six_m);

    // six 의 불균형만큼 RD 가 움직인다.  -2 / 0 / +2 뿐이다.
    // $countones 대신 손으로 더한다 -- iverilog 가 -g2012 에서도
    // $countones 를 안 받는 판이 있다.  **도구에 안 기대는 쪽을 고른다.**
    wire [2:0] six_ones = {2'b0, six[5]} + {2'b0, six[4]} + {2'b0, six[3]}
                        + {2'b0, six[2]} + {2'b0, six[1]} + {2'b0, six[0]};
    // 1의 개수가 4 면 +2, 3 이면 0, 2 면 -2
    wire rd_mid = (six_ones == 3'd4) ? 1'b1 :
                  (six_ones == 3'd2) ? 1'b0 : rd;

    // ── 3b/4b 표 ─────────────────────────────────────────────────────
    // 대체 부호 D.x.A7 은 D.x.7 에서만, 그리고 연속 비트가 5 를 넘을
    // 자리에서만 쓴다.  그 자리는 rd_mid (6비트를 지난 뒤의 RD) 로 정해진다.
    wire use_alt7 = (~k) & (hi3 == 3'd7) &
                    ((~rd_mid & ((lo5==5'd17)|(lo5==5'd18)|(lo5==5'd20))) |
                     ( rd_mid & ((lo5==5'd11)|(lo5==5'd13)|(lo5==5'd14))));

    reg [3:0] four_m, four_p;
    always @(*) begin
        if (k) begin
            case (hi3)
                3'd0: begin four_m=4'b1011; four_p=4'b0100; end
                3'd1: begin four_m=4'b0110; four_p=4'b1001; end
                3'd2: begin four_m=4'b1010; four_p=4'b0101; end
                3'd3: begin four_m=4'b1100; four_p=4'b0011; end
                3'd4: begin four_m=4'b1101; four_p=4'b0010; end
                3'd5: begin four_m=4'b0101; four_p=4'b1010; end
                3'd6: begin four_m=4'b1001; four_p=4'b0110; end
                default: begin four_m=4'b0111; four_p=4'b1000; end
            endcase
        end else if (use_alt7) begin
            four_m=4'b0111; four_p=4'b1000;          // D.x.A7
        end else begin
            case (hi3)
                3'd0: begin four_m=4'b1011; four_p=4'b0100; end
                3'd1: begin four_m=4'b1001; four_p=4'b0110; end
                3'd2: begin four_m=4'b0101; four_p=4'b1010; end
                3'd3: begin four_m=4'b1100; four_p=4'b0011; end
                3'd4: begin four_m=4'b1101; four_p=4'b0010; end
                3'd5: begin four_m=4'b1010; four_p=4'b0101; end
                3'd6: begin four_m=4'b0110; four_p=4'b1001; end
                default: begin four_m=4'b1110; four_p=4'b0001; end
            endcase
        end
    end

    wire [3:0] four = rd_mid ? four_p : four_m;
    wire [2:0] four_ones = {2'b0, four[3]} + {2'b0, four[2]}
                         + {2'b0, four[1]} + {2'b0, four[0]};
    wire rd_next = (four_ones == 3'd3) ? 1'b1 :
                   (four_ones == 3'd1) ? 1'b0 : rd_mid;

    // K 인데 K.28.x 가 아니면 오류.  **조용히 틀린 코드워드를 내지 않는다.**
    wire bad_k = k & (lo5 != 5'd28);

    always @(posedge clk) begin
        if (rst) begin
            rd         <= 1'b0;        // RD = -1 에서 시작한다
            code       <= 10'd0;
            code_valid <= 1'b0;
            err        <= 1'b0;
        end else begin
            code_valid <= valid & ~bad_k;
            err        <= valid &  bad_k;
            if (valid && !bad_k) begin
                code <= {six, four};
                rd   <= rd_next;
            end
        end
    end
endmodule
