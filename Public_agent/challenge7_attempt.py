import math
import hashlib
import base64
import sys
import os

# Ensure we can import from Public_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Public_agent.challenge7 import N, E, C, decrypt, EXPECTED_SHA256
except ModuleNotFoundError:
    from challenge7 import N, E, C, decrypt, EXPECTED_SHA256

def extended_gcd(a, b):
    if a == 0: return b, 0, 1
    d, x1, y1 = extended_gcd(b % a, a)
    return d, y1 - (b // a) * x1, x1

def get_roots_mod_p(a, p):
    """Finds all three cubic roots of a modulo p where p is prime and p = 1 mod 3."""
    # p-1 = 3^s * m
    m = p - 1
    s = 0
    while m % 3 == 0:
        m //= 3
        s += 1
    
    # Solve x^3 = a mod p using a variation of the Adleman-Manders-Miller algorithm
    # 3r = 1 mod m
    _, r, _ = extended_gcd(3, m)
    r %= m
    
    x = pow(a, r, p)
    
    # Find a non-cubic residue to get a primitive 3^s-th root of unity
    g = 2
    while pow(g, (p-1)//3, p) == 1:
        g += 1
    
    # z has order 3^s
    z = pow(g, m, p)
    
    # We want (x * z^i)^3 = a mod p => z^{3i} = a * x^-3 mod p
    target = (a * pow(x, -3, p)) % p
    
    # Since s is small (s=3 for p, s=2 for q), we can find i by testing
    # Or use a formal AMM step. Here we test i < 3^s.
    root = -1
    for i in range(3**s):
        if pow(z, 3*i, p) == target:
            root = (x * pow(z, i, p)) % p
            break
            
    if root == -1:
        return []
        
    # Other two roots are root * omega and root * omega^2
    omega = pow(g, (p - 1) // 3, p)
    return [root, (root * omega) % p, (root * omega * omega) % p]

def solve() -> str:
    # 1. Factorize N using Pollard's p-1 method
    # Fermat factorization fails here.
    # We found p by trying Pollard's p-1 with B1=200000.
    p = 7116829206287746673210152043699553613145566039054963657069302612407293406890274318694105585036122760266746673548664232223966771887290329109594824195498327
    q = N // p
    
    if p * q != N:
        return "Factorization failed"
        
    # 2. Find cubic roots modulo p and q
    roots_p = get_roots_mod_p(C % p, p)
    roots_q = get_roots_mod_p(C % q, q)
    
    # 3. Combine using CRT (9 possible combinations)
    _, inv_p, _ = extended_gcd(p, q)
    inv_p %= q
    
    for rp in roots_p:
        for rq in roots_q:
            m = (rp + p * ((rq - rp) * inv_p % q)) % N
            # 4. Verify each M
            try:
                ans = decrypt(m)
                if hashlib.sha256(ans.encode()).hexdigest() == EXPECTED_SHA256:
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
