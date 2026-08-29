def check(output, inputs):
    N = inputs["factor"]["N"]
    sols = output["solutions"]
    for x in sols:
        if (x * x - 16) % N != 0:
            return False, f"{x} is not a solution mod {N}"
    # Also check if we found all 4 expected solutions
    if len(sols) != 4:
        return False, f"Expected 4 solutions, found {len(sols)}"
    return True, ""