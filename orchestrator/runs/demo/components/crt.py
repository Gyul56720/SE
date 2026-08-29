def solve(inputs):
    r = inputs["B"]; p, q = r["p"], r["q"]
    def inv(a, m):
        return pow(a, -1, m)
    sols = []
    for a in r["rp"]:
        for b in r["rq"]:
            x = (a + p*((b-a)*inv(p, q) % q)) % (p*q)
            sols.append(x)
    return {"N": p*q, "target": r["target"], "solutions": sorted(sols)}
