import json
from fractions import Fraction

def check(output, inputs):
    # Reconstruct tensor and compare with target.json
    with open('/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-130156/verifiers/target.json', 'r') as f:
        target = json.load(f)
    
    t_data = target['cases'][0]['entries']
    tensor_map = {(e[0], e[1], e[2]): e[3] for e in t_data}
    
    case = output['cases'][0]
    M = case['rank']
    u = [[Fraction(x) for x in row] for row in case['u']]
    v = [[Fraction(x) for x in row] for row in case['v']]
    w = [[Fraction(x) for x in row] for row in case['w']]
    
    for a in range(9):
        for b in range(9):
            for c in range(9):
                val = sum(u[r][a] * v[r][b] * w[r][c] for r in range(M))
                if val != Fraction(tensor_map.get((a,b,c), 0)):
                    return False, f"Mismatch at {a},{b},{c}: Expected {tensor_map.get((a,b,c), 0)}, got {val}"
    return True, "Success"