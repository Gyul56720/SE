def check(output, inputs):
    required_keys = {'law', 'mathdrift', 'coin'}
    if not all(key in output for key in required_keys):
        return False, "Missing required system analysis keys."
    return True, "Diagnostic outputs validated for existence."