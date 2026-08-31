import sys

class SelfDoubtingAgent:
    def __init__(self, name="Socrates"):
        self.name = name

    def reason(self, statement: str) -> dict:
        """
        주어진 명제에 대해 '주장'을 세우고, 
        그 주장을 스스로 '의심(반례 및 한계 탐색)'하여 
        더 깊은 결론을 도출하는 에이전트의 사고 프로세스.
        """
        # 1단계: 초기 주장 (Assertion)
        initial_belief = f"명제 '{statement}'는 진실일 가능성이 높다."
        
        # 2단계: 자기 의심 (Self-Doubt / Refutation)
        doubts = [
            f"하지만 만약 이 명제를 지탱하는 전제 조건이 무너지면 어떻게 되는가?",
            f"이 명제는 특정한 관점(Context)에서만 참이며, 다른 체계에서는 거짓이 될 수 있지 않은가?",
            f"괴델의 불완전성 정리처럼, 이 주장을 증명하려는 시도 자체가 모순을 낳지는 않는가?"
        ]
        
        # 3단계: 종합 및 한계 인정 (Synthesis & Limitation)
        synthesis = f"따라서, '{statement}'에 대한 나의 초기 믿음은 절대적 진리가 아니며, 반증 가능성을 내포한 가설로 재정의되어야 한다."

        return {
            "agent": self.name,
            "statement": statement,
            "initial_belief": initial_belief,
            "doubts": doubts,
            "synthesis": synthesis
        }

if __name__ == "__main__":
    agent = SelfDoubtingAgent()
    result = agent.reason("수학의 모든 진실은 기계적으로 증명할 수 있다.")
    for k, v in result.items():
        print(f"[{k}] {v}")
