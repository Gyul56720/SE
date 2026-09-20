// RS 신드롬 누산 한 걸음:  s_out = s_in * alpha^j  XOR  r
//
// 544 심볼짜리 코드워드의 신드롬은 이 걸음을 544 번 도는 것이다 (X5 장).
// 곱셈은 GF(2^10), 기약다항식 0x409.

module rs_syn_step (input  wire [9:0] s_in,
                    input  wire [9:0] alpha_j,
                    input  wire [9:0] r,
                    output wire [9:0] s_out);
   wire [9:0] m;
   gf_mul10 u(.a(s_in), .b(alpha_j), .y(m));
   assign s_out = m ^ r;
endmodule
