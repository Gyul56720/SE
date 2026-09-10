def check(output, inputs):
    if "law" in output and "mathdrift" in output:
        if all("path" in output[k] for k in ["law", "mathdrift"]):
            return (True, "데이터 구조 확인 완료")
    return (False, "필수 키 누락")