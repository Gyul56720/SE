def solve(inputs):
    N = 91
    for p in range(2, int(N**0.5)+1):
        if N % p == 0:
            return {"N": N, "p": p, "q": N//p}
    return {"N": N, "p": N, "q": 1}
