def check(output, inputs):
    import json
    path = "/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-103223/verifiers/target.json"
    with open(path, 'r') as f:
        data = json.load(f)
    
    case_map = {c['id']: c for c in data['cases']}
    
    for out_case in output.get('cases', []):
        cid = out_case['id']
        if cid not in case_map:
            return False, f"Unknown case id {cid}"
        orig = case_map[cid]
        shape = orig['shape']
        d0, d1, d2 = shape
        budget = orig['budget']
        
        M = out_case['rank']
        if M > budget:
            return False, f"Rank {M} exceeds budget {budget}"
            
        u = out_case['u']
        v = out_case['v']
        w = out_case['w']
        
        if len(u) != M or len(v) != M or len(w) != M:
            return False, "Dimension mismatch in factor matrices"
            
        # Reconstruct tensor
        T_recon = [[[0 for _ in range(d2)] for _ in range(d1)] for _ in range(d0)]
        for r in range(M):
            ur = u[r]
            vr = v[r]
            wr = w[r]
            for a in range(d0):
                for b in range(d1):
                    for c in range(d2):
                        # parse string fractions if needed
                        def parse_val(val):
                            if isinstance(val, str):
                                if '/' in val:
                                    num, den = val.split('/')
                                    return float(num) / float(den)
                                return float(val)
                        val = parse_val(ur[a]) * parse_val(vr[b]) * parse_val(wr[c])
                        T_recon[a][b][c] += val
                        
        # Compare with original entries
        T_orig = [[[0 for _ in range(d2)] for _ in range(d1)] for _ in range(d0)]
        for entry in orig['entries']:
            if len(entry) == 4:
                a, b, c, val = entry
                T_orig[a][b][c] = val
            elif len(entry) == 3:
                a, b, val = entry
                T_orig[a][b] = val
                
        for a in range(d0):
            for b in range(d1):
                for c in range(d2):
                    if abs(T_recon[a][b][c] - T_orig[a][b][c]) > 1e-7:
                        return False, f"Mismatch at [{a},{b},{c}]: got {T_recon[a][b][c]}, expected {T_orig[a][b][c]}"
                        
    return True, "Verification passed successfully"