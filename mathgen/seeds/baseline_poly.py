"""기준선 씨앗. sympy 가 즉시 푸는 쉬운 부정적분.

이 생성기는 **통과하면 안 된다** -- 비자명성 축에서 떨어져야 정상이다. 심판이 아무것도
기각하지 못하면 그것도 고장이므로, 확실히 떨어지는 대조군을 하나 둔다."""
import random


def generate(seed: int) -> dict:
    rng = random.Random(seed)
    a, b, n = rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 4)
    expr = f"{a}*x**{n} + {b}*x"
    ans = f"{a}*x**{n + 1}/{n + 1} + {b}*x**2/2"
    return {
        "statement": f"다음 부정적분을 구하시오:  ∫ ({a}x^{n} + {b}x) dx",
        "spec": {"task": "integrate", "expr": expr, "var": "x"},
        "answer": ans,
        "solution": [f"{a}*x**{n+1}/{n+1}", f"{b}*x**2/2", ans],
    }
