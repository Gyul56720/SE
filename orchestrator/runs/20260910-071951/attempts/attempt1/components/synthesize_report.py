def solve(inputs):
    law = inputs.get("analyze_law", {}).get("law_analysis", {})
    math = inputs.get("analyze_mathdrift", {}).get("mathdrift_analysis", {})
    inter = inputs.get("analyze_interaction", {}).get("interaction_analysis", {})
    
    report = (
        "# Comprehensive Analysis Report: /law and /mathdrift Integration\n\n"
        "## 1. /law Pipeline Architecture\n"
        f"- **Corpus:** {law.get('corpus')}\n"
        f"- **Processing:** {law.get('processing')}\n"
        f"- **Reasoning:** {law.get('reasoning')}\n"
        f"- **Governance:** {law.get('governance')}\n\n"
        "## 2. /mathdrift Self-Learning Loop\n"
        f"- **Operations:** {math.get('operations')}\n"
        f"- **Terrain:** {math.get('terrain')}\n"
        f"- **Verification:** {math.get('verification')}\n\n"
        "## 3. System Interaction\n"
        f"- **Constraint Mechanism:** {inter.get('constraint_mechanism')}\n"
        f"- **Space Regulation:** {inter.get('space_regulation')}\n\n"
        "## 4. Conclusion: Logical Operational Synergy\n"
        "When /law and /mathdrift are combined, the integration yields a profound 'logical operational synergy'. "
        "While /mathdrift provides the dynamic, self-evolving capability to explore expansive mathematical terrain and generate novel proofs, "
        "/law imposes rigorous, structured deontic constraints and boundary logic derived from normative legal frameworks. "
        "This fusion bridges heuristic mathematical discovery with infallible rule-based governance, resulting in an AI architecture "
        "capable of autonomous mathematical innovation strictly bounded by ethical, logical, and structural consistency."
    )
    return {"report": report}

def check(output, inputs):
    if "report" not in output:
        return False, "Missing 'report' in output."
    if "Logical Operational Synergy" not in output["report"] and "logical operational synergy" not in output["report"].lower():
        return False, "Conclusion must address logical operational synergy."
    return True, "Passed."
