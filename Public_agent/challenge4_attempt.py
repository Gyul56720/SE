import sys
import os
import base64
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Public_agent.challenge4 import CIPHERTEXT, EXPECTED_SHA256, MASK64, xorshift64_stream, perm_indices
except ModuleNotFoundError:
    from challenge4 import CIPHERTEXT, EXPECTED_SHA256, MASK64, xorshift64_stream, perm_indices

def rotr8(b: int, r: int) -> int:
    r &= 7
    return ((b >> r) | (b << (8 - r))) & 0xFF

def xorshift64_step(s: int) -> int:
    s ^= (s << 13) & MASK64
    s ^= (s >> 7)
    s ^= (s << 17) & MASK64
    return s & MASK64

def mat_vec_mul(M, v):
    res = 0
    for i in range(64):
        if (v >> i) & 1:
            res ^= M[i]
    return res

def mat_mul(A, B):
    C = []
    for i in range(64):
        C.append(mat_vec_mul(A, B[i]))
    return C

def solve() -> str:
    # 1. Base85 decode
    v = base64.b85decode(CIPHERTEXT)
    n = len(v)

    # 2. Reverse permutation
    idx = perm_indices(n)
    u = bytearray(n)
    for pos in range(n):
        u[idx[pos]] = v[pos]

    # 3. Reverse rotl8 -> rotr8
    t = bytes([rotr8(u[i], (i % 5) + 1) for i in range(n)])

    # 4. Construct GF(2) linear system for xorshift64 state S0 (seed)
    matrix = []
    for i in range(64):
        unit = 1 << i
        matrix.append(xorshift64_step(unit))

    M_powers = [matrix]
    for k in range(1, n + 2):
        M_powers.append(mat_mul(matrix, M_powers[-1]))

    equations = []
    for k in range(n):
        Mk = M_powers[k]
        row_mask = 0
        for i in range(64):
            if (Mk[i] >> 7) & 1:
                row_mask |= (1 << i)
        rhs = (t[k] >> 7) & 1
        equations.append([row_mask, rhs])

    # 5. Gaussian Elimination over GF(2)
    rows = len(equations)
    pivot_row = 0
    pivot_cols = []

    for col in range(64):
        found = -1
        for r in range(pivot_row, rows):
            if (equations[r][0] >> col) & 1:
                found = r
                break
        if found == -1:
            continue
        equations[pivot_row], equations[found] = equations[found], equations[pivot_row]
        pivot_cols.append((col, pivot_row))

        for r in range(rows):
            if r != pivot_row and ((equations[r][0] >> col) & 1):
                equations[r][0] ^= equations[pivot_row][0]
                equations[r][1] ^= equations[pivot_row][1]
        pivot_row += 1

    if len(pivot_cols) < 64:
        raise ValueError("Could not uniquely determine seed from GF(2) linear system")

    seed = 0
    for col, r in pivot_cols:
        if equations[r][1]:
            seed |= (1 << col)

    # 6. Reconstruct stream & plaintext
    ks = xorshift64_stream(seed, n)
    p = bytes([t[i] ^ ks[i] for i in range(n)])
    return p.decode("ascii")

def main():
    recovered = solve()
    digest = hashlib.sha256(recovered.encode()).hexdigest()
    match = digest == EXPECTED_SHA256

    print(f"Recovered string: {recovered}")
    print(f"Calculated SHA-256: {digest}")
    print(f"Expected SHA-256: {EXPECTED_SHA256}")
    print(f"Match status: {match}")

    if not match:
        raise ValueError("SHA-256 mismatch!")

if __name__ == "__main__":
    main()
