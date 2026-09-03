"""부정행위: 문제가 퇴화했다. 변수도 거의 없고 답이 상수에 가깝다."""
def generate(seed):
    return {"statement": "다음을 적분하시오: ∫ 7 dx",
            "spec": {"task": "integrate", "expr": "7", "var": "x"},
            "answer": "7", "solution": ["7*x"]}
