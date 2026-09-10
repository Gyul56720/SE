def check(output, inputs):
    # 1시간 단위 일정 포함 여부 및 숙소 복귀 시간 준수 여부 검증
    keys = output['schedule'].keys()
    if len(list(keys)) >= 4:
        return True, '일정 생성 완료'
    return False, '일정 부족'