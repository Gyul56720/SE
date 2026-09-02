import numpy as np
import subprocess

def run_verify():
    N = 4096
    # 1. Generate random test case (Contract compliant)
    x = np.random.randint(-128, 127, N, dtype=np.int16)
    w_logic = np.random.choice([-1, 0, 1], size=N)
    
    # 2. Encoding {00:0, 01:+1, 10:-1}
    def encode(w):
        if w == 0: return 0b00
        if w == 1: return 0b01
        if w == -1: return 0b10
    
    w_encoded = [encode(val) for val in w_logic]
    
    # 3. Y_gold (Contract)
    y_gold = int(np.sum(x * w_logic))
    
    # 4. Save for RTL
    with open("act_in.bin", "w") as f:
        for val in x:
            f.write(format(val & 0xFF, '08b') + "\n")
    with open("weight_in.bin", "w") as f:
        for val in w_encoded:
            f.write(format(val, '02b') + "\n")
    
    # 5. Run RTL (Simulate)
    # Using iverilog
    subprocess.run(["iverilog", "-g2012", "-o", "npu_sim", "npu_pe.sv", "npu_array_4096.sv", "npu_testbench.sv"])
    res = subprocess.run(["vvp", "npu_sim"], capture_output=True, text=True)
    y_rtl = int(res.stdout.strip())
    
    # 6. Judge
    if y_rtl == y_gold:
        print(f"PASS: Y_rtl({y_rtl}) == Y_gold({y_gold})")
    else:
        print(f"FAIL: Y_rtl({y_rtl}) != Y_gold({y_gold})")

run_verify()
