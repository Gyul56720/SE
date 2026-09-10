def check(output, inputs):
    import json
    try:
        data = json.loads(output['schedule'])
        if len(data) == 4 and len(data['Day1']) == 13:
            return True, 'Success'
        return False, 'Invalid schedule length'
    except:
        return False, 'Parsing error'