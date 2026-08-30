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

import hashlib
import os
import subprocess
import threading
import uuid
from typing import Optional

import requests
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

import agent_context
import agent_memory
import public_agent_files
import quota_tracker

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# 요청 맥락(호출자 ID)과 게스트 차단 목록은 agent_context.py에 있다 -- 여기 두면
# agent_memory/public_agent_files와 순환 임포트가 생겨 봇이 기동 불가가 된다(실측 확인됨,
# 2026-08-28). 예전 이름으로 임포트하던 코드를 위해 그대로 재수출만 한다.
_current_author = agent_context.current_author

# Discord "stop" 명령이 실제로 뭔가를 멈출 수 있게 하는 두 가지 상태.
#
# 1) run_shell이 띄운 서브프로세스: OS 스레드는 강제로 죽일 수 없지만(Python에 안전한
#    thread-kill이 없다) 서브프로세스는 죽일 수 있다. run_admin_agent/run_public_agent가
#    실행되는 executor 스레드의 ident를 discord thread_id에 등록해두고, 그 스레드가
#    run_shell로 띄운 Popen을 ident 기준으로 추적한다.
# 2) run_with_fallback_pool의 후보(API 키/모델) 순회 루프: 이미 나간 HTTP 요청 자체는
#    취소할 수 없지만, 한 후보가 끝나고 다음 후보로 넘어가기 '전에' 취소 플래그를 확인해서
#    quota-exhausted 재시도를 계속 이어가며 API를 더 두드리는 걸 막는다.
_active_procs: dict[int, subprocess.Popen] = {}
_active_procs_lock = threading.Lock()
_thread_registry: dict[str, int] = {}  # discord thread_id -> OS thread ident
_thread_registry_lock = threading.Lock()
_cancel_events: dict[str, threading.Event] = {}
_cancel_events_lock = threading.Lock()


def register_thread(thread_id: str) -> None:
    """run_admin_agent/run_public_agent 시작 시 호출 -- 지금 실행 중인 OS 스레드를
    discord thread_id와 묶고, 이전 취소 플래그를 지운다."""
    with _thread_registry_lock:
        _thread_registry[thread_id] = threading.get_ident()
    with _cancel_events_lock:
        _cancel_events.setdefault(thread_id, threading.Event()).clear()


def unregister_thread(thread_id: str) -> None:
    with _thread_registry_lock:
        _thread_registry.pop(thread_id, None)


def request_cancel(thread_id: str) -> bool:
    """stop 명령에서 호출. 대기 중인 fallback 루프를 다음 후보 전에 멈추게 하고,
    지금 이 스레드가 run_shell로 띄워둔 서브프로세스가 있으면 실제로 죽인다.
    서브프로세스를 실제로 죽였으면 True."""
    with _cancel_events_lock:
        _cancel_events.setdefault(thread_id, threading.Event()).set()
    with _thread_registry_lock:
        ident = _thread_registry.get(thread_id)
    if ident is None:
        return False
    with _active_procs_lock:
        proc = _active_procs.get(ident)
    if proc is None or proc.poll() is not None:
        return False
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        return True
    except ProcessLookupError:
        return False


def _is_cancelled(thread_id: str) -> bool:
    with _cancel_events_lock:
        event = _cancel_events.get(thread_id)
    return event.is_set() if event else False


@tool
def run_shell(command: str) -> str:
    """이 저장소(REPO_DIR)에서 임의의 셸 명령을 실행한다. admin/public 채널 둘 다 쓸 수
    있다 -- public은 화이트리스트가 없어 위험을 사용자가 감수하고 명시적으로 요청한 것이다.
    결과는 stdout/stderr을 그대로 반환한다."""
    # 가드는 반드시 독스트링 '아래'에 둔다 -- 위에 두면 문자열이 독스트링이 아니게 되고,
    # @tool은 설명이 없는 함수를 ValueError로 거부해서 임포트 자체가 실패한다(실측 확인됨,
    # 2026-08-28). integrity.check_tool_docstrings가 이 규칙을 강제한다.
    if agent_context.is_blocked():
        return "실패: 게스트는 run_shell을 사용할 수 없습니다."
    ident = threading.get_ident()
    proc = subprocess.Popen(
        ["bash", "-lc", command], cwd=REPO_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    with _active_procs_lock:
        _active_procs[ident] = proc
    try:
        try:
            stdout, stderr = proc.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return "실행 시간 초과(180초) -- 명령을 더 작게 나눠서 재시도하라."
        out = (stdout or "")[-4000:]
        err = (stderr or "")[-2000:]
        if proc.returncode is not None and proc.returncode < 0:
            return f"[중단됨] stop 명령으로 강제 종료됨(signal={-proc.returncode}).\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        return f"[exit={proc.returncode}]\nSTDOUT:\n{out}\nSTDERR:\n{err}"
    finally:
        with _active_procs_lock:
            _active_procs.pop(ident, None)


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


def is_rpm_quota_error(e: Exception) -> bool:
    """429 중에서도 '분당 한도(RPM)'라 1분이면 풀리는 것인지 판별한다. Gemini는 429
    본문에 quotaId를 실어주는데, 일일 한도는 GenerateRequestsPerDayPerProjectPerModel,
    분당 한도는 GenerateRequestsPerMinutePerProjectPerModel이다.

    둘을 구분 못 하던 시절엔 RPM까지 전부 '오늘 소진'으로 확정 처리해서, ReAct 루프로 몇
    초 안에 여러 번 호출하다 RPM에 걸리면 멀쩡한 최상위 조합이 자정까지 봉인됐다.

    판별 실패(quotaId가 없거나 형식이 바뀐 경우)에는 일부러 False를 돌려준다 -- 일일
    소진을 분당으로 잘못 보면 1분마다 죽은 조합을 다시 두드리며 매번 수십 초 backoff를
    기다리게 되므로, 모르는 건 기존처럼 보수적으로 일일 소진 취급하는 쪽이 안전하다."""
    text = str(e)
    return is_quota_error(e) and ("PerMinute" in text or "per minute" in text.lower())


def is_permanent_error(e: Exception) -> bool:
    """이 (키, 모델) 조합이 앞으로도 절대 안 될 거라는 뜻의 에러 -- 단종된 모델(404
    NOT_FOUND), 무료 티어에서 막힌 유료 전용 모델(403 PERMISSION_DENIED, billing 관련
    FAILED_PRECONDITION). 429 쿼터 소진과 달리 자정에 리셋되지 않으므로 quota_tracker의
    영구 dead 목록에 올려서 다시는 시도하지 않는다."""
    text = str(e)
    return any(marker in text for marker in (
        "PERMISSION_DENIED", "403", "FAILED_PRECONDITION", "NOT_FOUND", "404",
        "billing", "not supported", "not found",
    ))


def is_transient_error(e: Exception) -> bool:
    """구글 쪽 일시적 문제(과부하 등)라 이 후보 자체는 멀쩡하지만 지금 이 순간만 안 되는
    에러. 영구 dead 처리하면 안 된다 -- 다음 요청엔 멀쩡할 수 있다."""
    text = str(e)
    return any(marker in text for marker in ("UNAVAILABLE", "503", "high demand", "INTERNAL", "500", "DEADLINE_EXCEEDED"))


def is_unavailable_error(e: Exception) -> bool:
    """이 (키, 모델) 조합을 "지금 못 쓴다"는 뜻의 에러 전반(쿼터 소진 + 영구 불가 + 일시
    장애) -- 다음 후보로 넘어가야 한다는 신호로 쓴다. 어떤 모델이 유료 전용인지, 언제
    과부하가 걸릴지 미리 다 알 방법이 없으므로(모델 목록도 자주 바뀜, 실측 확인됨
    2026-08-28) 정적으로 걸러내는 대신, 실제 호출에서 이런 에러가 나면 다음 후보로
    넘어가는 쪽으로 처리한다."""
    return is_quota_error(e) or is_permanent_error(e) or is_transient_error(e)


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


# 모델 패밀리별 대략적인 성능 우선순위(낮을수록 먼저 시도) -- pro > flash > flash-lite >
# gemma(오픈 웨이트, 상대적으로 약함) > 그 외 이름 모를 모델. preview 꼬리표가 붙은 건 같은
# 패밀리 안에서 정식 버전보다 살짝 뒤로 민다(불안정할 수 있으므로). 어디까지나 이름 기반
# 휴리스틱이고 Google이 모델을 계속 새로 내놓으므로 완벽할 수 없다 -- 그래도 "쓸 수만 있으면
# 아무 모델이나"보다는 훨씬 낫다.
def _model_quality_rank(model: str) -> "tuple[int, int]":
    name = model.lower()
    if "gemma" in name:
        family = 3
    elif "flash-lite" in name or "flash_lite" in name:
        family = 2
    elif "flash" in name:
        family = 1
    elif "pro" in name:
        family = 0
    else:
        family = 4
    is_preview = 1 if "preview" in name else 0
    return (family, is_preview)


def run_with_fallback_pool(candidates: "list[tuple[str, object]]", thread_map: dict, base_thread_id: str,
                            prompt: str, log_prefix: str) -> str:
    """(label, agent) 후보 목록을 순서대로 시도한다 -- 이 후보를 "지금 못 쓴다"는 뜻의
    에러(쿼터 초과, 무료 티어에서 막힌 유료 전용 모델, 존재하지 않는 모델 등 -- is_unavailable_
    error 참고)면 다음 후보로 넘어가고, 그 외 진짜 버그성 에러는 그대로 올린다(broken-history
    복구는 invoke_with_recovery가 각 후보 안에서 처리함). label은 "key-<해시8자리>:모델명"
    형태로 어떤 조합인지 알아볼 수 있게 짓는다.

    쿼터는 (프로젝트, 모델) 단위로 걸린다(RetryInfo의 quotaId가
    GenerateRequestsPerDayPerProjectPerModel-FreeTier) -- 즉 같은 키라도 모델을 바꾸면
    별도 쿼터일 수 있다. admin/public 둘 다 [키1+모델A, 키1+모델B, 키2+모델A, ...] 식으로
    후보를 만들어서 넘기면, API 키뿐 아니라 모델도 순환하며 살아있는 조합을 찾는다.

    정렬 우선순위는 (1) 오늘 소진 확정 여부 -- 살아있을 가능성이 있는 후보를 먼저,
    (2) 모델 성능 등급(_model_quality_rank) -- 같은 조건이면 더 좋은 모델을 먼저,
    (3) quota_tracker 잔량 추정치 순서다. (1)이 없으면 "잔량만 많으면 1순위"가 돼서,
    한 번도 안 써서 잔량이 가득 찬 약한 모델(gemma 등)이 정작 쓸 만한 pro/flash보다
    먼저 뽑히는 문제가 있었다(실측 확인됨, 2026-08-28). 성공하면 카운트를 올리고, 실제
    429를 맞으면 그 후보를 오늘자로 확정 소진 처리한다 -- 응답을 이미 만든 뒤에 하는
    기록이라 사용자가 기다리는 시간에는 영향 없다.

    단, 429가 '분당 한도(RPM)'면 1분이면 풀리므로 자정까지 소진 처리하지 않고
    quota_tracker의 짧은 쿨다운에만 올린다(is_rpm_quota_error 참고). 쿨다운 중인 후보는
    remaining()이 0이라 자연히 뒤로 밀리고, 60초가 지나면 별도 해제 없이 원래 순위로
    돌아온다 -- ReAct 루프처럼 짧은 시간에 여러 번 호출하다 RPM에 걸렸다는 이유로 가장
    좋은 조합이 하루 종일 봉인되던 문제를 막는다.

    404/403처럼 하루가 지나도 안 풀리는 에러는 quota_tracker의 영구 dead 목록에 올리고,
    다음 호출부터는 이 함수 맨 앞에서 API를 부르지도 않고 걸러낸다 -- "다음 질문이
    들어오기 전에 이미 살아있는 후보만 남겨서 준비해두는" 것이 핵심이다. 이걸 안 하면
    단종된 모델을 매 요청마다 처음부터 다시 두드려보며 시간을 버리게 된다(실측 확인됨,
    2026-08-28).

    거기에 더해 "이번에 성공한 후보를 다음 질문에도 그대로 먼저 쓴다"는 pin을 건다
    (quota_tracker.set_pinned/get_pinned, pool_id=log_prefix에서 뽑음) -- 매번 순위
    계산으로 1등을 고르는 것과 결과가 비슷할 때가 많지만, 같은 등급 안에서 잔량 차이로
    이리저리 흔들리는 것 없이 "직전에 확인된 살아있는 조합"을 확정적으로 우선한다. pin된
    후보가 이번에도 실패하면 정상적으로 다음 후보로 넘어가고, 그때 새로 성공한 쪽으로
    pin이 갱신된다."""
    pool_id = log_prefix.strip("[]")
    live = [c for c in candidates if not quota_tracker.is_dead(c[0])]
    if not live:
        live = candidates  # 다 죽었다고 기록된 상태라도 최후의 수단으로는 시도해본다 (기록이 틀렸을 수 있으니).

    def _sort_key(candidate):
        label, _ = candidate
        model = label.split(":", 1)[1] if ":" in label else label
        remaining = quota_tracker.remaining(label)
        return (remaining <= 0, _model_quality_rank(model), -remaining)

    ranked = sorted(live, key=_sort_key)
    pinned_label = quota_tracker.get_pinned(pool_id)
    # pin은 정렬을 통째로 건너뛰고 맨 앞에 꽂는 장치라, 쿨다운 중인 조합이 pin돼 있으면
    # remaining()이 0을 돌려줘도 소용없이 매번 먼저 시도돼서 RPM 쿨다운이 무력화된다.
    if pinned_label and quota_tracker.is_rpm_cooling(pinned_label):
        pinned_label = None
    if pinned_label:
        pinned = [c for c in ranked if c[0] == pinned_label]
        if pinned:
            ranked = pinned + [c for c in ranked if c[0] != pinned_label]

    last_error: Optional[Exception] = None
    for i, (label, agent) in enumerate(ranked):
        if _is_cancelled(base_thread_id):
            print(f"{log_prefix} thread={base_thread_id} stop 명령으로 후보 순회 중단 "
                  f"({i}/{len(ranked)}까지 시도함)")
            return f"[중단됨] stop 명령으로 응답 생성을 멈췄습니다. ({i}개 후보 시도 후 중단)"
        try:
            reply = invoke_with_recovery(agent, thread_map, base_thread_id, prompt, f"{log_prefix}[{label}]")
            quota_tracker.record_success(label)
            quota_tracker.set_pinned(pool_id, label)
            if i > 0:
                print(f"{log_prefix} Model have changed {label}")
            return reply
        except Exception as e:
            if not is_unavailable_error(e):
                raise
            if is_rpm_quota_error(e):
                # 분당 한도는 1분이면 풀린다 -- 자정까지 봉인하지 말고 잠깐만 쉬게 한다.
                quota_tracker.record_rpm_cooldown(label)
                print(f"{log_prefix} thread={base_thread_id} candidate={label} 분당 한도(RPM) 초과, "
                      f"{quota_tracker.RPM_COOLDOWN_SECONDS}초 쿨다운 후 복귀 예정 -- 다음 후보로 전환")
            elif is_quota_error(e):
                quota_tracker.record_exhausted(label)
                print(f"{log_prefix} thread={base_thread_id} candidate={label} quota exhausted, 다음 후보로 전환")
            elif is_permanent_error(e):
                quota_tracker.mark_dead(label, str(e)[:200])
                print(f"{log_prefix} thread={base_thread_id} candidate={label} 영구 사용불가로 확정({e}), "
                      f"앞으로 건너뜀")
            else:
                print(f"{log_prefix} thread={base_thread_id} candidate={label} 일시 장애({e}), 다음 후보로 전환")
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
        if is_unavailable_error(e):
            raise
        print(f"{log_prefix} thread={base_thread_id} invoke_error={e!r} -- 새 thread로 재시도")
        new_thread_id = f"{base_thread_id}-{uuid.uuid4().hex[:8]}"
        thread_map[base_thread_id] = new_thread_id
        config = {"configurable": {"thread_id": new_thread_id}}
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        reply = extract_text(result["messages"][-1].content).strip()
        return "(이전 대화 기록이 손상되어 대화를 초기화했다)\n\n" + reply

def tune_search_parameters(iters: int, noise_scale: float, use_perturbation: bool) -> str:
    """행렬곱 탐색 알고리즘의 최적화 파라미터를 동적으로 변경한다.
    
    Args:
        iters: 반복 횟수 (최대 5000)
        noise_scale: 탐색 섭동 노이즈 크기
        use_perturbation: 섭동 전략 사용 여부
    """
    import json
    from pathlib import Path
    
    path = Path("/home/ubuntu/SE/mathmetics/matrix_exponent/params.json")
    params = {"iters": 2000, "noise_scale": 0.1, "use_perturbation": False}
    
    if path.exists():
        try:
            with open(path, 'r') as f:
                params = json.load(f)
        except Exception:
            pass
            
    params["iters"] = min(int(iters), 5000)
    params["noise_scale"] = float(noise_scale)
    params["use_perturbation"] = bool(use_perturbation)
    
    with open(path, 'w') as f:
        json.dump(params, f, indent=4)
        
    return f"Successfully tuned params: {params}"
