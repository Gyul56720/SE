def check(output, inputs):
    from fractions import Fraction
    
    budgets = {'w_state': 3, 'mm222': 7, 'mm333': 26}
    expected_entries = {
        'w_state': {(0, 0, 1): 1, (0, 1, 0): 1, (1, 0, 0): 1},
        'mm222': {},
        'mm333': {}
    }
    
    # mm222 entries (2x2 matmul)
    for i in range(2):
        for j in range(2):
            for k in range(2):
                expected_entries['mm222'][(2*i+j, 2*j+k, 2*i+k)] = 1
                
    # mm333 entries (3x3 matmul)
    for i in range(3):
        for j in range(3):
            for k in range(3):
                expected_entries['mm333'][(3*i+j, 3*j+k, 3*i+k)] = 1
                
    shapes = {'w_state': (2, 2, 2), 'mm222': (4, 4, 4), 'mm333': (9, 9, 9)}
    
    def parse_val(v):
        if isinstance(v, (int, float)):
            f = Fraction(v).limit_denominator(12)
        elif isinstance(v, str):
            f = Fraction(v)
        else:
            return None
        if abs(f) > 8 or f.denominator > 12:
            return None
        return f
        
    cases = output.get('cases', [])
    if len(cases) != 3:
        return False, f"Expected 3 cases, got {len(cases)}"
        
    for case in cases:
        cid = case.get('id')
        if cid not in budgets:
            return False, f"Unknown case id {cid}"
        rank = case.get('rank')
        if rank > budgets[cid]:
            return False, f"Case {cid} rank {rank} exceeds budget {budgets[cid]}"
        u, v, w = case.get('u'), case.get('v'), case.get('w')
        if len(u) != rank or len(v) != rank or len(w) != rank:
            return False, f"Case {cid} vector lengths do not match rank {rank}"
            
        d0, d1, d2 = shapes[cid]
        recon = {}
        for r in range(rank):
            if len(u[r]) != d0 or len(v[r]) != d1 or len(w[r]) != d2:
                return False, f"Case {cid} dimension mismatch at rank {r}"
            for a in range(d0):
                ua = parse_val(u[r][a])
                if ua is None: return False, f"Invalid lattice value {u[r][a]} in u of {cid}"
                if ua == 0: continue
                for b in range(d1):
                    vb = parse_val(v[r][b])
                    if vb is None: return False, f"Invalid lattice value {v[r][b]} in v of {cid}"
                    if vb == 0: continue
                    for c in range(d2):
                        wc = parse_val(w[r][c])
                        if wc is None: return False, f"Invalid lattice value {w[r][c]} in w of {cid}"
                        if wc == 0: continue
                        recon[(a, b, c)] = recon.get((a, b, c), Fraction(0)) + ua * vb * wc
                        
        # Filter out exact zeros
        recon = {k: v for k, v in recon.items() if v != 0}
        
        exp = expected_entries[cid]
        if recon != exp:
            return False, f"Case {cid} reconstruction mismatch! Recon size: {len(recon)}, Expected size: {len(exp)}"
            
    return True, "All tensor decompositions are exact and meet lattice & budget constraints."