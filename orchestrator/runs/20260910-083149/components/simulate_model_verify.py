def check(output, inputs):
    if 'model_name' not in output or 'goodness_score' not in output:
        return False, "Missing model output fields"
    if not isinstance(output['goodness_score'], (int, float)):
        return False, "Goodness score must be numeric"
    return True, ""
