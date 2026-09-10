def check(output, inputs):
    report = output.get("report", "")
    if "/law" in report and "/mathdrift" in report and len(report) > 100:
        return (True, "리포트 생성 및 내용 검증 완료")
    return (False, "리포트 내용 불충분")