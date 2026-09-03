from fractions import Fraction

def check(output, inputs):
    cases_map = {c['id']: c for c in inputs['target_data']['cases']}
    for res in output['cases']:
        case = cases_map[res['id']]
        M = res['rank']
        if M > case['budget']: return False, f"Budget exceeded: {M} > {case['budget']}"
        
        # 검증: 재구성 텐서가 원본과 정확히 일치하는지 확인
        d0, d1, d2 = case['shape']
        reconstructed = {}
        for r in range(M):
            for i in range(d0):
                for j in range(d1):
                    for k in range(d2):
                        val = Fraction(res['u'][r][i]) * Fraction(res['v'][r][j]) * Fraction(res['w'][r][k])
                        reconstructed[(i, j, k)] = reconstructed.get((i, j, k), 0) + val
        
        for (i, j, k), v in reconstructed.items():
            if v != 0 and v != 1: return False, "Non-binary result"
        
        for e in case['entries']:
            if reconstructed.get((e[0], e[1], e[2]), 0) != e[3]: return False, "Mismatch"
    return True, "Success"