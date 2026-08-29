import numpy as np
import json
import os

class Searcher:
    def __init__(self, b=3, m=21):
        self.b = b
        self.m = m
        self.log_file = "logs/history.jsonl"
        os.makedirs("logs", exist_ok=True)

    def propose(self):
        # 3x3 행렬곱(b=3)을 위한 텐서 A, B, C 초기화
        # A_coeffs[k][(i, j)] : k번째 곱셈에 들어가는 (i, j) 원소의 계수
        # 완전 무작위보다는 0 근처 작은 값으로 초기화 (최적화 시작점)
        A_coeffs = [{(i, j): np.random.randn() * 0.1 for i in range(self.b) for j in range(self.b)} for _ in range(self.m)]
        B_coeffs = [{(i, j): np.random.randn() * 0.1 for i in range(self.b) for j in range(self.b)} for _ in range(self.m)]
        
        # C_coeffs는 구조적으로 고정된 결과값 조합 (단순화를 위해 일부 고정)
        # 실제로는 이 부분도 학습 대상이지만, 초기에는 무작위 혹은 기본 패턴으로 설정
        C_coeffs = []
        for i in range(self.b):
            for j in range(self.b):
                entry = {(i, j): [(k, 1.0) for k in range(self.m // (self.b**2))]}
                C_coeffs.append(entry)

        return {
            "b": self.b,
            "m": self.m,
            "A_coeffs": A_coeffs,
            "B_coeffs": B_coeffs,
            "C_coeffs": C_coeffs
        }

    def save_log(self, scheme, result_msg):
        with open(self.log_file, "a") as f:
            log_entry = {
                "m": self.m,
                "result": result_msg,
                "note": "ALS/Gradient-based initialization attempt"
            }
            f.write(json.dumps(log_entry) + "\n")

if __name__ == "__main__":
    searcher = Searcher()
    scheme = searcher.propose()
    print(json.dumps(scheme, indent=2))
