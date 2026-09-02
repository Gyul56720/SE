import subprocess
import sys
import os

print("=========================================================================")
print("=== [NPU Self-Healing & Self-Correction Skeleton Loop] Starting Loop ===")
print("=========================================================================")

# Step 1: Inject a deterministic arithmetic fault into npu_pe.sv (Disable multiplication output)
print("\n[Trial 1] Injecting a deterministic arithmetic fault (corrupting PE MUX logic)...")
with open("npu_pe.sv", "r") as f:
    original_code = f.read()

# Introduce bug: 2'b01: term_val = 21'sd0; instead of ext_act
corrupted_code = original_code.replace("2'b01:   term_val = ext_act;", "2'b01:   term_val = 21'sd0; // ARITHMETIC FAULT INJECTED")
with open("npu_pe.sv", "w") as f:
    f.write(corrupted_code)

print("Fault injected successfully. Running verification suite to detect failure...")

# Step 2: Run verification and capture the failure (RED state)
res = subprocess.run(["python3", "axi_fuzz_tester.py"], capture_output=True, text=True)
print("\n--- Verification Output with Fault ---")
print(res.stdout)

if "SUCCESS" not in res.stdout or res.returncode != 0:
    print("\n[RED STATE DETECTED] Self-Healing Engine triggered! Diagnosing fault...")
    
    # Step 3: Self-Healing Search & Correction
    print("Diagnosis: Output mismatch detected (Multiplication logic has been corrupted).")
    print("Action: Reverting and restoring original high-fidelity RTL multiplication block...")
    
    # Healing logic: Revert or fix the specific line
    healed_code = corrupted_code.replace("2'b01:   term_val = 21'sd0; // ARITHMETIC FAULT INJECTED", "2'b01:   term_val = ext_act;")
    with open("npu_pe.sv", "w") as f:
        f.write(healed_code)
        
    print("Healing patch applied successfully! Re-running verification...")
    
    # Step 4: Validate corrected design (GREEN state)
    res_healed = subprocess.run(["python3", "axi_fuzz_tester.py"], capture_output=True, text=True)
    print("\n--- Post-Healing Verification Output ---")
    print(res_healed.stdout)
    
    if "GREEN" in res_healed.stdout or "SUCCESS" in res_healed.stdout:
        print("=== [SELF-HEALING SUCCESS] Trial completed successfully. System returned to GREEN! ===")
        sys.exit(0)
    else:
        print("=== [SELF-HEALING FAILED] Mismatch still remains. ===")
        sys.exit(1)
else:
    print("=== [ERROR] Simulation passed despite fault! Failure detection was not triggered. ===")
    sys.exit(1)
