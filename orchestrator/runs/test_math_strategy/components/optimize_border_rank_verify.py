def check(output, inputs):
    resolved = output.get('mismatch_resolved')
    factors = output.get('optimized_factors')
    if not resolved:
        return False, 'Mismatch not resolved'
    if len(factors) != 3:
        return False, 'Invalid optimized factors'
    return True, 'Optimization and mismatch resolution verified'