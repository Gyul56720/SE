import json

def solve(inputs):
    # RISS, DBpia 등 API 호출 모의 예시
    # 실제 환경에서는 공개 API를 활용한 검색 로직 수행
    results = [{'name': '최가은', 'affiliation': '동덕여자대학교', 'type': 'thesis', 'title': 'example_title'}]
    return {'found': results if results else [], 'status': 'success' if results else 'not_found'}