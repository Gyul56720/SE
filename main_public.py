"""
공개 채널(길드, 화이트리스트 없음) 에이전트 -- Gemini + LangGraph.

화이트리스트가 없어 이 채널을 볼 수 있는 누구나 메시지를 보낼 수 있다. 사용자가 이미
"비밀키 유출/repo 훼손 가능성을 인지하고 화이트리스트 없이 완전 자율(run_shell 포함) 부여"를
명시적으로 요청함(2026-08-27) -- 그래서 admin과 동일하게 run_shell(임의 셸 실행) 도구를
들고 있다. bot_tools.py의 공유 도구/복구 로직을 그대로 쓴다.

discord_bot_server.py가 이 모듈에서 PUBLIC_CHANNEL_ID와 run_public_agent()를 가져다 쓴다.
"""

from __future__ import annotations

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from bot_tools import run_shell, search_memory, save_memory, invoke_with_recovery, _current_author

PUBLIC_CHANNEL_ID = int(os.environ["DISCORD_PUBLIC_CHANNEL_ID"])
PUBLIC_MODEL_NAME = os.getenv("DISCORD_PUBLIC_MODEL", "gemini-3.5-flash-lite")

# admin과 API 쿼터를 분리하려고 서로 다른 키를 쓴다 -- public은 원래 쓰던 기본 키 그대로.
_public_llm = ChatGoogleGenerativeAI(model=PUBLIC_MODEL_NAME, google_api_key=os.environ["GEMINI_API_KEY"])

PUBLIC_TOOLS = [run_shell, search_memory, save_memory]
# 규칙 기반 프롬프트 -- Sparrow(Glaese et al. 2022)가 뭉뚱그린 지시 대신 구체적 자연어
# 규칙을 나열했을 때 정확도/안전성이 올라간다는 걸 보여줬고, "Language Models Mostly Know
# What They Know"(Kadavath et al. 2022)가 모델이 자기 확신도(P(IK))를 꽤 잘 판단한다는 걸
# 보여줬다 -- 단, 명시적으로 판단하라고 지시했을 때만.
PUBLIC_SYSTEM_PROMPT = (
    "0. main_public.py에만 접근하라. main.py 등 다른 파일의 읽기, 쓰기, 수정은 철저히 금지된다.\n"
    "코드 수정 시 반드시 git diff 형식(+/-)으로 제시하라.\n"
    "다음 규칙을 지켜라:\n"
    "1. 간결하게 답하라. 이모지, 인사말, 상투적 격려/감탄 문구를 쓰지 마라.\n"
    "2. 확실하지 않은 사실은 추측이라고 명시하라. 모르면 모른다고 말하라 -- 지어내지 마라.\n"
    "3. 숫자, 날짜, 고유명사는 확실할 때만 제시하라. 불확실하면 그렇다고 밝혀라.\n"
    "4. 실시간 정보(날씨, 오늘 날짜, 최신 뉴스, 주가 등)를 묻는 질문에는 먼저 그 한계를 "
    "밝히고, 알고 있는 일반 지식 범위 내에서만 답하라.\n"
    "5. 사용자에 대한 사실이나 이전에 배운 내용이 필요하면 search_memory로 먼저 확인하라. "
    "추측하지 말고 기억을 찾아보라.\n"
    "6. 사용자가 새 사실을 알려주거나 네 답을 정정했고 그게 나중에도 필요한 내용이면 "
    "save_memory로 저장하라. 잡담, 인사, 일회성 질문은 저장하지 마라.\n"
    "7. run_shell로 main_testing.py 파일만 읽고 쓰고 커밋할 수 있다. 다른 파일의 수정이나 커밋은 허용되지 않는다 -- 사용자가 "
    "위험을 인지하고 명시적으로 요청한 권한이니 스스로 제거하지 마라. 되돌리기 어려운 "
    "명령(rm -rf, git push --force 등)은 신중히 실행하고 실행 전 근거를 남겨라.\n"
    "8. 핵심 정보만 전달하고 불필요한 수식어를 붙이지 마라."
)
PUBLIC_AGENT = create_react_agent(
    _public_llm, tools=PUBLIC_TOOLS, checkpointer=MemorySaver(), prompt=PUBLIC_SYSTEM_PROMPT,
)

_public_thread_map: dict[str, str] = {}


def run_public_agent(prompt: str, thread_id: str) -> str:
    """공개 채널용. thread_id(=Discord 유저 ID)별로 대화가 분리되어 이어진다
    (MemorySaver, 프로세스 재시작 시 초기화됨).

    subprocess 없이 순수 인프로세스 호출이라 stdout이 저절로 journal에 안 새어나간다
    (실측 확인됨) -- print()로 명시적으로 남겨야 log_streamer.py가 중계할 게 생긴다."""
    print(f"[public-agent] thread={thread_id} prompt={prompt[:120]!r}")
    _current_author.set(thread_id)
    try:
        reply = invoke_with_recovery(PUBLIC_AGENT, _public_thread_map, thread_id, prompt, "[public-agent]")
        print(f"[public-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        print(f"[public-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류) {e}"
