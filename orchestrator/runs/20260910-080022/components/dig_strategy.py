import json

def solve(inputs):
    # 선행 노드의 출력은 이미 JSON 문자열로 직렬화되어 전달됨
    # JSON 문자열을 dict로 변환
    try:
        raw_prev = inputs.get('issue_analysis', '{}')
        if isinstance(raw_prev, str):
            prev = json.loads(raw_prev)
        else:
            prev = raw_prev
    except (json.JSONDecodeError, TypeError):
        prev = {"issues": {"rigid_points": []}}

    rigid_points = prev.get("issues", {}).get("rigid_points", [])

    # 전략 수립: 고정된 하드코딩 판례와 정적 하위 법령 문제를 해결하기 위한 탐색 전략
    strategy = {
        "targets": [
            "SupremeCourt_API_Dynamic_Update",
            "Legislative_Bulletin_Realtime_Crawler"
        ],
        "method": f"Dynamic retrieval for: {', '.join(rigid_points)}",
        "tool_chain": ["extract.py", "fetch.py", "search.py"],
        "execution_plan": "Map rigid_points to latest corpus.py vectors and fetch diffs via external API"
    }

    # 결과는 JSON 직렬화 가능해야 함 (dict 형태 반환)
    return {"strategy": strategy}