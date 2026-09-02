import numpy as np
import subprocess
import sys

def encode_w(w):
    if w == 0: return 0
    if w == 1: return 1
    if w == -1: return 2
    return 3

print("=== [Fuzz / Self-Improvement Test Engine] Starting ===")

# Create a randomized input activation and weight pattern
rng = np.random.default_rng(42)
N = 4096

x = rng.integers(-128, 128, size=N, dtype=np.int16)
w = rng.choice([-1, 0, 1], size=N, p=[0.33, 0.34, 0.33])

y_gold = int(np.sum(x * w))
print(f"[Gold Reference] Calculated dot product: {y_gold}")

# Write raw files
with open("array_act_hex.txt", "w") as f_act:
    for val in x: f_act.write(f"{val & 0xFF:02x}\n")

with open("array_w_hex.txt", "w") as f_w:
    for val in w: f_w.write(f"{encode_w(val):02b}\n")

# Run simulation compile
compile_cmd = [
    "iverilog", "-g2012", "-o", "axi_sim",
    "npu_pe.sv", "npu_tile.sv", "npu_array_4096.sv", "npu_axi_top.sv", "npu_axi_testbench.sv"
]
res_comp = subprocess.run(compile_cmd, capture_output=True, text=True)
if res_comp.returncode != 0:
    print("Compilation Error:\n", res_comp.stderr)
    sys.exit(1)

# Run simulation
res_sim = subprocess.run(["vvp", "axi_sim"], capture_output=True, text=True)
print(res_sim.stdout)

if "SUCCESS" in res_sim.stdout:
    print("=== [SELF-IMPROVEMENT STATUS] GREEN: Full AXI Protocol Verification Passed! ===")
    sys.exit(0)
else:
    print("=== [SELF-IMPROVEMENT STATUS] RED: Mismatch detected! ===")
    sys.exit(1)
