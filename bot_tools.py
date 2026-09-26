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
import circuitdraw
import imageread
import pdfread

import requests
try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:                      # 판에 따라 자리가 다르다 -- 봇 전체를 못 뜨게 하지 않는다
    from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

import agent_context
import agent_memory
import filetools
import orchestrator_tool
import poolpick
import public_agent_files
import rpmgate
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

# 같은 나무에 같은 명령은 두 번 돌리지 않는다 -- 규칙과 저장소는 shellmemo(표준 라이브러리만). 조사가 켜고 끈다.
import shellmemo
# thread_id -> 그 실행에서 부른 것. 부르는 쪽(discord_bot_server)이 답과 견준다.
마지막셸: dict[str, list] = {}
# thread_id -> 그 실행에서 **그린 그림들**(회로도 등). 부르는 쪽이 답에 붙여 보낸다.
# 셸 기록과 같은 자리를 쓴다 -- 한 실행이 끝날 때 옮겨진다(`unregister_thread`).
마지막그림: dict[str, list] = {}
_그림기록: dict[int, list] = {}


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
    with _셸기록_lock:
        _그림기록[threading.get_ident()] = []


def unregister_thread(thread_id: str) -> None:
    # **이 실행에서 부른 것을 thread_id 쪽으로 옮긴다.** 부르는 쪽이 답과 견준다.
    with _셸기록_lock:
        마지막셸[thread_id] = _셸기록.pop(threading.get_ident(), [])
        마지막그림[thread_id] = _그림기록.pop(threading.get_ident(), [])
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
    작성자 = str(_current_author.get())
    차단중 = shellmemo.켜졌나(작성자)
    지문 = shellmemo.나무지문(_판) if 차단중 else ""
    if 차단중:
        전 = shellmemo.이미돌렸나(작성자, command, 지문)
        if 전 is not None:
            print(f"[run_shell] {작성자} :: 중복 차단 {redact_secrets(command)[:100]!r} (같은 나무 {지문})")
            return shellmemo.막힘말(command, 지문, 전)
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
        if 차단중:
            shellmemo.적기(작성자, command, 지문, proc.returncode, out + ("\n" + err if err.strip() else ""))
        if proc.returncode is not None and proc.returncode < 0:
            return f"[중단됨] stop 명령으로 강제 종료됨(signal={-proc.returncode}).\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        return f"[exit={proc.returncode}]\nSTDOUT:\n{out}\nSTDERR:\n{err}"
    finally:
        with _active_procs_lock:
            _active_procs.pop(ident, None)


@tool
def run_probes(commands: str, minutes: int = 2) -> str:
    """**탐침 여러 개를 한꺼번에** 돌린다 -- 줄마다 명령 하나(최대 12줄), 저장소(또는 계획판)에서 나란히
    실행해 명령마다 (끝값 · 걸린초 · 출력 꼬리) 표로 돌려준다. 가설 하나를 확인하려고 명령을 하나씩 돌리지
    말고, 갈릴 만한 탐침 3~6개를 한 번에 던져라: 예) "python3 tests/test_x.py" · "git log -3 --oneline -- 파일" ·
    "grep -n 이름 파일" · "python3 -c 'import 모듈'". 각 명령은 toolgate 를 지난다. minutes 는 명령마다의 상한."""
    if agent_context.is_blocked():
        return "실패: 게스트는 run_probes 를 사용할 수 없습니다."
    import probes
    줄들 = [c.strip() for c in (commands or "").splitlines() if c.strip()]
    막힌 = [(c, toolgate.검사(c)) for c in 줄들]
    막힌 = [(c, 왜) for c, 왜 in 막힌 if 왜]
    if 막힌:
        return "[도구 게이트 차단 -- 하나도 돌리지 않았다]\n" + "\n".join(f"  {redact_secrets(c)[:90]} -- {왜[:60]}" for c, 왜 in 막힌)
    _판 = _계획판() or REPO_DIR
    import entrypoints
    줄들 = [entrypoints.셸명령_모듈꼴(c, _판)[0] for c in 줄들]
    결과 = probes.묶음(줄들, cwd=_판, 초=max(1, min(int(minutes), 10)) * 60, env=child_env())
    for r in 결과:
        relay.적기(relay.줄(redact_secrets(r["명령"]), r["끝값"], r["걸린초"]))
        print(f"[run_probes] {_current_author.get()} :: [{r['끝값']}] {redact_secrets(r['명령'])[:120]!r}")
    return redact_secrets(probes.표(결과))


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
def send_email(to: str, subject: str, body: str, attach: str = "") -> str:
    """메일을 보낸다 -- SMTP 접속은 여기가 한다. **네가 smtplib 코드를 짜거나 발급 절차를
    설명하지 마라.** 수단(보내는 주소·앱 비밀번호)이 없으면 이 도구가 "무엇이 없고 어떻게
    주는지" 를 돌려준다 -- 그 말을 사용자에게 **그대로** 전하라(선택지를 나열하지 말고).
    사용자가 `!열쇠 이름=값` 으로 줬다고 하면 같은 인자로 다시 불러라 -- 바로 나간다.
    .env 는 이 도구가 별칭·값의 꼴로 알아서 뒤진다 -- 네가 read_file 로 .env 를 읽지 마라.
    to 에 "me" 를 주면 USER_EMAIL 로 간다. 본문에 [교수님 성함] 같은 자리표가 남아 있으면 안 보낸다
    -- 네가 다 채워서 다시 불러라(실존 인물 이름을 지어 서명하지 말고 직함·위원회로).
    제목 앞의 `[보고]`·`[공유]`·`[안내]`·`[긴급]`·`[회신]` 은 말머리라 자리표로 안 센다.

    **attach 로 파일을 붙인다** -- 저장소 기준 상대경로를 쉼표나 띄어쓰기로 여럿,
    글롭도 된다(`house/signoff/*`). 보고서 PDF·회로 소스·넷리스트·GDS 를 이걸로 보낸다.
    첨부를 달라는 부탁(도면·회로도·보고서를 메일로)에 본문만 보내지 마라 -- **첨부가
    없으면 그건 보고가 아니다.** 저장소 밖 경로와 비밀값 자리는 도구가 거절한다."""
    if agent_context.is_blocked():
        return "실패: 게스트는 send_email 을 사용할 수 없습니다."
    import mailer
    import mailattach
    붙일것, 거절 = mailattach.풀기(attach)
    if 거절 and not 붙일것:
        return "[첨부 거절] " + " · ".join(거절[:4])
    막힘 = mailattach.막히나(붙일것)
    if 막힘:
        return f"[첨부 거절] {막힘}"
    총 = mailattach.재기(붙일것)
    if 붙일것:
        r = mailer.보내기_첨부(to, subject, body, 붙일것,
                          허용자리표=mailattach.말머리)
    else:
        r = mailer.보내기(to, subject, body, 허용자리표=mailattach.말머리)
    꼬리 = (f" (첨부 {len(붙일것)}개 {총/1e6:.1f} MB)" if 붙일것 else "")
    relay.적기(f"✉ {to[:40]} {'보냄' if r['보냈나'] else '못 보냄'}{꼬리} -- "
             f"{r['말'].splitlines()[0][:60]}")
    말 = r["말"]
    if 거절:
        말 += "\n(붙이지 못한 것: " + " · ".join(거절[:3]) + ")"
    return 말


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


회로그림자리 = "inbox/회로그림"


def _그림남기기(경로: str) -> None:
    """이 실행이 그린 그림을 적어 둔다. 부르는 쪽이 답에 붙여 보낸다."""
    with _셸기록_lock:
        _그림기록.setdefault(threading.get_ident(), []).append(경로)


검사시뮬자리 = "inbox/시뮬"   # 회당 45KB HTML -- .gitignore 로 커밋에서 뺀다


@tool
def simulate_inspection(정책: str = "pi", dt: float = 0.02) -> str:
    """**항공기 결함검사 드론의 3D 동적 시뮬레이션 HTML 을 만든다.**

    무인 체계 제어 정책이 B737-800 검사 경로를 실제로 추종한 궤적을, Three.js 로 **움직이는
    인터랙티브 HTML** 로 낸다 -- 드론이 경로를 날고, 재생/일시정지 · 타임 슬라이더 · 속도 ·
    궤도/추적/드론뷰 카메라, 실시간 텔레메트리(위치 · 상태 h · 속도 · 표면거리)와 물리 규격
    검증(GSD · 스와스 · 표준거리 밴드 · 커버리지)이 함께 뜬다.

    **정책 = "pi"**(기본): 손 튜닝 3축 PI-SSM(베이스라인).
    **정책 = "mamba"**: **학습된 신경망 Mamba 정책**(PI 를 numpy 수동 BPTT 로 모방학습한
      그 정책)이 실제로 검사 경로를 난다 -- 손 Kp/Ki 가 아니라 학습된 대각 SSM 재귀 +
      SiLU 게이트. 그 재귀 h=a⊙h+b⊙x 가 곧 ssm/scan_mac 하드웨어가 처리하는 재귀다.

    이 HTML 은 **답과 함께 자동으로 디스코드에 올라간다** -- 받아서 브라우저로 열면 실제로
    애니메이션이 돈다(정지 이미지가 아니다). 경로를 답에 적을 필요 없다.

    수치는 지어내지 않는다 -- inspect3d 가 제어 정책을 실제로 돌려 낸 궤적· 규격이다.
    dt: 제어 시뮬 시간간격(초, PI 에만; Mamba 는 학습 dt=0.05 로 고정).
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 simulate_inspection 을 사용할 수 없습니다."
    import ctrl.model.inspect3d as I
    import ctrl.viz as V
    자리 = os.path.join(REPO_DIR, 검사시뮬자리)
    os.makedirs(자리, exist_ok=True)
    stem = uuid.uuid4().hex[:8]
    j = os.path.join(자리, f"검사3d-{stem}.json")
    h = os.path.join(자리, f"검사3d-{stem}.html")
    맘바 = str(정책).strip().lower() in ("mamba", "맘바", "신경망", "학습")
    try:
        r = I.추종_맘바() if 맘바 else I.추종(dt=float(dt))
        I.저장(r, j)
        V.만들기("검사3d", j, h)
    except Exception as e:                                   # noqa: BLE001
        return f"[시뮬 실패] {type(e).__name__}: {e}"
    _그림남기기(h)
    m = r["지표"]; v = m["검증"]; 통과 = sum(1 for x in v.values() if x)
    return "\n".join([
        f"[시뮬 생성] {os.path.basename(h)} -- **답과 함께 자동으로 올라간다.** "
        f"받아서 브라우저로 열면 드론이 실제로 난다(움직이는 3D, 정지 이미지 아님).",
        f"제어 정책: {r.get('정책이름','?')}",
        f"비행 {m['비행시간s']}s · 웨이포인트 {m['웨이포인트수']} · "
        f"표준거리 {m['표준거리min_m']}~{m['표준거리max_m']}m · 커버리지 {m['커버리지pct']}%",
        f"결함 검출 {m['검출수']}/{m['결함수']} · 물리 규격 {통과}/{len(v)} PASS · "
        f"GSD@표준 {m['GSD표준_mm']}mm(최소검출 {m['최소검출표준_mm']}mm)",
        ("학습된 Mamba 정책이 난다 -- 손 PI 가 아니다. 재귀 h=a⊙h+b⊙x 가 ssm/scan_mac 에 매핑."
         if 맘바 else
         "손 PI-SSM 베이스라인 -- 같은 재귀가 ssm/scan_mac 하드웨어에 매핑. `정책=mamba` 로 학습정책도 태운다."),
        "결함 표식은 근접검출 데모(실제 비전 아님).",
    ])


@tool
def simulate_formation() -> str:
    """**무인체계 편대(스웜)의 위협회피 동적 시뮬레이션 HTML 을 만든다.**

    5대 V편대가 바람 외란 속에서 전술 스택(계획 → MPC 중심궤적 → 편대 수행)으로
    위협원(비행금지구역)을 회피하는 것을 Canvas 애니메이션으로 낸다 -- 편대가 실제로
    날고, 재생/일시정지 · 속도 · 타임 슬라이더가 있다. 상단 버튼으로 세 계획을 토글:
    **중심만** · **편대폭** · **폭+실행마진**. 바깥 드론이 위협에 닿으면 빨강으로 뜬다.

    정직한 시연: 계획이 편대의 폭·하위 실행오차(바람+편대유지)를 덜 반영하면 바깥
    드론이 위협을 관통한다. 필요 안전마진 = 위협반경 + 편대 반폭 + 실행오차. 세 층이
    얽혀 있음을 눈으로 보여 준다. 수치는 지어내지 않는다 -- ctrl.model.tactical 이
    실제로 돌린 궤적· 여유다(재현/시연, paper/선행조사/무인체계_편대제어_MPC.md).

    이 HTML 은 **답과 함께 자동으로 디스코드에 올라간다** -- 받아서 브라우저로 열면
    편대가 실제로 난다(정지 이미지 아님).
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 simulate_formation 을 사용할 수 없습니다."
    import ctrl.swarm_viz as SV
    자리 = os.path.join(REPO_DIR, 검사시뮬자리)
    os.makedirs(자리, exist_ok=True)
    h = os.path.join(자리, f"편대-{uuid.uuid4().hex[:8]}.html")
    try:
        _, 요약 = SV.만들기(h)
    except Exception as e:                                   # noqa: BLE001
        return f"[편대 시뮬 실패] {type(e).__name__}: {e}"
    _그림남기기(h)
    줄 = [f"[편대 시뮬 생성] {os.path.basename(h)} -- **답과 함께 자동으로 올라간다.** "
          f"받아서 브라우저로 열면 편대가 실제로 난다(움직이는 2D, 정지 이미지 아님)."]
    for 이름, v in 요약.items():
        판정 = f"관통 {(-v['clr']):.2f}m ✗" if v["clr"] < 0 else f"전원회피 +{v['clr']}m ✓"
        줄.append(f"  {이름}(Rplan {v['Rplan']}): 편대유지 {v['fe']}m · {판정}")
    줄.append("필요 마진 = 위협반경 + 편대 반폭 + 실행오차(바람+유지). 세 층이 얽힌다.")
    return "\n".join(줄)


@tool
def draw_circuit(code: str = "", example: str = "", check: bool = True) -> str:
    """**회로도를 그린다.** CMOS·NMOS·PMOS·저항·축전기·코일·전류원·연산증폭기 등.

    그린 그림은 **답과 함께 자동으로 디스코드에 올라간다** -- 경로를 답에 적을 필요 없다.

    `example` 로 검증된 본보기를 바로 그릴 수 있다(전류미러 · CMOS인버터 · 공통소스 ·
    RC저역). 그 밖의 회로는 `code` 에 schemdraw 코드를 쓴다. `d` 라는 Drawing 안에서
    도니 `with` 없이 `d += elm.Resistor().right().label('$R_D$')` 처럼 쌓으면 된다.
    `elm` 과 `logic` 이 이미 들어와 있다.

    **트랜지스터 단자를 이을 때는 `M.absanchors['gate']` 를 써라.** `anchors` 는 소자
    안에서의 상대 좌표라, 그것으로 이으면 선이 엉뚱한 높이에 그어진다(실측으로 두 번
    틀렸다). 본보기들이 그 꼴을 그대로 보여 준다 -- 먼저 본보기를 그려 보고 고쳐 써라.

    `check` 가 참이면 **그린 그림을 다시 읽어** 무엇이 그려졌는지 글로 돌려준다.
    너는 그림을 볼 수 없으므로, 이것이 네가 제 그림을 확인하는 유일한 길이다.
    어긋났으면 코드를 고쳐 다시 그려라.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 draw_circuit 을 사용할 수 없습니다."
    자리 = os.path.join(REPO_DIR, 회로그림자리)
    os.makedirs(자리, exist_ok=True)
    쪽 = os.path.join(자리, f"회로-{uuid.uuid4().hex[:8]}.png")
    r = (circuitdraw.본보기그리기(example, 쪽) if example
         else circuitdraw.그리기(code, 쪽))
    if not r["됐나"]:
        return f"[회로 못 그림] {r['왜']}"
    _그림남기기(r["경로"])
    말 = [f"[그렸다] {os.path.basename(r['경로'])} -- **답과 함께 자동으로 올라간다**"]
    if check:
        본것 = imageread.읽기(r["경로"], "이 회로도에 무엇이 그려져 있나. 소자와 "
                                    "연결을 짧게 적어라. 떠 있는(안 이어진) 단자가 "
                                    "있으면 그것부터 말하라.",
                          repo=REPO_DIR)
        말 += ["", "그림을 다시 읽어 본 것 -- 어긋났으면 코드를 고쳐 다시 그려라:", 본것]
    return "\n".join(말)


def _rtl보고(머리: str, r: dict, 꼬리칸: "list[str]") -> str:
    """RTL 결과를 사람이 읽는 꼴로. **로그를 통째로 삼키지 않는다.**"""
    줄 = [f"{머리}: **{r['판정']}** -- {r['왜']}"]
    줄 += [f"{k}: {r[k]}" for k in 꼬리칸 if k in r and r[k] not in (-1, "", None)]
    로그 = (r.get("로그") or "").strip()
    if 로그:
        줄 += ["", "```", 자르기(로그, 1200, 1200), "```"]
    return "\n".join(줄)


@tool
def run_rtl(design: str, testbench: str, top: str = "tb", seconds: int = 60,
            waveform: bool = True, min_coverage: float = 0.0) -> str:
    """**Compile and actually RUN Verilog/SystemVerilog** (iverilog + vvp).

    `design` is the DUT, `testbench` is the bench that drives it. The bench MUST print
    an explicit `PASS` or `FAIL` — see below.

    Verdict is read from the **output**, never from the exit code: `vvp` exits 0 even
    when the bench prints FAIL (measured 2026-09-15). So:
      PASS  a pass marker is printed and no fail marker
      FAIL  a fail marker is printed (`FAIL`, `ERROR`, `$error`, `$fatal`, mismatch)
      못잼  neither was printed, or it did not even compile -- **not a pass**

    `waveform=True` (the default) also **draws the waveform and attaches it to the
    reply** — no need to mention a path. x/z is drawn as a red hatched band, never as 0,
    and the reply says in words which signals were x/z for the whole run. A bench can
    print PASS while every input sat at x (measured 2026-09-15); the waveform is how you
    see that. If the bench has no `$dumpfile`, one is injected and the reply says so.

    `min_coverage` (percent) turns this into an **IP-grade** check: the bench must both
    print PASS **and** reach that much coverage of the DUT, or the verdict is 못잼.
    Measured 2026-09-15: two benches for the same counter BOTH printed PASS, but one
    reached 52.9% (it never toggled `load`) and the other 100%. "It passes" is not a
    verification result — a commercial IP ships a coverage report, not a green log.
    Use 80-90 for anything you would call verified; the reply lists the dark points so
    you know what stimulus is missing. It costs ~10 s (Verilator builds a C++ model).

    Write self-checking benches: compare against expected values and
    `$display("FAIL: got %0d expected %0d", got, exp)` on mismatch,
    `$display("PASS")` at the end. Always `$finish`.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 run_rtl 을 사용할 수 없습니다."
    import rtl
    낼곳 = ""
    if waveform:
        자리 = os.path.join(REPO_DIR, 회로그림자리)
        os.makedirs(자리, exist_ok=True)
        낼곳 = os.path.join(자리, f"wave-{uuid.uuid4().hex[:8]}.png")
    r = rtl.시뮬(design, testbench, top, seconds, 낼곳, min_coverage)
    if r.get("커버리지말"):
        r["coverage"] = r["커버리지말"]
    if r.get("파형"):
        _그림남기기(r["파형"])
    if r.get("파형말"):
        r["waveform"] = r["파형말"]
    return _rtl보고("Simulation", r, ["coverage", "waveform", "끝값"])


@tool
def lint_rtl(design: str, strict: bool = True) -> str:
    """**Static-check Verilog with Verilator** (`--lint-only -Wall`).

    Catches width mismatches, unused/undriven signals, latch inference, blocking
    assignments in sequential blocks -- the things that simulate fine and then bite in
    synthesis. `strict=False` drops `-Wall` when the style warnings are too loud.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 lint_rtl 을 사용할 수 없습니다."
    import rtl
    return _rtl보고("Lint", rtl.린트(design, strict), ["경고수"])


@tool
def synth_rtl(design: str, top: str = "") -> str:
    """**Synthesize with Yosys and count cells** -- the 'A' in PPA.

    "It runs" is the first question; "how big is it" is the next one. Returns the cell
    count and the Yosys stat table. `top` is the top module (defaults to whatever
    Yosys picks).
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 synth_rtl 을 사용할 수 없습니다."
    import rtl
    return _rtl보고("Synthesis", rtl.합성(design, top), ["셀수"])


@tool
def prove_rtl(design: str, top: str = "", depth: int = 20, unbounded: bool = True,
              seconds: int = 280) -> str:
    """**Formally PROVE a property** over all inputs (Yosys SAT / temporal induction).

    A testbench only visits the states it happened to drive. The solver visits **every**
    state — so it finds the bug that only shows up on cycle 200. Put the property in the
    design as `assert (...)` inside the clocked block, e.g.

        always @(posedge clk)
            if (!rst_n) s <= 4'b0001;
            else begin
                s <= {s[2:0], s[3]};
                assert (s == 4'b0001 || s == 4'b0010 || s == 4'b0100 || s == 4'b1000);
            end

    Verdict is read from the output, never the exit code — measured 2026-09-15 on Yosys
    0.33, a counterexample, a vacuous pass and a bounded pass ALL exit 0:

        PASS  a property exists and was **proved unbounded** (induction)
        FAIL  a counterexample was found — **the trace comes back as a waveform picture**
        못잼  no `assert` at all (nothing to prove — the solver still says SUCCESS!),
              or only bounded (`unbounded=False`): "no counterexample within N steps"
              is NOT a proof — a design that breaks on cycle 200 was green at depth 20

    Formal starts from an **arbitrary** state, not from reset — a design that simulates
    fine can break here immediately. Give registers initial values (`reg x = 0;`) or
    constrain reset with an `assume`. Keep `depth` small first; induction is expensive.
    Identifiers must be ASCII — Korean names break the Yosys Verilog frontend.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 prove_rtl 을 사용할 수 없습니다."
    import formal
    자리 = os.path.join(REPO_DIR, 회로그림자리)
    os.makedirs(자리, exist_ok=True)
    낼곳 = os.path.join(자리, f"cex-{uuid.uuid4().hex[:8]}.png")
    r = formal.증명(design, top, depth, unbounded, 초=seconds, 반례낼곳=낼곳)
    if r.get("반례"):
        _그림남기기(r["반례"])
    r["properties"] = r.get("성질수", 0)
    r["depth"] = r.get("깊이", 0)
    return _rtl보고("Formal", r, ["properties", "depth"])


@tool
def place_rtl(design: str, target_mhz: float, top: str = "", chip: str = "hx8k",
              seconds: int = 500) -> str:
    """**Place, route and time the design on a real FPGA** (Yosys + nextpnr-ice40).

    `run_rtl` answers "does it work", `synth_rtl` answers "how big", this answers
    **"how fast"** — and that needs a real device, because most of the delay is wiring.
    Returns Fmax per clock plus LC/RAM/IO utilisation against the part.

    **`target_mhz` is required.** With no target, nextpnr compares against its own
    default and prints `PASS at 12.00 MHz` (measured 2026-09-15) — a green that has
    nothing to do with the speed your design will run at. No target, no verdict:

        PASS  every clock meets `target_mhz` after routing
        FAIL  a clock falls short — the reply says by how much
        못잼  no target given · does not fit the part · no clock at all · tool missing

    `--timing-allow-fail` is never used: measured, that one flag turns exit 1 into
    exit 0 on the same timing violation. Chips: `hx1k`(1280 LC) · `hx8k`(7680, default)
    · `lp384`(384) · `up5k`(5280). Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 place_rtl 을 사용할 수 없습니다."
    import pnr
    r = pnr.맞춰보기(design, top, target_mhz, chip, 초=seconds)
    말 = pnr.말로(r)
    if 말:
        r["timing"] = 말.replace("\n", " | ")
    return _rtl보고("Place & route", r, ["timing"])


@tool
def serdes_link(loss_db: float = 20.0, snr_db: float = 26.0, bits: int = 100000,
                ctle_peaking_db: float = 0.0, ffe_taps: int = 0, dfe_taps: int = 0,
                tap_bits: int = 0, keep_fraction: float = 1.0,
                ideal_decision: bool = False, eye: bool = True,
                reflections: str = "", dfe_positions: str = "",
                sps: int = 8, seed: int = 0) -> str:
    """**Actually simulate a wireline SerDes link and measure BER** (channel/CTLE/FFE/DFE).

    A lossy minimum-phase channel (`loss_db` at Nyquist) closes the eye with ISI; CTLE,
    an LMS-adapted FFE and a decision-feedback DFE reopen it. Returns the measured BER,
    the eye height/width, and an eye-diagram PNG. Calibrated: with `loss_db=0` and no
    equaliser the measured BER matches the closed form `Q(10^(snr_db/20))` -- that is
    what pins the SNR definition (noise relative to the ideal loss-free main cursor).

    Four things here are silently wrong if you do not guard them, and this does:

        * **0 errors is not BER 0** -- the reply gives the rule-of-three upper bound
        * taps are adapted on the first 30% of bits and BER is counted on the rest;
          measuring on the training bits is memorisation, not equalisation
        * the DFE feeds back **its own decisions**, so error propagation is included.
          `ideal_decision=True` feeds the true bits instead: it makes BER look better
          and is labelled as such in the reply. Hardware does not know the answer.
        * a diverged LMS is reported as diverged, not as "equalisation did not help"

    `tap_bits` quantises the taps (research contribution: BER vs word length) and
    `keep_fraction` prunes them.

    **`reflections` adds echoes** -- `"0.35@11"` is a coefficient 0.35 arriving 11 symbols
    late, several separated by commas. A real backplane is not just smooth skin-effect
    loss: connectors and via stubs send part of the signal back, and it returns as
    `H(f) = H_skin(f)(1 + sum Gamma_k e^-j2pi f tau_k)` -- a **notch** at f*tau = 1/2,
    20log10(1-Gamma) deep, which no smooth CTLE boost can fill. In time it is one
    isolated cursor at that delay. Measured: Gamma 0.35 at tau 11 puts a +0.358 cursor at
    tap 11 while every other residual is below 0.055.

    **`dfe_positions` places DFE taps at chosen delays** -- `"1,2,3,4,11"` instead of a
    contiguous bank (this is a floating-tap DFE, what real receivers do). Measured on
    that channel: eight contiguous taps cannot reach delay 11 and buy almost nothing
    (BER 1.4e-3 for 373 LC), while **one tap placed at 11 gives 2.0e-5 for 49 LC**.
    Where the taps go beats how many there are. Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 serdes_link 을 사용할 수 없습니다."
    import serdes
    try:
        반사 = serdes.반사읽기(reflections)
    except ValueError as e:
        return f"실패: {e}"
    자리 = [int(x) for x in str(dfe_positions).replace(" ", "").split(",") if x] or None
    r = serdes.링크(비트수=int(bits), 손실dB=loss_db, SNRdB=snr_db, sps=int(sps),
                  CTLE피킹dB=ctle_peaking_db, FFE탭=int(ffe_taps),
                  DFE탭=int(dfe_taps), 탭비트=int(tap_bits), 반사=반사, DFE자리=자리,
                  남길비율=keep_fraction, 이상적판정=bool(ideal_decision), 씨=int(seed))
    줄 = [serdes.말로(r)]
    if eye and r.get("판정") != "못잼":
        자리 = os.path.join(REPO_DIR, 회로그림자리)
        os.makedirs(자리, exist_ok=True)
        쪽 = os.path.join(자리, f"eye-{uuid.uuid4().hex[:8]}.png")
        파형 = serdes.받은파형(손실dB=loss_db, SNRdB=snr_db, sps=int(sps),
                          CTLE피킹dB=ctle_peaking_db, 비트수=min(int(bits), 4000),
                          씨=int(seed))
        g = serdes.아이그리기(파형, int(sps), 쪽,
                          f"loss {loss_db:.0f} dB, SNR {snr_db:.0f} dB"
                          + (f", CTLE {ctle_peaking_db:.0f} dB" if ctle_peaking_db else ""))
        _그림남기기(g["경로"])
        줄.append(f"Eye (channel output, before FFE/DFE): {g['왜']}")
        줄.append(f"[drew] {os.path.basename(g['경로'])} -- uploaded with this reply")
    return "\n".join(줄)


@tool
def quant_sweep(widths: str = "2,3,4,6,8,12", loss_db: float = 20.0,
                snr_db: float = 26.0, bits: int = 150000, ffe_taps: int = 11,
                dfe_taps: int = 8, sps: int = 8, seed: int = 7) -> str:
    """**BER versus tap word length** -- the quantisation trade-off curve, measured.

    Runs the same link once per word width and compares each against the floating-point
    baseline. Crucially it says which widths are **not distinguishable** from float at
    the bit count you ran: 11 errors versus 8 errors is not a difference, it is counting
    noise, and calling it "no degradation" is exactly the false green this repo hunts.
    To claim two widths are equal, run more bits and narrow the bars.

    Feed the smallest width that survives into `place_rtl` / `ip_signoff` to get the
    LUT/DSP/Fmax cost of that choice on a real device. Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 quant_sweep 을 사용할 수 없습니다."
    import serdes
    try:
        비트들 = tuple(int(x) for x in str(widths).replace(" ", "").split(",") if x)
    except ValueError:
        return f"실패: widths 를 못 읽었다: {widths!r} -- `2,3,4,6,8` 처럼 줘라"
    if not 비트들:
        return "실패: widths 가 비었다"
    s = serdes.비트폭쓸기(비트들, 비트수=int(bits), 손실dB=loss_db, SNRdB=snr_db,
                    sps=int(sps), FFE탭=int(ffe_taps), DFE탭=int(dfe_taps),
                    씨=int(seed))
    return serdes.쓸기말로(s)


@tool
def adc_sweep(widths: str = "4,5,6,7,8", full_scales: str = "2.0,2.5,3.0,4.0",
              loss_db: float = 25.0, snr_db: float = 30.0, bits: int = 300000,
              ffe_taps: int = 11, dfe_taps: int = 8, coef_bits: int = 0,
              sps: int = 8, seed: int = 7) -> str:
    """**BER versus ADC resolution AND full scale** -- the two cannot be chosen apart.

    An ADC is fixed by two numbers: how many bits, and how far it reaches. Narrow the
    full scale and large samples clip; widen it and the same bits buy a coarser step.
    Sweeping resolution alone silently assumes the full scale is already optimal, and
    that assumption has never been measured. This sweeps the grid and prints the clip
    rate next to every BER.

    Measured 2026-09-15 (25 dB channel, SNR 30 dB, FFE 11 + DFE 8): the floor sits at
    **2.5 sigma at every resolution**, and there the ADC clips **0.45%** of samples, not
    0% -- a well-set ADC clips a little on purpose. 3.0 sigma was slightly too wide.

    Each row's full scale is **chosen** by lowest BER, so that BER is optimistically
    biased (winner's curse). The reply re-runs the chosen full scale on a different seed
    and prints that separately -- quote the re-measured number, not the grid. Rows that
    do not separate from float print the bit count that would settle them; `NOT YET
    separated` is not `equal`.

    `coef_bits` quantises the equaliser taps at the same time, so you can ask the joint
    question instead of assuming the two word lengths are independent. Feed the answer
    into `place_rtl` for the LUT cost -- measured, an ADC bit costs ~249 LC in an 11-tap
    FFE against ~170 LC for a coefficient bit, and that is only the digital back end:
    the converter's own area and power (roughly doubling per bit) are **not measured by
    this stack**. Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 adc_sweep 을 사용할 수 없습니다."
    import serdes
    try:
        비트들 = tuple(int(x) for x in str(widths).replace(" ", "").split(",") if x)
        스케일들 = tuple(float(x) for x in str(full_scales).replace(" ", "").split(",") if x)
    except ValueError:
        return f"실패: widths/full_scales 를 못 읽었다: {widths!r} / {full_scales!r}"
    if not 비트들 or not 스케일들:
        return "실패: widths 나 full_scales 가 비었다"
    s = serdes.ADC쓸기(비트들, 스케일들, 비트수=int(bits), 손실dB=loss_db,
                    SNRdB=snr_db, sps=int(sps), FFE탭=int(ffe_taps),
                    DFE탭=int(dfe_taps), 탭비트=int(coef_bits), 씨=int(seed))
    return serdes.ADC쓸기말로(s)


@tool
def loss_sweep(losses: str = "15,20,25,30,35", widths: str = "7,8,9,10",
               target_ber: float = 1e-3, bits: int = 800000, seeds: str = "7,11,23,42",
               quantize_adc: bool = True, adc_full_scale: float = 2.5,
               ffe_taps: int = 11, dfe_taps: int = 8, sps: int = 8) -> str:
    """**How far does a given word length hold as the channel gets worse?**

    Sweeping loss at a fixed SNR cannot answer this. In this model SNR is referenced to
    the ideal loss-free main cursor, so raising the loss worsens ISI **and** the effective
    SNR together; measured at SNR 30 dB, 10-20 dB of loss gave zero errors (nothing to
    compare) while 30 dB was already a broken link. So each loss is first moved to a
    **common float BER** by bisecting on SNR -- then the rows differ in ISI, not in how
    broken the link is. The SNR column is the price of that.

    **Every cell is a mean over several seeds with its seed-to-seed spread**, because a
    single seed cannot name a word length. Measured 2026-09-15 at 30 dB loss, 7-bit
    coefficients read -4.7% on one seed and +26.2% on another: at coarse widths it is
    where that seed's LMS solution happens to round that decides, not the step size. A
    width is called sufficient only when the mean degradation AND the spread are both
    small -- a large spread means the answer depends on which seed you looked at, which
    is another way of saying the design has no margin.

    Measured result (coefficients only, ideal ADC): 7 bit is flat to 20 dB, its spread
    climbs from +-2.8% to +-10% by 30 dB, and its mean breaks to +11.7% at 35 dB. 8 bit
    stays within +-3% mean and +-3.7% spread out to 35 dB. Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 loss_sweep 을 사용할 수 없습니다."
    import serdes
    try:
        손실들 = tuple(float(x) for x in str(losses).replace(" ", "").split(",") if x)
        폭들 = tuple(int(x) for x in str(widths).replace(" ", "").split(",") if x)
        씨들 = tuple(int(x) for x in str(seeds).replace(" ", "").split(",") if x)
    except ValueError:
        return f"실패: losses/widths/seeds 를 못 읽었다: {losses!r} / {widths!r} / {seeds!r}"
    if not 손실들 or not 폭들 or not 씨들:
        return "실패: losses·widths·seeds 중에 빈 것이 있다"
    if len(씨들) < 2:
        return ("실패: **씨가 하나로는 워드 길이를 말할 수 없다** -- 실측으로 같은 7비트가 "
                "한 씨에서 -4.7%, 다른 씨에서 +26.2% 였다. 씨를 둘 이상 줘라")
    s = serdes.손실쓸기(손실들, 폭들, 목표BER=target_ber, 비트수=int(bits),
                    ADC도=bool(quantize_adc), ADC풀스케일시그마=adc_full_scale,
                    씨들=씨들, sps=int(sps), FFE탭=int(ffe_taps), DFE탭=int(dfe_taps))
    return serdes.손실쓸기말로(s)


@tool
def nn_equalizer(loss_db: float = 25.0, snr_db: float = 30.0, compression: float = 1.0,
                 bits: int = 300000, window: int = 10, hidden: int = 16,
                 epochs: int = 12, dfe_taps: int = 0, weight_bits: int = 0,
                 keep_fraction: float = 1.0, reflections: str = "",
                 adc_bits: int = 0, sps: int = 8, seed: int = 7) -> str:
    """**Neural-network equaliser** -- and the control that says when it is allowed to win.

    On a linear channel with AWGN the optimal equaliser **is linear** (MMSE-DFE), so an
    MLP can at best tie FFE+DFE. If it wins there, that is not physics, it is a leak:
    BER being counted on training bits, or true bits fed into the decision feedback.
    Measured 2026-09-16 at `compression=0`: linear 6.33e-4, net 6.75e-4 -- the net loses,
    which is what makes the rest of the numbers believable.

    `compression` is receiver-front-end saturation, `tanh(a*y)/a`. Put it at the RX, not
    the TX: NRZ has only two levels, so a memoryless nonlinearity on the transmitted
    symbols is **just a gain change** and moves BER not at all. It needs the many-level
    signal that ISI creates. No linear inverse exists, so this is the first thing FFE,
    DFE and CTLE cannot undo -- and the first thing a net can:

        compression   linear FFE11+DFE8      net        gain
             0.0          6.333e-04      6.746e-04     0.9x   <- loses, correctly
             0.5          1.786e-03      6.651e-04     2.7x
             1.0          2.421e-02      1.498e-03    16.2x
             1.5          5.680e-02      7.841e-03     7.3x
             2.0          8.240e-02      2.084e-02     4.1x

    The gain peaks and then falls: past a point saturation destroys the information
    irreversibly and no equaliser gets it back. Adding a DFE after the net changes almost
    nothing (1.498e-3 vs 1.548e-3) -- the net already did that job, so spending parameter
    budget there is waste.

    Training uses only the first 30% of bits and BER is counted on the rest; a run that
    did not converge is reported as 못잼, never as a bad BER. `weight_bits` and
    `keep_fraction` quantise and prune the weights for the hardware step.
    Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 nn_equalizer 을 사용할 수 없습니다."
    import serdes
    import nneq
    try:
        반사 = serdes.반사읽기(reflections)
    except ValueError as e:
        return f"실패: {e}"
    r = nneq.링크(비트수=int(bits), 손실dB=loss_db, SNRdB=snr_db, 압축=compression,
                sps=int(sps), 앞뒤=int(window), 은닉수=int(hidden), 에폭=int(epochs),
                DFE탭=int(dfe_taps), 가중치비트=int(weight_bits),
                남길비율=keep_fraction, 반사=반사, ADC비트=int(adc_bits), 씨=int(seed))
    선 = serdes.링크(비트수=int(bits), 손실dB=loss_db, SNRdB=snr_db, sps=int(sps),
                   FFE탭=11, DFE탭=8, 압축=compression, 반사=반사,
                   ADC비트=int(adc_bits), 씨=int(seed))
    줄 = [nneq.말로(r), "",
         f"linear FFE11+DFE8 on the same channel: {선['왜']}"]
    if r["오류수"] >= 0 and 선["오류수"] > 0:
        다름, 말 = serdes.구별되나(r["오류수"], r["잰비트"], 선["오류수"], 선["잰비트"])
        줄.append(("net vs linear: " + 말) if 다름 else
                  ("net vs linear: " + 말 + "  -- on a LINEAR channel this tie is the "
                   "expected result, not a failure"))
    return "\n".join(줄)


@tool
def eq_area(kind: str = "nn", taps: int = 5, hidden: int = 2, bits: int = 7,
            frac: int = 4, target_mhz: float = 50.0, chip: str = "hx8k",
            seconds: int = 300) -> str:
    """**Area and Fmax of an equaliser, on a real device** (yosys + nextpnr, iCE40).

    `kind` is `nn` (quantised MLP), `ffe` (linear feed-forward) or `dfe` (decision
    feedback). The neural net's Verilog is **bit-exact against `nnfix`**, the
    fixed-point reference -- `tests/test_nnfix.py` runs it and compares the final
    accumulator integer, not just the sign. That check is the reason these LC numbers
    mean anything: the smallest circuit is always the wrong one.

    Measured 2026-09-16, HX8K, target 50 MHz:

        DFE 4 taps W8      0 mults    211 LC  71.25 MHz  PASS
        DFE 8 taps W8      0 mults    439 LC  37.86 MHz  FAIL
        FFE 11 taps W7    11 mults  1,835 LC  56.11 MHz  PASS
        NN 5->2 Q2.4 7b   12 mults  2,368 LC  30.58 MHz  FAIL
        NN 5->2 Q3.6 10b  12 mults  4,498 LC  26.20 MHz  FAIL

    Three things that table says. **Word length is half the area** -- the same net at
    Q3.6/10-bit is 1.9x the size of Q2.4/7-bit and its BER is the same (the floor is
    the *integer* part, 2 bits; fractional resolution below 4 is what actually hurts).
    **DFE taps carry no multiplier at all** -- NRZ decisions are +-1, so feedback is an
    add or a subtract. And **what fails timing is combinational depth, not size**: the
    net puts multiply -> shift/clip -> multiply in one cycle, and an 8-tap DFE puts
    eight adds in one cycle; both miss 50 MHz while the bigger FFE makes it.

    `target_mhz` is mandatory in spirit: without a target nextpnr reports PASS against
    its own 12 MHz default, which is meaningless. Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 eq_area 을 사용할 수 없습니다."
    import eqrtl
    import pnr
    종 = (kind or "nn").strip().lower()
    if 종 == "nn":
        설계, top = eqrtl.nn(int(taps), int(hidden), XW=int(bits), WW=int(bits),
                            FRAC=int(frac)), "nneq_eq"
        곱 = int(taps) * int(hidden) + int(hidden)
    elif 종 == "ffe":
        설계, top = eqrtl.ffe(int(taps), W=int(bits)), "ffe"
        곱 = int(taps)
    elif 종 == "dfe":
        설계, top = eqrtl.dfe(range(1, int(taps) + 1), W=int(bits)), "dfe_pos"
        곱 = 0
    else:
        return f"실패: kind 는 nn · ffe · dfe 중 하나다 (받은 것: {kind!r})"
    r = pnr.맞춰보기(설계, top=top, 목표MHz=target_mhz, 칩=chip, 초=int(seconds))
    줄 = [f"{종} · {곱} multipliers · {r['판정']}", r["왜"]]
    말 = pnr.말로(r)
    if 말:
        줄.append(말)
    return "\n".join(줄)


@tool
def ip_signoff(design: str, testbench: str, top: str = "tb",
               min_coverage: float = 80.0, target_mhz: float = 0.0,
               chip: str = "hx8k", deliverables: str = "",
               seconds: int = 300) -> str:
    """**Run the IP sign-off gates an IP/design house actually passes before delivery.**

    "The RTL runs" is not a deliverable. Handing over commercial IP means handing over
    RTL + a self-checking bench + a coverage report + area + timing + an SDC + a
    register map + a TRM + a version. This runs the gates in order and refuses to call
    the result a pass unless **every** gate passed:

        LINT      verilator -Wall            no warnings
        SIM       iverilog + self-checking   a PASS marker must be printed
        COVERAGE  verilator, DUT only        must clear `min_coverage`
        FORMAL    yosys sat, unbounded       properties must exist AND be proven
        SYNTH     yosys                      cell count
        TIMING    nextpnr vs `target_mhz`    must meet the target
        DOCS      deliverable list           says what is missing

    One broken gate makes the whole sign-off FAIL; one unmeasured gate makes it 못잼.
    An unmeasured gate is never counted as a pass -- that is the whole point of the
    report. `deliverables` is a comma-separated list of what you actually have, out of
    `rtl, testbench, sdc, register_map, trm, version`.

    Formal cells are stripped (`chformal -remove`) before place & route and the reply
    says so -- measured 2026-09-15, a design carrying one `assert` dies in nextpnr with
    `cell type '$assert' is unsupported`, so a design with properties could otherwise
    never reach the TIMING gate at all. Put SVA-only functions (`$past`, `$rose`) inside
    `ifdef FORMAL`: iverilog cannot run them and the simulation never starts.

    DFT/ATPG, MBIST, CDC/RDC, IR drop, DRC/LVS and multi-corner are **not measured
    here** (they need commercial tools and a PDK). The reply lists them rather than
    letting their silence read as a pass. Identifiers must be ASCII.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 ip_signoff 을 사용할 수 없습니다."
    import ipflow
    있는것 = [x.strip() for x in (deliverables or "").replace("\n", ",").split(",")
            if x.strip()]
    r = ipflow.관문들(design, testbench, top, min_coverage, target_mhz, chip,
                    있는것, seconds)
    return ipflow.말로(r)


@tool
def run_spice(netlist: str, checks: str = "", seconds: int = 90) -> str:
    """**Actually SIMULATE an analog circuit** with ngspice (DC / AC / transient).

    Drawing a schematic is not verification. Give a full SPICE netlist and this runs it.
    Put the analysis inside a `.control` / `.endc` block and **measure** what you claim:

        * common-source amp            <- line 1 is eaten as the TITLE. Always waste it.
        .model nch NMOS (LEVEL=1 VTO=0.5 KP=200u LAMBDA=0.05)
        Vdd vdd 0 DC 1.8
        Vin in 0 DC 0.9 AC 1
        RD vdd out 20k
        M1 out in 0 0 nch W=3u L=1u
        CL out 0 1p
        .control
        op
        ac dec 50 1 10G
        meas ac av_db FIND vdb(out) AT=1k
        .endc

    The verdict is read from the **output**, never from the exit code -- measured on
    ngspice 42: a floating node, a mistyped node name, and a failed `.meas` all exit 0.

        PASS  it measured, and every measurement/check held
        FAIL  a `.meas` printed `failed!`, or a `checks` range was missed
        못잼  it did not run, or it ran and **measured nothing** -- not a pass

    `checks` is one `name low high` per line, matched against `.meas` names, e.g.
    `av_db 12 15`. Use it to state what you expect BEFORE you look; that is the
    difference between simulating and verifying.

    Built-in netlists you can pass by name instead (use `spice_example`):
    rc_lowpass, mosfet_iv, nmos_vth, current_mirror, common_source,
    cmos_inverter_vtc, diff_pair, rlc_resonance.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 run_spice 를 사용할 수 없습니다."
    import spice
    글 = spice.본보기찾기(netlist) or netlist
    r = spice.돌리기(글, checks, seconds)
    잰것 = r.get("잰것") or {}
    if 잰것:
        r["measured"] = " · ".join(f"{k} = {v:.6g}" for k, v in 잰것.items())
    return _rtl보고("SPICE", r, ["measured", "끝값"])


@tool
def monte_carlo(netlist: str, spread: str, runs: int = 30, checks: str = "",
                seed: int = 1234, seconds: int = 90) -> str:
    """**Process variation: run the circuit N times with parameters drawn from a Gaussian.**

    One nominal simulation says nothing about yield. Mismatch between two supposedly
    identical devices is what actually limits a mirror, a diff pair or a comparator.

    `spread` is one `param_name sigma` per line — **absolute** sigma, not a percentage —
    and each name must exist as a `.param name = value` line in the netlist, used from
    the model card as `{name}`:

        .param vtn2 = 0.5
        .model nch2 NMOS (LEVEL=1 VTO={vtn2} KP=200u)

    If the name has no `.param` to land on, this refuses to run instead of quietly
    simulating the same circuit N times and reporting 100% yield — measured, that is the
    biggest trap here. It also refuses if N runs produce **no spread at all** in the
    measurements, which means the parameter never reached the result.

    `checks` (`name low high`, same as `run_spice`) defines what counts as a pass; the
    yield comes back **with its own error bar** — 85% out of 20 runs is ±8%, and zero
    failures is reported by the rule of three (3/N), never as a flat 0%. Without
    `checks` there is no yield, only the spread, and the verdict is `못잼`.

    Built in: `mc_mirror` (current-mirror Vth mismatch) and `rc_noise` (thermal noise,
    whose answer is sqrt(kT/C), independent of R — verified to 0.06%).
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 monte_carlo 를 사용할 수 없습니다."
    import spice
    글 = spice.본보기찾기(netlist) or netlist
    r = spice.흩뿌리기(글, spread, runs, checks, seed, seconds)
    흩 = r.get("흩어짐") or {}
    if 흩:
        r["spread"] = " · ".join(
            f"{k}: mean {v['평균']:.6g}, sigma {v['시그마']:.4g}, "
            f"[{v['최소']:.6g}, {v['최대']:.6g}]" for k, v in 흩.items())
    r["runs"] = r.get("판수", 0)
    return _rtl보고("Monte Carlo", r, ["runs", "spread"])


@tool
def concept(name: str = "", level: str = "", domain: str = "",
            track: str = "") -> str:
    """**Look up an IC design concept** — the defining equation, what it governs, and the
    example you can actually run for it.

    Covers the undergrad / MS / PhD range of analog and digital IC design: device physics
    (square law, Vth, body effect, CLM, short-channel, subthreshold), single-stage amps,
    current mirrors and cascodes, differential pairs, OTAs (telescopic, folded, two-stage
    Miller), feedback and compensation, noise (thermal, kT/C, flicker), mismatch and
    Pelgrom, switched-capacitor, data converters, PLL, and on the digital side CMOS logic,
    logical effort, sequencing and timing, metastability and CDC, power, adders and
    multipliers, SRAM, interconnect and STA.

    Call with no arguments to see the index and how much of it is runnable. `level` is
    `학부`/`석사`/`박사`, `domain` is `analog`/`digital`/`device`/`mixed`, and `track`
    follows the IP-design-house career map: `공통기초` · `프론트엔드`(RTL+검증) ·
    `백엔드`(물리 구현 — **a third domain, neither digital logic design nor analog:
    it takes SPICE-characterized standard cells as black boxes**) · `아날로그` ·
    `IP특화`(AMBA/PCIe, VIP, soft vs hard IP, TRM) · `포트폴리오` · `생태계`
    (IDM/fabless/foundry/OSAT/chipless, PDK & tape-out, who captures the value).

    Every entry that names an example is **verified to run** — `tests/test_concepts.py`
    executes each linked netlist and draws each linked schematic, so a dead link is a red
    test, not a paragraph that merely claims coverage. Entries with no example are shown
    as explanation-only rather than hidden.

    Use this to fix the depth and the notation before answering, then run or draw the
    example instead of only describing it.
    """
    import concepts
    if not (name or "").strip():
        d = concepts.덮임()
        줄 = [f"**{d['모두']} concepts** — {d['돌려볼수있음']} with a runnable example, "
             f"{d['설명만']} explanation-only.",
             "by level: " + " · ".join(f"{k} {v}" for k, v in d["층별"].items()),
             "by domain: " + " · ".join(f"{k} {v}" for k, v in d["갈래별"].items()),
             "by track: " + " · ".join(f"{k} {v}" for k, v in d["트랙별"].items()), ""]
        for c in concepts.목록(level, domain, track):
            표 = "▶" if (c["넷리스트"] or c["회로도"]) else "·"
            줄.append(f"{표} {c['이름']} ({c['한글']}) — {c['층']}/{c['트랙']}")
        return "\n".join(줄)
    난것 = concepts.찾기(name)
    if not 난것:
        return (f"no concept matched {name!r}. Call `concept()` with no argument for the "
                "index, or try an alias like `cascode`, `gm/ID`, `SNM`, `FO4`, `CDC`.")
    return "\n\n".join(concepts.말로(c) for c in 난것[:3])


@tool
def textbook(question: str, sections: int = 5, section_id: str = "") -> str:
    """**Answer from the textbook, not from memory** — search the 170-chapter IP design
    book in `edu/` and get back the exact sections that bear on the question.

    Use this for **every** conceptual or design question about semiconductors, circuits,
    RTL, verification, timing, mixed-signal, protocols (MIPI/PCIe/Ethernet), IP business
    or patents — including questions asked in Korean. The book is English; Korean query
    terms are mapped through `edu/용어.py` before the search, and the reply tells you
    which Korean words could **not** be mapped, so a bad retrieval is visible rather than
    silent.

    `section_id` fetches one section in full (ids look like `X2_timing.ch_sta#4`) when a
    search hit is truncated and you need the rest of it.

    **How to answer once you have the sections** — graduate-seminar level, in this order:

    1. **What is actually being asked** — restate it precisely, and name the quantity.
    2. **The governing relation** — the equation or the invariant, with every symbol
       defined and its units. Derive it or say where it comes from; never assert it bare.
    3. **Where it is used** — which block, which part of the flow, which signoff check.
    4. **When it binds** — the regime where this term dominates and the regime where it
       is negligible. A number that always holds is not an engineering answer.
    5. **How to apply it** — the procedure, with a worked number the reader can redo.
    6. **What the industry code/constraint looks like** — SystemVerilog, SDC, Liberty,
       UPF or C++, quoted from the retrieved sections.
    7. **Where people get it wrong** — the specific failure mode, not a platitude.
    8. **What is not established** — what the book measured vs. what it only asserts.
       If the retrieved sections do not cover the question, say so plainly and answer
       from first principles marked as such. **Never present recall as the book's text.**

    Cite the section (`chapter / section`) next to each claim that came from it.
    """
    import sys as _s, os as _o
    _e = _o.path.join(REPO_DIR, "edu")
    if _e not in _s.path:
        _s.path.insert(0, _e)
    import kb
    return kb.답근거(question, sections, section_id)


@tool
def spice_example(name: str = "") -> str:
    """**List or fetch a ready-made, verified analog netlist** for `run_spice`.

    Every one of these was run and its numbers checked against hand calculation
    (within 5%, most within 1%). Call with no name to list them. Use them as the
    starting point for a design question instead of writing a netlist from scratch.
    """
    import spice
    if not (name or "").strip():
        return ("Built-in SPICE netlists (pass the name to `run_spice` directly):\n"
                + "\n".join(f"- `{k}` — {spice.본보기[k].splitlines()[0].lstrip('* ')}"
                            for k in spice.본보기))
    글 = spice.본보기찾기(name)
    if not 글:
        return (f"no such example: {name!r}. Available: "
                + ", ".join(spice.본보기))
    return f"```spice\n{글}```"


@tool
def read_image(path: str, question: str = "") -> str:
    """**사진·스크린샷을 실제로 본다.** 첨부 파일이 그림이면 `cat` 하지 말고 이걸 써라.

    그림에 적힌 것(문제·수식·표·오류 화면)을 글로 옮겨 돌려준다. `question` 을 주면
    옮긴 뒤 그 물음에도 답한다. path 는 첨부 메시지에 적힌 경로를 그대로 넣으면 된다.
    png·jpg·webp·gif·heic·pdf 를 읽는다. 글 파일은 read_file 을 써라.
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 read_image 를 사용할 수 없습니다."
    return imageread.읽기(path, question, repo=REPO_DIR,
                        자르개=lambda t: 자르기(t, 셸출력_앞, 셸출력_뒤))


@tool
def read_pdf(path: str, 모드: str = "", 쪽: str = "", 물음: str = "") -> str:
    """**PDF 를 골라서 읽는다.** 큰 문서는 read_image 로 통째로 보내면 토큰이 터진다.

    모드:
      `훑기`  (기본) 쪽수 · 글자수 · **목차** 를 준다. 큰 PDF 는 여기서 시작하라
      `찾기`  `물음` 에 준 말이 나오는 **쪽만** 앞뒤와 함께 준다. 2000 쪽에도 쓴다
      `읽기`  `쪽='120-150'` 처럼 준 범위만 글로 뽑는다
      `그림`  `쪽='137'` 그 쪽만 PNG 로 그려 시각 모델에 보낸다 (스캔본·도면)

    모드를 안 주면 알아서 고른다: `물음` 이 있으면 찾기, `쪽` 만 있으면 읽기,
    둘 다 없으면 훑기. **"너무 커서 못 읽는다" 고 답하지 마라 -- 이 도구가 그 길이다.**
    """
    if agent_context.is_blocked():
        return "실패: 게스트는 read_pdf 를 사용할 수 없습니다."
    return 자르기(pdfread.부르기(path, 모드=모드, 쪽=쪽, 물음=물음, repo=REPO_DIR),
                셸출력_앞, 셸출력_뒤)


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

    # 단발 경로도 같은 거름망을 거친다 -- `best_available_model` 의 독스트링이 경고하는
    # 바로 그 함정("품질 순위상 pro 가 1순위라 반드시 그걸 고르고 즉시 429 를 맞는다")이다.
    candidates = rpmgate.usable_models(candidates) if not model else candidates
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
            reply = _make_llm(name, api_key, label=label).invoke(prompt)
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
            else:
                # 단발 경로에도 같은 구멍이 있었다 -- 503 만 아무 데도 안 남아서 과부하
                # 중인 최상위 모델을 매 호출마다 다시 1순위로 두드렸다.
                quota_tracker.record_transient(label)
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


class _간격두기(BaseCallbackHandler):
    """**모델을 부르기 직전에 분당 한도만큼 간격을 둔다.**

    왜 콜백인가. 막아야 하는 것은 `agent.invoke()` 한 번이 아니라 그 **안에서** 나가는
    호출 하나하나다. ReAct 루프는 도구를 부를 때마다 모델을 다시 부르므로, 평범한 부탁
    하나가 열 번을 넘게 나간다. 그 자리는 `run_with_fallback_pool` 에서 안 보인다 --
    거기서는 invoke 가 한 번일 뿐이다. 콜백은 **실제 요청 직전**에 같은 스레드에서
    불리므로 여기서 재우면 요청이 그만큼 늦게 나간다.

    쿼터 장부(quota_tracker)와 하는 일이 다르다. 그쪽은 **맞고 난 뒤** 쉬게 하고,
    여기는 **맞기 전에** 간격을 둔다. 둘 다 필요하다 -- 다른 프로세스가 같은 키를 쓰면
    여기서는 안 보이고, 그건 429 를 맞아야 안다.
    """

    def __init__(self, label: str):
        self.label = label

    def _문(self, **_kw):
        잔 = rpmgate.지나가기(self.label)
        if 잔 > 0:
            print(f"[rpmgate] {self.label} 분당 한도가 차서 {잔:.1f}초 쉬고 부른다 "
                  f"(맞기 전에 간격을 둔다)")

    # langchain 은 채팅 모델이면 on_chat_model_start, 아니면 on_llm_start 를 부른다.
    def on_chat_model_start(self, *a, **kw):
        self._문()

    def on_llm_start(self, *a, **kw):
        self._문()


def _make_llm(model: str, key: str, label: "str | None" = None):
    """ChatGoogleGenerativeAI 생성. max_retries/timeout 을 모르는 버전에서도 뜨도록
    TypeError 면 기본 인자만으로 물러선다.

    `label` 은 분당 한도를 세는 단위다((키, 모델) -- 구글이 한도를 거는 단위와 같다).
    안 주면 여기서 짓는다."""
    if label is None:
        label = f"key-{hashlib.sha256((key or '').encode()).hexdigest()[:8]}:{model}"
    콜백 = [_간격두기(label)]
    try:
        return ChatGoogleGenerativeAI(model=model, google_api_key=key,
                                      max_retries=LLM_MAX_RETRIES, timeout=LLM_TIMEOUT,
                                      callbacks=콜백)
    except TypeError:
        try:
            return ChatGoogleGenerativeAI(model=model, google_api_key=key, callbacks=콜백)
        except TypeError:
            # 콜백조차 못 받는 판이면 간격 없이라도 뜬다 -- 조용히 넘기지 않는다.
            print(f"[rpmgate] 이 langchain 판은 callbacks 를 안 받는다 -- {label} 은 "
                  f"간격 없이 나간다(429 를 맞고 나서 quota_tracker 가 푼다)")
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
        # **429 만 주는 후보는 후보가 아니다.** 무료 티어에서 pro 계열의 분당 한도는
        # flash 의 몇 분의 일이라, 끼워 두면 매 메시지가 그것부터 두드리고(품질 순위가
        # 1등이다) 429 를 먹는다. 답도 못 받고 다음 시도만 늦어진다. llm_pool 은 이미
        # 이렇게 거르고 있었는데 이 경로만 안 거쳤다. GEMINI_ALLOW_PRO=1 로 되살린다.
        전 = list(key_models)
        key_models = rpmgate.usable_models(key_models)
        if len(key_models) < len(전):
            print(f"[bot_tools] key-{key_id}: 분당 한도가 너무 낮은 후보 "
                  f"{len(전) - len(key_models)}개를 뺐다 "
                  f"({', '.join(m for m in 전 if m not in key_models)[:120]})")
        for model in key_models:
            label = f"key-{key_id}:{model}"
            # **분당 한도를 세는 단위를 후보 이름과 같게 맞춘다.** 달랐으면 한쪽은
            # 간격을 재고 다른 쪽은 쿨다운을 걸면서 서로 다른 것을 세게 된다.
            llm = _make_llm(model, key, label=label)
            agent = create_react_agent(llm, tools=tools, checkpointer=checkpointer, prompt=prompt)
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
    pin이 갱신된다.

    **순서와 멈춤은 poolpick 이 정한다**(2026-09-21). 이 자리에 세 구멍이 있었다.

      1. 일시 장애(503)가 **아무 데도 안 남았다.** 429 는 소진/쿨다운으로, 404·403 은
         영구 사망으로 남는데 503 만 기록이 없어서, 잔량 가득 + 등급 높은 그 조합이
         **다음 요청에서도 또 1순위**가 됐다. 과부하가 이어지는 동안 매 메시지가 같은
         벽부터 다시 두드렸다 -- 사용자의 물음이 그것이었다("변환을 한거를 계속 안쓰고
         왜 처음부터 다시 찾지?"). 지금은 quota_tracker.record_transient 로 남기고,
         연달아 실패하면 쉬는 시간을 두 배씩 늘린다(성공하면 곧바로 지워진다).
      2. 쿨다운 중인 후보를 **정렬로 뒤로 미룰 뿐 건너뛰지는 않았다.** "지금 안 된다"고
         이미 아는 조합에 실제 호출을 넣고 langchain backoff 로 수십 초를 물었다. 지금은
         쉬는 중이면 아예 안 건다.
      3. **끝이 없었다.** 전부 막히면 전부 한 바퀴 돌고, 그동안 맨 앞 것이 풀려 다음
         메시지가 또 한 바퀴를 돌았다("도저히 멈추지 않아"). 지금은 poolpick.마감초 를
         넘기면 순회를 멈추고, 다 쉬는 중인데 곧 풀릴 것이면 그 하나만 기다리고,
         그것도 아니면 **언제 풀리는지를 적어 사실대로 답한다.**

    poolpick 이 따로 있는 까닭은 검사다 -- 이 모듈은 langchain/discord 를 임포트해서
    에이전트 컨테이너에서 못 부른다. 그래서 여태 이 규칙을 검사한 적이 없었다.
    tests/test_poolpick.py 가 그 자리를 붙든다."""
    pool_id = log_prefix.strip("[]")
    후보 = {}
    for label, agent in candidates:
        후보.setdefault(label, agent)
    labels = list(후보)

    def _등급(label):
        return _model_quality_rank(label.split(":", 1)[1] if ":" in label else label)

    시작 = time.monotonic()
    시도함: "set[str]" = set()
    last_error: Optional[Exception] = None
    마지막쉼: list = []

    while True:
        골 = poolpick.고르기(labels, pool_id, quota_tracker, _등급, 뺄것=시도함)
        마지막쉼 = 골["쉼"]
        차례 = 골["순서"]
        if not 차례:
            # **쉬는 중인 후보를 두드리지 않는다.** 두드려 봐야 backoff 로 수십 초를 물고
            # 같은 429/503 을 다시 받는다. 짧게 풀릴 것이면 기다리는 편이 싸다.
            #
            # 기다림을 **횟수로 세지 않는다.** 한 번만 기다리게 했더니, 그 한 번을 쓴
            # 뒤에는 남은 것이 1초여도 포기하고 사람에게 "1초 남았으니 다시 물어보라"
            # 고 답했다(실측 2026-09-21). 마감(벽시계) 안쪽이면 몇 번이든 기다린다 --
            # 다시 실패한 후보는 쉬는 시간이 두 배로 늘어 저절로 끝이 난다.
            기 = poolpick.기다릴까(마지막쉼, time.monotonic() - 시작)
            if 기 is None:
                break
            쉬는것, 남은 = 기
            print(f"{log_prefix} thread={base_thread_id} 후보가 모두 쉬는 중 -- "
                  f"{쉬는것} 의 쿨다운 {남은:.1f}초를 기다린다 (한 바퀴 더 도는 것보다 싸다)")
            time.sleep(남은 + 0.5)
            시도함.discard(쉬는것)
            continue

        for label in 차례:
            if _is_cancelled(base_thread_id):
                print(f"{log_prefix} thread={base_thread_id} stop 명령으로 후보 순회 중단 "
                      f"({len(시도함)}/{len(labels)}까지 시도함)")
                return (f"[중단됨] stop 명령으로 응답 생성을 멈췄습니다. "
                        f"({len(시도함)}개 후보 시도 후 중단)")
            쓴 = time.monotonic() - 시작
            if 쓴 > poolpick.마감초:
                print(f"{log_prefix} thread={base_thread_id} 순회 마감({쓴:.0f}초) -- 멈춘다")
                시도함.update(차례)
                break
            시도함.add(label)
            try:
                reply = invoke_with_recovery(후보[label], thread_map, base_thread_id,
                                             prompt, f"{log_prefix}[{label}]")
                quota_tracker.record_success(label)
                quota_tracker.set_pinned(pool_id, label)
                if len(시도함) > 1:
                    print(f"{log_prefix} Model have changed {label}")
                    # 왜 느렸는지의 흔한 답이 이것이다 -- 앞 후보들이 막혀 갈아탔다.
                    relay.적기(f"↻ 모델 전환 → {label.split(':', 1)[-1]} "
                              f"(앞 {len(시도함) - 1}개 후보 막힘)")
                return reply
            except Exception as e:
                if not is_unavailable_error(e):
                    raise
                if is_rpm_quota_error(e):
                    # 분당 한도는 1분이면 풀린다 -- 자정까지 봉인하지 말고 잠깐만 쉬게 한다.
                    quota_tracker.record_rpm_cooldown(label)
                    print(f"{log_prefix} thread={base_thread_id} candidate={label} "
                          f"분당 한도(RPM) 초과, {quota_tracker.RPM_COOLDOWN_SECONDS}초 "
                          f"쿨다운 후 복귀 예정 -- 다음 후보로 전환")
                elif is_quota_error(e):
                    quota_tracker.record_exhausted(label)
                    print(f"{log_prefix} thread={base_thread_id} candidate={label} "
                          f"quota exhausted, 다음 후보로 전환")
                elif is_permanent_error(e):
                    quota_tracker.mark_dead(label, str(e)[:200])
                    print(f"{log_prefix} thread={base_thread_id} candidate={label} "
                          f"영구 사용불가로 확정({e}), 앞으로 건너뜀")
                else:
                    # **일시 장애도 기록한다.** 안 남기면 잔량 가득 + 등급 높은 이 조합이
                    # 다음 요청에서도 또 1순위가 되어, 과부하가 이어지는 동안 매 메시지가
                    # 같은 벽부터 다시 두드린다(실측 2026-09-21).
                    쉼 = quota_tracker.record_transient(label)
                    print(f"{log_prefix} thread={base_thread_id} candidate={label} "
                          f"일시 장애({e}), {쉼:.0f}초 쉬게 하고 다음 후보로 전환")
                last_error = e

    if last_error is None and not 시도함:
        raise RuntimeError("후보가 비어있음")
    # 여기까지 왔으면 이번 요청에서는 걸 곳이 없다. **계속 두드리지 않고 사실대로 답한다.**
    print(f"{log_prefix} thread={base_thread_id} 후보 {len(시도함)}개를 다 시도했고 "
          f"남은 곳이 없다 ({time.monotonic() - 시작:.0f}초)")
    if 마지막쉼:
        return poolpick.막힌말(마지막쉼, len(labels))
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
    config = rpmgate.설정(thread_id)
    try:
        result = agent.invoke({"messages": [("user", prompt)]}, config=config)
        relay.턴기록(base_thread_id, result["messages"])
        _간추림(base_thread_id, thread_map, result["messages"])
        return extract_text(result["messages"][-1].content).strip()
    except Exception as e:
        if is_unavailable_error(e):
            raise
        if rpmgate.바퀴넘침(e):
            # **한 메시지 안에서 도는 바퀴에는 끝이 있다.** 여기서 새 thread 로 재시도하면
            # 같은 일을 처음부터 또 돌면서 분당 한도만 두 배로 쓴다. 대화는 남아 있으니
            # 다음 메시지에서 이어가면 된다 -- 사용자에게 그렇게 말한다.
            print(f"{log_prefix} thread={base_thread_id} 바퀴 상한({rpmgate.바퀴상한})에 "
                  f"닿았다 -- 끊는다")
            relay.적기(f"⏹ 한 메시지 안에서 {rpmgate.바퀴상한} 바퀴를 넘겼다 -- 여기서 끊는다")
            # **무엇을 했는지 같이 준다.** 이번 턴에 실제로 돈 셸 줄이 그 증거다.
            돈것 = []
            try:
                돈것 = [줄[0] if isinstance(줄, (list, tuple)) else str(줄)
                      for 줄 in (이번셸() or [])]
            except Exception:                                  # noqa: BLE001
                pass
            return rpmgate.끊긴말(한일=돈것)
        print(f"{log_prefix} thread={base_thread_id} invoke_error={e!r} -- 새 thread로 재시도")
        new_thread_id = f"{base_thread_id}-{uuid.uuid4().hex[:8]}"
        thread_map[base_thread_id] = new_thread_id
        config = rpmgate.설정(new_thread_id)
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
