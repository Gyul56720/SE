import json
import numpy as np
from fractions import Fraction

def check(output, inputs):
    path = "/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-103223/verifiers/target.json"
    with open(path, 'r') as f:
        data = json.load(f)
        
    cases_dict = {c['id']: c for c in data['cases']}
    out_cases = output.get('cases', [])
    
    for oc in out_cases:
        cid = oc['id']
        if cid not in cases_dict:
            return False, f"Unknown case id: {cid}"
        tc = cases_dict[cid]
        shape = tc['shape']
        budget = tc['budget']
        entries = tc['entries']
        
        T_target = np.zeros(shape, dtype=int)
        for a, b, c, val in entries:
            T_target[a][b][c] = val
            
        rank = oc['rank']
        if rank > budget:
            return False, f"{cid} rank {rank} exceeds budget {budget}"
            
        u = oc['u']
        v = oc['v']
        w = oc['w']
        
        if len(u) != rank or len(v) != rank or len(w) != rank:
            return False, f"{cid} factor dimensions mismatch rank"
            
        # Check lattice constraints: |val| <= 8, denominator <= 12
        for matrix in [u, v, w]:
            for row in matrix:
                for val in row:
                    if isinstance(val, str):
                        if '/' in val:
                            num, den = val.split('/')
                            f_val = Fraction(int(num), int(den))
                        else:
                            f_val = Fraction(int(val))
                    else:
                        f_val = Fraction(val)
                    if abs(f_val.numerator) > 8 * f_val.denominator or f_val.denominator > 12:
                        return False, f"{cid} component {val} violates lattice constraints"
                        
        # Reconstruct tensor exactly
        T_recon = np.zeros(shape, dtype=int)
        for r in range(rank):
            ur = np.array([float(Fraction(x)) if isinstance(x, (int, str)) else float(x) for x in u[r]])
            vr = np.array([float(Fraction(x)) if isinstance(x, (int, str)) else float(x) for x in v[r]])
            wr = np.array([float(Fraction(x)) if isinstance(x, (int, str)) else float(x) for x in w[r]])
            
            term = np.outer(ur, np.outer(vr, wr).ravel()).reshape(shape)
            T_recon += np.round(term).astype(int)
            
        diff = T_target - T_recon
        max_diff = np.max(np.abs(diff))
        non_zeros = np.count_nonzero(diff)
        if non_zeros > 0:
            return False, f"{cid} reconstruction failed: {non_zeros} entries incorrect (max error {max_diff})"
            
    return True, "All tensor decompositions verified successfully with zero error."