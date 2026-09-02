import numpy as np
import subprocess

def encode_w(w):
    if w == 0: return 0
    if w == 1: return 1
    if w == -1: return 2
    return 3

# Corner Case: Maximum Overflow Test
N = 4096
x = np.full(N, 127, dtype=np.int16)
w = np.full(N, 1, dtype=np.int8)

y_gold = int(np.sum(x * w))
print(f"Golden Reference (Max Overflow): {y_gold}")

# Write Hex files for SystemVerilog $fscanf
with open("array_act_hex.txt", "w") as f_act:
    for val in x: f_act.write(f"{val & 0xFF:02x}\n")

with open("array_w_hex.txt", "w") as f_w:
    for val in w: f_w.write(f"{encode_w(val):02b}\n")

# RTL 컴파일 및 실행
subprocess.run(["iverilog", "-g2012", "-o", "axi_sim", "npu_pe.sv", "npu_tile.sv", "npu_array_4096.sv", "npu_axi_top.sv", "npu_axi_testbench.sv"], check=True)
res = subprocess.run(["vvp", "axi_sim"], capture_output=True, text=True)

print("\n--- Simulation Output ---")
print(res.stdout)

if str(y_gold) in res.stdout:
    print("AXI4 INTEGRATION SUCCESS: Bit-Exact Result Verified via SoC Interface.")
else:
    print("AXI4 INTEGRATION FAILED: Result Mismatch.")
