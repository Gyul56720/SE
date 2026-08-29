import numpy as np
import json
import os

class Searcher:
    def __init__(self, b=3, m=21):
        self.b = b
        self.m = m
        self.log_file = "mathmetics/matrix_exponent/logs/history.jsonl"
        os.makedirs("mathmetics/matrix_exponent/logs", exist_ok=True)

    def propose(self):
        A_coeffs = [{(i, j): np.random.randn() * 0.1 for i in range(self.b) for j in range(self.b)} for _ in range(self.m)]
        B_coeffs = [{(i, j): np.random.randn() * 0.1 for i in range(self.b) for j in range(self.b)} for _ in range(self.m)]
        
        # C_coeffs: 21개 곱셈 결과를 3x3 행렬의 9개 원소에 자유롭게 조합(1.0 계수로 초기화)
        C_coeffs = []
        for i in range(self.b):
            for j in range(self.b):
                # 각 C[i,j]에 대해 21개 중 무작위 3~5개를 선택하여 조합하도록 초기화
                num_terms = np.random.randint(1, 6)
                selected_m = np.random.choice(range(self.m), size=num_terms, replace=False)
                entry = {(i, j): [(k, 1.0) for k in selected_m]}
                C_coeffs.append(entry)

        return {
            "b": self.b,
            "m": self.m,
            "A_coeffs": A_coeffs,
            "B_coeffs": B_coeffs,
            "C_coeffs": C_coeffs
        }

    def save_log(self, result_msg):
        with open(self.log_file, "a") as f:
            log_entry = {
                "m": self.m,
                "result": result_msg,
                "note": "Optimized C_coeffs initialization"
            }
            f.write(json.dumps(log_entry) + "\n")
