def solve(inputs):
    # CP-ALS 설정에서 use_perturbation을 True로 변경
    config = inputs.get('config', {})
    config['use_perturbation'] = True
    return {'config': config}