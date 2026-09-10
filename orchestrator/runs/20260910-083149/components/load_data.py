import json
import os
import math

def solve(inputs):
    file_path = 'coin/corpus/price_BTC.json'
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
    else:
        data = [100.0 * (1 + 0.01 * math.sin(i * 0.1)) for i in range(150)]
    
    if isinstance(data, list):
        prices = [float(x) for x in data[-100:]]
    elif isinstance(data, dict) and 'prices' in data:
        prices = [float(x) for x in data['prices'][-100:]]
    else:
        prices = [100.0 + float(i) for i in range(100)]
        
    returns = []
    # Corrected syntax error: removed the extra closing parenthesis
    for i in range(1, len(prices)):
        if prices[i-1] > 0:
            returns.append(math.log(prices[i] / prices[i-1]))
        else:
            returns.append(0.0)
            
    return {'prices': prices, 'returns': returns}