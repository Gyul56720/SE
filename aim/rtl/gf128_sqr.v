// GF(2^128) 제곱 -- 선형이다. 랜덤이 들지 않는다.
module gf128_sqr (input wire [127:0] a, output wire [127:0] z);
`include "gf128.vh"
  assign z = gf128_reduce(gf128_spread(a));
endmodule
