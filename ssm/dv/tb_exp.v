// exp_unit 을 골든 벡터로 비트 대조. RESULT: PASS/FAIL 를 낸다(aim 방식).
`timescale 1ns/1ps
module tb_exp;
  localparam IDXBITS = 6;
  reg  [15:0] m;
  wire [15:0] abar;
  exp_unit #(.IDXBITS(IDXBITS), .LUTFILE("ssm/dv/exp_lut_64.memh")) dut (.m(m), .abar(abar));

  integer fd, n, vectors, fails, code;
  reg [15:0] m_in, exp_abar;
  initial begin
    fd = $fopen("ssm/dv/exp_vec_64.txt", "r");
    if (fd == 0) begin $display("벡터 파일 못 엶"); $finish; end
    vectors = 0; fails = 0;
    while (!$feof(fd)) begin
      code = $fscanf(fd, "%h %h\n", m_in, exp_abar);
      if (code == 2) begin
        m = m_in; #1;
        vectors = vectors + 1;
        if (abar !== exp_abar) begin
          fails = fails + 1;
          if (fails <= 5) $display("불일치 m=%h abar=%h 기대=%h", m_in, abar, exp_abar);
        end
      end
    end
    $fclose(fd);
    $display("vectors=%0d fails=%0d", vectors, fails);
    if (vectors > 0 && fails == 0) $display("RESULT: PASS");
    else $display("RESULT: FAIL");
    $finish;
  end
endmodule
