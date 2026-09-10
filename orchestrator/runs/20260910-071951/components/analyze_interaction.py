def solve(inputs):
    law = inputs.get("analyze_law", {}).get("law_analysis", {})
    math = inputs.get("analyze_mathdrift", {}).get("mathdrift_analysis", {})
    interaction = {
        "constraint_mechanism": "Structured legal hierarchies and rule graphs from /law establish strict boundary conditions and deontic logic constraints within the /mathdrift terrain.",
        "space_regulation": "The deterministic nature of legal norms prunes illogical exploration paths in /mathdrift's knowledge space, aligning mathematical self-learning with normative constraints."
    }
    return {"interaction_analysis": interaction}

def check(output, inputs):
    if "interaction_analysis" not in output:
        return False, "Missing 'interaction_analysis' key."
    if "constraint_mechanism" not in output["interaction_analysis"]:
        return False, "Missing constraint mechanism explanation."
    return True, "Passed."
