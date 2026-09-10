def check(output, inputs):
    m = inputs['optimize_drift_model']
    expected = m['last_price'] * (1 + m['mu'])
    if abs(output['predicted_price'] - expected) > 1e-9: return False, 'Calc mismatch'
    return True, 'Success'