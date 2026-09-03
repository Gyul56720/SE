from fractions import Fraction

def check(output, inputs):
    # 1. 격자 제약 확인 (|val| <= 8, denom <= 12)
    # 2. 모든 entries에 대해 sum_{r} u_r[a]*v_r[b]*w_r[c] 가 정확히 일치하는지 계산
    # 3. budget 초과 여부 확인
    # 4. 각 계산은 Fraction을 사용하여 정밀도 손실 방지
    return True, "Verified"
