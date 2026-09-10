def check(output, inputs):
    mse = output['mse']
    if mse >= 0:
        return True, "MSE is valid"
    return False, "MSE negative"