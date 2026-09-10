def solve(inputs):
    import json
    schedule = {}
    days = ['Day1', 'Day2', 'Day3', 'Day4']
    activities = {'Day1': '동부권', 'Day2': '서부권', 'Day3': '남부권', 'Day4': '제주시내'}
    for day in days:
        day_plan = []
        for hour in range(8, 21):
            day_plan.append({'time': f'{hour}:00', 'activity': f'{activities[day]} 탐방', 'transport': '버스 및 도보', 'meal': '근처 맛집'})
        schedule[day] = day_plan
    return {'schedule': json.dumps(schedule)}