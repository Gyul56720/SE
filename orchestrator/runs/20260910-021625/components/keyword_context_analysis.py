def solve(inputs):
    keyword = "시작 만화 라노벨 8000"
    # 시뮬레이션된 검색 및 맥락 분석
    analysis = {
        "keyword": keyword,
        "intent": "만화 및 라노벨 추천 또는 대규모(8000자) 가이드/콘텐츠 생성",
        "target_length": 8000,
        "categories": ["만화", "라이트노벨"]
    }
    return {"analysis": analysis}

def check(output, inputs):
    res = output.get("analysis")
    if not isinstance(res, dict):
        return False, "analysis is not a dict"
    if res.get("target_length") != 8000:
        return False, "target_length must be 8000"
    return True, ""