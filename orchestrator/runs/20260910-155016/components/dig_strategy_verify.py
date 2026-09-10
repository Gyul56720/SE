def check(output, inputs):
    data = output.get("strategy_json", {})
    if not isinstance(data, dict): return False, "Output must be a dict"
    if "keywords" not in data or len(data["keywords"]) < 4:
        return False, "Must include at least 4 key research topics"
    return True, "Strategy successfully formulated"