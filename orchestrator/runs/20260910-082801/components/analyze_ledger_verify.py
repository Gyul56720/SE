def check(output, inputs):
    required_keys = ['total_records', 'success_count', 'failure_count', 'top_success_ops', 'evolution_summary', 'failure_bottlenecks']
    for k in required_keys:
        if k not in output:
            return False, f"Missing key: {k}"
    if not isinstance(output['total_records'], int) or output['total_records'] < 0:
        return False, "total_records must be a non-negative integer"
    if output['success_count'] + output['failure_count'] > output['total_records']:
        return False, "Sum of successes and failures exceeds total records"
    return True, "Ledger analysis verified successfully."