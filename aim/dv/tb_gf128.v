// RTL 을 **레퍼런스가 낸 벡터**로 대조한다. 정답을 내가 짓지 않는다.
//
// Verilog 식별자와 파일 이름은 **아스키만 쓴다.** 셸에서 겪은 것과 같은 함정이라
// (CLAUDE.md '셸 스크립트에 한글 변수명을 쓰지 마라'), 여기서도 안 쓴다.
`timescale 1ns/1ps
module tb_gf128;
  reg  [127:0] x, y;
  wire [127:0] rtl_sq, rtl_mul, rtl_mer7;
  reg  [127:0] ref_sq, ref_mul, ref_mer7;
  integer fd, cnt, bad_sq, bad_mul, bad_mer, r, run;

  gf128_sqr u_sq  (.a(x),        .z(rtl_sq));
  gf128_mul u_mul (.a(x), .b(y), .z(rtl_mul));
  mer7      u_m7  (.x(x),        .z(rtl_mer7));

  initial begin
    cnt = 0; bad_sq = 0; bad_mul = 0; bad_mer = 0; run = 1;
    fd = $fopen("aim/dv/vectors.txt", "r");
    if (fd == 0) begin
      $display("FAIL: cannot open aim/dv/vectors.txt");
      $finish;
    end
    while (run) begin
      r = $fscanf(fd, "%h %h %h %h %h\n", x, y, ref_sq, ref_mul, ref_mer7);
      if (r != 5) begin
        run = 0;
      end else begin
        #1;
        if (rtl_sq !== ref_sq) begin
          bad_sq = bad_sq + 1;
          if (bad_sq <= 2) $display("sqr  mismatch x=%h rtl=%h ref=%h", x, rtl_sq, ref_sq);
        end
        if (rtl_mul !== ref_mul) begin
          bad_mul = bad_mul + 1;
          if (bad_mul <= 2) $display("mul  mismatch x=%h y=%h rtl=%h ref=%h", x, y, rtl_mul, ref_mul);
        end
        if (rtl_mer7 !== ref_mer7) begin
          bad_mer = bad_mer + 1;
          if (bad_mer <= 2) $display("mer7 mismatch x=%h rtl=%h ref=%h", x, rtl_mer7, ref_mer7);
        end
        cnt = cnt + 1;
      end
    end
    $fclose(fd);
    $display("");
    $display("vectors=%0d  sqr_bad=%0d  mul_bad=%0d  mer7_bad=%0d", cnt, bad_sq, bad_mul, bad_mer);
    // 벡터가 0개이면 '틀린 게 없다'가 아니라 **검사를 안 한 것**이다. 초록으로 세지 않는다.
    if (cnt == 0)
      $display("RESULT: FAIL (no vectors -- an unchecked green)");
    else if (bad_sq + bad_mul + bad_mer == 0)
      $display("RESULT: PASS");
    else
      $display("RESULT: FAIL");
    $finish;
  end
endmodule
