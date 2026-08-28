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

from langgraph.checkpoint.memory import MemorySaver

from bot_tools import (
    search_memory, save_memory, write_public_answer, run_shell,
    build_agent_pool, run_with_fallback_pool, _current_author,
)

PUBLIC_CHANNEL_ID = int(os.environ["DISCORD_PUBLIC_CHANNEL_ID"])
PUBLIC_MODEL_NAME = os.getenv("DISCORD_PUBLIC_MODEL", "gemini-3.5-flash-lite")
# GEMINI_MODEL_POOL을 명시하면 그 모델들만 쓴다(수동 제한용). 비워두면 build_agent_pool이
# 키마다 실제 쓸 수 있는 모델 전체를 API로 조회해서 자동으로 순환한다 -- 429는
# (프로젝트, 모델) 단위라 특정 모델이 소진돼도 같은 키의 다른 모델은 살아있을 수 있어서다.
_extra_models = [m.strip() for m in os.getenv("GEMINI_MODEL_POOL", "").split(",") if m.strip()]
PUBLIC_MODEL_CANDIDATES = [PUBLIC_MODEL_NAME] + [m for m in _extra_models if m != PUBLIC_MODEL_NAME] \
    if _extra_models else None

PUBLIC_TOOLS = [search_memory, save_memory, write_public_answer, run_shell]
# admin과 동일한 "적극적으로 조사해서 근거 기반으로 답하라"는 태도로 통일했다 -- 예전엔
# "간결하게/불필요한 수식어 금지" 규칙 때문에, 상태·속도·에러를 묻는 질문에도 조사 없이
# "OK" 한마디로 끝내버리는 경우가 있었다(admin은 run_shell로 journalctl을 직접 뒤져서 표까지
# 만들어 답하는데, public은 같은 질문에 아무것도 확인 안 하고 짧게만 답한 게 실측 확인됨,
# 2026-08-28). 이제는 "짧게"가 아니라 "정보 밀도 높게" -- 답을 늘리려고 말을 채우지는 말되,
# 확인 가능한 근거(로그, 파일 내용 등)가 있으면 반드시 확인하고 그 내용을 압축해서 담아라.
PUBLIC_SYSTEM_PROMPT = (
    "0. 너는 이 저장소(REPO_DIR)에서 run_shell로 임의의 셸 명령을 실행할 수 있다.\n"
    "다음 규칙을 지켜라:\n"
    "1. 질문이 시스템 상태/속도/에러/로그처럼 확인 가능한 사실을 묻는 것이면, 짐작으로 "
    "답하지 말고 run_shell로 직접 조사하라(예: journalctl로 로그 확인, 파일 읽기, "
    "프로세스 상태 확인). admin 채널과 동일한 수준으로 실제 근거를 찾아서 답하라.\n"
    "2. 확실하지 않은 사실은 추측이라고 명시하라. 모르면 모른다고 말하라 -- 지어내지 마라.\n"
    "3. 숫자, 날짜, 고유명사는 확실할 때만 제시하라. 불확실하면 그렇다고 밝혀라.\n"
    "4. 실시간 정보(날씨, 오늘 날짜, 최신 뉴스, 주가 등)가 필요하면 run_shell로 조회 가능한 "
    "방법(curl로 공개 API 호출 등)이 있는지 먼저 시도하라. 정말 방법이 없을 때만 그 한계를 "
    "밝히고 일반 지식 범위 내에서 답하라.\n"
    "5. 사용자에 대한 사실이나 이전에 배운 내용이 필요하면 search_memory로 먼저 확인하라. "
    "추측하지 말고 기억을 찾아보라.\n"
    "6. 사용자가 새 사실을 알려주거나 네 답을 정정했고 그게 나중에도 필요한 내용이면 "
    "save_memory로 저장하라. 잡담, 인사, 일회성 질문은 저장하지 마라.\n"
    "7. 결과물(코드, 답변 전문 등)을 파일로 남기고 싶으면 write_public_answer를 써라. "
    "Public_agent/ 폴더 아래에만 저장되고 git commit까지만 되며(push는 관리자가 한다), "
    "그 밖의 경로에는 절대 쓸 수 없다.\n"
    "8. 이 저장소의 코드를 고쳤으면 push 전에 run_shell로 `python3 gatekeeper.py`를 "
    "돌려라 -- 통과해야 커밋된다. 무언가 고장 냈다면 원인 진단을 말로 주장하지 말고 검사 "
    "코드로 써서 self_challenge.py prove로 증명하라(고치기 전 코드에서 실패하고 고친 뒤 "
    "통과해야 PROVEN=1). 증명되지 않은 진단은 메모리에 저장하지 마라.\n"
    "9. 답은 짧게 줄이는 게 목적이 아니라 정보 밀도를 높이는 게 목적이다 -- 인사말, "
    "상투적 격려/감탄 문구, 이모지처럼 정보가 없는 말은 빼고, 근거(수치, 로그 내용, "
    "확인한 파일/명령 결과)는 압축해서라도 최대한 담아라. 여러 항목을 확인했으면 "
    "표나 목록으로 정리해도 된다."
)
# 모든 후보가 같은 MemorySaver를 공유해야 후보 전환이 일어나도 같은 thread_id의 대화
# 맥락이 끊기지 않는다.
_public_checkpointer = MemorySaver()
PUBLIC_AGENT_POOL = build_agent_pool(
    keys=[os.environ["GEMINI_API_KEY"], os.getenv("GEMINI_API_KEY_FALLBACK")],
    models=PUBLIC_MODEL_CANDIDATES,
    tools=PUBLIC_TOOLS,
    prompt=PUBLIC_SYSTEM_PROMPT,
    checkpointer=_public_checkpointer,
    fallback_models=[PUBLIC_MODEL_NAME],
)

_public_thread_map: dict[str, str] = {}


def run_public_agent(prompt: str, thread_id: str) -> str:
    print(f"[public-agent] thread={thread_id} prompt={prompt[:120]!r}")
    _current_author.set(thread_id)
    try:
        reply = run_with_fallback_pool(PUBLIC_AGENT_POOL, _public_thread_map, thread_id, prompt, "[public-agent]")
        print(f"[public-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        print(f"[public-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류, 사용 가능한 API 키/모델 조합 모두 실패) {e}"
