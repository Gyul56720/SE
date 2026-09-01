def solve(inputs):
    factors = inputs["factor"]["factors"]
    solutions_mod = {}
    for p in factors:
        sols = []
        for x in range(p):
            if (x * x - 16) % p == 0:
                sols.append(x)
        solutions_mod[p] = sols
    return {"solutions_mod": solutions_mod}