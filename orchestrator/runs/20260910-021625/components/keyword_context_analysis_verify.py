def check(output, inputs):
    res = output.get("analysis")
    if not isinstance(res, dict):
        return False, "analysis must be a dictionary"
    if "intent" not in res:
        return False, "intent is missing"
    return True, "success"