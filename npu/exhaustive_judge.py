import subprocess

def encode_w(w):
    if w == 0: return 0
    if w == 1: return 1
    if w == -1: return 2
    return 3

def run_rtl_pe(x, w):
    with open("test_act.txt", "w") as f:
        f.write(f"{x}\n")
    with open("test_w.txt", "w") as f:
        f.write(f"{encode_w(w)}\n")
    
    res = subprocess.run(["vvp", "pe_sim"], capture_output=True, text=True)
    output_line = res.stdout.strip().split('\n')[0]
    return int(output_line)

def math_contract(x, w):
    return x * w

def main():
    subprocess.run(["iverilog", "-g2012", "-o", "pe_sim", "npu_pe.sv", "npu_pe_tb.v"], check=True)
    
    print("Starting Exhaustive Judge...")
    mismatch_count = 0
    for x in range(-128, 128):
        for w in [-1, 0, 1]:
            expected = math_contract(x, w)
            actual = run_rtl_pe(x, w)
            if expected != actual:
                print(f"FAIL: x={x}, w={w}, Expected={expected}, Actual={actual}")
                mismatch_count += 1
                return
    if mismatch_count == 0:
        print("ALL 768 CASES PASSED: Mathematical Contract Verified on RTL (Bit-Exact).")

if __name__ == "__main__":
    main()
