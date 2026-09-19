// GF(2^10) 곱셈기 -- 기약다항식 x^10 + x^3 + 1 (0x409).
// 한 파일에 한 모듈, 파일 이름은 모듈 이름 (verilator DECLFILENAME).
module gf_mul10 (input wire [9:0] a, input wire [9:0] b, output wire [9:0] y);
   reg [9:0] acc, p;
   integer i;
   always @* begin
      acc = 10'd0;
      p   = a;
      for (i = 0; i < 10; i = i + 1) begin
         if (b[i]) acc = acc ^ p;
         if (p[9]) p = (p << 1) ^ 10'h009;   // x^10 + x^3 + 1, 하위 10 비트
         else      p = (p << 1);
      end
   end
   assign y = acc;
endmodule
