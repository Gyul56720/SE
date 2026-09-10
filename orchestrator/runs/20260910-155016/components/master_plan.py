def solve(inputs):
    plan = {
        "Phase_1": "Establish harness-level verification and prompt-time MCTS wrappers without modifying core repository code.",
        "Phase_2": "Integrate agentic RAG and self-correction feedback loops into the orchestrator execution loop, utilizing gatekeeper for safety.",
        "Phase_3": "Deploy continuous evaluation pipelines using mathdrift/law modules to benchmark quantized models against Opus-level standards.",
        "target_model": "Quantized Open-Source Models",
        "objective": "Opus-level reliability via harness architecture"
    }
    return {"master_plan": plan}

def check(output, inputs):
    mp = output.get("master_plan", {})
    if not isinstance(mp, dict): return False, "Master plan must be a dict"
    if "Phase_1" not in mp or "Phase_2" not in mp or "Phase_3" not in mp:
        return False, "Master plan must contain Phase 1, 2, and 3"
    return True, "Master plan successfully generated"