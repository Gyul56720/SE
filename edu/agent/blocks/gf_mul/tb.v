// 자극 파일을 읽어 출력 파일을 내는 얇은 테스트벤치.
module tb;
   reg  [9:0] a, b;
   wire [9:0] y;
   integer fi, fo, r;
   gf_mul dut(.a(a), .b(b), .y(y));
   initial begin
      fi = $fopen("stim.txt", "r");
      fo = $fopen("out.txt", "w");
      if (fi == 0) begin $display("stim.txt 없음"); $finish; end
      while (!$feof(fi)) begin
         r = $fscanf(fi, "%h %h\n", a, b);
         if (r == 2) begin
            #1;
            $fwrite(fo, "%h\n", y);
         end
      end
      $fclose(fi); $fclose(fo);
      $finish;
   end
endmodule
