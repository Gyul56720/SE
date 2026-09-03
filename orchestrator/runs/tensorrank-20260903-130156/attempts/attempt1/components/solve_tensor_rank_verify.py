import json
from fractions import Fraction

def check(output, inputs):
    # Reconstruct the tensor from u, v, w factors and compare with entries in target.json
    target_path = '/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-130156/verifiers/target.json'
    with open(target_path, 'r') as f:
        target = json.load(f)
    
    for case_res in output['cases']:
        case_id = case_res['id']
        case_ref = next(c for c in target['cases'] if c['id'] == case_id)
        M = case_res['rank']
        u, v, w = case_res['u'], case_res['v'], case_res['w']
        
        # Verify lattice constraints: |val| <= 8 and den <= 12
        for mat in [u, v, w]:
            for row in mat:
                for val in row:
                    f = Fraction(str(val))
                    if abs(f.numerator) > 8 * f.denominator or f.denominator > 12:
                        return False, f"Lattice violation: {val}"
        
        # Check exact reconstruction for all entries
        for entry in case_ref['entries']:
            a, b, c, val = entry
            sum_val = Fraction(0)
            for r in range(M):
                sum_val += Fraction(str(u[r][a])) * Fraction(str(v[r][b])) * Fraction(str(w[r][c]))
            if sum_val != Fraction(val):
                return False, f"Mismatch at {a,b,c}: {sum_val} != {val}"
    return True, "Success"