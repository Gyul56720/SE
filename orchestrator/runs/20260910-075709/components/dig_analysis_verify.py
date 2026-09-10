def check(output, inputs):
    if "analysis_result" not in output:
        return False, "analysis_result 키가 누락되었습니다."
    val = output["analysis_result"]
    if not isinstance(val, str) or len(val) < 10:
        return False, "분석 결과가 충분히 상세하지 않습니다."
    return True, ""