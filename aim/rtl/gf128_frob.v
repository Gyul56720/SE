// **이 모듈은 재서 버렸다. 쓰이지 않는다.** 지우지 않는 까닭은 아래 수 때문이다.
//
// 7 단을 직렬로 지나는 배럴이라 조합 깊이가 크다. SYN(nsw10.lib, 27 코너)이 낸
// 최악 슬랙이 **가수 -368.4 ns 대 이진법 -57.6 ns** 로 5.0 배였고, 그 5 배가 이것이다.
// 이 회로가 쓰는 Frobenius 지수는 정해진 8 개뿐이므로 `gf128_frob_sel` 로 갈았다.
// 임의의 m 이 필요한 설계(다른 e, 다른 n)로 넓힐 때 다시 볼 수 있어 남겨 둔다.
//
// GF(2^128) 의 **Frobenius 거듭제곱** sigma^m(x) = x^(2^m), m in [0,128).
//
// 왜 이 모듈이 따로 있나: AIM2 의 역 Mersenne S-box 를 가수로 펴면
// x^e~ = x * s(x) * ... * s^(d-1)(x) 가 되는데, 여기 s 가 이것이다.
// **선형이라 마스킹에서 신선한 랜덤이 0비트**다 -- 그것이 이 설계의 전제다.
//
// 꼴: 배럴. m 의 비트마다 sigma^(2^j) 한 단을 지나거나 건너뛴다. 7 단이면 된다.
// 각 단은 제곱을 2^j 번 편 것이므로 **상수 GF(2) 선형 회로**다(합성이 접는다).
module gf128_frob (input wire [127:0] a, input wire [6:0] m, output wire [127:0] z);
`include "gf128.vh"

  // sigma^k(x) -- 정수 k 는 상수여야 한다(생성 시각에 펴진다)
  function automatic [127:0] frob_pow(input [127:0] v, input integer k);
    integer i;
    begin
      frob_pow = v;
      for (i = 0; i < k; i = i + 1) frob_pow = gf128_reduce(gf128_spread(frob_pow));
    end
  endfunction

  wire [127:0] s [0:7];
  assign s[0] = a;
  genvar j;
  generate
    for (j = 0; j < 7; j = j + 1) begin : stage
      wire [127:0] hop;
      assign hop    = frob_pow(s[j], 1 << j);
      assign s[j+1] = m[j] ? hop : s[j];
    end
  endgenerate
  assign z = s[7];
endmodule
