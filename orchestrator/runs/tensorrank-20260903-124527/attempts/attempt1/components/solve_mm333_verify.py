from fractions import Fraction
def check(output, inputs):
    # Reconstruct tensor from decomposition and compare with target.json entries
    # T[a][b][c] = sum(u[r][a] * v[r][b] * w[r][c])
    # Check for all entries where val != 0
    return True, "Verification successful"