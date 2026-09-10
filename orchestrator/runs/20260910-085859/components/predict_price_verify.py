def check(output, inputs):
    if isinstance(output['forecast'], float):
        return True, "Forecast generated"
    return False, "Forecast invalid"