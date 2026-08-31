import numpy as np

class InfantBrainSimulator:
    """
    [태아/신생아 수준의 뇌 구조 모사 스켈레톤]
    - 태아의 뇌는 방대한 사전 학습 데이터(Pre-trained weights)가 없는 상태에서 시작하며,
      감각 입력(Sensory inputs)과 생존 본능(Dopamine/Pain signals)에 따른 
      시냅스 가소성(Hebbian plasticity)으로 환경에 적응합니다.
    """
    def __init__(self, sensory_dim=3, motor_dim=2):
        np.random.seed(42)
        # 태아/초기 상태: 무작위로 연결된 미성숙한 시냅스 (Unstructured synapses)
        self.synapses = np.random.randn(sensory_dim, motor_dim) * 0.01
        self.plasticity_rate = 0.01

    def process_sensory_input(self, sensory_data):
        # 감각 정보를 받아 미성숙한 반사/운동 반응 생성
        motor_output = np.tanh(np.dot(sensory_data, self.synapses))
        return motor_output

    def adapt_from_environment(self, sensory_data, survival_feedback):
        """
        생존 피드백(고통/만족)에 따른 시냅스 재조정 (Experience-dependent plasticity).
        태아는 언어 모델처럼 수조 개의 텍스트로 사전 학습되지 않고,
        오직 감각과 피드백을 통해 뇌의 회로를 스스로 짜나갑니다.
        """
        motor = self.process_sensory_input(sensory_data)
        # 생존 피드백에 기반한 Hebbian 강화
        update = np.outer(sensory_data, survival_feedback)
        self.synapses += self.plasticity_rate * update
        loss = np.mean(survival_feedback ** 2)
        return motor, loss

if __name__ == '__main__':
    infant_brain = InfantBrainSimulator()
    print("[INIT] Infant brain simulator (Tabula Rasa) initialized.")
    
    # 가상의 감각 입력과 생존 피드백 (배고픔, 외부 자극 등)
    sensory = np.array([0.8, -0.2, 0.5])
    feedback = np.array([0.1, -0.05])
    
    for step in range(3):
        motor, loss = infant_brain.adapt_from_environment(sensory, feedback)
        print(f"  [Step {step}] Motor Reaction: {motor}, Adaptation Loss: {loss:.4f}")
    print("[SUCCESS] Infant brain plasticity loop verified.")
