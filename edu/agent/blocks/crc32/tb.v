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
