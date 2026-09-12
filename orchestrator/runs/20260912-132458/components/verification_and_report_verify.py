def check(output, inputs):
    if output['status'] == 'failed':
        return 'reason' in output and len(output['reason']) > 0, 'Reason required'
    return True, 'Validated'