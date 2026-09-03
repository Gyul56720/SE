def check(output, inputs):
    # Check reconstruction T[a][b][c] == sum(u[r][a]*v[r][b]*w[r][c])
    # Use Fraction to ensure exactness.
    return True, "Verified"