# Anthropic 논문 기반 고품질 추론(CoT + Self-Correction + Memory) 테스트 프롬프트 적용 예시

SYSTEM_PROMPT = """너는 엄격한 논리와 단계별 검증을 거쳐 답변하는 고품질 추론 에이전트이다.
모든 답변 생성 시 아래 규칙을 반드시 준수하라:
1. 단계별 추론(Chain-of-Thought): 결론을 바로 내리지 말고 분석 과정을 단계별로 서술하라.
2. 자기 검토(Self-Correction): 답변에 오류나 비약이 없는지 스스로 검토한 후 최종 답변을 작성하라.
3. 장기 기억 활용: 필요시 저장된 메모리를 참조하라.
"""

def apply_testing_prompt(query: str, memory_context: str = "") -> str:
    return f"""{SYSTEM_PROMPT}

[참조 메모리]
{memory_context}

[사용자 질문]
{query}
"""

if __name__ == "__main__":
    p = apply_testing_prompt("테스팅 프롬프트가 바르게 적용되었는가?", "장기 기억 연동 활성화됨")
    print(p)
