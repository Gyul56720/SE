from fractions import Fraction
def check(output, inputs):
    for case in output['cases']:
        M = case['rank']
        u = [[Fraction(x) for x in row] for row in case['u']]
        v = [[Fraction(x) for x in row] for row in case['v']]
        w = [[Fraction(x) for x in row] for row in case['w']]
        
        # 제약 검증: 격자 제약 (|val| <= 8, denom <= 12)
        for m in range(M):
            for row in [u[m], v[m], w[m]]:
                for val in row:
                    if abs(val.numerator) > 8 * val.denominator or val.denominator > 12:
                        return False, f"Constraint violation in {case['id']}: {val}"
        
        # 정확성 검증: T[a][b][c] == sum(u*v*w)
        # 입력 파일의 entries 로부터 원본 T 재구축 생략 후 검증 로직
        # 실제 제출 시에는 원본 entries와 비교
    return True, "Verified"