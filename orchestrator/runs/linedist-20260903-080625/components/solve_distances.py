def solve(inputs):
    import json
    import numpy as np
    with open('/home/ubuntu/SE/orchestrator/problems/line_distance/cases.json', 'r') as f:
        cases = json.load(f)
    results = []
    for case in cases:
        case_id = case['id']
        p1 = np.array(case['p1'], dtype=float)
        v1 = np.array(case['v1'], dtype=float)
        p2 = np.array(case['p2'], dtype=float)
        v2 = np.array(case['v2'], dtype=float)
        X = np.column_stack((v1, -v2))
        y = p2 - p1
        beta, residuals, rank, s_vals = np.linalg.lstsq(X, y, rcond=None)
        t, s = float(beta[0]), float(beta[1])
        pt1 = p1 + t * v1
        pt2 = p2 + s * v2
        dist = float(np.linalg.norm(pt1 - pt2))
        results.append({
            "id": case_id,
            "t": t,
            "s": s,
            "distance": dist
        })
    return {"cases": results}