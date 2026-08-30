def check(output, inputs):
    """오케스트레이터의 결과물을 검증한다."""
    if not isinstance(output, dict):
        return False, "Output must be a dictionary"
    if "tol" not in output or output["tol"] != 1e-3:
        return False, "Tolerance must be exactly 1e-3"
    if "factors" not in output:
        return False, "Missing factors in output"
    if not output.get("converged", False):
        return False, "CP-ALS did not converge"
    return True, ""
