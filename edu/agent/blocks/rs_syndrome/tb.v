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
