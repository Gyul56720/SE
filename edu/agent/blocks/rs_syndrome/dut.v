// RS 신드롬 누산 한 걸음:  s_out = s_in * alpha^j  XOR  r
//
// 544 심볼짜리 코드워드의 신드롬은 이 걸음을 544 번 도는 것이다 (X5 장).
// 곱셈은 GF(2^10), 기약다항식 0x409.
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

module rs_syn_step (input  wire [9:0] s_in,
                    input  wire [9:0] alpha_j,
                    input  wire [9:0] r,
                    output wire [9:0] s_out);
   wire [9:0] m;
   gf_mul10 u(.a(s_in), .b(alpha_j), .y(m));
   assign s_out = m ^ r;
endmodule

module tb;
   reg  [9:0] s_in, alpha_j, r;
   wire [9:0] s_out;
   integer fi, fo, rc;
   rs_syn_step dut(.s_in(s_in), .alpha_j(alpha_j), .r(r), .s_out(s_out));
   initial begin
      fi = $fopen("stim.txt", "r");
      fo = $fopen("out.txt", "w");
      if (fi == 0) begin $display("stim.txt 없음"); $finish; end
      while (!$feof(fi)) begin
         rc = $fscanf(fi, "%h %h %h\n", s_in, alpha_j, r);
         if (rc == 3) begin
            #1;
            $fwrite(fo, "%h\n", s_out);
         end
      end
      $fclose(fi); $fclose(fo);
      $finish;
   end
endmodule
