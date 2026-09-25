// scan_mac 을 골든 스트림으로 비트 대조. hprev 는 직전 스텝의 h 를 물린다.
`timescale 1ns/1ps
module tb_scan;
  localparam N = 16;
  reg  signed [15:0]     x;
  reg         [16*N-1:0] Abar, Bbar, C, hprev;
  wire        [16*N-1:0] h;
  wire signed [15:0]     y;
  scan_mac #(.N(N)) dut(.x(x), .Abar(Abar), .Bbar(Bbar), .C(C), .hprev(hprev), .h(h), .y(y));

  integer fi, fo, code, t, n, fails; reg [15:0] tmp, exp_y; reg [16*N-1:0] exp_h;
  initial begin
    fi = $fopen("ssm/dv/scan_in_N16.txt","r"); fo = $fopen("ssm/dv/scan_out_N16.txt","r");
    if (fi==0 || fo==0) begin $display("벡터 못 엶"); $finish; end
    hprev = 0; t = 0; fails = 0;
    code = $fscanf(fi, "%h", tmp);
    while (code == 1) begin
      x = tmp;
      for (n=0;n<N;n=n+1) begin code=$fscanf(fi,"%h",tmp); Abar[16*n +:16]=tmp; end
      for (n=0;n<N;n=n+1) begin code=$fscanf(fi,"%h",tmp); Bbar[16*n +:16]=tmp; end
      for (n=0;n<N;n=n+1) begin code=$fscanf(fi,"%h",tmp); C[16*n +:16]=tmp;    end
      for (n=0;n<N;n=n+1) begin code=$fscanf(fo,"%h",tmp); exp_h[16*n +:16]=tmp; end
      code=$fscanf(fo,"%h",exp_y);
      #1;
      if (h !== exp_h || y !== exp_y) begin
        fails = fails + 1;
        if (fails<=5) $display("t=%0d 불일치 y=%h 기대=%h  h[0]=%h 기대=%h", t, y, exp_y, h[15:0], exp_h[15:0]);
      end
      hprev = h;                 // 상태 물림
      t = t + 1;
      code = $fscanf(fi, "%h", tmp);
    end
    $fclose(fi); $fclose(fo);
    $display("steps=%0d fails=%0d", t, fails);
    if (t>0 && fails==0) $display("RESULT: PASS"); else $display("RESULT: FAIL");
    $finish;
  end
endmodule
