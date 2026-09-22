import subprocess, tempfile, os

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

판 = tempfile.mkdtemp()
path = os.path.join(판, "simple_counter.v")
with open(path, "w") as f:
    f.write(design)

cmd = f"read_verilog {path}; synth_ice40 -top simple_counter -json counter.json"
p1 = subprocess.run(["yosys", "-p", cmd], cwd=판, capture_output=True, text=True)
print("yosys ret:", p1.returncode)
if p1.returncode == 0:
    p2 = subprocess.run(["nextpnr-ice40", "--hx8k", "--json", "counter.json", "--asc", "counter.asc", "--freq", "50"], cwd=판, capture_output=True, text=True)
    print("nextpnr ret:", p2.returncode)
    print("stdout:", p2.stdout)
    print("stderr:", p2.stderr)
else:
    print("yosys stderr:", p1.stderr)
