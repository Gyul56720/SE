import numpy as np
import subprocess
import sys

def encode_w(w):
    if w == 0: return 0
    if w == 1: return 1
    if w == -1: return 2
    return 3

print("=== Compiling SystemVerilog AXI4 Top & Testbench ===")
compile_cmd = [
    "iverilog", "-g2012", "-o", "axi_sim",
    "npu_pe.sv", "npu_tile.sv", "npu_array_4096.sv", "npu_axi_top.sv", "npu_axi_testbench.sv"
]

res_comp = subprocess.run(compile_cmd, capture_output=True, text=True)
if res_comp.returncode != 0:
    print("Compilation Error:\n", res_comp.stderr)
    sys.exit(1)

print("Compilation Successful! Running Simulation...")
res_sim = subprocess.run(["vvp", "axi_sim"], capture_output=True, text=True)
print(res_sim.stdout)

if "ALL AXI4 RTL INTEGRATION & CORNER TESTS PASSED BIT-EXACT!" in res_sim.stdout:
    print(">> SUCCESS: AXI4 Bus Protocol, Memory Mapping, and Corner Cases are Bit-Exact!")
    sys.exit(0)
else:
    print(">> FAILURE: Testbench did not pass cleanly.")
    if res_sim.stderr:
        print(res_sim.stderr)
    sys.exit(1)
