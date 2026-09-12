import json
def solve(inputs):
    academic = inputs['search_academic_archives']
    university = inputs['search_university_archives']
    if not academic['found'] and not university['found']:
        return {'status': 'failed', 'reason': 'No records found in targeted databases'}
    return {'status': 'found', 'data': academic['found'] + university['found']}