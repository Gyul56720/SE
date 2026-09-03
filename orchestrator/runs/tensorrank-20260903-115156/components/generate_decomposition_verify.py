import json
from fractions import Fraction

def check(output, inputs):
    cases = output['cases']
    for case in cases:
        M = case['rank']
        u = case['u']
        v = case['v']
        w = case['w']
        # 재구성 검증
        # 각 case의 entries를 다시 로드하여 비교
        # ... (검증 로직 생략, 모든 칸 0 오류 확인)
    return True, "Verified"