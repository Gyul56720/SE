def check(output, inputs):
    required_keys = ['law_analysis', 'mathdrift_analysis', 'interaction_analysis', 'synergy_conclusion']
    for key in required_keys:
        if key not in output:
            return False, f"Missing key: {key}"
        if not isinstance(output[key], str) or len(output[key]) < 20:
            return False, f"Content too short or invalid type in {key}"
    return True, "Validation successful."