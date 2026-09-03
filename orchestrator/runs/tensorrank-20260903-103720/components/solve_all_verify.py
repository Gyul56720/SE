def check(output, inputs):
    from fractions import Fraction
    
    cases = output.get("cases", [])
    if len(cases) != 3:
        return False, f"Expected 3 cases, got {len(cases)}"
        
    targets = {
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
            "budget": 26,
            "entries": {
                (0, 0, 0): 1, (0, 1, 1): 1, (0, 2, 2): 1,
                (1, 3, 0): 1, (1, 4, 1): 1, (1, 5, 2): 1,
                (2, 6, 0): 1, (2, 7, 1): 1, (2, 8, 2): 1,
                (3, 0, 3): 1, (3, 1, 4): 1, (3, 2, 5): 1,
                (4, 3, 3): 1, (4, 4, 4): 1, (4, 5, 5): 1,
                (5, 6, 3): 1, (5, 7, 4): 1, (5, 8, 5): 1,
                (6, 0, 6): 1, (6, 1, 7): 1, (6, 2, 8): 1,
                (7, 3, 6): 1, (7, 4, 7): 1, (7, 5, 8): 1,
                (8, 6, 6): 1, (8, 7, 7): 1, (8, 8, 8): 1
            }
        }
    }
    
    def parse_val(v):
        if isinstance(v, (int, float)):
            f = Fraction(v).limit_denominator(12)
        elif isinstance(v, str):
            f = Fraction(v)
        else:
            raise ValueError(f"Invalid value {v}")
        if abs(f) > 8 or f.denominator > 12:
            raise ValueError(f"Lattice constraint violated: {f}")
        return f
        
    for c in cases:
        cid = c["id"]
        if cid not in targets:
            return False, f"Unknown case {cid}"
        tgt = targets[cid]
        d0, d1, d2 = tgt["shape"]
        M = c["rank"]
        if M > tgt["budget"]:
            return False, f"Case {cid}: rank {M} exceeds budget {tgt['budget']}"
            
        u, v, w = c["u"], c["v"], c["w"]
        if len(u) != M or len(v) != M or len(w) != M:
            return False, f"Case {cid}: list lengths do not match rank {M}"
            
        # Reconstruct tensor
        recon = {}
        for r in range(M):
            if len(u[r]) != d0 or len(v[r]) != d1 or len(w[r]) != d2:
                return False, f"Case {cid}: vector shape mismatch at rank {r}"
            u_r = [parse_val(x) for x in u[r]]
            v_r = [parse_val(x) for x in v[r]]
            w_r = [parse_val(x) for x in w[r]]
            
            for a in range(d0):
                if u_r[a] == 0: continue
                for b in range(d1):
                    if v_r[b] == 0: continue
                    prod_ab = u_r[a] * v_r[b]
                    for c_idx in range(d2):
                        if w_r[c_idx] == 0: continue
                        val = prod_ab * w_r[c_idx]
                        key = (a, b, c_idx)
                        recon[key] = recon.get(key, Fraction(0)) + val
                        
        # Check exact equality
        for key, val in recon.items():
            expected = tgt["entries"].get(key, 0)
            if val != expected:
                return False, f"Case {cid}: mismatch at {key}, expected {expected}, got {val}"
        for key, val in tgt["entries"].items():
            if recon.get(key, Fraction(0)) != val:
                return False, f"Case {cid}: missing entry at {key}, expected {val}"
                
    return True, "All cases exactly verified within budget"
