import numpy as np
from fractions import Fraction

def check(output, inputs):
    for res_case in output["cases"]:
        case_id = res_case["id"]
        case_data = next(c for c in inputs["cases"] if c["id"] == case_id)
        
        M = res_case["rank"]
        if M > case_data["budget"]: return False, f"{case_id}: budget 초과"
        
        u = np.array([[float(Fraction(x)) for x in row] for row in res_case["u"]])
        v = np.array([[float(Fraction(x)) for x in row] for row in res_case["v"]])
        w = np.array([[float(Fraction(x)) for x in row] for row in res_case["w"]])
        
        shape = case_data["shape"]
        reconstructed = np.zeros(shape)
        for r in range(M):
            reconstructed += np.einsum('i,j,k->ijk', u[r], v[r], w[r])
            
        for entry in case_data.get("entries", []):
            r, c1, c2, val = entry
            if not np.isclose(reconstructed[r, c1, c2], val, atol=1e-9):
                return False, f"{case_id}: 재구성 불일치"
    return True, "성공"