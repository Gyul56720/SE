from rtl import 시뮬, 린트, 합성
design = """
module simple_counter(
    input wire clk,
    input wire rst_n,
    input wire load,
    input wire [3:0] d,
    output reg [3:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 4'b0000;
        else if (load)
            q <= d;
        else
            q <= q + 1'b1;
    end
endmodule
"""

tb = """
module tb;
    reg clk;
    reg rst_n;
    reg load;
    reg [3:0] d;
    wire [3:0] q;

    simple_counter uut (.clk(clk), .rst_n(rst_n), .load(load), .d(d), .q(q));

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst_n = 0; load = 0; d = 0;
        #12 rst_n = 1;
        #20;
        if (q == 4'd2) ("PASS: got %0d", q);
        else ("FAIL: got %0d expected 2", q);
        ;
    end
endmodule
"""

print("=== run_rtl (시뮬) ===")
res_sim = 시뮬(design, tb, top="tb")
print(res_sim)

print("=== lint_rtl (린트) ===")
res_lint = 린트(design)
print(res_lint)

print("=== synth_rtl (합성) ===")
res_synth = 합성(design, top="simple_counter")
print(res_synth)
