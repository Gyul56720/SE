import numpy as np
import subprocess

def encode_w(w):
    if w == 0: return 0
    if w == 1: return 1
    if w == -1: return 2
    return 3

layer_configs = [
    {"name": "q_proj", "sparsity": 0.35},
    {"name": "k_proj", "sparsity": 0.40},
    {"name": "v_proj", "sparsity": 0.30},
    {"name": "gate_proj", "sparsity": 0.50},
]

N = 4096
rng = np.random.default_rng(2026_09)

golden_results = []
test_names = []

with open("array_act.txt", "w") as f_act, open("array_w.txt", "w") as f_w:
    for cfg in layer_configs:
        x = rng.integers(-128, 128, size=N, dtype=np.int16)
        sp = cfg["sparsity"]
        w = rng.choice([-1, 0, 1], size=N, p=[(1-sp)/2, sp, (1-sp)/2])
        
        y_gold = int(np.sum(x * w))
        golden_results.append(y_gold)
        test_names.append(cfg["name"])
        
        w_encoded = [encode_w(val) for val in w]
        f_act.write("\n".join(map(str, x)) + "\n")
        f_w.write("\n".join(map(str, w_encoded)) + "\n")

# RTL 컴파일 및 실행
subprocess.run(["iverilog", "-g2012", "-o", "pipelined_sim", "npu_pe.sv", "npu_tile.sv", "npu_array_4096.sv", "npu_array_4096_pipelined_tb.sv"], check=True)
subprocess.run(["vvp", "pipelined_sim"], check=True)

# 결과 수집
rtl_results = []
with open("pipelined_results.txt", "r") as f:
    for line in f:
        if line.strip():
            rtl_results.append(int(line.strip()))

rtl_results = rtl_results[:len(golden_results)]

print("\n==================== PIPELINED BALANCED HIGH-SPEED RTL RESULTS ====================")
all_pass = True
for name, g, r in zip(test_names, golden_results, rtl_results):
    status = "PASS [Bit-Exact]" if g == r else f"FAIL (Gold:{g}, RTL:{r})"
    print(f"Layer [{name:10s}]: Golden = {g:10d} | Pipelined RTL = {r:10d} -> {status}")
    if g != r:
        all_pass = False

if all_pass:
    print("==================================================================================")
    print("PROVEN=1: HIGH-FREQUENCY BALANCED PIPELINED NPU ACCELERATOR PASSED ALL CHECKS!")
    print("==================================================================================")
