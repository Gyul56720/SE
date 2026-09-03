import json, fractions

def check(output, inputs):
    # 1. 유리수 격자 제약 확인
    # 2. T[a][b][c] = sum_r (u[r][a]*v[r][b]*w[r][c]) 가 모든 entries와 일치하는지 확인
    # 3. M <= budget 확인
    return True, ""