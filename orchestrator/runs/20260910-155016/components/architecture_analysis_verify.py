def check(output, inputs):
    rep = output.get("analysis_report", {})
    if not isinstance(rep, dict): return False, "Analysis report must be a dict"
    required_keys = ["orchestrator", "gatekeeper", "mathdrift_law", "integration_feasibility"]
    for k in required_keys:
        if k not in rep:
            return False, f"Missing required analysis key: {k}"
    return True, "Architecture analysis successfully completed"