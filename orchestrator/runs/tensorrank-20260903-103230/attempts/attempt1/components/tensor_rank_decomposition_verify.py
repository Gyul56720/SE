def check(output, inputs):
    import json
    file_path = "/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-103230/verifiers/target.json"
    with open(file_path, "r") as f:
        data = json.load(f)
    
    case_map = {c["id"]: c for c in data["cases"]}
    
    for out_case in output["cases"]:
        cid = out_case["id"]
        if cid not in case_map:
            return False, f"Unknown case id {cid}"
        target_case = case_map[cid]
        shape = target_case["shape"]
        budget = target_case["budget"]
        M = out_case["rank"]
        
        if M > budget:
            return False, f"Rank {M} exceeds budget {budget} for {cid}"
            
        # Reconstruct target tensor
        target = {}
        for a, b, c, val in target_case["entries"]:
            target[(int(a), int(b), int(c))] = val
            
        u = out_case["u"]
        v = out_case["v"]
        w = out_case["w"]
        
        # Compute reconstructed tensor and compare exactly
        d0, d1, d2 = shape
        recon = {}
        for r in range(M):
            ur = u[r]
            vr = v[r]
            wr = w[r]
            for a in range(d0):
                ura = ur[a]
                if ura == 0:
                    continue
                for b in range(d1):
                    vrb = vr[b]
                    if vrb == 0:
                        continue
                    prod_ab = ura * vrb
                    for c in range(d2):
                        wrc = wr[c]
                        if wrc == 0:
                            continue
                        val = prod_ab * wrc
                        key = (a, b, c)
                        recon[key] = recon.get(key, 0) + val
                        
        # Check all entries match
        all_keys = set(target.keys()).union(set(recon.keys()))
        for k in all_keys:
            if target.get(k, 0) != recon.get(k, 0):
                return False, f"Mismatch at {k}: target {target.get(k, 0)} vs recon {recon.get(k, 0)}"
                
    return True, "Verification successful"
