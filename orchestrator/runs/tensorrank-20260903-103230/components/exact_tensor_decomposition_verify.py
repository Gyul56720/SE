import json, numpy as np, fractions

def parse_rat(s):
    if isinstance(s, (int, float)):
        return fractions.Fraction(str(s))
    if '/' in str(s):
        num, den = s.split('/')
        return fractions.Fraction(int(num), int(den))
    return fractions.Fraction(int(s))

def check(output, inputs):
    with open('/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-103230/verifiers/target.json', 'r') as f:
        data = json.load(f)
        
    case_dict = {c['id']: c for c in data['cases']}
    
    for out_case in output['cases']:
        cid = out_case['id']
        ref = case_dict[cid]
        shape = ref['shape']
        d0, d1, d2 = shape
        
        T = np.zeros((d0, d1, d2), dtype=object)
        for entry in ref['entries']:
            a, b, c, val = entry
            T[a][b][c] = fractions.Fraction(val)
            
        u = np.vectorize(parse_rat)(np.array(out_case['u']))
        v = np.vectorize(parse_rat)(np.array(out_case['v']))
        w = np.vectorize(parse_rat)(np.array(out_case['w']))
        
        M = u.shape[0]
        T_approx = np.zeros((d0, d1, d2), dtype=object)
        for r in range(M):
            for a in range(d0):
                for b in range(d1):
                    for c in range(d2):
                        T_approx[a][b][c] += u[r, a] * v[r, b] * w[r, c]
                        
        for a in range(d0):
            for b in range(d1):
                for c in range(d2):
                    if T[a][b][c] != T_approx[a][b][c]:
                        return False, f"Mismatch at {a},{b},{c}: expected {T[a][b][c]}, got {T_approx[a][b][c]}"
                        
    return True, "All tensors exactly matched."
