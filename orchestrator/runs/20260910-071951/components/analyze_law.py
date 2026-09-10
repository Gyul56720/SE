def solve(inputs):
    analysis = {
        "corpus": "Source raw legal texts, statutes, and precedents.",
        "processing": "OCR and HWP parsing to convert unstructured documents into machine-readable text.",
        "reasoning": "logic/leet module for legal logic extraction, analogical reasoning, and LEET-style problem solving.",
        "governance": "gate/tuner for regulatory compliance, alignment, and parameter tuning."
    }
    return {"law_analysis": analysis}

def check(output, inputs):
    if not isinstance(output, dict):
        return False, "Output must be a dictionary."
    if "law_analysis" not in output:
        return False, "Missing 'law_analysis' key."
    if not isinstance(output["law_analysis"], dict):
        return False, "'law_analysis' must be a dictionary."
    if not all(k in output["law_analysis"] for k in ["corpus", "processing", "reasoning", "governance"]):
        return False, "Incomplete pipeline stages in /law analysis."
    return True, "Passed."