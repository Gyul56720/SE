def check(output, inputs):
    if 'is_drift_point' not in output or 'chaos_index' not in output:
        return False, "Missing drift evaluation fields"
    if not isinstance(output['is_drift_point'], bool):
        return False, "is_drift_point must be boolean"
    return True, ""
