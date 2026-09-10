def solve(inputs):
    prev = inputs["search_info"]
    plan = {
        "period": "2026-09-13(일) ~ 2026-09-16(수) (3박 4일)",
        "accommodation": prev["accommodation"],
        "transportation": prev["route_info"],
        "schedule": [
            {
                "date": "2026-09-13",
                "day_of_week": "일",
                "morning": "서울 출발 -> 제주국제공항 도착",
                "afternoon": "제주지방법원 인근 숙소 체크인 후 북동부 해안도로(함덕 등) 탐방",
                "evening": "저녁 식사 및 숙소 복귀"
            },
            {
                "date": "2026-09-14",
                "day_of_week": "월",
                "morning": "성산일출봉 대중교통 이동 및 관광",
                "afternoon": "우도 방문 또는 섭지코지 탐방",
                "evening": "제주시 숙소 복귀 및 휴식"
            },
            {
                "date": "2026-09-15",
                "day_of_week": "화",
                "morning": "비자림 숲길 산책",
                "afternoon": "세화해변 및 해안도로 카페 투어",
                "evening": "제주시내 맛집 탐방 및 숙소 복귀"
            },
            {
                "date": "2026-09-16",
                "day_of_week": "수",
                "morning": "제주시티투어 및 동문시장 기념품 쇼핑",
                "afternoon": "제주국제공항 이동",
                "evening": "제주 출발 -> 서울 도착"
            }
        ]
    }
    return plan