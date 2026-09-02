import subprocess
import sys
import os
import re

def run_test():
    res = subprocess.run(["python3", "axi_fuzz_tester.py"], capture_output=True, text=True)
    return "SUCCESS" in res.stdout or "GREEN" in res.stdout

print("=========================================================================")
print("=== [NPU Self-Improvement Loop] Attempting Performance Optimization ===")
print("=========================================================================")

# Goal: Pipeline the reduction tree in npu_tile.sv to improve fMAX (Timing Closure)
print("\n[Step 1] Reading current RTL (npu_tile.sv and npu_array_4096.sv)...")

with open("npu_tile.sv", "r") as f:
    tile_code = f.read()
with open("npu_array_4096.sv", "r") as f:
    array_code = f.read()

# Improvement: Convert combinational tile tree to pipelined tree (4 stages)
improved_tile = re.sub(
    r"always_comb begin.*?end",
    """always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for(int i=0; i<8; i++) stage1[i] <= 0;
            for(int i=0; i<4; i++) stage2[i] <= 0;
            for(int i=0; i<2; i++) stage3[i] <= 0;
            stage4 <= 0;
        end else begin
            for (int k = 0; k < 8; k++)  stage1[k] <= pe_acc[2*k] + pe_acc[2*k+1];
            for (int k = 0; k < 4; k++)  stage2[k] <= stage1[2*k] + stage1[2*k+1];
            for (int k = 0; k < 2; k++)  stage3[k] <= stage2[2*k] + stage2[2*k+1];
            stage4 <= stage3[0] + stage3[1];
        end
    end""",
    tile_code, flags=re.DOTALL
)

# Update npu_tile.sv assign statements
improved_tile = improved_tile.replace("assign tile_out  = stage4;", "assign tile_out  = stage4;") # already correct
improved_tile = re.sub(
    r"assign valid_out = pe_valid\[0\];",
    """logic [3:0] tile_v_pipe;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) tile_v_pipe <= 4'b0;
        else tile_v_pipe <= {tile_v_pipe[2:0], pe_valid[0]};
    end
    assign valid_out = tile_v_pipe[3];""",
    improved_tile
)

# Since npu_tile now has 4 more cycles of latency, adjust npu_array_4096's valid_pipe
# Total latency was 10, now it should be 14.
# In npu_array_4096, valid_pipe is 10 bits. We need to make it 14 bits.
improved_array = array_code.replace("logic [9:0] valid_pipe;", "logic [13:0] valid_pipe;")
improved_array = improved_array.replace("valid_pipe <= 10'b0;", "valid_pipe <= 14'b0;")
improved_array = improved_array.replace("valid_pipe <= {valid_pipe[8:0], tile_valid[0]};", "valid_pipe <= {valid_pipe[12:0], tile_valid[0]};")
improved_array = improved_array.replace("assign valid_out = valid_pipe[9];", "assign valid_out = valid_pipe[13];")

print("[Step 2] Applying optimization patches to RTL...")
with open("npu_tile.sv", "w") as f:
    f.write(improved_tile)
with open("npu_array_4096.sv", "w") as f:
    f.write(improved_array)

print("[Step 3] Verifying functional correctness (Bit-Exact) with new pipeline depth...")
if run_test():
    print("\n=== [IMPROVEMENT SUCCESS] RTL successfully pipelined for higher throughput! ===")
    print("Functional verification passed with 14-cycle latency (previously 10).")
    sys.exit(0)
else:
    print("\n=== [IMPROVEMENT FAILED] Functional mismatch or simulation error. Reverting... ===")
    with open("npu_tile.sv", "w") as f:
        f.write(tile_code)
    with open("npu_array_4096.sv", "w") as f:
        f.write(array_code)
    sys.exit(1)
