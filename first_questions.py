"""
역사적 수학/컴퓨터과학 논문들의 오프닝 질문(First Question / Introduction Premise) 분석
"""

papers = [
    {
        "author": "Alan Turing (1936)",
        "paper": "On Computable Numbers, with an Application to the Entscheidungsproblem",
        "first_question": "'결정문제(Entscheidungsproblem)'란 주어진 수학적 명제가 참인지 거짓인지 기계적으로 판별할 수 있는 일반적인 방법이 존재하는가?"
    },
    {
        "author": "Claude Shannon (1948)",
        "paper": "A Mathematical Theory of Communication",
        "first_question": "통신의 근본적인 문제(The fundamental problem of communication)란 한 지점에서 선택된 메시지를 다른 지점으로 정확히 또는 근사하게 재현하는 것인가?"
    },
    {
        "author": "Andrew Wiles (1995)",
        "paper": "Modular elliptic curves and Fermat's Last Theorem",
        "first_question": "모든 세미-스태이블(semi-stable) 타원 곡선은 모듈러 형식인가? (이 질문이 곧 350년 된 페르마의 마지막 정리를 여는 열쇠인가?)"
    }
]

for p in papers:
    print(f"[{p['author']}]")
    print(f"논문: {p['paper']}")
    print(f"핵심 첫 질문: {p['first_question']}\n")
