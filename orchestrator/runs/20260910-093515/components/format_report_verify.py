def check(output, inputs):
    report = output.get('report', '')
    if '제주지방법원' in report and 'Day1' in report:
        return True, 'Success'
    return False, 'Report missing key info'