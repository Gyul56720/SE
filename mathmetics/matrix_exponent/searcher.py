import numpy as np
import json
import os

class Searcher:
    def __init__(self, b=3, m=21, learning_rate=0.01):
        self.b = b
        self.m = m
        self.lr = learning_rate
        self.log_file = "mathmetics/matrix_exponent/logs/history.jsonl"
        os.makedirs("mathmetics/matrix_exponent/logs", exist_ok=True)

    def propose(self):
        # 경사하강을 위한 작은 무작위 초기화 (정규화)
        A_coeffs = [{(i, j): np.random.normal(0, 0.1) for i in range(self.b) for j in range(self.b)} for _ in range(self.m)]
        B_coeffs = [{(i, j): np.random.normal(0, 0.1) for i in range(self.b) for j in range(self.b)} for _ in range(self.m)]
        
        # C_coeffs: 더 높은 수렴 확률을 위해 21개 중 임의 조합 (가중치 포함)
        C_coeffs = []
        for i in range(self.b):
            for j in range(self.b):
                num_terms = np.random.randint(1, 10)
                selected_m = np.random.choice(range(self.m), size=num_terms, replace=False)
                entry = {(i, j): [(k, np.random.normal(0, 1)) for k in selected_m]}
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
                "note": "Gaussian-initialized optimized C_coeffs search"
            }
            f.write(json.dumps(log_entry) + "\n")
