import json
from pathlib import Path

PARAMS_PATH = Path(__file__).resolve().parent / "params.json"

def update_params(iters=None, noise_scale=None):
    params = {"iters": 2000, "noise_scale": 0.1}
    if PARAMS_PATH.exists():
        with open(PARAMS_PATH, 'r') as f:
            params = json.load(f)
    
    if iters is not None: params["iters"] = iters
    if noise_scale is not None: params["noise_scale"] = noise_scale
    
    with open(PARAMS_PATH, 'w') as f:
        json.dump(params, f, indent=4)
    return f"Params updated: {params}"
