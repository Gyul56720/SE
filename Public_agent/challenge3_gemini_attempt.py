import base64
import hashlib
from Public_agent.challenge3 import OBFUSCATED, MULT, SEED, EXPECTED_SHA256, stride_perm_indices, xorshift32_stream, rotr8

def solve() -> str:
    # 1. Base85 decode
    permuted = base64.b85decode(OBFUSCATED)
    n = len(permuted)
    
    # 2. Step D Inverse (Stride Permutation)
    data = bytearray(n)
    idx = stride_perm_indices(n)
    for pos in range(n):
        data[idx[pos]] = permuted[pos]
        
    # 3. Step C Inverse (rotl8 -> rotr8)
    for i in range(n):
        data[i] = rotr8(data[i], (i % 7) + 1)
        
    # 4. Step B Inverse (XOR -> XOR)
    stream = xorshift32_stream(SEED, n)
    for i in range(n):
        data[i] ^= stream[i]
        
    # 5. Step A Inverse (Affine Inverse)
    # Find MULT_INV such that (MULT * MULT_INV) % 256 == 1
    # MULT is 167, and its modular inverse is 23
    mult_inv = -1
    for x in range(256):
        if (MULT * x) % 256 == 1:
            mult_inv = x
            break
            
    for i in range(n):
        val = (data[i] - (i*i + 7)) & 0xFF
        data[i] = (mult_inv * val) & 0xFF
        
    return data.decode('utf-8', errors='replace')

def main():
    recovered = solve()
    digest = hashlib.sha256(recovered.encode()).hexdigest()
    match = digest == EXPECTED_SHA256
    
    print(f"Recovered string: {recovered}")
    print(f"Calculated SHA-256: {digest}")
    print(f"Expected SHA-256: {EXPECTED_SHA256}")
    print(f"Match status: {match}")
    
    if not match:
        raise ValueError("Failed to recover the original string (SHA-256 mismatch)")

if __name__ == "__main__":
    main()
