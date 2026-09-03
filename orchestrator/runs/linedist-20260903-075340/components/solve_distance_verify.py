def check(output, inputs):
    import json
    import numpy as np
    
    try:
        with open('/home/ubuntu/SE/orchestrator/problems/line_distance/cases.json', 'r') as f:
            cases = json.load(f)
    except Exception as e:
        return False, f"Failed to load inputs: {str(e)}"
        
    case_dict = {c['id']: c for c in cases}
    
    if 'cases' not in output:
        return False, "Output does not contain 'cases'"
        
    for res in output['cases']:
        cid = res['id']
        if cid not in case_dict:
            return False, f"Unknown case id: {cid}"
            
        case = case_dict[cid]
        p1 = np.array(case['p1'], dtype=np.float64)
        v1 = np.array(case['v1'], dtype=np.float64)
        p2 = np.array(case['p2'], dtype=np.float64)
        v2 = np.array(case['v2'], dtype=np.float64)
        
        t = res['t']
        s = res['s']
        reported_dist = res['distance']
        
        pt1 = p1 + t * v1
        pt2 = p2 + s * v2
        actual_dist = np.linalg.norm(pt1 - pt2)
        
        if not np.isclose(reported_dist, actual_dist, rtol=1e-7, atol=1e-7):
            return False, f"Case {cid}: reported distance {reported_dist} does not match actual distance {actual_dist}"
            
        w = pt1 - pt2
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        proj1 = np.dot(w, v1) / norm_v1 if norm_v1 > 0 else 0
        proj2 = np.dot(w, v2) / norm_v2 if norm_v2 > 0 else 0
        
        if abs(proj1) > 1e-5 or abs(proj2) > 1e-5:
            return False, f"Case {cid}: optimality condition failed. proj1={proj1:.2e}, proj2={proj2:.2e}"
            
        np.random.seed(42)
        for _ in range(200):
            scale_t = max(1.0, abs(t) * 0.01)
            scale_s = max(1.0, abs(s) * 0.01)
            dt = np.random.normal(0, scale_t)
            ds = np.random.normal(0, scale_s)
            
            npt1 = p1 + (t + dt) * v1
            npt2 = p2 + (s + ds) * v2
            new_dist = np.linalg.norm(npt1 - npt2)
            
            if new_dist < actual_dist - 1e-6:
                return False, f"Case {cid}: Found smaller distance {new_dist} at t={t+dt}, s={s+ds} than minimum {actual_dist}"
                
    return True, "All cases verified successfully."