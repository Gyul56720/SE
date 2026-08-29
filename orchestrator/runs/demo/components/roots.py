def solve(inputs):
    f = inputs["A"]; p, q = f["p"], f["q"]
    target = 16  # x^2 ≡ 16
    rp = [x for x in range(p) if (x*x) % p == target % p]
    rq = [x for x in range(q) if (x*x) % q == target % q]
    return {"p": p, "q": q, "target": target, "rp": rp, "rq": rq}
