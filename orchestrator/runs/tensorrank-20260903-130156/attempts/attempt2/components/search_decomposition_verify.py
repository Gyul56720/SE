import json
from fractions import Fraction

def check(output, inputs):
    # Reconstruct and verify every single cell of the 9x9x9 tensor
    target_file = '/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-130156/verifiers/target.json'
    with open(target_file, 'r') as f: target = json.load(f)
    
    c_data = next(c for c in target['cases'] if c['id'] == 'mm333')
    tensor = {}
    for entry in c_data['entries']:
        tensor[(entry[0], entry[1], entry[2])] = entry[3]
    
    res = output['cases'][0]
    u, v, w = res['u'], res['v'], res['w']
    M = res['rank']
    
    for i in range(9):
        for j in range(9):
            for k in range(9):
                val = sum(u[r][i] * v[r][j] * w[r][k] for r in range(M))
                if val != tensor.get((i, j, k), 0):
                    return False, f"Mismatch at {i,j,k}: Expected {tensor.get((i,j,k),0)}, Got {val}"
    return True, "Match"
