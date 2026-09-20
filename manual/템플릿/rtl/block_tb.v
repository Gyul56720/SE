// block_tb.v -- 골든 벡터로 DUT 를 잰다.
//
//     iverilog -g2012 -o sim.out block_tb.v block.v
//     ./golden vec 400 1 > vec.txt
//     vvp sim.out
//
// vec.txt 한 줄:  "<입력> <정답>"   (10진, golden.cpp 와 같은 형식)
//
// ── 이 테스트벤치가 이미 지키고 있는 것 ──────────────────────────────
//  * 자극은 **negedge 에 넣고** 결과는 **posedge 에 잰다**
//      둘 다 posedge 에서 하면 경주가 난다 -- 실제로 물린 자리다
//  * 리셋을 **여러 클럭** 준다
//      한 클럭만 주면 FSM 이 첫 입력을 놓쳐 **첫 줄만** 틀린다.
//      하나만 틀리는 결함은 "가끔 틀린다"로 읽혀 몇 주를 먹는다
//  * **놀고 있는 사이클**을 관찰한다
//      valid=0 인데 out_valid 가 뜨는 결함을 잡는다.  자극을 꽉 채우면
//      그 경로를 아예 안 밟는다
//  * 벡터 수가 적으면 **쓸모없음**을 찍는다
`timescale 1ns/1ps
module tb;
    localparam integer IN_W = 8, OUT_W = 8;   // TODO block.v 와 맞춘다

    reg clk = 0, rst = 1, in_valid = 0;
    reg signed [IN_W-1:0] in_data = 0;
    wire out_valid;
    wire signed [OUT_W-1:0] out_data;

    block #(.IN_W(IN_W), .OUT_W(OUT_W)) dut (
        .clk(clk), .rst(rst),
        .in_valid(in_valid), .in_data(in_data),
        .out_valid(out_valid), .out_data(out_data)
    );

    always #5 clk = ~clk;

    integer fd, fc, rc, n, bad, idle_bad, cyc;
    reg signed [31:0] a, b;

    always @(posedge clk) if (!rst) cyc = cyc + 1;

    initial begin
        n = 0; bad = 0; idle_bad = 0; cyc = 0;
        fd = $fopen("vec.txt", "r");
        if (fd == 0) begin
            $display("FAIL vec.txt 를 못 연다 -- ./golden vec 400 1 > vec.txt 를 먼저");
            $finish;
        end

        // 리셋을 넉넉히
        repeat (4) @(posedge clk);
        rst = 0;
        repeat (2) @(posedge clk);

        rc = 2;
        while (rc == 2) begin
            rc = $fscanf(fd, "%d %d\n", a, b);
            if (rc != 2) begin end else begin
                @(negedge clk);
                in_data  = a[IN_W-1:0];
                in_valid = 1'b1;
                @(negedge clk);
                in_valid = 1'b0;

                @(posedge clk);                 // 결과가 잡히는 엣지
                if (out_valid !== 1'b1) begin
                    if (bad < 6) $display("FAIL 줄 %0d: out_valid 가 안 떴다", n);
                    bad = bad + 1;
                end else if (out_data !== b[OUT_W-1:0]) begin
                    if (bad < 6)
                        $display("FAIL 줄 %0d: in=%0d  기대 %0d  얻음 %0d",
                                 n, a, b[OUT_W-1:0], out_data);
                    bad = bad + 1;
                end

                // 놀고 있는 사이클: out_valid 가 0 이어야 한다
                @(posedge clk);
                if (out_valid !== 1'b0) begin
                    if (idle_bad < 3)
                        $display("FAIL 줄 %0d: 노는 사이클에 out_valid 가 떴다", n);
                    idle_bad = idle_bad + 1;
                end

                n = n + 1;
            end
        end
        $fclose(fd);

        fc = $fopen("cycles.txt", "w");
        $fwrite(fc, "%0d\n", cyc);
        $fclose(fc);

        $display("잰것 %0d  틀림 %0d  노는사이클오류 %0d  사이클 %0d",
                 n, bad + idle_bad, idle_bad, cyc);
        if (n < 64) $display("쓸모없음 벡터가 %0d 개뿐이다 -- 더 뽑아라", n);
        $finish;
    end
endmodule
