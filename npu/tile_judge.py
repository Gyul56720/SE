import numpy as np
import subprocess

def encode_w(w):
    if w == 0: return 0
    if w == 1: return 1
    if w == -1: return 2
    return 3

def decode_w(code):
    if code == 0: return 0
    if code == 1: return 1
    if code == 2: return -1
    return 0

# 1. 1,000회 무작위 Vector Stimulus 생성
num_tests = 1000
rng = np.random.default_rng(2026)

stimulus_data = []
golden_results = []

for _ in range(num_tests):
    x = rng.integers(-128, 128, size=16, dtype=np.int16)
    w = rng.choice([-1, 0, 1], size=16)
    
    # Golden Sum
    y_gold = int(np.sum(x * w))
    golden_results.append(y_gold)
    
    w_encoded = [encode_w(val) for val in w]
    stimulus_data.append((x, w_encoded))

# Stimulus 파일 쓰기
with open("tile_stimulus.txt", "w") as f:
    for x, w_enc in stimulus_data:
        x_str = " ".join(map(str, x))
        w_str = " ".join(map(str, w_enc))
        f.write(f"{x_str} {w_str}\n")

# RTL 컴파일 및 시뮬레이션
subprocess.run(["iverilog", "-g2012", "-o", "tile_sim", "npu_pe.sv", "npu_tile.sv", "npu_tile_tb.sv"], check=True)
subprocess.run(["vvp", "tile_sim"], check=True)

# RTL 결과 대조
rtl_results = []
with open("tile_results.txt", "r") as f:
    for line in f:
        if line.strip():
            rtl_results.append(int(line.strip()))

mismatches = 0
for i, (g, r) in enumerate(zip(golden_results, rtl_results)):
    if g != r:
        print(f"FAIL at test {i}: Expected {g}, Got {r}")
        mismatches += 1

if mismatches == 0 and len(rtl_results) == num_tests:
    print("=========================================================")
    print("SUCCESS: npu_tile.sv PASSED 1,000 RANDOM VECTOR TESTS!")
    print("Y_RTL == Y_Golden (Bit-Exact Verification Confirmed)")
    print("=========================================================")
else:
    print(f"FAILED: {mismatches} mismatches out of {len(rtl_results)} tests.")
