def solve(inputs):
    import json
    import numpy as np

    with open('/home/ubuntu/SE/orchestrator/problems/line_distance/cases.json', 'r') as f:
        cases = json.load(f)
        
    results = []
    for case in cases:
        case_id = case['id']
        p1 = np.array(case['p1'], dtype=np.float64)
        v1 = np.array(case['v1'], dtype=np.float64)
        p2 = np.array(case['p2'], dtype=np.float64)
        v2 = np.array(case['v2'], dtype=np.float64)
        
        w0 = p1 - p2
        a = np.dot(v1, v1)
        b = np.dot(v1, v2)
        c = np.dot(v2, v2)
        d = np.dot(v1, w0)
        e = np.dot(v2, w0)
        
        D = a * c - b * b
        
        if a * c == 0:
            if a == 0 and c == 0:
                t, s = 0.0, 0.0
            elif a == 0:
                t = 0.0
                s = e / c
            else:
                s = 0.0
                t = -d / a
        elif D / (a * c) < 1e-14:
            s = 0.0
            t = -d / a
        else:
            t = (b * e - c * d) / D
            s = (a * e - b * d) / D
            
        pt1 = p1 + t * v1
        pt2 = p2 + s * v2
        dist = np.linalg.norm(pt1 - pt2)
        
        results.append({
            "id": case_id,
            "t": float(t),
            "s": float(s),
            "distance": float(dist)
        })
        
    return {"cases": results}