def check(output, inputs):
    import fractions

    def parse_val(x):
        if isinstance(x, int):
            return fractions.Fraction(x, 1)
        elif isinstance(x, str):
            return fractions.Fraction(x)
        elif isinstance(x, float):
            return fractions.Fraction(x).limit_denominator(12)
        return fractions.Fraction(0, 1)

    expected_cases = {
        "w_state": {
            "shape": [2, 2, 2],
            "budget": 3,
            "entries": {(0, 0, 1): 1, (0, 1, 0): 1, (1, 0, 0): 1}
        },
        "mm222": {
            "shape": [4, 4, 4],
            "budget": 7,
            "entries": {
                (0, 0, 0): 1, (0, 1, 1): 1, (1, 2, 0): 1, (1, 3, 1): 1,
                (2, 0, 2): 1, (2, 1, 3): 1, (3, 2, 2): 1, (3, 3, 3): 1
            }
        },
        "mm333": {
            "shape": [9, 9, 9],
            "budget": 27,
            "entries": {
                (3*i + j, 3*j + k, 3*i + k): 1
                for i in range(3) for j in range(3) for k in range(3)
            }
        }
    }

    out_cases = output.get("cases", [])
    if len(out_cases) != len(expected_cases):
        return False, f"Expected {len(expected_cases)} cases, got {len(out_cases)}"

    for c in out_cases:
        cid = c.get("id")
        if cid not in expected_cases:
            return False, f"Unknown case id: {cid}"
        spec = expected_cases[cid]
        rank = c.get("rank")
        if rank > spec["budget"]:
            return False, f"Case {cid}: rank {rank} exceeds budget {spec['budget']}"

        u, v, w = c.get("u", []), c.get("v", []), c.get("w", [])
        if not (len(u) == len(v) == len(w) == rank):
            return False, f"Case {cid}: length mismatch in factors"

        d0, d1, d2 = spec["shape"]
        for r in range(rank):
            if len(u[r]) != d0 or len(v[r]) != d1 or len(w[r]) != d2:
                return False, f"Case {cid}: vector shape mismatch at rank {r}"
            for val in u[r] + v[r] + w[r]:
                f = parse_val(val)
                if abs(f) > 8 or f.denominator > 12:
                    return False, f"Case {cid}: lattice constraint violated by {val}"

        # Reconstruct tensor
        recon = {}
        for r in range(rank):
            u_r = [parse_val(x) for x in u[r]]
            v_r = [parse_val(x) for x in v[r]]
            w_r = [parse_val(x) for x in w[r]]
            for a in range(d0):
                if u_r[a] == 0: continue
                for b in range(d1):
                    if v_r[b] == 0: continue
                    uv = u_r[a] * v_r[b]
                    for c_idx in range(d2):
                        if w_r[c_idx] == 0: continue
                        key = (a, b, c_idx)
                        recon[key] = recon.get(key, fractions.Fraction(0, 1)) + uv * w_r[c_idx]

        # Check exact equality
        for a in range(d0):
            for b in range(d1):
                for c_idx in range(d2):
                    key = (a, b, c_idx)
                    expected_val = fractions.Fraction(spec["entries"].get(key, 0), 1)
                    actual_val = recon.get(key, fractions.Fraction(0, 1))
                    if expected_val != actual_val:
                        return False, f"Case {cid}: mismatch at {key}, expected {expected_val} got {actual_val}"

    return True, "All cases decomposed and verified exactly within budgets and lattice constraints."