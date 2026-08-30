def check(output, inputs):
    factors = output.get('factors')
    rank = output.get('rank')
    if factors is None or len(factors) != 3:
        return False, 'Factors missing or incorrect dimension'
    if rank <= 0:
        return False, 'Rank must be positive'
    return True, 'Border rank formulation verified'