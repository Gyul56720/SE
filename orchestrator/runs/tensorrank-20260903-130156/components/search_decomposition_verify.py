import json, fractions

def check(output, inputs):
    # Verify using the target.json definition: T[a][b][c] = sum(u*v*w)
    with open('/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-130156/verifiers/target.json', 'r') as f:
        target = json.load(f)
    
    case = output['cases'][0]
    # Reconstruct tensor from decomposition
    recon = {}
    M = case['rank']
    u = [[fractions.Fraction(val) for val in row] for row in case['u']]
    v = [[fractions.Fraction(val) for val in row] for row in case['v']]
    w = [[fractions.Fraction(val) for val in row] for row in case['w']]
    
    for r in range(M):
        for i in range(9):
            for j in range(9):
                for k in range(9):
                    val = u[r][i] * v[r][j] * w[r][k]
                    recon[(i, j, k)] = recon.get((i, j, k), 0) + val

    # Compare with target entries
    for entry in target['cases'][0]['entries']:
        i, j, k, v_target = entry
        if recon.get((i, j, k), 0) != v_target:
            return False, f"Mismatch at {i},{j},{k}: Expected {v_target}, got {recon.get((i, j, k), 0)}"
    return True, "OK"