// =====================================================================
//  nsw_aim.sv -- Nowon Silicon Works
//  AIM2 (KpqC AIMer v2.0) 의 역 Mersenne S-box, GF(2^128)
//
//  **이 파일은 생성물이다.** 진실은 aim/rtl/ 이고 aim/흐름용_RTL만들기.py
//  가 `include 를 펴서 여기에 낸다. 손으로 고치지 마라.
// =====================================================================
// ---------------------------------------------------------------- gf128_sqr.v
// GF(2^128) 제곱 -- 선형이다. 랜덤이 들지 않는다.
module gf128_sqr (input wire [127:0] a, output wire [127:0] z);
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

  assign z = gf128_reduce(gf128_spread(a));
endmodule

// ---------------------------------------------------------------- gf128_mul.v
// GF(2^128) 곱 -- 조합회로 한 판. 마스킹에서 **신선한 랜덤이 드는 유일한 자리**다.
module gf128_mul (input  wire [127:0] a, input wire [127:0] b, output wire [127:0] z);
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

  assign z = gf128_reduce(gf128_clmul(a, b));
endmodule

// ---------------------------------------------------------------- gf128_frob_sel.v
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

// ---------------------------------------------------------------- aim_mer_inv.v
// AIM2 의 **역 Mersenne S-box** Mer[e]^-1(x) = x^e~,  e~ = (2^e-1)^-1 mod (2^n-1).
// AIMer v2.0 규격서 Table 3 의 AIM2-I 첫 S-box (n=128, e=49).
//
// **같은 회로 안에 두 셈법을 넣고 파라미터로 가른다.** 그래야 합성이 둘을 직접 견준다.
//
//   MODE=0  이진법 (레퍼런스 gf_exp 와 같은 셈법)
//           r=1, t=x;  i=0..127:  e~[i] 면 r=r*t;  t=t*t
//           128 사이클, 그중 **곱 81 회**. 배럴이 필요 없다(제곱기만 쓴다).
//
//   MODE=1  Frobenius 가수
//           acc = x*s(x)*...*s^(d-1)(x) 를 반복제곱법으로
//           **8 사이클 = 곱 8 회**. 대신 배럴 Frobenius 가 든다.
//
// 재는 것: 사이클(=곱 횟수, 곧 마스킹의 랜덤 비트)과 면적. 둘의 맞바꿈이 이 설계의 물음이다.
module aim_mer_inv #(parameter MODE = 1) (
  input  wire         clk,
  input  wire         rst_n,
  input  wire         start,
  input  wire [127:0] x,
  output reg          busy,
  output reg          done,
  output reg  [127:0] z
);
  localparam [127:0] ETILDE = 128'hb6b6d6d6dadb5b5b6b6b6d6dadadb5b5;  // e~ for e=49
  localparam integer NSTEP  = 8;                                      // 가수의 곱 횟수

  // 가수의 걸음표: {덧셈걸음인가, Frobenius 지수}
  // 유도: acc=x, m=1; d=81=0b1010001 의 최상위 뒤 비트마다
  //       DOUBLE(exp=e*m), m*=2;  비트가 1 이면 ADD(exp=e*m), m+=1
  function automatic [7:0] step_rom(input integer k);
    begin
      case (k)
        0: step_rom = {1'b0, 7'd49};
        1: step_rom = {1'b0, 7'd98};
        2: step_rom = {1'b1, 7'd68};
        3: step_rom = {1'b0, 7'd117};
        4: step_rom = {1'b0, 7'd106};
        5: step_rom = {1'b0, 7'd84};
        6: step_rom = {1'b0, 7'd40};
        7: step_rom = {1'b1, 7'd80};
        default: step_rom = 8'd0;
      endcase
    end
  endfunction

  reg [127:0] acc, t, xr;
  reg [7:0]   i;

  wire [7:0]   st      = step_rom(i);
  wire         is_add  = st[7];

  wire [127:0] frob_in = is_add ? xr : acc;
  wire [127:0] frob_o, mul_o, sqr_o;

  // 걸음마다 Frobenius 지수가 하나씩이므로 **걸음 번호가 곧 선택자**다.
  // 배럴(7단 직렬) 대신 고정 선형맵 8 개 + 8:1 먹스 -- 깊이가 1 맵으로 준다.
  gf128_frob_sel u_frob (.a(frob_in), .sel(i[2:0]), .z(frob_o));
  gf128_sqr  u_sqr  (.a(t),                 .z(sqr_o));
  gf128_mul  u_mul  (.a(MODE ? acc : acc), .b(MODE ? frob_o : t), .z(mul_o));

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      busy <= 1'b0; done <= 1'b0; z <= 128'd0;
      acc  <= 128'd0; t <= 128'd0; xr <= 128'd0; i <= 8'd0;
    end else begin
      done <= 1'b0;
      if (!busy) begin
        if (start) begin
          busy <= 1'b1; i <= 8'd0; xr <= x;
          acc  <= (MODE != 0) ? x : 128'd1;      // 가수는 x 에서, 이진법은 1 에서
          t    <= x;
        end
      end else if (MODE != 0) begin
        acc <= mul_o;                            // 걸음마다 곱 한 번
        if (i == NSTEP - 1) begin
          busy <= 1'b0; done <= 1'b1; z <= mul_o;
        end
        i <= i + 8'd1;
      end else begin
        if (ETILDE[i[6:0]]) acc <= mul_o;        // 비트가 1 일 때만 곱한다
        t <= sqr_o;                              // 제곱은 매 걸음
        if (i == 8'd127) begin
          busy <= 1'b0; done <= 1'b1;
          z <= ETILDE[127] ? mul_o : acc;
        end
        i <= i + 8'd1;
      end
    end
  end
endmodule
