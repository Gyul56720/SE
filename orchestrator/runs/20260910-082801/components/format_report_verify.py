def check(output, inputs):
    if 'report' not in output:
        return False, "Output missing 'report' key"
    report = output['report']
    if "[MathDrift Ledger 심층 분석 보고서]" not in report:
        return False, "Report title missing"
    if "성공 기록 분석" not in report or "한계점 식별" not in report:
        return False, "Report missing required sections"
    return True, "Report formatted and verified successfully."