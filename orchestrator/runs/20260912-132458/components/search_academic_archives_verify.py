def check(output, inputs):
    if not isinstance(output.get('found'), list):
        return False, 'Output format error'
    if output['status'] == 'success':
        return all('동덕여자대학교' in item['affiliation'] for item in output['found']), 'Affiliation mismatch'
    return True, 'Status check passed'