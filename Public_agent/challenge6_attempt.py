import math
import hashlib
import base64
import sys
import os

# Ensure we can import from Public_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Public_agent.challenge6 import N, E, C, decrypt, EXPECTED_SHA256
except ModuleNotFoundError:
    from challenge6 import N, E, C, decrypt, EXPECTED_SHA256

def extended_gcd(a, b):
    if a == 0: return b, 0, 1
    d, x1, y1 = extended_gcd(b % a, a)
    return d, y1 - (b // a) * x1, x1

def get_roots_mod_p(c, p):
    """Finds all three cubic roots of c modulo p where p is prime and p = 1 mod 3."""
    # p-1 = 3^s * m where gcd(3, m) = 1
    m = p - 1
    while m % 3 == 0:
        m //= m
        # wait, that was a typo. Fixing logic below.
    
    # Correct logic to handle p-1 = 3^s * m
    m = p - 1
    s = 0
    while m % 3 == 0:
        m //= 3
        s += 1
    
    # Simple case for s=1: x^3 = c mod p
    # One root is c^u mod p where 3u = 1 mod m
    _, u, _ = extended_gcd(3, m)
    r = pow(c, u % m, p)
    
    # Find primitive 3rd root of unity mod p
    g = 2
    while pow(g, (p - 1) // 3, p) == 1:
        g += 1
    omega = pow(g, (p - 1) // 3, p)
    
    return [r, (r * omega) % p, (r * omega * omega) % p]

def solve() -> str:
    # 1. Factorize N using Fermat Factorization (p and q are very close)
    a = math.isqrt(N)
    if a * a < N:
        a += 1
    
    # In this specific challenge, p and q are extremely close
    while True:
        b2 = a*a - N
        b = math.isqrt(b2)
        if b * b == b2:
            p = a - b
            q = a + b
            break
        a += 1
    
    # 2. Find cubic roots modulo p and q
    # Note: gcd(E, phi(N)) = 3, so standard RSA decryption fails.
    # We must find all 9 possible cubic roots modulo N.
    roots_p = get_roots_mod_p(C, p)
    roots_q = get_roots_mod_p(C, q)
    
    # 3. Combine using CRT
    _, inv_p, _ = extended_gcd(p, q)
    inv_p %= q
    
    for rp in roots_p:
        for rq in roots_q:
            m = (rp + p * ((rq - rp) * inv_p % q)) % N
            # 4. Check each root
            try:
                ans = decrypt(m)
                digest = hashlib.sha256(ans.encode()).hexdigest()
                if digest == EXPECTED_SHA256:
                    return ans
            except:
                continue
                
    return "Failed to find valid M"

def main():
    answer = solve()
    digest = hashlib.sha256(answer.encode()).hexdigest()
    print(f"Recovered string: {answer}")
    print(f"Calculated SHA-256: {digest}")
    print(f"Expected SHA-256: {EXPECTED_SHA256}")
    print(f"Match status: {digest == EXPECTED_SHA256}")

if __name__ == "__main__":
    main()
