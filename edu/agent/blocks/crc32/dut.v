// CRC-32 (IEEE 802.3) -- 한 사이클에 8 비트.
//
// 다항식 0x04C11DB7, 반사 입력/출력, 초기값 0xFFFFFFFF, 최종 XOR 0xFFFFFFFF.
// 이더넷 FCS 가 쓰는 바로 그 설정이다 (Y3 장 참고).
module crc32_8 (input  wire [31:0] crc_in,
                input  wire  [7:0] d,
                output wire [31:0] crc_out);
   function [31:0] step;
      input [31:0] c;
      input        b;
      begin
         if ((c[0]) ^ b) step = (c >> 1) ^ 32'hEDB88320;
         else            step = (c >> 1);
      end
   endfunction

   reg [31:0] c;
   integer i;
   always @* begin
      c = crc_in;
      for (i = 0; i < 8; i = i + 1)
        c = step(c, d[i]);
   end
   assign crc_out = c;
endmodule

module tb;
   reg  [31:0] crc_in;
   reg   [7:0] d;
   wire [31:0] crc_out;
   integer fi, fo, r;
   crc32_8 dut(.crc_in(crc_in), .d(d), .crc_out(crc_out));
   initial begin
      fi = $fopen("stim.txt", "r");
      fo = $fopen("out.txt", "w");
      if (fi == 0) begin $display("stim.txt 없음"); $finish; end
      while (!$feof(fi)) begin
         r = $fscanf(fi, "%h %h\n", crc_in, d);
         if (r == 2) begin
            #1;
            $fwrite(fo, "%h\n", crc_out);
         end
      end
      $fclose(fi); $fclose(fo);
      $finish;
   end
endmodule
