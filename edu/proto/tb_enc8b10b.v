// tb_enc8b10b.v -- 골든 벡터로 부호기를 잰다.
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst = 1, valid = 0, k = 0;
    reg [7:0] data;
    wire [9:0] code;
    wire code_valid, rd, err;

    enc8b10b dut (.clk(clk), .rst(rst), .valid(valid), .data(data), .k(k),
                  .code(code), .code_valid(code_valid), .rd(rd), .err(err));

    always #5 clk = ~clk;

    integer fd, rc, n, bad;
    reg [31:0] a, b, c, d;
    reg [31:0] exp_code, exp_rd;

    initial begin
        n = 0; bad = 0;
        fd = $fopen("vec.txt", "r");
        if (fd == 0) begin $display("FAIL vec.txt 를 못 연다"); $finish; end
        repeat (4) @(posedge clk);
        rst = 0;
        repeat (2) @(posedge clk);

        rc = 4;
        while (rc == 4) begin
            rc = $fscanf(fd, "%d %d %d %d\n", a, b, c, d);
            if (rc != 4) begin end else begin
                // 자극은 negedge 에 넣는다 -- posedge 에 넣고 posedge 에
                // 재면 경주가 난다
                @(negedge clk);
                data = a[7:0]; k = b[0]; valid = 1'b1;
                exp_code = c; exp_rd = d;
                @(negedge clk);
                valid = 1'b0;
                // 출력은 다음 posedge 에 잡힌다
                @(posedge clk);
                if (code_valid !== 1'b1) begin
                    if (bad < 6) $display("FAIL 줄 %0d: code_valid 가 안 떴다", n);
                    bad = bad + 1;
                end else if (code !== exp_code[9:0] || rd !== exp_rd[0]) begin
                    if (bad < 6)
                        $display("FAIL 줄 %0d: data=%0d k=%0d  얻음 %b rd=%0d  기대 %b rd=%0d",
                                 n, a, b, code, rd, exp_code[9:0], exp_rd[0]);
                    bad = bad + 1;
                end
                n = n + 1;
            end
        end
        $fclose(fd);
        $display("잰것 %0d  틀림 %0d", n, bad);
        if (n < 64) $display("쓸모없음 벡터가 %0d 개뿐이다", n);
        $finish;
    end
endmodule
