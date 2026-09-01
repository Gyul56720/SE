def check(output, inputs):
    factors = inputs["factor"]["factors"]
    solutions_mod = output["solutions_mod"]
    for p in factors:
        if p not in solutions_mod:
            return False, f"Missing solutions for mod {p}"
        for x in solutions_mod[p]:
            if (x * x - 16) % p != 0:
                return False, f"{x} is not a solution mod {p}"
    return True, ""