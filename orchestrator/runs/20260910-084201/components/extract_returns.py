import json

def solve(inputs):
    try:
        with open('coin/corpus/price_XRP.json', 'r') as f:
            data = json.load(f)
    except Exception:
        return {'returns': [], 'last_price': 0.0}

    # 데이터 구조 확인: 리스트 내부에 딕셔너리가 있는 경우와 데이터 전체가 딕셔너리인 경우 모두 고려
    if isinstance(data, dict):
        # 만약 데이터가 {'data': [...]} 형태라면 처리
        if 'data' in data:
            data = data['data']
        else:
            # 키가 날짜이고 값이 딕셔너리인 경우 등
            data = list(data.values())

    prices = []
    for entry in data:
        # 데이터가 딕셔너리형태인지 확인하고 price 추출
        if isinstance(entry, dict) and 'price' in entry:
            prices.append(float(entry['price']))
        elif isinstance(entry, (int, float)):
            prices.append(float(entry))

    if len(prices) < 2:
        return {'returns': [0.0], 'last_price': prices[-1] if prices else 0.0}

    returns = [(prices[i] / prices[i - 1]) - 1 for i in range(1, len(prices))]
    
    # JSON 직렬화 가능하도록 보장
    return {
        'returns': [float(x) for x in returns],
        'last_price': float(prices[-1])
    }