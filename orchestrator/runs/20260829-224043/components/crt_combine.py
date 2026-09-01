def solve(inputs):
    N = inputs["factor"]["N"]
    factors = inputs["factor"]["factors"]
    solutions_mod = inputs["sub_equations"]["solutions_mod"]
    
    p1, p2 = factors[0], factors[1]
    sols1 = solutions_mod[str(p1)]
    sols2 = solutions_mod[str(p2)]
    
    all_sols = set()
    for a1 in sols1:
        for a2 in sols2:
            inv_p1 = pow(p1, -1, p2)
            x = (a1 + p1 * ((a2 - a1) * inv_p1 % p2)) % N
            all_sols.add(x)
            
    return {"solutions": sorted(list(all_sols))}