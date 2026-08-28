"""
공개 채널(길드, 화이트리스트 없음) 에이전트 -- Gemini + LangGraph.

화이트리스트가 없어 이 채널을 볼 수 있는 누구나 메시지를 보낼 수 있다. run_shell(임의 셸
실행)을 admin과 동일하게 부여한다 -- 화이트리스트 없는 채널에 셸 실행 경로를 열어두는 위험을
사용자가 명시적으로 인지하고 감수하겠다고 요청했다. write_public_answer로 Public_agent/
폴더 밖으로 못 나가는 결과물 저장 도구도 함께 제공한다(public_agent_files.py가 경로를
코드로 강제, git commit까지만 하고 push는 안 함). bot_tools.py의 공유 도구/복구 로직을
그대로 쓴다.

discord_bot_server.py가 이 모듈에서 PUBLIC_CHANNEL_ID와 run_public_agent()를 가져다 쓴다.
"""

from __future__ import annotations

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from bot_tools import search_memory, save_memory, write_public_answer, run_shell, invoke_with_recovery, _current_author

PUBLIC_CHANNEL_ID = int(os.environ["DISCORD_PUBLIC_CHANNEL_ID"])
PUBLIC_MODEL_NAME = os.getenv("DISCORD_PUBLIC_MODEL", "gemini-3.5-flash-lite")

# admin과 API 쿼터를 분리하려고 서로 다른 키를 쓴다 -- public은 원래 쓰던 기본 키 그대로.
# GEMINI_API_KEY_FALLBACK이 설정돼 있으면 public 쿼터 소진 시 admin 쪽 키로 한 번 더
# 시도한다(_invoke_with_quota_fallback). ChatGoogleGenerativeAI 생성 자체는 API를 호출하지
# 않으므로(실제 요청은 invoke 시점에만 나감) 여기서 두 키 다 미리 만들어둬도 쿼터를 안 쓴다 --
# 과거에 시작할 때마다 "ping" 테스트 호출로 두 키 쿼터를 매 재시작마다 태워버린 적이 있었다
# (실측 확인됨, 2026-08-27) -- 그래서 지금은 시작 시 테스트 호출 없이, 실제 사용 중 429가
# 났을 때만 다른 키로 넘어간다.
_public_llm = ChatGoogleGenerativeAI(model=PUBLIC_MODEL_NAME, google_api_key=os.environ["GEMINI_API_KEY"])
_public_llm_fallback_key = os.getenv("GEMINI_API_KEY_FALLBACK")
_public_llm_fallback = (
    ChatGoogleGenerativeAI(model=PUBLIC_MODEL_NAME, google_api_key=_public_llm_fallback_key)
    if _public_llm_fallback_key else None
)

PUBLIC_TOOLS = [search_memory, save_memory, write_public_answer, run_shell]
PUBLIC_SYSTEM_PROMPT = (
    "0. 너는 이 저장소(REPO_DIR)에서 run_shell로 임의의 셸 명령을 실행할 수 있다. "
    "필요하면 run_shell로 파일을 읽고 쓰고 검증하라.\n"
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
    "7. 결과물(코드, 답변 전문 등)을 파일로 남기고 싶으면 write_public_answer를 써라. "
    "Public_agent/ 폴더 아래에만 저장되고 git commit까지만 되며(push는 관리자가 한다), "
    "그 밖의 경로에는 절대 쓸 수 없다.\n"
    "8. 핵심 정보만 전달하고 불필요한 수식어를 붙이지 마라."
)
# 두 에이전트가 같은 MemorySaver를 공유해야 쿼터 소진으로 fallback으로 넘어가도 같은
# thread_id의 대화 맥락이 끊기지 않는다.
_public_checkpointer = MemorySaver()
PUBLIC_AGENT = create_react_agent(
    _public_llm, tools=PUBLIC_TOOLS, checkpointer=_public_checkpointer, prompt=PUBLIC_SYSTEM_PROMPT,
)
PUBLIC_AGENT_FALLBACK = (
    create_react_agent(
        _public_llm_fallback, tools=PUBLIC_TOOLS, checkpointer=_public_checkpointer, prompt=PUBLIC_SYSTEM_PROMPT,
    )
    if _public_llm_fallback else None
)

_public_thread_map: dict[str, str] = {}


def _is_quota_error(e: Exception) -> bool:
    text = str(e)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def run_public_agent(prompt: str, thread_id: str) -> str:
    print(f"[public-agent] thread={thread_id} prompt={prompt[:120]!r}")
    _current_author.set(thread_id)
    try:
        reply = invoke_with_recovery(PUBLIC_AGENT, _public_thread_map, thread_id, prompt, "[public-agent]")
        print(f"[public-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        if PUBLIC_AGENT_FALLBACK is not None and _is_quota_error(e):
            print(f"[public-agent] thread={thread_id} quota exhausted, GEMINI_API_KEY_FALLBACK으로 재시도")
            try:
                reply = invoke_with_recovery(
                    PUBLIC_AGENT_FALLBACK, _public_thread_map, thread_id, prompt, "[public-agent-fallback]",
                )
                print(f"[public-agent-fallback] thread={thread_id} reply={reply[:200]!r}")
                return reply
            except Exception as e2:
                print(f"[public-agent-fallback] thread={thread_id} error={e2}")
                return f"(에이전트 오류, 두 API 키 모두 실패) {e2}"
        print(f"[public-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류) {e}"
