def check(output, inputs):
    if not isinstance(output, dict):
        return False, "Output must be a dictionary"
    required_keys = ["data_flow", "risk_management", "strategic_role", "conclusion"]
    for k in required_keys:
        if k not in output:
            return False, f"Missing key: {k}"
        if not isinstance(output[k], str) or len(output[k]) == 0:
            return False, f"Invalid value for key: {k}"
    return True, "Validation passed"