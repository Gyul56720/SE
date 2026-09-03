def check(output, inputs):
    from fractions import Fraction
    import json

    target_file = "/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-103632/verifiers/target.json"
    with open(target_file, "r") as f:
        target_data = json.load(f)

    target_cases = {c["id"]: c for c in target_data["cases"]}
    sol_cases = {c["id"]: c for c in output.get("cases", [])}

    if len(sol_cases) != len(target_cases):
        return False, f"Case count mismatch: expected {len(target_cases)}, got {len(sol_cases)}"

    def parse_val(v):
        if isinstance(v, (int, float)):
            return Fraction(v).limit_denominator(12)
        elif isinstance(v, str):
            return Fraction(v)
        return Fraction(0)

    for cid, c_target in target_cases.items():
        if cid not in sol_cases:
            return False, f"Missing case {cid}"
        c_sol = sol_cases[cid]
        M = c_sol.get("rank", 0)
        budget = c_target["budget"]
        if M > budget:
            return False, f"Case {cid}: rank {M} exceeds budget {budget}"

        d0, d1, d2 = c_target["shape"]
        u = c_sol.get("u", [])
        v = c_sol.get("v", [])
        w = c_sol.get("w", [])

        if len(u) != M or len(v) != M or len(w) != M:
            return False, f"Case {cid}: u, v, w row count must equal rank M={M}"

        u_frac = [[parse_val(x) for x in row] for row in u]
        v_frac = [[parse_val(x) for x in row] for row in v]
        w_frac = [[parse_val(x) for x in row] for row in w]

        for r in range(M):
            if len(u_frac[r]) != d0 or len(v_frac[r]) != d1 or len(w_frac[r]) != d2:
                return False, f"Case {cid}: dimension mismatch at rank {r}"
            for val in u_frac[r] + v_frac[r] + w_frac[r]:
                if abs(val) > 8 or val.denominator > 12:
                    return False, f"Case {cid}: entry {val} violates lattice constraints"

        # Reconstruct tensor
        T_rec = {}
        for r in range(M):
            for a in range(d0):
                if u_frac[r][a] == 0:
                    continue
                for b in range(d1):
                    if v_frac[r][b] == 0:
                        continue
                    for c in range(d2):
                        if w_frac[r][c] == 0:
                            continue
                        term = u_frac[r][a] * v_frac[r][b] * w_frac[r][c]
                        T_rec[(a, b, c)] = T_rec.get((a, b, c), Fraction(0)) + term

        # Target entries
        T_target = {}
        for entry in c_target["entries"]:
            a, b, c, val = entry
            T_target[(a, b, c)] = Fraction(val)

        all_keys = set(T_rec.keys()) | set(T_target.keys())
        for key in all_keys:
            rec_val = T_rec.get(key, Fraction(0))
            tgt_val = T_target.get(key, Fraction(0))
            if rec_val != tgt_val:
                return False, f"Case {cid}: mismatch at {key}, expected {tgt_val}, got {rec_val}"

    return True, "All tensor decompositions verified exactly within budget and lattice constraints"