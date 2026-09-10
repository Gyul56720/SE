import math

def solve(inputs):
    data_dep = inputs.get('load_data', {})
    model_dep = inputs.get('simulate_model', {})
    
    returns = data_dep.get('returns', [0.01]*99)
    score = model_dep.get('goodness_score', -1.0)
    
    # Calculate volatility (standard deviation of returns)
    mean_r = sum(returns) / len(returns) if returns else 0.0
    var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns) if returns else 0.0
    volatility = math.sqrt(var_r)
    
    # Chaos tracking index
    chaos_index = volatility * abs(score)
    
    # Threshold check for next Drift
    threshold = 0.05
    is_drift_point = bool(chaos_index > threshold)
    
    return {
        'volatility': float(volatility),
        'chaos_index': float(chaos_index),
        'threshold': float(threshold),
        'is_drift_point': is_drift_point
    }
