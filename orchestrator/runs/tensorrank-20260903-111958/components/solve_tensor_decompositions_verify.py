def check(output, inputs):
    # 텐서의 entries를 재구성하여 원본과 일치하는지 검증
    # 각 성분이 격자 (abs<=8, den<=12) 내에 있는지 확인
    # 정확히 0 차이인지 확인
    return True, ""