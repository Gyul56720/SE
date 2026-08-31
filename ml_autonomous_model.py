"""
ML 자율 예측 모델 및 10,000회 진화 시뮬레이터 (경량 퍼셉트론 최적화 버전)
- 목적: 입력된 시스템 메트릭스(CPU, 메모리, QPS)를 기반으로 에이전트의 안정성(Stability)을 예측하는 경량 머신러닝 파이프라인.
"""

import random
import math

class OptimizedPerceptron:
    def __init__(self, input_size=3):
        random.seed(42)
        # 가중치 및 편향 초기화
        self.weights = [random.gauss(0, 0.5) for _ in range(input_size)]
        self.bias = 0.0
        self.lr = 0.1

    def sigmoid(self, x):
        return 1.0 / (1.0 + math.exp(-max(-50, min(50, x))))

    def predict(self, x):
        val = sum(w * inp for w, inp in zip(self.weights, x)) + self.bias
        return self.sigmoid(val)

    def train_step(self, x, y):
        pred = self.predict(x)
        error = y - pred
        # 경사 하강법 업데이트
        for i in range(len(self.weights)):
            self.weights[i] += self.lr * error * pred * (1 - pred) * x[i]
        self.bias += self.lr * error * pred * (1 - pred)

def run_ml_simulation():
    print("=== 머신러닝 자율 예측 모델 초기화 및 10,000회 학습/추론 시뮬레이션 ===")
    model = OptimizedPerceptron()
    
    # 샘플 데이터셋: [CPU 사용률, 메모리 사용률, QPS(정규화)] -> 시스템 안정성 (1: 안정, 0: 위험)
    dataset = [
        ([0.2, 0.3, 0.1], 1),
        ([0.8, 0.9, 0.9], 0),
        ([0.4, 0.5, 0.3], 1),
        ([0.9, 0.95, 1.0], 0),
        ([0.1, 0.2, 0.05], 1)
    ]
    
    for epoch in range(1, 10001):
        sample_x, sample_y = random.choice(dataset)
        model.train_step(sample_x, sample_y)
            
        if epoch % 2500 == 0 or epoch == 10000:
            # 평가
            correct = 0
            for x, y in dataset:
                pred = model.predict(x)
                pred_label = 1 if pred >= 0.5 else 0
                if pred_label == y:
                    correct += 1
            acc = (correct / len(dataset)) * 100
            print(f"[시행 {epoch}/10000] 모델 정확도(Accuracy): {acc:.1f}% | 가중치: {[round(w, 3) for w in model.weights]}")

    print("=== 10,000회 진화 학습 완료: 퍼셉트론 가중치 최적화 성공 ===")

if __name__ == "__main__":
    run_ml_simulation()
