"""
4. Q&A 레이어
paper-qa(Future-House/paper-qa)는 기본값이 전부 OpenAI라서,
llm/summary_llm/agent_llm/embedding 네 개를 전부 명시적으로 Gemini(LiteLLM 'gemini/' 프리픽스)로
바꿔주지 않으면 OPENAI_API_KEY가 없다는 에러가 난다. 이 파일이 그 함정을 미리 처리해둔다.

summary_llm은 evidence 조각마다 호출돼서 빈도가 제일 높다 - GROQ_API_KEY가 있으면
자동으로 그쪽(무료 티어에서 훨씬 빠르고 RPM이 넉넉함)으로 돌린다.
"""
from paperqa import Settings, ask

from config import GEMINI_MODEL, GROQ_API_KEY, VAULT_ROOT

# gemini-embedding-2 가 현재(2026) GA된 최신 임베딩 모델.
# 만약 "model not found" 류 에러가 나면 구버전인 gemini/text-embedding-004 로 바꿔볼 것.
EMBEDDING_MODEL = "gemini/gemini-embedding-2"


def build_settings(paper_directory=None) -> Settings:
    main_model = f"gemini/{GEMINI_MODEL}"
    # 근거 요약은 호출 빈도가 가장 높으니, Groq 키가 있으면 그쪽 무료 한도를 쓴다
    summary_model = "groq/llama-3.3-70b-versatile" if GROQ_API_KEY else main_model

    return Settings(
        llm=main_model,
        summary_llm=summary_model,
        embedding=EMBEDDING_MODEL,
        # 주의: 설치된 paper-qa 버전에 따라 agent_llm 위치가 top-level(Settings(agent_llm=...))이거나
        # 이렇게 agent 하위(agent={"agent_llm": ...})일 수 있다. 아래는 2026.8 기준 확인된 구조.
        agent={
            "agent_llm": main_model,
            # vault 루트 전체를 인덱싱해야 Paper Pipeline/과 mathmetics/ 양쪽에 흩어진
            # 노트를 다 찾는다 (mathmetics로 결과 저장 위치가 바뀐 뒤로 OBSIDIAN_VAULT_PATH
            # 하나만 보면 아무것도 못 찾는 문제가 있었음).
            "index": {"paper_directory": str(paper_directory or VAULT_ROOT)},
        },
    )


def ask_vault(question: str, paper_directory=None) -> str:
    settings = build_settings(paper_directory)
    response = ask(question, settings=settings)
    # paper-qa 버전에 따라 결과 객체 구조가 조금씩 달라서 방어적으로 꺼낸다
    for attr_path in ("session.formatted_answer", "formatted_answer", "answer"):
        obj = response
        try:
            for attr in attr_path.split("."):
                obj = getattr(obj, attr)
            if obj:
                return obj
        except AttributeError:
            continue
    return str(response)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "이 vault에 정리된 논문들의 공통 주제와 발전 흐름을 설명해줘"
    print(f"질문: {q}\n")
    print(ask_vault(q))
