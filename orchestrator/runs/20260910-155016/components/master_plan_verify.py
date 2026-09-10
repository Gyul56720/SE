def check(output, inputs):
    mp = output.get("master_plan", {})
    if not isinstance(mp, dict): return False, "Master plan must be a dict"
    if "Phase_1" not in mp or "Phase_2" not in mp or "Phase_3" not in mp:
        return False, "Master plan must contain Phase 1, 2, and 3"
    return True, "Master plan successfully generated"