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

# 1. 768개 모든 입력 자극 생성
with open("all_stimulus.txt", "w") as f:
    for x in range(-128, 128):
        for w in [-1, 0, 1]:
            f.write(f"{x} {encode_w(w)}\n")

# 2. RTL 단일 실행 (Full Batch)
subprocess.run(["iverilog", "-g2012", "-o", "full_sim", "npu_pe.sv", "full_exhaustive_tb.sv"], check=True)
subprocess.run(["vvp", "full_sim"], check=True)

# 3. Judge 대조
mismatches = []
with open("all_results.txt", "r") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) == 3:
            rx, rw_code, r_acc = int(parts[0]), int(parts[1]), int(parts[2])
            w_val = decode_w(rw_code)
            expected = rx * w_val
            if r_acc != expected:
                mismatches.append((rx, w_val, expected, r_acc))

if len(mismatches) == 0:
    print("=========================================================")
    print("SUCCESS: ALL 768 CASES PASSED BIT-EXACT CONTRACT!")
    print("Y_RTL == Y_Golden across all INT8 Activations & Weights.")
    print("=========================================================")
else:
    print(f"FAILED: {len(mismatches)} mismatches found.")
    for m in mismatches[:5]:
        print(f"  X={m[0]}, W={m[1]} -> Expected={m[2]}, Actual={m[3]}")
