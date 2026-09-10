def check(output, inputs):
    req_keys = ["sentiment", "volatility_status", "critical_time", "report"]
    for k in req_keys:
        if k not in output or not isinstance(output[k], str) or len(output[k]) == 0:
            return False, f"Missing or invalid key: {k}"
    if "XRP" not in output["report"]:
        return False, "Report must mention XRP"
    return True, "Validation passed successfully"