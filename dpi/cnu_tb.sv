// SystemVerilog 테스트벤치 -- RTL 을 **DPI-C 레퍼런스 모델**과 매 벡터 맞댄다.
module cnu_tb;
  localparam int W = 6;
  localparam int LIM = (1 << (W-1)) - 1;

  // ---- DPI-C 로 C++ 레퍼런스를 불러온다 -------------------------------
  import "DPI-C" function void cnu_ref(input int q0, input int q1,
                                       input int q2, input int q3,
                                       output int r0, output int r1,
                                       output int r2, output int r3);

  logic signed [W-1:0] q0, q1, q2, q3;
  wire  signed [W-1:0] r0, r1, r2, r3;
  int                  e0, e1, e2, e3;

  cnu #(.W(W)) dut (.q0(q0), .q1(q1), .q2(q2), .q3(q3),
                    .r0(r0), .r1(r1), .r2(r2), .r3(r3));

  int unsigned seed = 32'hC0FFEE;
  int bad = 0, n = 0;

  function automatic int unsigned rnd();
    seed = seed * 32'd1103515245 + 32'd12345;
    return seed;
  endfunction

  initial begin
    for (int k = 0; k < 2000; k++) begin
      q0 = (rnd() % (2*LIM+1)) - LIM;
      q1 = (rnd() % (2*LIM+1)) - LIM;
      q2 = (rnd() % (2*LIM+1)) - LIM;
      q3 = (rnd() % (2*LIM+1)) - LIM;
      #1;                                       // 조합회로가 안정되기를 기다린다
      cnu_ref(int'(q0), int'(q1), int'(q2), int'(q3), e0, e1, e2, e3);
      n++;
      if (int'(r0) !== e0 || int'(r1) !== e1 || int'(r2) !== e2 || int'(r3) !== e3) begin
        bad++;
        if (bad <= 5)
          $display("FAIL k=%0d  q=[%0d %0d %0d %0d]  rtl=[%0d %0d %0d %0d]  ref=[%0d %0d %0d %0d]",
                   k, q0,q1,q2,q3, r0,r1,r2,r3, e0,e1,e2,e3);
      end
    end
    if (bad == 0) $display("PASS  %0d vectors, RTL == C++ DPI reference", n);
    else          $display("FAIL  %0d / %0d mismatches", bad, n);
    $finish;
  end
endmodule
