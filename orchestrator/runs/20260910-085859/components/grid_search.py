import json
import numpy as np

def solve(inputs):
    # 선행 노드에서 이미 JSON 문자열로 넘어온 데이터를 파싱
    raw_data = inputs['load_data']
    if isinstance(raw_data, str):
        data = json.loads(raw_data)
    else:
        data = raw_data
        
    btc = np.array(data['btc'])
    xrp = np.array(data['xrp'])
    
    best_mse = float('inf')
    best_params = {"alpha": 0.0, "beta": 0.0}
    
    # 정밀 탐색을 위해 스텝을 0.05 단위(41개 지점)로 조정하여 최적화
    alphas = np.linspace(-1.0, 1.0, 41)
    betas = np.linspace(-1.0, 1.0, 41)
    
    for a in alphas:
        for b in betas:
            # 선형 모델: xrp_pred = alpha * btc + beta
            pred = a * btc + b
            mse = float(np.mean((xrp - pred)**2))
            if mse < best_mse:
                best_mse = mse
                best_params = {"alpha": float(a), "beta": float(b)}
    
    # 결과를 JSON 직렬화가 가능한 딕셔너리 형태로 반환
    return {
        "params": best_params, 
        "mse": float(best_mse)
    }