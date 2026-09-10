def check(output, inputs):
    prices = output.get('prices', [])
    returns = output.get('returns', [])
    if len(prices) != 100:
        return False, "Prices length must be exactly 100"
    if len(returns) != 99:
        return False, "Returns length must be exactly 99"
    for i in range(1, len(prices)):
        if prices[i-1] > 0:
            expected_ret = __import__('math').log(prices[i] / prices[i-1])
            if abs(returns[i-1] - expected_ret) > 1e-7:
                return False, "Return calculation mismatch"
    return True, ""
