// GF(2^128) Frobenius -- **이 설계가 실제로 쓰는 지수만** 고른다.
//
// 왜 배럴을 버렸나(실측): 배럴은 sigma^(2^j) 7 단을 **직렬로** 지난다. 각 단이
// XOR 트리 한 겹이라 깊이가 7 단 x 한 겹 + 먹스가 된다. SYN 이 낸 최악 슬랙이
// 가수 -368.4 ns 대 이진법 -57.6 ns 로 **5.0 배**였고, 그 5 배가 곧 이 캐스케이드다.
//
// 그런데 이 회로가 쓰는 Frobenius 지수는 **정해진 8 개**다(가수의 걸음표에서 나온다):
//     49  98  68  117  106  84  40  80
// 고정 선형맵 8 개를 나란히 두고 8:1 먹스로 고르면 **깊이가 1 맵 + 먹스**로 준다.
// 면적은 비슷하고(맵 8 개 대 7 개) 깊이는 크게 준다.
module gf128_frob_sel (input wire [127:0] a, input wire [2:0] sel, output wire [127:0] z);
`include "gf128.vh"

  // sigma^k(x) = x^(2^k). k 가 상수라 생성 시각에 펴지고 합성이 **선형 XOR 망**으로 접는다.
  function automatic [127:0] frob_pow(input [127:0] v, input integer k);
    integer i;
    begin
      frob_pow = v;
      for (i = 0; i < k; i = i + 1) frob_pow = gf128_reduce(gf128_spread(frob_pow));
    end
  endfunction

  wire [127:0] u0 = frob_pow(a,  49);
  wire [127:0] u1 = frob_pow(a,  98);
  wire [127:0] u2 = frob_pow(a,  68);
  wire [127:0] u3 = frob_pow(a, 117);
  wire [127:0] u4 = frob_pow(a, 106);
  wire [127:0] u5 = frob_pow(a,  84);
  wire [127:0] u6 = frob_pow(a,  40);
  wire [127:0] u7 = frob_pow(a,  80);

  assign z = (sel == 3'd0) ? u0 : (sel == 3'd1) ? u1 :
             (sel == 3'd2) ? u2 : (sel == 3'd3) ? u3 :
             (sel == 3'd4) ? u4 : (sel == 3'd5) ? u5 :
             (sel == 3'd6) ? u6 :                 u7;
endmodule
