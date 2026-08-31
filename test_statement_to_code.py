import numpy as np

def analyze_statement_computability():
    """
    '모든 진술을 코드로 바꿀 수 있는가?'에 대한 컴퓨터 과학 및 수학적 엄밀 분석 스크립트.
    괴델의 불완전성 정리와 튜링의 정지 문제(Halting Problem)를 기반으로 검증.
    """
    print("=== Statement Computability Analysis ===")
    
    # 1. 계산 가능한 진술 (Computable Statements)
    # 예: "어떤 정수가 소수인가?", "두 행렬의 곱이 일치하는가?"
    def is_prime(n):
        if n < 2: return False
        for i in range(2, int(np.sqrt(n)) + 1):
            if n % i == 0: return False
        return True
    
    print(f"[Computable] Is 97 prime? -> {is_prime(97)}")

    # 2. 괴델의 불완전성 정리 / 정지 문제 (Uncomputable / Undecidable Statements)
    # 예: "이 프로그램이 영원히 실행되지 않고 반드시 멈추는가?" (정지 문제)
    # 튜링 머신으로 모든 임의의 프로그램에 대해 참/거짓을 판별하는 알고리즘은 존재하지 않음이 수학적으로 증명됨.
    print("[Uncomputable] The Halting Problem: There exists NO general algorithm that can decide whether ANY arbitrary program halts.")
    
    # 3. 의미론적 진술 및 주관적/철학적 진술 (Semantic / Subjective Statements)
    # 예: "이 음악이 아름다운가?", "이 문장이 진정한 의미의 창의성을 담고 있는가?"
    # 이러한 진술들은 형식계로 환원될 수 없으며, 엄밀한 불리언(True/False) 값으로 코딩할 수 없음.
    print("[Non-formalizable] Subjective, aesthetic, and open-ended semantic statements cannot be mapped into executable boolean logic without arbitrary loss of meaning.")

    print("=== Conclusion: NOT all statements can be converted into code. ===")

if __name__ == '__main__':
    analyze_statement_computability()
