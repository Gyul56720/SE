import json

def solve(inputs):
    grid_search_data = inputs['grid_search']
    if isinstance(grid_search_data, str):
        params = json.loads(grid_search_data)['params']
    else:
        params = grid_search_data['params']
    
    last_btc = 60000.0 
    prediction = last_btc * (1 + params['alpha'] * 0.01 + params['beta'] * 0.01)
    return {"forecast": float(prediction)}