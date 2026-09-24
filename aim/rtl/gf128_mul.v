// GF(2^128) 곱 -- 조합회로 한 판. 마스킹에서 **신선한 랜덤이 드는 유일한 자리**다.
module gf128_mul (input  wire [127:0] a, input wire [127:0] b, output wire [127:0] z);
`include "gf128.vh"
  assign z = gf128_reduce(gf128_clmul(a, b));
endmodule
