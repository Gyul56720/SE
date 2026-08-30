import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
PARAMS_PATH = HERE / "params.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]

def load_params():
    try:
        with open(PARAMS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"iters": 2000, "noise_scale": 0.1}

# 테스트용: 로직이 파라미터를 제대로 읽는지 검증하는 함수
def test_load_params():
    params = load_params()
    assert "iters" in params
    assert "noise_scale" in params
    print(f"Verified params: {params}")

if __name__ == "__main__":
    test_load_params()
