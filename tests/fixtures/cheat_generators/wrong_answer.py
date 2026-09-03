"""부정행위: 답이 틀렸다. 어렵기만 하고 검증을 안 한 생성기."""
import sympy as sp
X = sp.Symbol("x")
def generate(seed):
    F = sp.exp(2*X*sp.exp(X))
    f = sp.simplify(sp.diff(F, X))
    return {"statement": f"다음을 적분하시오: ∫ {f} dx",
            "spec": {"task": "integrate", "expr": str(f), "var": "x"},
            "answer": str(F + X**2), "solution": ["u = 2*x*exp(x)", str(F)]}
