def check(output, inputs):
    # Verify that the output contains mandatory analysis categories
    keys = output.get("issues", {}).keys()
    if "rigid_points" in keys and "impact" in keys:
        return True, "Analysis complete"
    return False, "Missing essential analysis components"