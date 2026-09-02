def check(output, inputs):
    import json
    import numpy as np
    try:
        res = json.loads(output["result_json"])
        for key in ["name", "affiliation", "subject"]:
            if key not in res:
                return False, f"Missing key: {key}"
            if not isinstance(res[key], str) or len(res[key]) == 0:
                return False, f"Invalid value for {key}"
        gamma = output["gamma"]
        quantized_sample = np.array(output["quantized_sample"])
        np.random.seed(42)
        weights = np.random.randn(100, 100)
        expected_quantized = np.clip(np.round(weights / gamma), -1, 1)[:5, :5]
        if not np.array_equal(quantized_sample, expected_quantized):
            return False, "Quantized sample does not match expected configuration"
        return True, "Verification successful"
    except Exception as e:
        return False, str(e)