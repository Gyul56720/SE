def check(output, inputs):
    returns = output['returns']
    if not isinstance(returns, list) or len(returns) == 0: return False, 'Empty returns'
    return True, 'Success'