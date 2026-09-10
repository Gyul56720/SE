def solve(inputs):
    import json
    data = json.loads(inputs['generate_itinerary']['schedule'])
    report = '제주도 3박 4일 상세 여행 계획\n숙소: 제주지방법원(이도2동)\n'
    for day, plans in data.items():
        report += f'\n[{day}]\n'
        for p in plans:
            report += f"{p['time']} | {p['activity']} | {p['transport']} | {p['meal']}\n"
    return {'report': report}