def solve(inputs):
    N = 91
    factors = []
    d = 2
    temp = N
    while d * d <= temp:
        if temp % d == 0:
            factors.append(d)
            while temp % d == 0:
                temp //= d
        d += 1
    if temp > 1:
        factors.append(temp)
    return {"N": N, "factors": factors}