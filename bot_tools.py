"""
Discord 관리 채널(admin)과 공개 채널(public) 에이전트가 공유하는 도구/유틸리티.

REPO_DIR, run_shell(임의 셸 실행, admin 전용) 도구, 기억 검색/저장 도구, 공개 채널 결과물
저장 도구(write_public_answer), Gemini 응답 파싱, 그리고 LangGraph MemorySaver가 깨졌을 때
(도구 호출 도중 중단되어 ToolMessage가 누락된 경우 등) 자동으로 새 thread로 재시도하는 복구
헬퍼를 모아둔다. admin/public 양쪽 모듈이 이 파일의 도구를 그대로 가져다 쓴다 -- 중복 정의를
피하고, 한쪽에서 도구 동작을 고치면 양쪽에 반영되게.

run_shell은 admin 채널만 쓴다. public 채널은 화이트리스트가 없어 임의 셸 실행을 주면
위험하므로 write_public_answer로 Public_agent/ 폴더 안에만 결과 파일을 남기게 한다
(public_agent_files.py가 경로를 코드로 강제한다).
"""

from __future__ import annotations

import contextvars
import os
import subprocess
import uuid

from langchain_core.tools import tool

import agent_memory
import public_agent_files

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# 도구 함수는 모델이 부르므로 인자에 작성자 ID를 실어보낼 수 없다 -- 요청 단위로 여기에 담아둔다.
_current_author: contextvars.ContextVar[str] = contextvars.ContextVar("current_author", default="unknown")


@tool
def run_shell(command: str) -> str:
    """이 저장소(REPO_DIR)에서 임의의 셸 명령을 실행한다 -- admin 채널 전용 전권 도구다.
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


def invoke_with_recovery(agent, thread_map: dict, base_thread_id: str, prompt: str, log_prefix: str) -> str:
    """LangGraph 에이전트를 호출하되, 대화 기록이 깨져 있으면(예: run_shell 호출 도중
    프로세스가 중단되어 tool_call에 대응하는 ToolMessage가 안 남은 경우) 새 thread_id로
    한 번 자동 재시도한다.

    MemorySaver는 프로세스가 살아있는 한 상태가 그대로 남아서, 한 번 깨지면 같은
    thread_id로는 재시작 전까지 계속 같은 INVALID_CHAT_HISTORY 에러가 반복된다
    (실측 확인됨). thread_map에 "원래 thread_id -> 현재 쓰는 thread_id" 매핑을 저장해두고,
    복구가 필요하면 매핑을 새 값으로 바꿔서 그 사용자만 대화가 초기화되게 한다."""
    thread_id = thread_map.get(base_thread_id, base_thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        return extract_text(result["messages"][-1].content).strip()
    except Exception as e:
        print(f"{log_prefix} thread={base_thread_id} invoke_error={e!r} -- 새 thread로 재시도")
        new_thread_id = f"{base_thread_id}-{uuid.uuid4().hex[:8]}"
        thread_map[base_thread_id] = new_thread_id
        config = {"configurable": {"thread_id": new_thread_id}}
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        reply = extract_text(result["messages"][-1].content).strip()
        return "(이전 대화 기록이 손상되어 대화를 초기화했다)\n\n" + reply
