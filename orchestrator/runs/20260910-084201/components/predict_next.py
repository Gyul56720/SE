def solve(inputs):
    m = inputs['optimize_drift_model']
    next_price = m['last_price'] * (1 + m['mu'])
    is_drift = m['sigma'] > 0.05
    return {'predicted_price': next_price, 'return': m['mu'], 'is_drift': is_drift}