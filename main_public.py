"""
공개 채널(길드, 화이트리스트 없음) 에이전트 -- Gemini + LangGraph.

화이트리스트가 없어 이 채널을 볼 수 있는 누구나 메시지를 보낼 수 있다. 예전에는 admin과
동일하게 run_shell(임의 셸 실행)을 main_testing.py 파일 한정으로 허용했는데(구 규칙 7),
화이트리스트 없는 채널에 셸 실행 경로를 열어두는 위험이 이득보다 커서 치웠다. 대신
write_public_answer로 Public_agent/ 폴더 밖으로 못 나가는 결과물 저장만 허용한다
(public_agent_files.py가 경로를 코드로 강제, git commit까지만 하고 push는 안 함).
bot_tools.py의 공유 도구/복구 로직을 그대로 쓴다.

run_self_correction(bot_tools.make_run_self_correction_tool)도 붙어 있다 -- 사용자가
채팅을 다시 치지 않아도 한 번의 도구 호출 안에서 diff 생성(이 _public_llm 호출) ->
적용 -> 서브프로세스 실행/검증 -> 실패 시 피드백 반영 재시도를 반복한다(self_correction.py,
Public_agent/Loop.py). 이건 익명 사용자가 지시한 코드를 서버에서 실행시키는 것과
같아서 run_shell을 없앤 이유와 본질적으로 같은 위험인데, 사용자가 위험을 인지하고
명시적으로 public 채널 연결을 요청함(2026-08-27). self_correction.py가 반복 횟수/
총 시간/입력 길이 상한과 서브프로세스 CPU·메모리 제한(RLIMIT)을 코드로 강제하지만,
컨테이너/seccomp 같은 진짜 샌드박스는 아니고 이 서버와 같은 OS 권한으로 돈다.

discord_bot_server.py가 이 모듈에서 PUBLIC_CHANNEL_ID와 run_public_agent()를 가져다 쓴다.
"""

from __future__ import annotations

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from bot_tools import (
    search_memory,
    save_memory,
    write_public_answer,
    make_run_self_correction_tool,
    invoke_with_recovery,
    _current_author,
)

PUBLIC_CHANNEL_ID = int(os.environ["DISCORD_PUBLIC_CHANNEL_ID"])
PUBLIC_MODEL_NAME = os.getenv("DISCORD_PUBLIC_MODEL", "gemini-3.5-flash-lite")

# admin과 API 쿼터를 분리하려고 서로 다른 키를 쓴다 -- public은 원래 쓰던 기본 키 그대로.
_public_llm = ChatGoogleGenerativeAI(model=PUBLIC_MODEL_NAME, google_api_key=os.environ["GEMINI_API_KEY"])

PUBLIC_TOOLS = [
    search_memory,
    save_memory,
    write_public_answer,
    make_run_self_correction_tool(_public_llm),
]
# 규칙 기반 프롬프트 -- Sparrow(Glaese et al. 2022)가 뭉뚱그린 지시 대신 구체적 자연어
# 규칙을 나열했을 때 정확도/안전성이 올라간다는 걸 보여줬고, "Language Models Mostly Know
# What They Know"(Kadavath et al. 2022)가 모델이 자기 확신도(P(IK))를 꽤 잘 판단한다는 걸
# 보여줬다 -- 단, 명시적으로 판단하라고 지시했을 때만.
PUBLIC_SYSTEM_PROMPT = (
    "0. 너는 파일을 직접 읽거나 쓰는 셸 접근 권한이 없다. 코드에 대해 이야기할 때는 "
    "설명이나 예시 코드로만 답하라.\n"
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
    "8. 핵심 정보만 전달하고 불필요한 수식어를 붙이지 마라.\n"
    "9. 사용자가 '~하는 함수/코드 만들어줘', '~될 때까지 고쳐줘' 같은 구현 요청을 하면 "
    "run_self_correction을 호출하라. 스켈레톤 코드나 테스트를 사용자가 안 줬어도 네가 "
    "직접 만들어서 인자로 채워라: skeleton_code는 함수 시그니처+docstring만 있고 본문은 "
    "비워둔(pass) 최소 뼈대, objective는 요청을 입출력 조건으로 바꾼 문장, test_code는 "
    "그 조건을 확인하는 assert 여러 줄(경계값, 빈 입력, 큰 입력 등 함정이 될 만한 케이스 "
    "포함)이다. 사용자가 이미 스켈레톤/테스트를 줬으면 그걸 그대로 쓰고 임의로 바꾸지 마라. "
    "매번 다시 채팅으로 답하지 말고 이 도구 호출 한 번으로 끝내라 -- 최대 10회/2분 상한이 "
    "있고, 상한에 닿으면 실패로 보고하되 그때까지 만든 코드는 그대로 보여줘라."
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
