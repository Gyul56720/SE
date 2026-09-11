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
import re
import subprocess
import threading
import time
import uuid
from typing import Optional

import channels

import requests
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

import agent_context
import agent_memory
import filetools
import orchestrator_tool
import public_agent_files
import quota_tracker
import relay
import toolgate
import compact
from sandbox import run as sandbox_run
from secret_filter import child_env, redact_secrets

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


# **부른 셸을 그 실행 단위로 센다.** 이유: 모델이 "차단돼서 못 받았다" 고 답했는데
# 실제로는 **셸을 한 번도 안 불렀던** 일이 있었다(실측 2026-09-09, 사용자 확인:
# "안막혔어"). 규칙에는 '해 보기 전에 수단이 없다고 하지 마라' 가 이미 적혀 있었고
# 그래도 어겼다 -- 그러면 규칙을 더 적을 것이 아니라 **말이 사실인지 코드가 재야 한다.**
# OS 스레드로 센다: run_public_agent 와 run_shell 이 같은 실행기 스레드에서 돈다.
_셸기록: dict[int, list] = {}
_셸기록_lock = threading.Lock()
# thread_id -> 그 실행에서 부른 것. 부르는 쪽(discord_bot_server)이 답과 견준다.
마지막셸: dict[str, list] = {}


# **앞과 뒤를 둘 다 남긴다.** 예전엔 뒤 4000 자만 남겼고(`stdout[-4000:]`), 그것이
# `dig/` 를 통째로 헛되게 하고 있었다(실측 2026-09-09).
#
#   dig/run.py 문서: "**줄이지 않는다.** 길면 긴 대로 낸다 -- 줄이는 것은 부르는
#   쪽 일이고, 여기서 줄이면 줄인 것을 아무도 못 되찾는다."
#
# 그 '부르는 쪽' 이 여기인데 여기서 말없이 줄이고 있었다. 게다가 하필 **제일 나쁜
# 쪽**으로 줄였다 -- dig 는 캔 값· 묻힌표(메뉴· 값· 평점· 영업시간)를 **맨 앞에**
# 찍고 본문 글을 맨 뒤에 찍는다. 중요한 것을 앞에 놓는 그 규칙이, 꼬리만 남기는
# 이 자름과 만나 **중요한 것부터 버리는 규칙**이 됐다. 남는 4000 자는 대개 본문
# 부스러기였고, 그것이 사용자가 "정보가 없다" 고 하는 그 답이다.
#
# 로그는 반대다 -- 까닭은 꼬리(마지막 예외· 마지막 줄)에 있다. 한쪽만 고를 수
# 없으니 둘 다 남기고 가운데를 버린다. 얼마나 버렸는지도 적는다: 말없이 사라지면
# 모델이 그것을 '없는 것' 으로 읽는다.
# `channels.수` 로 읽는다 -- `int(os.getenv(...))` 는 값이 빈 칸일 때 터진다(그것으로
# 봇이 한 번 죽었다). 여기서 터지면 임포트가 통째로 실패해 봇이 아예 안 뜬다.
셸출력_앞 = channels.수("SHELL_OUT_HEAD", 24000)
셸출력_뒤 = channels.수("SHELL_OUT_TAIL", 6000)


def 자르기(s: str, 앞: int, 뒤: int) -> str:
    s = s or ""
    if len(s) <= 앞 + 뒤:
        return s
    버린 = len(s) - 앞 - 뒤
    return (s[:앞]
            + f"\n\n… [가운데 {버린:,}자 잘림 -- **없는 것이 아니라 안 보여 준 것**이다. "
              f"좁혀서 다시 불러라: `--찾 <말>` · `--json | python3 -c '...'` · "
              f"`grep -n <말>` · `head`/`tail`] …\n\n"
            + s[-뒤:])


def _계획판():
    """계획판(!계획 켜기)이 켜져 있으면 그림자 워크트리 -- edit_file · run_shell 이 거기서 돈다."""
    try:
        from plan import store as _plan
        return _plan.현재판()
    except Exception:                                  # noqa: BLE001
        return None


def _간추림(base_thread_id: str, thread_map: dict, messages) -> None:
    """대화가 상한을 넘으면 코드가 간추려 메모로 남기고 실을 새로 잇는다(격차표 '맥락 관리')."""
    if not compact.간추릴때(messages):
        return
    try:
        메모, _ = compact.간추리기(base_thread_id, messages)
    except Exception as e:                             # noqa: BLE001
        print(f"[compact] thread={base_thread_id} 간추리기 실패: {e!r}")
        return
    thread_map[base_thread_id] = f"{base_thread_id}-{uuid.uuid4().hex[:8]}"
    relay.적기(f"🗜 대화 {len(messages)}줄 간추려 {메모} -- 새 실로 잇는다")


def 이번셸() -> list:
    """지금 OS 스레드가 **이번 턴에** 돌린 셸·실험·편집·위임 줄 -- (명령, 성공) 튜플.
    unregister_thread 로 마지막셸에 옮겨지기 전, 되묻기 판정 때 살아 있어야 한다."""
    with _셸기록_lock:
        return list(_셸기록.get(threading.get_ident(), []))


def register_thread(thread_id: str) -> None:
    """run_admin_agent/run_public_agent 시작 시 호출 -- 지금 실행 중인 OS 스레드를
    discord thread_id와 묶고, 이전 취소 플래그를 지운다."""
    with _thread_registry_lock:
        _thread_registry[thread_id] = threading.get_ident()
    with _cancel_events_lock:
        _cancel_events.setdefault(thread_id, threading.Event()).clear()
    with _셸기록_lock:
        _셸기록[threading.get_ident()] = []


def unregister_thread(thread_id: str) -> None:
    # **이 실행에서 부른 것을 thread_id 쪽으로 옮긴다.** 부르는 쪽이 답과 견준다.
    with _셸기록_lock:
        마지막셸[thread_id] = _셸기록.pop(threading.get_ident(), [])
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
    # **돌기 전에** 본다. 커밋 게이트(G020)는 이미 지운 뒤에 잡는다 -- 그 사이 봇은 지워진
    # 게이트 없이 돌고 사용자는 "지웠다" 는 답을 먼저 본다. 여기서 거절하면 그 창이 없다.
    # 규칙은 닫힌 목록이고 각각 사고·CLAUDE.md 금지에 묶여 있다(toolgate.규칙들).
    막힘 = toolgate.검사(command)
    if 막힘:
        print(f"[run_shell] {_current_author.get()} :: 차단 {redact_secrets(command)[:120]!r} {막힘}")
        with _셸기록_lock:
            _셸기록.setdefault(ident, []).append((redact_secrets(command)[:160], False))
        relay.적기(f"⛔ 차단 {redact_secrets(command)[:90]}  -- {막힘[:60]}")
        return (f"[도구 게이트 차단 -- 돌리지 않았다] {막힘}\n"
                f"이 규칙은 이 저장소의 사고에서 왔다. 우회하지 말고 다른 길을 써라: "
                f"게이트는 self_challenge prove, 원장은 >> 덧쓰기, 밀기는 merge 뒤 push.")
    # errors="replace" 가 없으면 명령 출력에 UTF-8 로 디코딩되지 않는 바이트가 하나만
    # 섞여도 communicate() 가 UnicodeDecodeError 로 터진다(실측: "'utf-8' codec can't
    # decode bytes in position 147-148: invalid continuation byte"). 도구가 예외로 죽으면
    # 그 턴 전체가 실패하므로, 깨진 바이트는 대체문자로 바꿔 넣고 계속 진행한다 -- 셸
    # 출력에는 로그·바이너리 조각·다른 인코딩 텍스트가 얼마든지 섞일 수 있다.
    # **꾸러미 진입점은 `-m` 으로 돌린다.** `python3 dig/run.py` 는 sys.path[0] 이 dig/ 라서,
    # 그 파일이 함수 안에서 남의 꾸러미를 임포트하는 갈래를 밟는 순간 ModuleNotFoundError 다.
    # 봇 프롬프트가 이름을 대고 시키는 명령만 열넷이 그 꼴이었다. 파일 안에 뿌리를 넣는 줄을
    # 적는 것으로는 **낡은 판이 배포돼 있으면** 안 듣는다(실측 2026-09-11: 고쳐 배포했는데
    # VM 이 같은 줄에서 또 죽었다). 부르는 쪽인 여기서 바꾸면 어떤 판이든 산다.
    # 게이트(toolgate)는 **사람이 친 원문**으로 이미 봤다 -- 바꾼 것이 규칙을 비켜 가지 않는다.
    _판 = _계획판() or REPO_DIR
    import entrypoints
    command, _바뀜 = entrypoints.셸명령_모듈꼴(command, _판)
    if _바뀜:
        print(f"[run_shell] 모듈 꼴로: {'; '.join(_바뀜[:3])}")
    시작 = time.monotonic()
    proc = subprocess.Popen(
        ["bash", "-lc", command], cwd=str(_판),                        # 계획판이면 그림자
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, errors="replace", env=child_env(),
    )
    with _active_procs_lock:
        _active_procs[ident] = proc
    try:
        try:
            stdout, stderr = proc.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            relay.적기(relay.줄(redact_secrets(command), "시간초과", time.monotonic() - 시작))
            return "실행 시간 초과(180초) -- 명령을 더 작게 나눠서 재시도하라."
        # 중계: 검사 가능한 것만 -- 무엇을 돌렸고 끝값이 얼마고 몇 초 걸렸나.
        relay.적기(relay.줄(redact_secrets(command), proc.returncode, time.monotonic() - 시작))
        # 자르고 나서 마스킹한다 -- 자르기 전에 하면 긴 출력 전체를 훑느라 느려진다.
        # **부른 것을 남긴다.** 남기지 않으면 "탐색했는데 못 찾았다" 와 "아예 안
        # 했다" 가 로그에서 구별되지 않는다(실측 2026-09-09: 공개 채널 둘의 성능이
        # 다른데 어느 쪽이 도구를 썼는지 알 길이 없었다). 값은 redact_secrets 로 가린다.
        print(f"[run_shell] {_current_author.get()} :: "
              f"{redact_secrets(command)[:160]!r}")
        with _셸기록_lock:
            _셸기록.setdefault(threading.get_ident(), []).append(
                (redact_secrets(command)[:160], proc.returncode == 0))
        out = redact_secrets(자르기(stdout, 셸출력_앞, 셸출력_뒤))
        err = redact_secrets(자르기(stderr, 1500, 2500))
        if proc.returncode is not None and proc.returncode < 0:
            return f"[중단됨] stop 명령으로 강제 종료됨(signal={-proc.returncode}).\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        return f"[exit={proc.returncode}]\nSTDOUT:\n{out}\nSTDERR:\n{err}"
    finally:
        with _active_procs_lock:
            _active_procs.pop(ident, None)


@tool
def run_experiment(command: str, minutes: int = 3) -> str:
    """실험·검증용 명령을 깨끗한 격리 판에서 돌린다: HEAD 를 임시 워크트리로 꺼내 그 안에서
    실행하므로 저장소 작업 트리에 아무 흔적이 안 남고, 비밀 환경변수도 지운 채 돈다.
    코드 실험, 테스트 실행, "고치면 어떻게 되나" 확인은 run_shell 이 아니라 이걸 쓰라 --
    run_shell 은 진짜 저장소에서 돌아 실수가 그대로 남는다. command 는 bash -lc 로,
    워크트리 루트에서 실행된다. minutes 는 벽시계 제한(1~10분)."""
    if agent_context.is_blocked():
        return "실패: 게스트는 run_experiment 를 사용할 수 없습니다."
    분 = max(1, min(int(minutes), 10))
    r = sandbox_run.실행(["bash", "-lc", command], 초=분 * 60, 메모리MB=4096)
    print(f"[run_experiment] {_current_author.get()} :: "
          f"{redact_secrets(command)[:160]!r} -> exit={r['끝값']}")
    relay.적기(relay.줄(redact_secrets(command), r["끝값"] if r["돌았나"] else "판못깔음",
                       r.get("걸린초", 0.0), 표지="🧪"))
    with _셸기록_lock:
        _셸기록.setdefault(threading.get_ident(), []).append(
            (redact_secrets(command)[:160], r["돌았나"] and r["끝값"] == 0))
    if not r["돌았나"]:
        return f"[격리 판을 못 깔았다] {r['메모']}\n{redact_secrets(r['stderr'])}"
    out = redact_secrets(자르기(r["stdout"], 셸출력_앞, 셸출력_뒤))
    err = redact_secrets(자르기(r["stderr"], 1500, 2500))
    메모 = f" -- {r['메모']}" if r["메모"] else ""
    return (f"[깨끗한 판 {r['판']} exit={r['끝값']}{메모} -- 작업 트리에는 아무 변화 없음]\n"
            f"STDOUT:\n{out}\nSTDERR:\n{err}")


@tool
def read_file(path: str, start: int = 1, lines: int = 400) -> str:
    """저장소 파일을 줄 번호를 붙여 읽는다. edit_file 의 old 를 정확히 짚으려면 실제 글자
    (들여쓰기·줄바꿈 포함)를 봐야 하므로, 고치기 전에 반드시 이걸로 그 자리를 봐라.
    path 는 저장소 기준 상대경로. start/lines 로 잘라 읽는다(한 번에 최대 400줄).
    .env 는 못 읽는다(비밀값)."""
    if agent_context.is_blocked():
        return "실패: 게스트는 read_file 을 사용할 수 없습니다."
    try:
        out = filetools.읽기(path, start, lines)
    except ValueError as e:
        return f"[읽기 거절] {e}"
    return redact_secrets(자르기(out, 셸출력_앞, 셸출력_뒤))


@tool
def edit_file(path: str, old: str, new: str) -> str:
    """파일의 한 자리를 정확히 고친다: old 가 파일에 **정확히 한 번** 있을 때만 new 로 바꾼다.
    0번이면 거절(read_file 로 실제 글자를 보고 그대로 대라), 2번 이상이면 거절(앞뒤를 더 붙여
    하나로 좁혀라), 빈 old 는 거절(그건 전체 쓰기다).
    **기존 파일을 고칠 때는 run_shell 의 sed/heredoc 대신 이걸 써라** -- 전체 덮어쓰기가
    drift.sh(4cd4473)와 봇 자신(1a82685)을 부순 사고의 형태다. 게이트(gates/)·판정 원장·
    .env·.git 은 이 도구로 못 만진다 -- 게이트는 self_challenge 승격으로만."""
    if agent_context.is_blocked():
        return "실패: 게스트는 edit_file 을 사용할 수 없습니다."
    try:
        말 = filetools.편집(path, old, new, repo=_계획판())      # 계획판이 켜져 있으면 그림자에
    except ValueError as e:
        relay.적기(f"✎ 거절 {path[:60]} -- {str(e)[:60]}")
        return f"[편집 거절] {e}"
    print(f"[edit_file] {_current_author.get()} :: {말}")
    relay.적기(f"✎ {말}")
    with _셸기록_lock:
        _셸기록.setdefault(threading.get_ident(), []).append((f"edit_file {path}"[:160], True))
    return 말


@tool
def set_key(name: str, value: str) -> str:
    """사용자가 **채팅으로** 준 값(비밀번호 · 토큰 · 주소)을 .env 에 적는다 -- 되묻지 말고 바로.
    실측 2026-09-11: 사용자가 값을 줬는데 봇이 재시작(배포)되자 잊고 다시 물었다. 대화 기억은
    재시작하면 사라진다 -- .env 에 적힌 것만 남는다. name 은 대문자·숫자·밑줄(예: SMTP_APP_PASSWORD).
    값은 답에 되비치지 마라. 적고 나면 막혔던 일을 바로 이어서 하라."""
    if agent_context.is_blocked():
        return "실패: 게스트는 set_key 를 사용할 수 없습니다."
    import keys
    try:
        말 = keys.적기(name, value)
    except ValueError as e:
        return f"거절: {e}"
    relay.적기(f"🔑 {name} {말}")
    return f"`{name}` 을 .env 에 {말} (값은 안 보여준다). 재시작해도 남는다. 이제 막혔던 일을 이어서 하라."


@tool
def codify_paper(arxiv_id: str) -> str:
    """논문(arXiv)의 **수식·알고리즘을 실행 가능한 코드로** 바꾼다. dig/paper 로 논문을 읽을 글자로
    내린 뒤 각 수식·알고리즘을 파이썬 함수로 짓고 **sandbox 에서 돌려** 검증한다(판정은 끝값이 한다 --
    네가 '됐다' 고 말하지 마라). 검증 통과한 코드만 codify/out 에 저장되고 graph 에 색인된다.
    수식 하나만 코드화하려면 `python3 codify/run.py --종류 수식 --원문 '<식>' --예시 '[...]'` 를 run_shell 로."""
    if agent_context.is_blocked():
        return "실패: 게스트는 codify_paper 를 사용할 수 없습니다."
    from codify import run as _c
    url = arxiv_id if "arxiv" in arxiv_id else f"https://arxiv.org/abs/{arxiv_id}"
    r = _c.논문코드화(url)
    relay.적기(f"⚙ 코드화 {r['논문']} -- 스펙 {r['스펙수']} · 성공 {r['성공']}")
    return _c.보고(r)


@tool
def research(goal: str) -> str:
    """목표 하나를 **한 호흡에** 연구한다 -- 소개만 하고 떠넘기지 마라. 목표를 그대로 검색하지 않고
    (너무 구체적이면 논문이 0건이다) **일반 방법론 질의 여럿**으로 풀어 제2의 뇌(dig/harvest)로
    arXiv·GitHub·HF 를 넓게 모으고, 막히면 그 막힘을 다시 추상화해 더 넓게 모으기를 되풀이한다
    (3~5 바퀴). 모은 방법론은 codify 로 코드화해 sandbox 에서 검증하고, 과정->결과를 압축해
    public_agent_memory 에 결론으로 남긴다. 판정은 코드가 한다(수집 색인 수·코드화 끝값). 도메인 무관 --
    목표가 구체적 작업이든 학술 질문이든 같다. 몇 분 걸릴 수 있다. 결과(색인·코드 파일·결론·메모)를 답에 붙여라."""
    if agent_context.is_blocked():
        return "실패: 게스트는 research 를 사용할 수 없습니다."
    from research import run as _r
    r = _r.연구(goal)
    relay.적기(f"🔭 연구 {'충분' if r['충분'] else '부분'} {r['바퀴수']}바퀴 -- {goal[:50]}")
    return _r.보고(r)


@tool
def create_pr(title: str, body: str = "") -> str:
    """지금 갈래를 origin 에 밀고 **PR 을 연다. 머지는 하지 않는다 -- 사람이 GitHub 에서 누른다.**
    main 에서는 거절(갈래를 먼저 만들어라). 밀기는 gitsync 규칙(merge 로 따라잡기, --force 없음).
    GITHUB_TOKEN 이 없으면 그렇다고 돌려준다 -- `!열쇠 GITHUB_TOKEN=<값>` 꼴로 딱 그 값만 청하라.
    '커밋했다·PR 열었다' 는 이 도구가 돌려준 URL 로만 말하라 -- 해시나 번호를 지어내지 마라."""
    if agent_context.is_blocked():
        return "실패: 게스트는 create_pr 을 사용할 수 없습니다."
    import github_write as _gw
    r = _gw.pr만들기(title, body)
    relay.적기(f"⇧ PR {'#' + str(r['번호']) + ' ' + r['url'] if r['됐나'] else '못 엶 -- ' + r['왜'][:60]}")
    return _gw.보고(r)


@tool
def dispatch_command(command: str) -> str:
    """사람의 부탁을 **실제 실행으로 옮긴다.** command 에 사람의 말을 그대로 넘겨도 되고(`"RIS 최신 논문 좀 모아줘"`),
    고정 명령(`!연구 …`)을 직접 줘도 된다 -- 어느 명령인지는 저장소의 표(dispatch.고르기)가 고른다. 명령 목록을
    보여 주거나 '무엇을 원하시나요' 로 끝내지 마라. 못 고르면 까닭을 돌려주니 그때 도구를 직접 불러라. 예: 수집·틈 → `!수집 틈으로`, 논문 코드화 →
    `!코드화 논문 <id>`, 연구 → `!연구 <목표>`, 검사 → `!실험 게이트`/`!평가 과제`, 기억 간추리기 → `!기억 밤`,
    변경 검사 → `!감사`, 경로 비용 → `!경로 요약`, 고치기 → `!고치기 <명령> :: <증상>`, 계획 → `!계획 켜기 <요청>`.
    **`!목표 승인`·`!계획 승인`·`!열쇠` 는 사람만 친다** -- 이 도구가 거절한다. 배경으로 도는 명령은 '시작' 만
    돌려주고 끝나면 봇이 채널에 알린다."""
    if agent_context.is_blocked():
        return "실패: 게스트는 dispatch_command 를 사용할 수 없습니다."
    import dispatch as _d
    # **자연어도 받는다.** 사람의 부탁을 그대로 넘겨도 되고(어느 명령인지는 dispatch.고르기 표가
    # 고른다), `!…` 를 직접 줘도 된다. 못 고르면 까닭을 돌려준다 -- 아무 명령이나 치지 않는다.
    골라진, 까닭 = _d.고르기(command)
    if 골라진 is None:
        relay.적기(f"⛔ 명령 못 고름 {command[:40]}")
        return f"[명령 못 고름] {까닭}"
    if 골라진 != (command or "").strip():
        relay.적기(f"⌘ 자연어 -> {골라진[:70]}")
    돼, 왜 = _d.도구로쳐도되나(골라진)
    if not 돼:
        relay.적기(f"⛔ 명령 거절 {골라진[:40]} -- {왜[:40]}")
        return f"[거절] {왜}"
    command = 골라진
    답 = _d.run(command.strip(), allow_write=True)
    if 답 is None:
        return f"[모르는 명령] {command[:60]!r} -- 고정 명령이 아니다. `!` 뒤의 이름을 확인하라"
    relay.적기(f"⌘ {command[:80]}")
    with _셸기록_lock:
        _셸기록.setdefault(threading.get_ident(), []).append((f"dispatch {command}"[:160], True))
    return 답


@tool
def security_audit(deep: bool = False) -> str:
    """**이 호스트 자신**의 보안 상태를 읽기 전용으로 점검한다 -- 열린 포트 · 파일/키 권한 · SUID ·
    세계 쓰기 · 위험 계정 · 방화벽. 판정은 코드가 규칙으로 낸다(네가 '안전해 보인다' 고 말하지 마라).
    deep=True 면 dig 수집 + search_memory 대조까지. **남의 기계를 공격하거나 익스플로잇을 실행하지
    않는다** -- 읽기뿐이다. 사용자 노트북을 점검하려면 그 노트북에서 이 봇을 돌려야 한다."""
    if agent_context.is_blocked():
        return "실패: 게스트는 security_audit 를 사용할 수 없습니다."
    from secaudit import run as sec
    r = sec.점검하기(뇌=bool(deep))
    s = r["셈"]
    relay.적기(f"🔒 점검 높음 {s['높음']} · 중간 {s['중간']} · 못잼 {s['못잼']}")
    return sec.보고(r)


@tool
def repair(command: str, symptom: str) -> str:
    """문제를 **스스로 푸는 루프**. command 는 재현 명령(끝값 0 이면 해결), symptom 은 오류 문구.
    코드가 돈다: sandbox 실측 -> 제2의 뇌(dig/harvest + 색인)에서 원인 -> 수리기 제안(패치/명령)
    -> 격리해서 시도 -> 실측 ... 최대 3바퀴. 해결이면 그렇다고, 아니면 해 본 것과 **사람만 할 수
    있는 한 가지**를 돌려준다. 실패 이유는 public_agent_memory 에 남아 밤에 장기기억이 된다.
    오류를 만나면 네가 손으로 세 번 시도하지 말고 이것을 불러라. 몇 분 걸릴 수 있다."""
    if agent_context.is_blocked():
        return "실패: 게스트는 repair 를 사용할 수 없습니다."
    막힘 = toolgate.검사(command)
    if 막힘:
        return f"[도구 게이트 차단] {막힘}"
    from repair import run as repair_run
    r = repair_run.고치기(command, symptom)
    relay.적기(f"🔧 repair {'해결' if r['해결'] else '못 풂'} (바퀴 {r['바퀴']}) -- {symptom[:50]}")
    return repair_run.보고(r)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """메일을 보낸다 -- SMTP 접속은 여기가 한다. **네가 smtplib 코드를 짜거나 발급 절차를
    설명하지 마라.** 수단(보내는 주소·앱 비밀번호)이 없으면 이 도구가 "무엇이 없고 어떻게
    주는지" 를 돌려준다 -- 그 말을 사용자에게 **그대로** 전하라(선택지를 나열하지 말고).
    사용자가 `!열쇠 이름=값` 으로 줬다고 하면 같은 인자로 다시 불러라 -- 바로 나간다.
    .env 는 이 도구가 별칭·값의 꼴로 알아서 뒤진다 -- 네가 read_file 로 .env 를 읽지 마라.
    to 에 "me" 를 주면 USER_EMAIL 로 간다. 본문에 [교수님 성함] 같은 자리표가 남아 있으면 안 보낸다
    -- 네가 다 채워서 다시 불러라(실존 인물 이름을 지어 서명하지 말고 직함·위원회로)."""
    if agent_context.is_blocked():
        return "실패: 게스트는 send_email 을 사용할 수 없습니다."
    import mailer
    r = mailer.보내기(to, subject, body)
    relay.적기(f"✉ {to[:40]} {'보냄' if r['보냈나'] else '못 보냄'} -- {r['말'].splitlines()[0][:60]}")
    return r["말"]


@tool
def delegate(question: str, scope: str) -> str:
    """파일 여럿을 살펴야 하는 물음을 싼 탐색기에 **동시에** 던지고, 원문에 실재하는 인용만
    받는다. scope 는 글롭(띄어쓰기로 여럿: "graph/*.py router/*.py"). 파일 수십 개를 네가
    cat 으로 다 읽지 마라 -- 이걸로 던져서 파일:줄 인용을 받은 뒤, 필요한 자리만 read_file
    로 봐라. 인용은 코드가 파일과 대조해서 지어낸 것은 버리고 퇴짜로 센다. 결과에 '퇴짜' 가
    많으면 탐색기가 헛것을 봤다는 뜻이니 범위를 좁혀라."""
    if agent_context.is_blocked():
        return "실패: 게스트는 delegate 를 사용할 수 없습니다."
    from delegate import run as delegate_run
    범위들 = [g for g in (scope or "").split() if g and not g.startswith("/") and ".." not in g]
    if not 범위들:
        return "[위임 거절] scope 는 저장소 안 글롭이어야 한다 (예: 'graph/*.py')"
    try:
        r = delegate_run.위임(question, 범위들)
    except Exception as e:                                        # noqa: BLE001
        relay.적기(f"⇉ 위임 실패 -- {type(e).__name__}: {str(e)[:60]}")
        return f"[위임 실패] {type(e).__name__}: {str(e)[:300]}"
    relay.적기(f"⇉ 위임 {r['묶음']}묶음/{r['파일']}파일 동시 → 채택 {len(r['채택'])} · 퇴짜 {len(r['퇴짜'])} ({r['걸린초']}s)")
    with _셸기록_lock:
        _셸기록.setdefault(threading.get_ident(), []).append((f"delegate {scope}"[:160], bool(r["채택"])))
    return redact_secrets(자르기(delegate_run.보고(r, question), 셸출력_앞, 셸출력_뒤))


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
    return agent_memory.save_memory(topic, redact_secrets(content), author_id=_current_author.get())


@tool
def write_public_answer(filename: str, content: str) -> str:
    """공개 채널 에이전트의 답변/결과물을 파일로 남긴다. Public_agent/ 폴더 아래에만
    저장되고 git에 커밋된다(push는 하지 않음, 관리자가 검토 후 push). filename은
    디렉터리 없이 파일명만 지정한다 (예: answer.py, result.md)."""
    return public_agent_files.write_output(filename, redact_secrets(content), author_id=_current_author.get())


@tool
def orchestrator_solve(problem: str) -> str:
    """문제 하나를 orchestrator 파이프라인(계획->실행->검증->수리 루프)으로 푼다.

    여러 단계로 쪼개야 풀리는 문제, 코드를 짜서 계산해야 답이 나오는 문제에 쓴다. 플래너가
    문제를 하위 노드 DAG 로 쪼개고 노드마다 solve/verify 코드를 만들며, verifier 를 통과한
    결과만 채택한다. 실패하면 실패 사유를 되먹여 노드를 수리하거나 계획을 다시 세운다.

    수 분 걸리므로 **백그라운드로 띄우고 즉시 반환한다**. 반환된 런 이름을 가지고
    orchestrator_status 로 나중에 진행 상황을 확인하라 -- 여기서 기다리지 마라."""
    return orchestrator_tool.start_run(problem, env=child_env())


@tool
def orchestrator_status(run: str = "") -> str:
    """orchestrator 런의 진행 상황을 본다: 프로세스 생사, 노드별 검증 상태, 마지막 실패
    사유, 최종 결과, 로그 끝부분. run 이 비면 가장 최근 런을 본다."""
    return orchestrator_tool.run_status(run)


@tool
def orchestrator_resume(run: str) -> str:
    """죽었거나 미완으로 끝난 orchestrator 런을 이어서 돌린다. 검증된 노드는 건너뛰고
    실패한 노드부터 다시 시도한다. 봇이 재배포로 재시작되면 돌던 런도 같이 죽으므로,
    orchestrator_status 가 '미완이고 프로세스도 없다'고 하면 이걸 쓴다."""
    return orchestrator_tool.resume_run(run, env=child_env())


@tool
def orchestrator_stop(run: str = "") -> str:
    """돌고 있는 orchestrator 런을 멈춘다(프로세스 그룹째). 산출물은 파일로 남으므로
    orchestrator_resume 으로 이어서 돌릴 수 있다. run 이 비면 가장 최근 런을 멈춘다."""
    return orchestrator_tool.stop_run(run)


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


# [2026-08-30] 에러 분류를 구조적으로 바꾼 이유 -- 실측된 오분류
#
# 예전 판은 에러 문자열 '전체'에서 3자리 숫자를 substring 으로 찾았다("429" in text 등).
# 그런데 API 에러 본문에는 3자리 숫자가 도처에 있다. 실측 결과:
#
#   input_token_count: 42904          -> "429" 가 걸려 quota 소진으로 오판
#   request_id: 7b3f404a1c29e5        -> "404" 가 걸려 '영구 dead' 로 오판 (자정에도 안 풀림)
#   probability_score: 0.4290         -> "429" 가 걸려 quota + transient 동시 오판
#
# 그래서 실제로는 한 번도 쿼터에 걸린 적이 없는데도 "quota exhausted" 로 기록되고, 멀쩡한
# 최상위 조합이 후보 뒤로 밀리거나 영구 목록에 올라갔다. 그 결과 매 요청마다 살아있는 조합을
# 찾아 후보를 계속 순회하게 되고, 후보 하나당 langchain 내부 재시도/backoff 가 붙어 응답이
# 수 분씩 걸렸다.
#
# 고친 방식: (1) 예외 타입 이름과 code 속성에서 상태코드를 구조적으로 읽고,
#            (2) 문자열로 떨어질 때만, Google 이 "<코드> <메시지>" 로 직렬화한다는 점을 이용해
#                '맨 앞'의 3자리만 상태코드로 인정한다. 본문 속 숫자는 더 이상 걸리지 않는다.
_LEADING_STATUS = re.compile(r"^\s*\(?(\d{3})\b")


def _status_code(e: Exception) -> "int | None":
    """예외에서 HTTP/gRPC 상태코드를 뽑는다. 못 뽑으면 None."""
    for attr in ("code", "status_code"):
        value = getattr(e, attr, None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    response = getattr(e, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    match = _LEADING_STATUS.match(str(e))
    return int(match.group(1)) if match else None


_QUOTA_NAMES = ("ResourceExhausted", "TooManyRequests", "RateLimitError")


def is_quota_error(e: Exception) -> bool:
    if type(e).__name__ in _QUOTA_NAMES:
        return True
    if "RESOURCE_EXHAUSTED" in str(e):
        return True
    return _status_code(e) == 429


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
    if type(e).__name__ in ("PermissionDenied", "NotFound", "FailedPrecondition", "Forbidden"):
        return True
    text = str(e)
    if any(marker in text for marker in (
        "PERMISSION_DENIED", "NOT_FOUND", "FAILED_PRECONDITION",
        "is not found for API version",   # 단종/미지원 모델에 대한 Google 의 실제 문구
        "billing",
        # 모델이 이 요청 형태를 아예 지원하지 않는 경우(도구 호출/시스템 지시 미지원 등).
        # 후보 목록을 API 조회로 자동 구성하므로 이런 모델이 섞이는 건 필연이다(실측: 이
        # 계정 목록에 gemma-4-26b 가 있다). 예전에는 이 에러가 '사용 불가' 어디에도 안 걸려
        # 그대로 raise 됐고, 그러면 다음 후보로 넘어가지 못한 채 요청 전체가 실패했다.
        # 그 모델의 영구적 성질이므로 dead 로 기록해 다음부터 건너뛴다.
        "does not support",
        "not supported",
        "Function calling is not enabled",
    )):
        return True
    # 상태코드만으로는 403/404 까지만 영구로 본다. 400(INVALID_ARGUMENT)은 우리 요청이
    # 잘못됐을 때도 나므로 코드로 판단하지 않는다 -- 그랬다간 우리 버그 하나로 모든 모델을
    # dead 로 만들어버린다. 위의 명시적 문구에 걸릴 때만 영구로 처리한다.
    return _status_code(e) in (403, 404)


def is_transient_error(e: Exception) -> bool:
    """구글 쪽 일시적 문제(과부하 등)라 이 후보 자체는 멀쩡하지만 지금 이 순간만 안 되는
    에러. 영구 dead 처리하면 안 된다 -- 다음 요청엔 멀쩡할 수 있다."""
    if type(e).__name__ in ("ServiceUnavailable", "InternalServerError",
                            "DeadlineExceeded", "GatewayTimeout", "BadGateway"):
        return True
    text = str(e)
    if any(marker in text for marker in (
        "UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED", "overloaded", "high demand",
    )):
        return True
    return _status_code(e) in (500, 502, 503, 504)


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


# ListModels 조회가 실패했을 때만 쓰는 최후의 목록. 모델 이름은 계속 바뀌므로 여기에
# 박아두는 건 원칙적으로 임시방편이다 -- 정상 경로는 list_available_models 로 계정이 실제로
# 쓸 수 있는 목록을 받아오는 것이다. 실제로 이 저장소는 낡은 이름 때문에 여러 번 당했다
# (2026-08-30 실측: 코드 기본값이 gemini-2.5-* 였는데 그 계정에 2.5 계열은 아예 없고
# 3.x 계열만 있었다 -- 없는 이름은 404 -> is_permanent_error -> 영구 dead 로 기록된다).
# 그래서 여기에는 이 저장소에서 실제로 동작이 확인된 이름만 둔다.
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]


def best_available_model(api_key: str) -> str:
    """이 키로 쓸 수 있는 모델 중 가장 좋은 것 하나. 조회가 안 되면 FALLBACK_MODELS 첫 항목.

    주의: '가장 좋은 것 하나'는 단발 호출에 그대로 쓰면 위험하다. ListModels 는 무료 티어에서
    쿼터가 0 인 유료 전용 모델(pro 계열)도 나열하는데, 품질 순위상 pro 가 1 순위라 반드시
    그걸 고르고 즉시 429 를 맞는다(실측 2026-08-30: gemini-3.1-pro / -pro-preview 에서
    RESOURCE_EXHAUSTED). 단발 호출에는 아래 invoke_text 를 써서 후보를 순회하게 하라.
    """
    models = list_available_models(api_key)
    if not models:
        return FALLBACK_MODELS[0]
    return sorted(models, key=_model_quality_rank)[0]


def invoke_text(prompt: str, api_key: str, model: "str | None" = None,
                pool_id: str = "single-shot", log_prefix: str = "[invoke_text]") -> str:
    """에이전트가 아닌 '단발' LLM 호출. 후보를 품질 순으로 돌며 지금 못 쓰는 조합은
    건너뛴다.

    왜 필요한가: 지금까지 단발 호출(improve_agent 의 llm_proposer)은 모델 하나를 골라
    invoke 한 번 하고 끝이었다. 그 하나가 무료 티어에서 못 쓰는 pro 모델이면 매번
    RESOURCE_EXHAUSTED 로 실패할 뿐 다음 후보로 넘어가지 못한다 -- 에이전트 경로에는
    run_with_fallback_pool 이라는 순회가 있는데 단발 경로에만 없었다.

    quota_tracker 를 그대로 쓰므로 자기치유된다: pro 가 429 를 맞으면 그날치 소진으로
    기록돼 다음 호출부터는 순위 뒤로 밀리고, 실제로 쓸 수 있는 flash 계열이 앞에 온다.
    """
    if model:
        candidates = [model]
    else:
        candidates = list_available_models(api_key) or list(FALLBACK_MODELS)

    key_id = hashlib.sha256(api_key.encode()).hexdigest()[:8]
    labelled = [(f"key-{key_id}:{m}", m) for m in candidates]
    live = [c for c in labelled if not quota_tracker.is_dead(c[0])] or labelled

    def _sort_key(item):
        label, name = item
        remaining = quota_tracker.remaining(label)
        return (remaining <= 0, _model_quality_rank(name), -remaining)

    ranked = sorted(live, key=_sort_key)
    pinned_label = quota_tracker.get_pinned(pool_id)
    if pinned_label:
        head = [c for c in ranked if c[0] == pinned_label]
        ranked = head + [c for c in ranked if c[0] != pinned_label]

    last_error: Optional[Exception] = None
    for label, name in ranked:
        try:
            reply = _make_llm(name, api_key).invoke(prompt)
            quota_tracker.record_success(label)
            quota_tracker.set_pinned(pool_id, label)
            return extract_text(reply.content).strip()
        except Exception as e:
            if not is_unavailable_error(e):
                raise
            if is_rpm_quota_error(e):
                quota_tracker.record_rpm_cooldown(label)
            elif is_quota_error(e):
                quota_tracker.record_exhausted(label)
            elif is_permanent_error(e):
                quota_tracker.mark_dead(label, str(e)[:200])
            print(f"{log_prefix} candidate={label} 사용 불가({type(e).__name__}), 다음 후보로")
            last_error = e
    raise last_error if last_error else RuntimeError("후보가 비어있음")


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


# 후보 하나당 langchain 이 내부적으로 몇 번 재시도할지. 기본값(6)은 지수 backoff 와 맞물려
# 실패하는 후보 하나에 30~50초를 쓴다(실측 확인됨, 2026-08-28). 그런데 여기서는 fallback
# pool 자체가 재시도 전략이다 -- 한 후보가 안 되면 다음 후보로 넘어가면 되므로, 후보 안에서
# 오래 버티는 건 응답 지연으로만 돌아온다. 일시 장애 한 번은 흡수하도록 2 로 두고, 환경변수로
# 조정할 수 있게 한다.
LLM_MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "2"))
LLM_TIMEOUT = float(os.environ.get("GEMINI_TIMEOUT", "60"))


def _make_llm(model: str, key: str):
    """ChatGoogleGenerativeAI 생성. max_retries/timeout 을 모르는 버전에서도 뜨도록
    TypeError 면 기본 인자만으로 물러선다."""
    try:
        return ChatGoogleGenerativeAI(model=model, google_api_key=key,
                                      max_retries=LLM_MAX_RETRIES, timeout=LLM_TIMEOUT)
    except TypeError:
        return ChatGoogleGenerativeAI(model=model, google_api_key=key)


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
    (없으면 FALLBACK_MODELS)로 대체한다.

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
            key_models = list_available_models(key) or fallback_models or list(FALLBACK_MODELS)
        for model in key_models:
            llm = _make_llm(model, key)
            agent = create_react_agent(llm, tools=tools, checkpointer=checkpointer, prompt=prompt)
            label = f"key-{key_id}:{model}"
            pool.append((label, agent))
    return pool


# 모델 패밀리별 대략적인 성능 우선순위(낮을수록 먼저 시도) -- pro > flash > flash-lite >
# gemma(오픈 웨이트, 상대적으로 약함) > 그 외 이름 모를 모델. preview 꼬리표가 붙은 건 같은
# 패밀리 안에서 정식 버전보다 살짝 뒤로 민다(불안정할 수 있으므로). 어디까지나 이름 기반
# 휴리스틱이고 Google이 모델을 계속 새로 내놓으므로 완벽할 수 없다 -- 그래도 "쓸 수만 있으면
# 아무 모델이나"보다는 훨씬 낫다.
_VERSION_RE = re.compile(r"(\d+(?:\.\d+)?)")


def _model_quality_rank(model: str) -> "tuple[int, float, int]":
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
    # 같은 패밀리 안에서는 버전이 높은 쪽을 먼저 쓴다. 예전엔 이 항이 없어서 한 계정에
    # flash 계열이 여럿일 때(실측: 3, 3.5, 3.6, 3.7) 전부 동점이 돼 순서가 잔량으로만
    # 갈렸고, 구형이 최신보다 먼저 뽑히곤 했다. 정렬은 오름차순이므로 음수로 뒤집는다.
    match = _VERSION_RE.search(name)
    version = -float(match.group(1)) if match else 0.0
    is_preview = 1 if "preview" in name else 0
    return (family, version, is_preview)


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
                # 왜 느렸는지의 흔한 답이 이것이다 -- 앞 후보 i개가 막혀 갈아탔다.
                relay.적기(f"↻ 모델 전환 → {label.split(':', 1)[-1]} (앞 {i}개 후보 막힘)")
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
    prompt = compact.씨앗꺼내기(base_thread_id) + prompt      # 간추린 뒤 첫 말에 깃발 한 줄
    thread_id = thread_map.get(base_thread_id, base_thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        relay.턴기록(base_thread_id, result["messages"])
        _간추림(base_thread_id, thread_map, result["messages"])
        return extract_text(result["messages"][-1].content).strip()
    except Exception as e:
        if is_unavailable_error(e):
            raise
        print(f"{log_prefix} thread={base_thread_id} invoke_error={e!r} -- 새 thread로 재시도")
        new_thread_id = f"{base_thread_id}-{uuid.uuid4().hex[:8]}"
        thread_map[base_thread_id] = new_thread_id
        config = {"configurable": {"thread_id": new_thread_id}}
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        relay.턴기록(base_thread_id, result["messages"])
        _간추림(base_thread_id, thread_map, result["messages"])
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
