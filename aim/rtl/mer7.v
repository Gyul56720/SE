// AIM2 의 **최종 Mersenne S-box**: Mer[3](x) = x^(2^3 - 1) = x^7.
//
// 레퍼런스는 gf_exp 로 돌려 곱을 3회 쓴다(첫 곱이 out=1 에 낭비된다).
// 가수로 펴면 **곱 2회**면 된다:
//
//     x -> x^2 -> x^3 = x^2 * x -> x^6 = (x^3)^2 -> x^7 = x^6 * x
//          제곱      곱             제곱             곱
//
// 제곱 2회는 선형이라 마스킹에서 공짜다. 그러니 이 S-box 의 마스킹 비용은 **곱 2개**다.
module mer7 (input wire [127:0] x, output wire [127:0] z);
  wire [127:0] x2, x3, x6;
  gf128_sqr u_sq1 (.a(x),  .z(x2));
  gf128_mul u_m1   (.a(x2), .b(x),  .z(x3));
  gf128_sqr u_sq2 (.a(x3), .z(x6));
  gf128_mul u_m2   (.a(x6), .b(x),  .z(z));
endmodule
