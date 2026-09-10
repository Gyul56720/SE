import statistics
def solve(inputs):
    prev = inputs['extract_returns']
    returns = prev.get('returns', [])
    if len(returns) < 2:
        mu = returns[0] if returns else 0.0
        sigma = 0.0001
    else:
        mu = statistics.mean(returns)
        sigma = statistics.stdev(returns)
    return {'mu': mu, 'sigma': sigma, 'last_price': prev.get('last_price', 0.0)}