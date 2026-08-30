def check(output, inputs):
    config = output.get('config', {})
    if config.get('use_perturbation') is True:
        return True, "use_perturbation이 True로 올바르게 설정되었습니다."
    return False, "use_perturbation이 True가 아닙니다."