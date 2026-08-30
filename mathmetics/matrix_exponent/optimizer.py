import json
from pathlib import Path

PARAMS_PATH = Path(__file__).resolve().parent / "params.json"
DEFAULTS = {"iters": 2000, "noise_scale": 0.1, "use_perturbation": False}

# 정체가 확인될 때마다 한 칸씩 올라가는 탐색 예산 사다리. 예전엔 정체 때마다 무조건
# iters=5000을 다시 써서, 이미 5000인 상태에서도 매 회 같은 값을 파일에 쓰며 "예산을
# 올렸다"고 출력했다(실제로는 아무것도 안 바뀜). 단계로 만들어 두면 더 올릴 여지가
# 남았는지, 사다리 끝에 도달했는지를 호출부가 구분할 수 있다.
BUDGET_LADDER = [
    {"iters": 2000, "noise_scale": 0.10},
    {"iters": 3000, "noise_scale": 0.08},
    {"iters": 5000, "noise_scale": 0.05},
    {"iters": 8000, "noise_scale": 0.03},
]


def load_params() -> dict:
    params = dict(DEFAULTS)
    if PARAMS_PATH.exists():
        try:
            with open(PARAMS_PATH, "r") as f:
                params.update(json.load(f))
        except (json.JSONDecodeError, OSError, ValueError):
            pass
    return params


def update_params(iters=None, noise_scale=None, use_perturbation=None):
    """파라미터를 갱신한다. 실제로 값이 바뀌었을 때만 파일에 쓰고 changed=True를 돌려준다
    -- 호출부가 '바뀐 게 없는데 바뀐 척' 보고하지 않게 하려는 것."""
    params = load_params()
    before = dict(params)

    if iters is not None:
        params["iters"] = int(iters)
    if noise_scale is not None:
        params["noise_scale"] = float(noise_scale)
    if use_perturbation is not None:
        params["use_perturbation"] = bool(use_perturbation)

    changed = params != before
    if changed:
        with open(PARAMS_PATH, "w") as f:
            json.dump(params, f, indent=4)
    return changed, params


def escalate_budget():
    """현재 설정보다 한 칸 위의 예산으로 올린다. 이미 사다리 끝이면 아무것도 안 바꾸고
    changed=False를 돌려준다 -- '더 올릴 데가 없다'는 걸 호출부가 알 수 있어야 한다."""
    params = load_params()
    current = params.get("iters", DEFAULTS["iters"])
    for step in BUDGET_LADDER:
        if step["iters"] > current:
            changed, params = update_params(
                iters=step["iters"], noise_scale=step["noise_scale"], use_perturbation=True
            )
            return changed, params
    return False, params
