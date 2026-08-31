import numpy as np

class PrimordialAgent:
    """
    [환경과 공진하는 원시적 주체]
    - 지식(데이터) 대신 감각(State)과 반응(Action)만 존재.
    - 정답(Label) 대신 생존 보상(Reward)만 존재.
    - 언어 기반의 모든 지식을 차단하고 오직 원시적 신경망만 작동.
    """
    def __init__(self):
        # 0: 배고픔, 1: 온도, 2: 위험도
        self.state = np.array([0.5, 0.5, 0.0]) 
        # 신경망의 가중치 (아무런 지식도 없음)
        self.weights = np.random.randn(3, 2) * 0.1
        self.history = []

    def react(self):
        # 원시적 반응 (Action: 0-움직임, 1-휴식)
        activation = np.tanh(np.dot(self.state, self.weights))
        action = np.argmax(activation)
        return action

    def update(self, action):
        # 환경과의 상호작용 (Self-loop)
        # 움직이면 배고픔 줄고 온도 변화, 위험도 증가
        if action == 0:
            self.state[0] -= 0.1 # 배고픔 감소
            self.state[1] += 0.05 # 온도 변화
            self.state[2] += 0.1  # 위험도 증가
        else:
            self.state[0] += 0.05 # 배고픔 증가
            self.state[1] -= 0.02
        
        # 보상 계산: 생존(배고픔 적고 위험도 낮음)
        reward = - (self.state[0]**2 + self.state[2]**2)
        
        # 간단한 학습: 보상이 높으면 시냅스 강화
        if reward > -0.5:
            self.weights += 0.01 * np.outer(self.state, np.eye(2)[action])
            
        return reward

if __name__ == '__main__':
    agent = PrimordialAgent()
    print("[INIT] Primordial growth loop started.")
    for t in range(5):
        act = agent.react()
        rew = agent.update(act)
        print(f"  [Step {t}] State: {np.round(agent.state, 2)} | Action: {'Move' if act==0 else 'Rest'} | Reward: {rew:.2f}")
