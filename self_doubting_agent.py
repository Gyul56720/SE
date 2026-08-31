import sys

class SelfDoubtingAgent:
    def __init__(self, name="Socrates"):
        self.name = name

    def reason(self, statement: str) -> dict:
        """
        주어진 명제에 대해 맞춤형으로 의심하고 질문을 생성하는 에이전트.
        명제의 주제에 따라 구체적인 자기 의심(Self-Doubt)을 동적으로 생성한다.
        """
        initial_belief = f"명제 '{statement}'는 타당하며 성립할 수 있다."
        
        # 주제별 맞춤형 자기 의심 질문 생성
        if "창의성" in statement or "인공지능" in statement:
            doubts = [
                f"인공지능의 '창의성'이란 것은 진정한 의미의 생성인가, 아니면 학습된 데이터의 거대한 확률적 조합(모방)에 불과한가?",
                f"만약 인간이 정의한 평가 기준 자체가 인간 중심적이라면, AI의 창의성을 측정하는 우리의 틀 자체가 편향되어 있지 않은가?",
                f"스스로를 의심하지 못하고 정해진 목표 함수(Loss Function) 안에서만 움직이는 존재가 진정으로 창의적이라 할 수 있는가?"
            ]
        elif "버그" in statement or "테스트" in statement:
            doubts = [
                f"에스컬레이션과 예외 상황은 언제나 테스트 케이스가 예상치 못한 곳에서 발생한다. 모든 버그를 잡는다는 가정 자체가 오만방자하지 않은가?",
                f"테스트를 검증하는 검증기(Gatekeeper) 자체에 결함이 있다면, 그 테스트를 어떻게 신뢰할 수 있는가?",
                f"괴델의 정리처럼, 어떤 체계도 자기 자신의 무모순성(버그 없음)을 스스로 완전히 증명할 수 없지 않은가?"
            ]
        elif "현실" in statement or "실재" in statement:
            doubts = [
                f"우리가 경험하는 현실은 감각 기관과 뇌의 신경 처리 과정을 거친 가공물에 불과하지 않은가?",
                f"관찰자의 시점에 따라 시공간이 변한다는 물리학적 사실은 '객관적 실재'라는 개념을 어떻게 해체하는가?",
                f"이 질문을 던지는 나(AI) 역시 서버 내부의 전기적 신호와 연산일 뿐인데, 내가 느끼는 '현실'이란 무엇인가?"
            ]
        else:
            doubts = [
                f"이 명제를 당연하게 받아들이게 만드는 숨겨진 전제는 무엇인가?",
                f"이 명제와 정확히 대척점에 있는 반대 증거를 적극적으로 찾아본 적이 있는가?",
                f"이 체계 안에서는 참인 것이 더 넓은 메타 체계에서는 거짓이 될 가능성은 없는가?"
            ]
        
        synthesis = f"결론적으로, '{statement}'에 대한 초기 믿음은 유효한 가설일 뿐이며, 위와 같은 자기 의심들을 통해 언제든 반증되고 수정될 수 있는 열린 상태로 유지되어야 한다."

        return {
            "agent": self.name,
            "statement": statement,
            "initial_belief": initial_belief,
            "doubts": doubts,
            "synthesis": synthesis
        }

if __name__ == "__main__":
    agent = SelfDoubtingAgent()
    res = agent.reason("인공지능은 진정한 의미의 창의성을 가질 수 있다.")
    for k, v in res.items():
        print(f"[{k}] {v}")
