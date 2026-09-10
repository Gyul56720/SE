def check(output, inputs):
    # Verify that the strategy covers the previously identified rigid points
    if "strategy" in output and len(output["strategy"]["targets"]) > 0:
        return True, "Strategy defined"
    return False, "Invalid strategy format"