def check(output, inputs):
    N = output["N"]
    factors = output["factors"]
    prod = 1
    for f in factors:
        prod *= f
    if prod != N:
        return False, "Product of factors does not equal N"
    for f in factors:
        if N % f != 0:
            return False, f"{f} is not a factor of {N}"
    return True, ""