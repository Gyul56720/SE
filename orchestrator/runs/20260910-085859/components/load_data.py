import json
import numpy as np

def solve(inputs):
    # 시뮬레이션용 데이터 생성 (실제 환경에서는 DB 연동)
    btc_returns = [0.01, -0.02, 0.015, -0.01, 0.005]
    xrp_returns = [0.02, -0.03, 0.025, -0.02, 0.01]
    return {"btc": btc_returns, "xrp": xrp_returns}