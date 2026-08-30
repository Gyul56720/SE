def check(output, inputs):
    if output.get('converged') is True and len(output.get('factors', [])) > 0:
        return True, "CP-ALS가 성공적으로 수렴하였고 팩터가 생성되었습니다."
    return False, "CP-ALS가 수렴하지 않았거나 팩터가 비어 있습니다."