"""
Discord 관리 채널(admin)과 공개 채널(public) 에이전트가 공유하는 도구/유틸리티.

REPO_DIR, run_shell(임의 셸 실행) 도구, 기억 검색/저장 도구, 공개 채널 결과물 저장 도구
(write_public_answer), Gemini 응답 파싱, 그리고 LangGraph MemorySaver가 깨졌을 때
(도구 호출 도중 중단되어 ToolMessage가 누락된 경우 등) 자동으로 새 thread로 재시도하는 복구
헬퍼를 모아둔다. admin/public 양쪽 모듈이 이 파일의 도구를 그대로 가져다 쓴다 -- 중복 정의를
피하고, 한쪽에서 도구 동작을 고치면 양쪽에 반영되게.

run_shell은 admin/public 채널 둘 다 쓴다. public 채널은 화이트리스트가 없어 임의 셸 실행을
주는 위험(누구나 트리거 가능)이 있지만, 사용자가 이를 명시적으로 인지하고 감수하겠다고
요청했다. write_public_answer는 별개로 계속 제공되며 Public_agent/ 폴더 안에만 결과 파일을
남기게 한다(public_agent_files.py가 경로를 코드로 강제한다).
"""

from __future__ import annotations

import contextvars
import hashlib
import os
import subprocess
import uuid
from typing import Optional

import requests
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

import agent_memory
import public_agent_files
import quota_tracker

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# 도구 함수는 모델이 부르므로 인자에 작성자 ID를 실어보낼 수 없다 -- 요청 단위로 여기에 담아둔다.
_current_author: contextvars.ContextVar[str] = contextvars.ContextVar("current_author", default="unknown")


@tool
def run_shell(command: str) -> str:
    """이 저장소(REPO_DIR)에서 임의의 셸 명령을 실행한다. admin/public 채널 둘 다 쓸 수
    있다 -- public은 화이트리스트가 없어 위험을 사용자가 감수하고 명시적으로 요청한 것이다.
    결과는 stdout/stderr을 그대로 반환한다."""
    try:
        result = subprocess.run(
            ["bash", "-lc", command], cwd=REPO_DIR, capture_output=True, text=True, timeout=180,
        )
        out = (result.stdout or "")[-4000:]
        err = (result.stderr or "")[-2000:]
        return f"[exit={result.returncode}]\nSTDOUT:\n{out}\nSTDERR:\n{err}"
    except subprocess.TimeoutExpired:
        return "실행 시간 초과(180초) -- 명령을 더 작게 나눠서 재시도하라."


@tool
def search_memory(query: str) -> str:
    """저장된 장기 기억에서 query와 관련된 내용을 찾는다.

    사용자가 이전에 알려준 사실, 정정한 내용, 배경 정보를 확인해야 할 때 먼저 이걸 호출하라.
    """
    return agent_memory.search_memory(query)


@tool
def save_memory(topic: str, content: str) -> str:
    """새로 알게 된 사실을 장기 기억에 저장한다 (git에 커밋되어 다음 대화에도 남는다).

    사용자가 새로운 사실을 알려주거나 내 답을 정정했을 때, 나중에 다시 알아야 할 내용이면
    호출하라. topic은 짧은 제목, content는 기억할 내용이다. 잡담이나 일회성 대화는 저장하지 마라.
    """
    return agent_memory.save_memory(topic, content, author_id=_current_author.get())


@tool
def write_public_answer(filename: str, content: str) -> str:
    """공개 채널 에이전트의 답변/결과물을 파일로 남긴다. Public_agent/ 폴더 아래에만
    저장되고 git에 커밋된다(push는 하지 않음, 관리자가 검토 후 push). filename은
    디렉터리 없이 파일명만 지정한다 (예: answer.py, result.md)."""
    return public_agent_files.write_output(filename, content, author_id=_current_author.get())


def extract_text(content) -> str:
    """최신 Gemini 응답은 content가 평문 문자열이 아니라 파트 리스트로 올 수 있다
    (예: [{"type": "text", "text": "...", "extras": {...}}], extras에 thinking
    signature 등이 딸려온다) -- text 파트만 이어붙인다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return str(content)


def is_quota_error(e: Exception) -> bool:
    text = str(e)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


# ListModels가 돌려주는 이름 중 이런 키워드가 들어간 건 텍스트 채팅용이 아니다(TTS/이미지
# 생성/로보틱스/deep-research/computer-use/음악 등) -- ChatGoogleGenerativeAI에 그대로
# 물리면 응답 형식이 안 맞아 429가 아닌 다른 에러가 나고, run_with_fallback_pool은 쿼터
# 에러만 다음 후보로 넘기므로 이런 모델에 걸리면 남은 후보를 더 시도해보지도 못하고 그
# 자리에서 죽는다(실측 확인됨, 2026-08-28 -- 이 키로 실제 조회했더니 39개 모델 중 다수가
# 이런 비-채팅 모델이었다).
_NON_CHAT_MODEL_MARKERS = (
    "tts", "audio", "image", "transcribe", "robotics", "computer-use",
    "deep-research", "lyria", "antigravity", "embedding", "aqa", "banana",
)


def list_available_models(api_key: str, timeout: int = 15) -> "list[str]":
    """이 키로 실제 쓸 수 있는 '텍스트 채팅용' Gemini 모델 이름 목록을 API에서 직접
    조회한다(v1beta ListModels -- 이 호출 자체는 generateContent 쿼터를 소모하지 않는
    메타데이터 조회다). supportedGenerationMethods에 "generateContent"가 없는 모델과,
    이름에 _NON_CHAT_MODEL_MARKERS가 들어간 비-채팅 모델은 걸러낸다. 조회 자체가
    실패하면(네트워크 오류 등) 빈 리스트를 반환한다 -- 호출자가 정적 fallback 목록으로
    대체해야 한다."""
    try:
        resp = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key, "pageSize": 1000},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[bot_tools] 모델 목록 조회 실패: {e}")
        return []
    names = []
    for m in data.get("models", []):
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        name = m.get("name", "")
        name = name[len("models/"):] if name.startswith("models/") else name
        if any(marker in name.lower() for marker in _NON_CHAT_MODEL_MARKERS):
            continue
        names.append(name)
    return names


def build_agent_pool(keys: "list[str | None]", models: "list[str] | None", tools: list, prompt: str,
                      checkpointer, fallback_models: "list[str] | None" = None) -> "list[tuple[str, object]]":
    """(키, 모델) 조합마다 ChatGoogleGenerativeAI + create_react_agent를 하나씩 만들어
    [(label, agent), ...] 로 돌려준다. 키가 먼저 도는 순서(키1+모델1, 키1+모델2, ...,
    키2+모델1, ...)로 우선순위를 매긴다 -- 원래 기본 키를 최대한 먼저 써보고, 그래도
    안 되면 모델을 바꿔보고, 그것도 안 되면 다음 키로 넘어가는 순서.

    models가 None이면 키마다 list_available_models로 그 키가 실제 쓸 수 있는 모델 전체를
    동적으로 조회해서 쓴다 -- 특정 모델의 일일 쿼터가 소진돼도 같은 키의 다른 모델은 아직
    쿼터가 남아있을 수 있으므로(429의 quotaId가 GenerateRequestsPerDayPerProjectPerModel),
    "쓸 수 있는 모델을 다 시도해본다"가 기본 동작이 된다. 조회가 실패하면 fallback_models
    (없으면 ["gemini-2.5-flash"])로 대체한다.

    ChatGoogleGenerativeAI 생성 자체는 API를 호출하지 않으므로(실제 요청은 invoke 시점에만
    나감) 조합을 몇 개를 만들든 미리 만들어두는 것 자체는 쿼터를 안 쓴다 (과거에 시작할 때마다
    "ping" 테스트 호출로 매 재시작마다 쿼터를 태워버린 적이 있었다 -- 실측 확인됨,
    2026-08-27 -- 그래서 여기서도 절대 테스트 호출을 하지 않는다).
    모든 후보가 같은 checkpointer를 공유해서, 후보 간 전환이 일어나도 같은 thread_id의
    대화 맥락이 끊기지 않는다."""
    pool: list = []
    for key in keys:
        if not key:
            continue
        # 키 앞 8글자로 라벨을 만들면 Gemini 키들이 흔히 공통 접두사(예: "AQ.Ab8RN")를
        # 공유해서 서로 다른 키가 같은 라벨로 뭉개진다(실측 확인됨, 2026-08-28) -- quota
        # 추적/로그가 두 키를 구분 못 해서 잔량 기반 재정렬이 무효화됐었다. 키 전체를
        # 해시해서 절대 충돌 안 나는 라벨을 쓴다.
        key_id = hashlib.sha256(key.encode()).hexdigest()[:8]
        key_models = models
        if key_models is None:
            key_models = list_available_models(key) or fallback_models or ["gemini-2.5-flash"]
        for model in key_models:
            llm = ChatGoogleGenerativeAI(model=model, google_api_key=key)
            agent = create_react_agent(llm, tools=tools, checkpointer=checkpointer, prompt=prompt)
            label = f"key-{key_id}:{model}"
            pool.append((label, agent))
    return pool


def run_with_fallback_pool(candidates: "list[tuple[str, object]]", thread_map: dict, base_thread_id: str,
                            prompt: str, log_prefix: str) -> str:
    """(label, agent) 후보 목록을 순서대로 시도한다 -- 429 쿼터 초과면 다음 후보로 넘어가고,
    그 외 에러는 그대로 올린다(broken-history 복구는 invoke_with_recovery가 각 후보 안에서
    처리함). label은 보통 "키 앞 8자리:모델명" 같은 식으로 어떤 조합인지 알아볼 수 있게 짓는다.

    쿼터는 (프로젝트, 모델) 단위로 걸린다(RetryInfo의 quotaId가
    GenerateRequestsPerDayPerProjectPerModel-FreeTier) -- 즉 같은 키라도 모델을 바꾸면
    별도 쿼터일 수 있다. admin/public 둘 다 [키1+모델A, 키1+모델B, 키2+모델A, ...] 식으로
    후보를 만들어서 넘기면, API 키뿐 아니라 모델도 순환하며 살아있는 조합을 찾는다.

    quota_tracker로 후보별 오늘자 호출 수를 미리 추정해서 잔량 많은 순으로 재정렬한다 --
    실제 429를 맞기 전에(그 자체가 30~50초 걸림, 실측 확인됨) 소진 가능성이 높은 후보를
    뒤로 미뤄서, 다음 호출은 처음부터 살아있을 가능성이 높은 후보로 간다. 성공하면
    카운트를 올리고, 실제 429를 맞으면 그 후보를 오늘자로 확정 소진 처리한다 -- 응답을
    이미 만든 뒤에 하는 기록이라 사용자가 기다리는 시간에는 영향 없다."""
    ranked = quota_tracker.rank_candidates(candidates)
    last_error: Optional[Exception] = None
    for i, (label, agent) in enumerate(ranked):
        try:
            reply = invoke_with_recovery(agent, thread_map, base_thread_id, prompt, f"{log_prefix}[{label}]")
            quota_tracker.record_success(label)
            if i > 0:
                print(f"{log_prefix} Model have changed {label}")
            return reply
        except Exception as e:
            if not is_quota_error(e):
                raise
            quota_tracker.record_exhausted(label)
            print(f"{log_prefix} thread={base_thread_id} candidate={label} quota exhausted, 다음 후보로 전환")
            last_error = e
    raise last_error if last_error else RuntimeError("후보가 비어있음")


def invoke_with_recovery(agent, thread_map: dict, base_thread_id: str, prompt: str, log_prefix: str) -> str:
    """LangGraph 에이전트를 호출하되, 대화 기록이 깨져 있으면(예: run_shell 호출 도중
    프로세스가 중단되어 tool_call에 대응하는 ToolMessage가 안 남은 경우) 새 thread_id로
    한 번 자동 재시도한다.

    MemorySaver는 프로세스가 살아있는 한 상태가 그대로 남아서, 한 번 깨지면 같은
    thread_id로는 재시작 전까지 계속 같은 INVALID_CHAT_HISTORY 에러가 반복된다
    (실측 확인됨). thread_map에 "원래 thread_id -> 현재 쓰는 thread_id" 매핑을 저장해두고,
    복구가 필요하면 매핑을 새 값으로 바꿔서 그 사용자만 대화가 초기화되게 한다.

    쿼터 초과(429)는 새 thread로 재시도해도 똑같은 키/쿼터라 무조건 또 실패한다 -- 그런데도
    재시도하면 API 쪽 자체 backoff(길게는 수십 초)를 두 번 기다리게 돼서 응답만 느려진다
    (실측 확인됨, 2026-08-28). 그래서 쿼터 에러는 재시도 없이 바로 올려서, 호출자가(예:
    다른 API 키로) 곧장 넘어갈 수 있게 한다."""
    thread_id = thread_map.get(base_thread_id, base_thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        return extract_text(result["messages"][-1].content).strip()
    except Exception as e:
        if is_quota_error(e):
            raise
        print(f"{log_prefix} thread={base_thread_id} invoke_error={e!r} -- 새 thread로 재시도")
        new_thread_id = f"{base_thread_id}-{uuid.uuid4().hex[:8]}"
        thread_map[base_thread_id] = new_thread_id
        config = {"configurable": {"thread_id": new_thread_id}}
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        reply = extract_text(result["messages"][-1].content).strip()
        return "(이전 대화 기록이 손상되어 대화를 초기화했다)\n\n" + reply
