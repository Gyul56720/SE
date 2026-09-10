def check(output, inputs):
    if 'routes' in output and len(output['routes']) >= 2:
        return True, '데이터 수집 완료'
    return False, '필수 노선 데이터 누락'