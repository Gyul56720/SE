// 클럭된 역 Mersenne S-box 를 **레퍼런스 벡터**로 대조한다. 두 모드를 같은 벡터로 본다.
`timescale 1ns/1ps
module tb_mer_inv;
  // rst_n 을 0 으로 **시작**하면 negedge 가 없어 비동기 리셋이 한 번도 안 걸린다
  // (레지스터가 X 로 남아 busy 가 X 가 되고 start 를 영영 못 받는다 -- 실측으로 겪었다).
  // 그래서 1 에서 시작해 내려찍는다.
  reg clk = 0, rst_n = 1, start = 0;
  reg [127:0] x = 0, ref_y = 0;
  wire [127:0] z0, z1;
  wire busy0, done0, busy1, done1;
  integer fd, cnt, bad0, bad1, r, run, c0, c1, tick;
  // done 은 한 사이클 펄스이고 두 모드의 길이가 다르다(128 대 8).
  // 동시에 높을 수 없으므로 **각각 붙잡는다.**
  reg seen0, seen1;
  reg [127:0] got0, got1;
  always @(posedge clk) if (done0) begin seen0 <= 1'b1; got0 <= z0; end
  always @(posedge clk) if (done1) begin seen1 <= 1'b1; got1 <= z1; end

  always #5 clk = ~clk;

  aim_mer_inv #(.MODE(0)) u0 (.clk(clk), .rst_n(rst_n), .start(start), .x(x),
                              .busy(busy0), .done(done0), .z(z0));
  aim_mer_inv #(.MODE(1)) u1 (.clk(clk), .rst_n(rst_n), .start(start), .x(x),
                              .busy(busy1), .done(done1), .z(z1));

  // 사이클 세기 -- 각 모드가 실제로 몇 걸음 도는지 **재서** 낸다
  always @(posedge clk) if (busy0) c0 = c0 + 1;
  always @(posedge clk) if (busy1) c1 = c1 + 1;

  initial begin
    cnt = 0; bad0 = 0; bad1 = 0; run = 1; c0 = 0; c1 = 0; seen0 = 0; seen1 = 0;
    fd = $fopen("aim/dv/vectors_merinv.txt", "r");
    if (fd == 0) begin $display("FAIL: cannot open vectors_merinv.txt"); $finish; end
    #1 rst_n = 0; @(posedge clk); @(posedge clk); rst_n = 1; @(posedge clk);
    while (run) begin
      r = $fscanf(fd, "%h %h\n", x, ref_y);
      if (r != 2) run = 0;
      else begin
        c0 = 0; c1 = 0; seen0 = 0; seen1 = 0;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        tick = 0;
        while (!(seen0 && seen1) && tick < 400) begin @(posedge clk); tick = tick + 1; end
        if (tick >= 400) begin $display("FAIL: timeout at vector %0d", cnt); $finish; end
        if (got0 !== ref_y) begin bad0 = bad0 + 1;
          if (bad0 <= 2) $display("MODE0 mismatch x=%h rtl=%h ref=%h", x, got0, ref_y); end
        if (got1 !== ref_y) begin bad1 = bad1 + 1;
          if (bad1 <= 2) $display("MODE1 mismatch x=%h rtl=%h ref=%h", x, got1, ref_y); end
        cnt = cnt + 1;
        @(posedge clk);
      end
    end
    $fclose(fd);
    $display("");
    $display("vectors=%0d  MODE0(binary) bad=%0d  MODE1(chain) bad=%0d", cnt, bad0, bad1);
    $display("cycles: MODE0=%0d  MODE1=%0d", c0, c1);
    if (cnt == 0)                        $display("RESULT: FAIL (no vectors)");
    else if (bad0 + bad1 == 0)           $display("RESULT: PASS");
    else                                  $display("RESULT: FAIL");
    $finish;
  end
endmodule
