def solve(inputs):
    strategy = {
        "keywords": ["Test-time compute", "MCTS", "Chain-of-Thought verification", "Agentic RAG", "Self-Correction loops", "Quantization-aware alignment"],
        "sources": ["arXiv", "HuggingFace Papers", "GitHub Trending", "AI Conferences (NeurIPS, ICLR)"],
        "actions": [
            "fetch latest pre-prints on test-time scaling and MCTS for LLMs",
            "search repository patterns for agentic workflows",
            "extract architectural integration points for quantized models"
        ],
        "schedule": "Continuous weekly ingestion and automated filtering"
    }
    return {"strategy_json": strategy}

def check(output, inputs):
    data = output.get("strategy_json", {})
    if not isinstance(data, dict): return False, "Output must be a dict"
    if "keywords" not in data or len(data["keywords"]) < 4:
        return False, "Must include at least 4 key research topics"
    return True, "Strategy successfully formulated"