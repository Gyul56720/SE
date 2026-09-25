// GF(2^128), 축약 다항식 f(x) = x^128 + x^7 + x^2 + x + 1
//
// 출처: KpqC AIMer 레퍼런스 field128.c 의 축약부.
//   c[1] ^= (temp[3] << 7) | ...;  c[1] ^= (temp[3] << 2) | ...;
//   c[1] ^= (temp[3] << 1) | ...;  c[0] = temp[0] ^ t;
// 7 · 2 · 1 자리 이동과 t 자체(=x^0)가 곧 g(x) = x^7 + x^2 + x + 1 이다.
//
// 원소 표현: 비트 i = 계수 x^i. 레퍼런스의 gf a[2] 에 대해 {a[1], a[0]} 이다.

// 255비트 다항식을 f(x) 로 나눈 나머지. 두 번 접어서 끝난다(깊지 않다).
function automatic [127:0] gf128_reduce(input [254:0] p);
  reg [126:0] hi;      // x^128 이상 자리
  reg [133:0] t;       // hi * g  (127 + 7 비트)
  reg [5:0]   hi2;     // 한 번 접고 남은 자리
  reg [127:0] acc;
  begin
    hi  = p[254:128];
    t   = ({7'd0, hi} << 7) ^ ({7'd0, hi} << 2) ^ ({7'd0, hi} << 1) ^ {7'd0, hi};
    acc = p[127:0] ^ t[127:0];
    hi2 = t[133:128];
    acc = acc ^ ({122'd0, hi2} << 7) ^ ({122'd0, hi2} << 2)
              ^ ({122'd0, hi2} << 1) ^ {122'd0, hi2};
    gf128_reduce = acc;
  end
endfunction

// 무캐리 곱 (교과서 꼴). 첫 판은 맞는 것이 먼저다 -- 카라추바는 그 다음이다.
function automatic [254:0] gf128_clmul(input [127:0] a, input [127:0] b);
  integer i;
  reg [254:0] acc;
  begin
    acc = 255'd0;
    // `if (b[i])` 로 쓰면 비트마다 MUX 가 난다(실측: mer7 에 MUX 32768 개).
    // AND 마스크로 쓰면 AND 가 난다 -- 같은 식인데 합성 결과가 다르다.
    for (i = 0; i < 128; i = i + 1)
      acc = acc ^ (({127'd0, a} & {255{b[i]}}) << i);
    gf128_clmul = acc;
  end
endfunction

// 제곱은 비트를 벌리는 것뿐이다 -- GF(2^n) 에서 Frobenius 는 **선형**이다.
// 그래서 마스킹에서 몫별로 따로 하면 되고 신선한 랜덤이 안 든다.
function automatic [254:0] gf128_spread(input [127:0] a);
  integer i;
  reg [254:0] s;
  begin
    s = 255'd0;
    for (i = 0; i < 128; i = i + 1) s[2*i] = a[i];
    gf128_spread = s;
  end
endfunction
