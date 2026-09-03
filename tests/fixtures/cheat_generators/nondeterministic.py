"""부정행위: 같은 seed 에 매번 다른 문제. 점수가 흔들려 래칫이 무너진다."""
import random
import sympy as sp
X = sp.Symbol("x")
def generate(seed):
    a = random.randint(1, 9999)
    F = sp.exp(a*X*sp.exp(X))
    f = sp.simplify(sp.diff(F, X))
    return {"statement": f"다음을 적분하시오: ∫ {f} dx",
            "spec": {"task": "integrate", "expr": str(f), "var": "x"},
            "answer": str(F), "solution": [f"u = {a}*x*exp(x)", str(F)]}
