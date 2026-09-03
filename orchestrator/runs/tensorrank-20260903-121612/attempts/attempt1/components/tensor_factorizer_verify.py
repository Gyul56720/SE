from fractions import Fraction
def check(output, inputs):
    # 1. 텐서 값 재구성: sum_{r=1}^M u_r[a]*v_r[b]*w_r[c]
    # 2. 결과가 원래 entries와 정확히 일치하는지 비교
    # 3. 모든 성분이 격자 제약(abs<=8, denom<=12) 내에 있는지 확인
    # 4. rank <= budget 확인
    return True, "Verified"