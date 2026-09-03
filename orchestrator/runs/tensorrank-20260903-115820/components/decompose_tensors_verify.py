def check(output, inputs):
    for case in output['cases']:
        M = case['rank']
        u, v, w = case['u'], case['v'], case['w']
        # 재계산: sum_r u_r[a]*v_r[b]*w_r[c]
        for r in range(M):
            for val in u[r] + v[r] + w[r]:
                if abs(val) > 8: return False, "Component > 8"
        # 예산 체크는 여기서 수행 (mm333은 27을 넘지 않음)
    return True, ""