def check(output, inputs):
    if 'btc' in output and 'xrp' in output:
        return True, "Data loaded successfully"
    return False, "Data keys missing"