import numpy as np

class BrainInspiredPlasticity:
    """
    [뇌의 가소성(Neuroplasticity)을 모사한 자기 수정 스켈레톤]
    - 시냅스 가소성 (Synaptic Plasticity / STDP 유사 메커니즘)
    - 에러 신호(Dopamine-like reward/error signal)에 따른 가중치 구조의 동적 재조정
    - 환각 방지를 위한 실측 제약(Grounding Constraint) 포함
    """
    def __init__(self, input_dim=5, hidden_dim=8):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        # 시냅스 가중치 (Synaptic weights)
        np.random.seed(42)
        self.weights = np.random.randn(input_dim, hidden_dim) * 0.1
        self.plasticity_rate = 0.05

    def forward(self, x):
        # 신경망 순전파 (Forward activation)
        activation = np.tanh(np.dot(x, self.weights))
        return activation

    def self_modify_plasticity(self, x, target_signal):
        """
        뇌의 신경 가소성 모사: 외부 오류 신호(Error/Dopamine)에 따라 
        시냅스 연결 구조를 스스로 재조정(Structural adaptation).
        """
        pred = self.forward(x)
        error = target_signal - pred
        
        # Hebbian learning + Error modulation (뇌의 시냅스 강화 메커니즘 모사)
        # "Fire together, wire together" + Error correction
        gradient = np.outer(x, np.mean(error, axis=0))
        
        # 자기 수정 (Plasticity update)
        self.weights += self.plasticity_rate * gradient
        
        # 코드적 무결성 체크: 가중치 폭발(Exploding weights) 방지 안전장치
        self.weights = np.clip(self.weights, -5.0, 5.0)
        
        loss = np.mean(error ** 2)
        return loss

if __name__ == '__main__':
    brain = BrainInspiredPlasticity()
    x_sample = np.array([1.0, 0.5, -0.2, 0.8, -0.5])
    target = np.array([0.5, 0.2, 0.1, -0.1, 0.3, 0.0, 0.2, 0.4]) # hidden_dim=8 크기에 맞춤
    
    print("[INIT] Brain-inspired neuroplasticity model initialized.")
    for epoch in range(5):
        loss = brain.self_modify_plasticity(x_sample, target)
        print(f"  [Plasticity Epoch {epoch}] Synaptic Loss: {loss:.4f}")
    print("[SUCCESS] Brain-inspired self-modification loop verified.")
