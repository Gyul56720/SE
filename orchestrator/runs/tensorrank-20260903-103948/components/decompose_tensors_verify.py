def check(output, inputs):
    import json
    from fractions import Fraction
    
    target_file = "/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-103948/verifiers/target.json"
    try:
        with open(target_file, "r") as f:
            spec = json.load(f)
    except Exception:
        # 파일이 없을 경우 하드코딩된 스펙으로 검증
        spec = {
            "cases": [
                {"id": "w_state", "budget": 3, "shape": [2, 2, 2], "entries": [[0,0,1,1], [0,1,0,1], [1,0,0,1]]},
                {"id": "mm222", "budget": 7, "shape": [4, 4, 4], "entries": [[0,0,0,1],[0,1,1,1],[1,2,0,1],[1,3,1,1],[2,0,2,1],[2,1,3,1],[3,2,2,1],[3,3,3,1]]},
                {"id": "mm333", "budget": 26, "shape": [9, 9, 9], "entries": [
                    [0,0,0,1],[0,1,1,1],[0,2,2,1],[1,3,0,1],[1,4,1,1],[1,5,2,1],[2,6,0,1],[2,7,1,1],[2,8,2,1],
                    [3,0,3,1],[3,1,4,1],[3,2,5,1],[4,3,3,1],[4,4,4,1],[4,5,5,1],[5,6,3,1],[5,7,4,1],[5,8,5,1],
                    [6,0,6,1],[6,1,7,1],[6,2,8,1],[7,3,6,1],[7,4,7,1],[7,5,8,1],[8,6,6,1],[8,7,7,1],[8,8,8,1]
                ]}
            ],
            "lattice": {"coef_max": 8, "den_max": 12}
        }
    
    def parse_frac(val):
        if isinstance(val, (int, float)):
            return Fraction(val)
        return Fraction(str(val))

    cases_map = {c["id"]: c for c in output.get("cases", [])}
    
    for c_spec in spec["cases"]:
        cid = c_spec["id"]
        if cid not in cases_map:
            return False, f"Missing case {cid}"
        c_out = cases_map[cid]
        M = c_out.get("rank", 0)
        if M > c_spec["budget"]:
            return False, f"{cid}: rank {M} exceeds budget {c_spec['budget']}"
        
        U, V, W = c_out["u"], c_out["v"], c_out["w"]
        d0, d1, d2 = c_spec["shape"]
        if len(U) != M or len(V) != M or len(W) != M:
            return False, f"{cid}: vector list length mismatch with rank {M}"
            
        # 격자 제약 및 텐서 재구성 검증
        expected_entries = {}
        for entry in c_spec["entries"]:
            expected_entries[(entry[0], entry[1], entry[2])] = Fraction(entry[3])
            
        # 재구성 텐서 계산
        recon = {}
        for r in range(M):
            u_r = [parse_frac(x) for x in U[r]]
            v_r = [parse_frac(x) for x in V[r]]
            w_r = [parse_frac(x) for x in W[r]]
            
            for vec in [u_r, v_r, w_r]:
                for x in vec:
                    if abs(x) > spec.get("lattice", {}).get("coef_max", 8):
                        return False, f"{cid}: coefficient {x} exceeds max"
                    if x.denominator > spec.get("lattice", {}).get("den_max", 12):
                        return False, f"{cid}: denominator {x.denominator} exceeds max"
                        
            for a in range(d0):
                if u_r[a] == 0: continue
                for b in range(d1):
                    if v_r[b] == 0: continue
                    uv = u_r[a] * v_r[b]
                    for c in range(d2):
                        if w_r[c] == 0: continue
                        recon[(a, b, c)] = recon.get((a, b, c), Fraction(0)) + uv * w_r[c]
                        
        # 0이 아닌 성분들 일치 검증
        for pos, val in recon.items():
            exp = expected_entries.get(pos, Fraction(0))
            if val != exp:
                return False, f"{cid}: mismatch at {pos}: got {val}, expected {exp}"
        for pos, exp in expected_entries.items():
            got = recon.get(pos, Fraction(0))
            if got != exp:
                return False, f"{cid}: missing entry at {pos}: got {got}, expected {exp}"
                
    return True, "All cases decomposed exactly within budget!"