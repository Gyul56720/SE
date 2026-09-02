import numpy as np

# Qwen2.5-Coder-7B Parameters
HIDDEN_SIZE = 3584
PAD_SIZE = 4096 # 256 tiles x 16 PEs

# 1. Theoretical Bounds Calculation
max_pos_3584 = HIDDEN_SIZE * 127
max_neg_3584 = HIDDEN_SIZE * (-128)

s16_max = 32767
s16_min = -32768

print("=== Qwen2.5-Coder-7B (hidden_size=3584) Accumulator Analysis ===")
print(f"Theoretical Max Positive Sum (3584 * +127) = {max_pos_3584:,}")
print(f"Theoretical Max Negative Sum (3584 * -128) = {max_neg_3584:,}")
print(f"16-bit Signed Accumulator Range           = [{s16_min:,}, {s16_max:,}]")
print(f"S16 Overflow Multiplier                    = {max_pos_3584 / s16_max:.2f}x overflow!")

# 2. Minimum Required Bit Width
bits_required = int(np.ceil(np.log2(abs(max_neg_3584)))) + 1 # +1 for sign bit
print(f"Minimum Required Accumulator Width          = {bits_required} bits")

s21_max = (1 << 20) - 1
s21_min = -(1 << 20)
print(f"Current RTL 21-bit Accumulator Range        = [{s21_min:,}, {s21_max:,}]")
print(f"21-bit Accumulator Headroom Margin          = {s21_max / max_pos_3584:.2f}x safety headroom!")

# 3. Simulation of S16 overflow vs S21 accuracy on Qwen2.5 random activation/weight distribution
rng = np.random.default_rng(2026)
num_trials = 1000
overflow_count_s16 = 0

for _ in range(num_trials):
    x = rng.integers(-128, 128, size=HIDDEN_SIZE, dtype=np.int16)
    w = rng.choice([-1, 0, 1], size=HIDDEN_SIZE, p=[0.325, 0.35, 0.325])
    dot_prod = int(np.sum(x * w))
    
    # Check if fit in S16
    if dot_prod > s16_max or dot_prod < s16_min:
        overflow_count_s16 += 1

print(f"\n--- 1,000 Trial Qwen2.5-Coder-7B Layer Simulation ---")
print(f"S16 Overflow Rate                           = {overflow_count_s16 / num_trials * 100:.1f}% of layers overflow in 16-bit!")
print(f"S21 Overflow Rate                           = 0.0% (Bit-Exact Guaranteed)")

