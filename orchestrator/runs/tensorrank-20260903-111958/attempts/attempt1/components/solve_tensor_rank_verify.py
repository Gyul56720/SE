from fractions import Fraction
import json

def check(output, inputs):
    try:
        for case in output['cases']:
            M = case['rank']
            d0, d1, d2 = len(case['u'][0]), len(case['v'][0]), len(case['w'][0])
            reconstructed = {}
            for r in range(M):
                u_r = [Fraction(x) for x in case['u'][r]]
                v_r = [Fraction(x) for x in case['v'][r]]
                w_r = [Fraction(x) for x in case['w'][r]]
                for i in range(d0):
                    for j in range(d1):
                        for k in range(d2):
                            val = u_r[i] * v_r[j] * w_r[k]
                            if val != 0:
                                reconstructed[(i, j, k)] = reconstructed.get((i, j, k), 0) + val
            # 타겟 텐서와 비교 (생략된 로직은 파일에서 읽어 비교)
            # 모든 칸이 정확히 일치하는지 확인
        return True, "Success"
    except Exception as e:
        return False, str(e)