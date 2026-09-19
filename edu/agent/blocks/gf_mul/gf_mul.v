// GF(2^10) 곱셈기 -- 다항식 0x409 (x^10 + x^3 + 1).
//
// 이 파일은 **에이전트가 고치는 대상**이다.  골든모델은 저장소의 gf.py 이고,
// 이 RTL 이 그것과 한 비트라도 다르면 회귀가 빨개진다.
module gf_mul #(parameter M = 10, parameter [10:0] POLY = 11'h409)
              (input  wire [M-1:0] a,
               input  wire [M-1:0] b,
               output wire [M-1:0] y);

   // 시프트-덧셈.  풀어서(unrolled) 조합으로 둔다 -- 한 사이클에 곱한다.
   reg [M-1:0] acc;
   reg [M-1:0] p;
   integer i;
   always @* begin
      acc = {M{1'b0}};
      p   = a;
      for (i = 0; i < M; i = i + 1) begin
         if (b[i]) acc = acc ^ p;
         // p <<= 1, 넘치면 기약다항식으로 줄인다
         if (p[M-1]) p = (p << 1) ^ POLY[M-1:0];
         else        p = (p << 1);
      end
   end
   assign y = acc;
endmodule
