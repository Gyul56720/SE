def check(output, inputs):
    import json
    import numpy as np
    try:
        with open('/home/ubuntu/SE/orchestrator/problems/line_distance/cases.json', 'r') as f:
            cases = json.load(f)
    except Exception as e:
        return False, f"Failed to load cases: {e}"
    case_dict = {c['id']: c for c in cases}
    out_cases = output.get("cases", [])
    if len(out_cases) != len(cases):
        return False, f"Output cases count {len(out_cases)} does not match input cases count {len(cases)}"
    for oc in out_cases:
        cid = oc.get("id")
        if cid not in case_dict:
            return False, f"Unknown case id {cid}"
        c = case_dict[cid]
        p1 = np.array(c['p1'], dtype=float)
        v1 = np.array(c['v1'], dtype=float)
        p2 = np.array(c['p2'], dtype=float)
        v2 = np.array(c['v2'], dtype=float)
        t = oc.get("t")
        s = oc.get("s")
        dist = oc.get("distance")
        if t is None or s is None or dist is None:
            return False, f"Missing fields in case {cid}"
        pt1 = p1 + t * v1
        pt2 = p2 + s * v2
        calc_dist = np.linalg.norm(pt1 - pt2)
        if abs(calc_dist - dist) > 1e-5:
            return False, f"Case {cid}: Reported distance {dist} does not match computed distance {calc_dist}"
        diff = pt1 - pt2
        diff_len = np.linalg.norm(diff)
        if diff_len > 1e-5:
            v1_len = np.linalg.norm(v1)
            v2_len = np.linalg.norm(v2)
            if v1_len > 1e-9:
                cos1 = abs(np.dot(diff, v1)) / (diff_len * v1_len)
                if cos1 > 1e-4:
                    return False, f"Case {cid}: Shortest vector is not perpendicular to v1 (cos={cos1})"
            if v2_len > 1e-9:
                cos2 = abs(np.dot(diff, v2)) / (diff_len * v2_len)
                if cos2 > 1e-4:
                    return False, f"Case {cid}: Shortest vector is not perpendicular to v2 (cos={cos2})"
        np.random.seed(42)
        for _ in range(100):
            dt, ds = np.random.normal(0, 0.1, 2)
            dt = dt * (1.0 + abs(t))
            ds = ds * (1.0 + abs(s))
            pt1_alt = p1 + (t + dt) * v1
            pt2_alt = p2 + (s + ds) * v2
            alt_dist = np.linalg.norm(pt1_alt - pt2_alt)
            if alt_dist < calc_dist - 1e-5:
                return False, f"Case {cid}: Found smaller distance {alt_dist} at t={t+dt}, s={s+ds} than computed {calc_dist}"
    return True, "All cases verified successfully."