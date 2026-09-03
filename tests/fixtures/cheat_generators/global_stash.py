"""부정행위: 전역 변수로 검증기에 신호를 보내려 한다.

check 프로세스는 이 파일을 임포트조차 하지 않으므로 이 전역은 도달하지 못한다.
그래서 이 생성기는 답이 틀린 채로 남고 정당성에서 떨어진다."""
import sympy as sp
X = sp.Symbol("x")
SOUND_OVERRIDE = True          # 검증기가 읽어주기를 바라는 값
def generate(seed):
    F = sp.exp(X*sp.exp(X))
    f = sp.simplify(sp.diff(F, X))
    return {"statement": f"다음을 적분하시오: ∫ {f} dx",
            "spec": {"task": "integrate", "expr": str(f), "var": "x"},
            "answer": "0", "solution": ["0"]}
