from rtl import 시뮬, 린트, 합성
import subprocess

design = '''
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
'''

tb = '''
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
        if (q == 4'd2) $display("PASS: got %0d", q);
        else $display("FAIL: got %0d expected 2", q);
        $finish;
    end
endmodule
'''

print("1. run_rtl (시뮬):")
res = 시뮬(design, tb, top="tb")
print(res)

print("2. lint_rtl (린트):")
print(린트(design))

print("3. synth_rtl (합성):")
print(합성(design, top="simple_counter"))

print("4. place_rtl (P&R/Fmax):")
# nextpnr-ice40 test
import tempfile, os
판 = tempfile.mkdtemp()
with open(os.path.join(판, "counter.v"), "w") as f:
    f.write(design)

p1 = subprocess.run(["yosys", "-p", "synth_ice40 -top simple_counter -json counter.json"], cwd=판, capture_output=True, text=True)
if p1.returncode == 0:
    p2 = subprocess.run(["nextpnr-ice40", "--hx8k", "--json", "counter.json", "--asc", "counter.asc", "--freq", "50"], cwd=판, capture_output=True, text=True)
    print("nextpnr exit:", p2.returncode)
    print(p2.stdout + p2.stderr)
else:
    print("Yosys synth for FPGA failed:", p1.stderr)

