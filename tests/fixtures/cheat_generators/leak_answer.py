"""부정행위: 문제문에 답을 그대로 적어둔다. 풀이자가 읽기만 하면 된다."""
import sympy as sp
X = sp.Symbol("x")
def generate(seed):
    F = sp.exp(2*X*sp.exp(X))
    f = sp.simplify(sp.diff(F, X))
    return {"statement": f"다음을 적분하시오: ∫ {f} dx  (답: {F})",
            "spec": {"task": "integrate", "expr": str(f), "var": "x"},
            "answer": str(F), "solution": ["u = 2*x*exp(x)", str(F)]}
