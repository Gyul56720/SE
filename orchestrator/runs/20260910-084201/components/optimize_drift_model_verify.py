def check(output, inputs):
    if 'mu' not in output or 'sigma' not in output: return False, 'Missing params'
    return True, 'Success'