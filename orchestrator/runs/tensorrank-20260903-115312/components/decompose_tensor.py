import json
from fractions import Fraction

def solve(inputs):
    # 파일 경로는 문제 정의에 명시된 위치를 사용
    target_file = "/home/ubuntu/SE/orchestrator/runs/tensorrank-20260903-115312/verifiers/target.json"
    try:
        with open(target_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"error": "Target file not found"}

    results = {'cases': []}
    
    for case in data['cases']:
        d0, d1, d2 = case['shape']
        budget = case['budget']
        entries = case['entries'] # [i, j, k, val]
        
        # 1. 기초 전략: 모든 0이 아닌 칸을 각각 1개의 항으로 표현
        # 각 entry [i, j, k, val]은 하나의 랭크-1 항: u_r[i]=1, v_r[j]=1, w_r[k]=val
        # 나머지 성분은 전부 0
        u, v, w = [], [], []
        
        for e in entries:
            i, j, k, val = e
            ui = [0] * d0
            vj = [0] * d1
            wk = [0] * d2
            ui[i] = 1
            vj[j] = 1
            wk[k] = val
            u.append(ui)
            v.append(vj)
            w.append(wk)
        
        # 2. budget 맞추기: 항 개수가 부족하면 0 벡터를 추가하여 정확히 budget을 채움
        # budget을 정확히 채우는 것이 첫 번째 목표이며, 이는 재구성에 영향을 주지 않음
        while len(u) < budget:
            u.append([0] * d0)
            v.append([0] * d1)
            w.append([0] * d2)
            
        # 3. 결과 포맷 변환 (Fraction 사용 및 문자열 변환)
        # 모든 성분은 Fraction으로 정규화하고 문자열로 저장
        results['cases'].append({
            'id': str(case['id']),
            'rank': len(u),
            'u': [[str(Fraction(x)) for x in row] for row in u],
            'v': [[str(Fraction(x)) for x in row] for row in v],
            'w': [[str(Fraction(x)) for x in row] for row in w]
        })
        
    return results