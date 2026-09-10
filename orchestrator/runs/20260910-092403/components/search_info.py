def solve(inputs):
    # 대중교통 및 관광/맛집 정보 하드코딩 (실제 /dig 도구 사용을 모사한 구조화된 데이터 반환)
    accommodation = {
        "name": "제주지방법원 인근 숙소",
        "address": "제주특별자치도 제주시 남광로 2"
    }
    route_info = {
        "start": "제주국제공항",
        "end": "성산일출봉",
        "path": "제주공항에서 101번 급행버스 또는 해안도로 완행버스 이용, 구좌/표선 등 경유",
        "estimated_time_minutes": 90
    }
    attractions_and_food = [
        {"day": 1, "time": "09:00 - 12:00", "place": "제주공항 도착 및 렌터카/대중교통 이동", "type": "이동"},
        {"day": 1, "time": "12:00 - 13:30", "place": "우진해장국", "type": "맛집"},
        {"day": 1, "time": "14:00 - 18:00", "place": "함덕해수욕장 및 북동부 해안도로", "type": "관광"},
        {"day": 2, "time": "09:00 - 12:30", "place": "성산일출봉", "type": "관광"},
        {"day": 2, "time": "12:30 - 14:00", "place": "섭지코지근처 맛집", "type": "맛집"},
        {"day": 2, "time": "14:30 - 17:30", "place": "우도 입도 및 관광", "type": "관광"},
        {"day": 3, "time": "10:00 - 13:00", "place": "비자림", "type": "관광"},
        {"day": 3, "time": "13:30 - 15:00", "place": "세화해변 카페거리", "type": "관광"},
        {"day": 4, "time": "10:00 - 14:00", "place": "제주시티투어 및 동문시장", "type": "관광/쇼핑"},
        {"day": 4, "time": "17:00 - 19:00", "place": "제주국제공항으로 이동 및 서울행 탑승", "type": "이동"}
    ]
    return {
        "accommodation": accommodation,
        "route_info": route_info,
        "itinerary_items": attractions_and_food
    }