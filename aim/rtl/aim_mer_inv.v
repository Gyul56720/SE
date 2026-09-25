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
