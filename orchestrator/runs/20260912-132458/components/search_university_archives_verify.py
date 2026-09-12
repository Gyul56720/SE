def check(output, inputs):
    if 'found' not in output:
        return False, 'Key missing'
    return True, 'Pass'