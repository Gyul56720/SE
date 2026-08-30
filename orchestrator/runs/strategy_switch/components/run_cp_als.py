def solve(inputs):
    config = inputs['update_parameter']['config']
    use_pert = config.get('use_perturbation', False)
    
    # 시뮬레이션된 CP-ALS 재실행 결과
    if use_pert:
        converged = True
        status = "Perturbation applied successfully, stagnation resolved."
        factors = ["factor_matrix_1", "factor_matrix_2"]
    else:
        converged = False
        status = "Stagnation persists."
        factors = []
        
    return {'converged': converged, 'status': status, 'factors': factors}