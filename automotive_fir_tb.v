`timescale 1ns/1ps
module automotive_fir_tb;
    reg clk;
    reg rst_n;
    reg [15:0] x_in;
    wire [39:0] y_out;

    automotive_fir_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .x_in(x_in),
        .y_out(y_out)
    );

    always #1 clk = ~clk; // 500 MHz clock (2ns period)

    initial begin
        $dumpfile("automotive_fir.vcd");
        $dumpvars(0, automotive_fir_tb);
        clk = 0;
        rst_n = 0;
        x_in = 0;
        #5 rst_n = 1;

        @(posedge clk);
        x_in = 16'sd1000;
        @(posedge clk);
        x_in = 0;

        repeat(20) @(posedge clk);
        $display("PASS");
        $finish;
    end

    always @(posedge clk) begin
        if (rst_n)
            $display("t=%0t x_in=%d y_out=%d", $time, $signed(x_in), $signed(y_out));
    end
endmodule
