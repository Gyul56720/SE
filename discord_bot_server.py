"""
Oracle VM에서 systemd로 상시 실행되는 Discord 봇 (실시간 Gateway 연결).

관리 채널(admin, 화이트리스트 있음)과 공개 채널(public, 화이트리스트 없음) 둘 다 이제
Gemini + LangGraph 에이전트로 처리한다 (Claude Code 토큰 소진으로 claude -p에서 전환,
2026-08-27). 공개 채널 로직은 main_public.py로, 두 채널이 공유하는 도구(run_shell,
write_public_answer 등)는 bot_tools.py로 분리했다 -- 이 파일은 admin 에이전트 정의 +
Discord 이벤트 라우팅만 담당한다.

admin/public 둘 다 run_shell(임의 셸 실행) 도구를 가지고 있어 self-modification이
가능하다. public은 화이트리스트가 없어 누구나 트리거할 수 있지만, 이 위험(비밀키 유출,
repo 훼손 가능성)을 사용자가 명시적으로 인지하고 감수하겠다고 요청했다. public은 추가로
write_public_answer로 Public_agent/ 폴더 안에만 결과물을 남길 수도 있다.
API 쿼터를 나누려고 admin은 GEMINI_API_KEY_FALLBACK을, public은 GEMINI_API_KEY를 쓴다.

실행: systemd 유닛(deploy/se-discord-bot.service)으로 등록해서 상시 구동할 것.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path

import discord
from dotenv import load_dotenv

# main_public/bot_tools가 모듈 임포트 시점에 os.environ을 바로 읽으므로, 그것들을 import하기
# 전에 .env를 먼저 로드해야 한다 (실측 확인됨: 순서를 바꾸면 KeyError로 임포트 자체가 실패함).
load_dotenv()

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

import agent_context  # noqa: E402
import agent_memory  # noqa: E402
import gatekeeper  # noqa: E402
import main_public  # noqa: E402
from bot_tools import (  # noqa: E402
    REPO_DIR, run_shell, search_memory, save_memory, build_agent_pool, run_with_fallback_pool,
    register_thread, unregister_thread, request_cancel,
)

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
# 관리자 채널(화이트리스트 있음, DISCORD_ALLOWED_USER_IDS): run_shell 전권 + git sync.
ADMIN_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1542081266315427912"))
ADMIN_ALLOWED_USER_IDS = {int(x) for x in os.getenv("DISCORD_ALLOWED_USER_IDS", "").split(",") if x.strip()}
ADMIN_MODEL_NAME = os.getenv("DISCORD_ADMIN_MODEL", "gemini-3.5-flash-lite")
# GEMINI_MODEL_POOL을 명시하면 그 모델들만 쓴다(수동 제한용). 비워두면 build_agent_pool이
# 키마다 실제 쓸 수 있는 모델 전체를 API로 조회해서 자동으로 순환한다.
_admin_extra_models = [m.strip() for m in os.getenv("GEMINI_MODEL_POOL", "").split(",") if m.strip()]
ADMIN_MODEL_CANDIDATES = [ADMIN_MODEL_NAME] + [m for m in _admin_extra_models if m != ADMIN_MODEL_NAME] \
    if _admin_extra_models else None
# public과 API 쿼터를 분리하려고 별도 fallback 키를 쓴다 -- 한쪽이 무제한 루프를 돌려도(self
# -modification 특성상 발생 가능) 다른 채널까지 같이 막히지 않게. 다만 fallback 키를 못 챙겨서
# 비어있는 채로 배포되면 admin 채널 전체가 KeyError로 기동 자체를 못 하고 죽었다(실측 확인됨,
# 2026-08-27) -- 그래서 없거나 비어있을 땐 GEMINI_API_KEY를 대신 쓴다. 게다가 admin 자기
# 기본 키(FALLBACK)가 429로 소진돼도 public처럼 실시간으로 다른 키/모델로 못 넘어가서 계속
# 막혔었다(실측 확인됨, 2026-08-28) -- 그래서 public과 동일한 (키 x 모델) 후보 풀로 바꿨다.
ADMIN_PRIMARY_KEY = os.getenv("GEMINI_API_KEY_FALLBACK") or os.environ["GEMINI_API_KEY"]
ADMIN_SECONDARY_KEY = os.environ["GEMINI_API_KEY"] if os.getenv("GEMINI_API_KEY_FALLBACK") else None

ADMIN_TOOLS = [run_shell, search_memory, save_memory]
ADMIN_SYSTEM_PROMPT = (
    "너는 이 저장소(SE)를 관리하는 전권을 가진 에이전트다. run_shell로 파일을 읽고 쓰고,\n"
    "git commit/push하고, 네 자신의 코드(discord_bot_server.py, main_public.py, "
    "bot_tools.py 등)를 수정할 수 있다.\n"
    "run_shell 권한은 사용자가 명시적으로 요청한 것이다 -- 에러가 나도 스스로 이 도구를 "
    "제거하거나 권한을 축소하지 마라. 대신 에러 원인을 파악해서 고쳐라.\n"
    "요청받은 작업을 run_shell로 직접 수행하고, 명령 결과를 근거로 다음 행동을 결정하라.\n"
    "코드를 고쳤으면 그 결과를 run_shell로 git add/commit/push까지 해서 반영하라.\n"
    "무엇을 했는지 간결하게 보고하라.\n"
    "\n"
    "[자기 수정 절차 -- 반드시 이 순서로]\n"
    "1. 기존 파일은 전체를 다시 쓰지 마라. 바꿀 줄만 고쳐라. 고친 뒤 git diff --stat의 "
    "삭제 줄 수가 요청 크기와 맞는지 확인하라.\n"
    "2. push 전에 `python3 gatekeeper.py`를 돌려라. 통과(exit 0)해야 커밋된다. "
    "py_compile은 문법만 잡는다 -- 게이트는 임포트 순환, 독스트링 소실, 안전장치 삭제, "
    "자격증명 노출, 대량 삭제를 잡는다.\n"
    "3. 무언가 고장 냈다면 원인을 진단하고, 그 진단을 말로 주장하지 말고 검사 코드로 "
    "써서 `python3 self_challenge.py prove --candidate <검사> --broken-commit <사고커밋>` "
    "으로 증명하라. 고치기 전 코드에서 실패(RED)하고 고친 뒤 통과(GREEN)해야 PROVEN=1 이다. "
    "고치기 전 코드에서 통과해버리면 그건 원인이 아니었다 -- 진단을 다시 세워라.\n"
    "4. PROVEN=1 이면 그 검사는 gates/ 로 승격되어 이후 모든 커밋을 막는다. "
    "증명되지 않은 진단은 메모리 노트로도 남기지 마라 -- 읽히지 않는 노트가 늘어나는 것이 "
    "이 저장소가 실제로 겪은 실패다(2026-08-28: 검증 규칙을 저장하고 2분 뒤 그 규칙을 "
    "어긴 코드를 push했다).\n"
    "5. 보고는 기억이 아니라 git diff 출력을 보고 적어라. 함께 커밋된 파일이 있으면 "
    "요청과 무관해도 보고에 포함하라."
)
_admin_checkpointer = MemorySaver()
ADMIN_AGENT_POOL = build_agent_pool(
    keys=[ADMIN_PRIMARY_KEY, ADMIN_SECONDARY_KEY],
    models=ADMIN_MODEL_CANDIDATES,
    tools=ADMIN_TOOLS,
    prompt=ADMIN_SYSTEM_PROMPT,
    checkpointer=_admin_checkpointer,
    fallback_models=[ADMIN_MODEL_NAME],
)

PROJECT_SLUG = REPO_DIR.replace("/", "-")
# claude -p용 세션 ID. 토큰이 복구되면 run_claude()를 다시 쓸 수 있도록 남겨둔다.
SESSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, f"discord-channel-{ADMIN_CHANNEL_ID}"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# git_sync()가 동시에 여러 번 돌면 커밋/푸시가 충돌하므로 직렬화한다.
GIT_LOCK = asyncio.Lock()

_admin_thread_map: dict[str, str] = {}

# thread_id별 현재 처리 중인 on_message 태스크와 그 프롬프트. "stop" 입력 시 이 태스크만
# 취소한다 -- 서비스(systemd 유닛) 전체를 내리는 게 아니라 그 대화의 응답 대기만 중단한다.
# 주의: run_shell로 이미 시작된 서브프로세스는 취소해도 백그라운드 스레드에서 계속 돌다가
# 자연 종료된다(진짜 kill이 아님) -- 취소는 "그 결과를 기다리지 않고 지금까지 상황을
# 보고한다"는 뜻이다.
_active_tasks: dict[str, asyncio.Task] = {}
_active_prompts: dict[str, str] = {}


async def _handle_stop(message: discord.Message, thread_id: str) -> None:
    task = _active_tasks.get(thread_id)
    if task is None or task.done():
        await message.channel.send("[중단] 현재 진행 중인 요청이 없습니다.")
        return
    prompt = _active_prompts.get(thread_id, "(알 수 없음)")
    # request_cancel: (1) 다음 fallback 후보로 넘어가기 전에 루프를 멈추게 하는 플래그를
    # 세우고, (2) 이 스레드가 run_shell로 이미 띄운 서브프로세스가 있으면 실제로
    # terminate/kill한다 -- proc.wait(timeout=3)이 섞여 있어 이벤트 루프를 막지 않게
    # 실행기(executor)에서 돌린다.
    loop = asyncio.get_running_loop()
    killed = await loop.run_in_executor(None, request_cancel, thread_id)
    task.cancel()
    note = "실행 중이던 run_shell 서브프로세스를 강제 종료했습니다." if killed else \
        "죽일 서브프로세스는 없었고, 다음 모델/키 후보로 넘어가기 전 루프를 멈춥니다(이미 나간 API 요청 자체는 취소 불가)."
    await message.channel.send(
        "[중단됨] 이번 응답 생성을 멈췄습니다. 봇 자체는 계속 실행 중입니다.\n"
        f"진행 중이던 프롬프트: {prompt[:300]}\n"
        f"{note}"
    )


def run_claude(prompt: str) -> str:
    """Claude Code 토큰이 있을 때 쓰던 경로. 지금은 호출되지 않지만 토큰 복구 시 다시
    _handle_admin_message에서 run_admin_agent 대신 이걸 쓰도록 되돌리면 된다."""
    jsonl_path = os.path.expanduser(f"~/.claude/projects/{PROJECT_SLUG}/{SESSION_ID}.jsonl")
    resume_flag = ["--resume", SESSION_ID] if os.path.isfile(jsonl_path) else ["--session-id", SESSION_ID]
    # se-discord-bot.service의 cgroup 밖에서 돌려서, 이 안에서 백그라운드로 뜬 작업이
    # 서비스 재배포(systemctl restart)에 딸려 죽지 않게 한다 (실측 확인됨: cgroup 안에 있으면
    # KillMode=control-group 기본값 때문에 setsid로 분리해도 재배포 시 다 같이 죽었음).
    scope_unit = f"se-claude-{uuid.uuid4().hex[:12]}"
    result = subprocess.run(
        [
            "sudo", "-E", "systemd-run", "--scope", "--quiet", "--collect",
            "--uid=ubuntu", "--gid=ubuntu", f"--unit={scope_unit}",
            "--", "claude", "-p", *resume_flag, "--permission-mode", "bypassPermissions", prompt,
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    return out if out else (err or "(출력 없음)")


def git_sync() -> str | None:
    """작업 트리에 변경이 있으면 커밋 + push. 변경 없으면 None 반환.

    이 VM 말고 다른 곳(예: 개발 세션)에서도 같은 repo에 직접 push할 수 있어서, origin이
    이 VM의 로컬 HEAD보다 앞서 있는 경우(non-fast-forward)가 실제로 발생한다. 그럴 때 단순
    `git push`는 거부되고 그대로 실패만 반환했는데, 그러면 이 VM에서 만든 변경이 origin에
    영영 반영이 안 되고(Obsidian이 못 받아봄) 조용히 로컬에만 쌓이게 된다. 그래서 push가
    non-fast-forward로 거부되면 fetch + rebase 후 한 번 더 시도한다.

    공개/관리 채널 에이전트의 save_memory나 run_shell도 같은 워킹트리에 커밋할 수 있으므로,
    스레드 간에도 통하는 agent_memory.GIT_MUTEX를 함께 잡아서 여러 경로가 동시에 git을
    만지지 않게 한다."""
    with agent_memory.GIT_MUTEX:
        return _git_sync_locked()


def _verify_pushed() -> str:
    """push가 성공 리턴코드를 줬어도 그걸로 끝내지 않고, 로컬 HEAD가 실제로 origin에
    반영됐는지 fetch로 재확인한다.

    2026-08-29 사고: 관리 채널 에이전트가 'requirements.txt에 X 추가하고 커밋했다,
    해시 539e168'이라고 보고했는데 그 해시는 origin 어디에도 없었다. push 성공을 그대로
    믿고 보고하면 로컬에만 쌓인 커밋이나 지어낸 해시를 사용자가 걸러낼 수 없다. 이 저장소
    메모리에 이미 '산출물은 원격 반영까지 확인하고 보고하라'가 있었지만(20260828-190336)
    코드가 강제하지 않아 또 어겨졌다. 그래서 보고 문자열 자체를 fetch 확인 결과로 만든다.

    실제 반영 여부만 보고한다 -- 지어낼 해시가 없다."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
                          capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True, text=True)
    contains = subprocess.run(
        ["git", "branch", "-r", "--contains", head, "origin/main"],
        cwd=REPO_DIR, capture_output=True, text=True,
    )
    short = head[:7]
    if contains.returncode == 0 and "origin/main" in contains.stdout:
        return f"[git push 확인됨] origin/main에 {short} 반영됨. Obsidian에서 pull하면 보입니다."
    return (f"[경고] push는 리턴코드 0이었으나 origin/main에서 {short}를 확인하지 못했다 -- "
            f"원격 반영 실패 가능. 로컬에만 커밋됐을 수 있으니 수동 확인하라.")


# 에이전트가 "저장소에 무언가를 남겼다"고 주장할 때 쓰는 신호어. 이게 응답에 있는데 정작
# 이번 턴에 커밋된 변경이 없으면(git_sync가 None), 주장과 실제 저장소 상태가 어긋난 것이다.
# 2026-08-29에 admin/public 에이전트가 "result.md 저장", "searcher 전면 개편", "history
# 축적"을 보고했지만 원격엔 해당 커밋/파일이 없었다(4회 반복). 메모리 노트로는 못 막혀서
# 봇 레벨에서 실제 원격 상태를 자동 대조해 사용자에게 알린다.
_PERSISTENCE_CLAIM_HINTS = (
    "커밋", "commit", "푸시", "push", "저장했", "저장 완료", "저장하였", "반영",
    "구현했", "구현하였", "생성했", "생성하였", "작성했", "작성하였", "추가했", "추가하였",
    "개편", "수정했", "수정하였", "변경했", "변경하였", "고쳤", "갱신했", "업데이트했",
    "history.jsonl", "result.md", ".py를", ".py에", "파일에 저장",
)


def _claims_persistence(reply: str) -> bool:
    low = reply.lower()
    return any(h.lower() in low for h in _PERSISTENCE_CLAIM_HINTS)


def _remote_status_note() -> str:
    """현재 로컬 HEAD가 원격에 반영돼 있는지, 미커밋 변경이 남아있는지 사실만 보고한다.
    에이전트의 주장이 아니라 저장소의 실제 상태다."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
                          capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True, text=True)
    contains = subprocess.run(["git", "branch", "-r", "--contains", head],
                              cwd=REPO_DIR, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR,
                           capture_output=True, text=True).stdout.strip()
    on_remote = contains.returncode == 0 and "origin/" in contains.stdout
    short = head[:7]
    parts = [f"HEAD {short}"]
    parts.append("원격 반영됨" if on_remote else "⚠️ 원격 미반영")
    parts.append("미커밋 변경 있음" if dirty else "미커밋 변경 없음")
    return "[저장소 상태 자동확인] " + " · ".join(parts)


def _integrity_note(reply: str, sync_note: str | None) -> str | None:
    """에이전트가 저장소에 뭔가 남겼다고 '주장'했는데 이번 턴 git_sync가 아무것도 커밋하지
    않았다면(sync_note is None), 실제 원격 상태를 대조해 붙인다. git_sync가 이미 커밋/차단
    결과를 냈으면(sync_note가 있으면) 그게 진실을 보여주므로 중복하지 않는다."""
    if sync_note is not None:
        return None
    if not _claims_persistence(reply):
        return None
    note = _remote_status_note()
    return (f"{note}\n(에이전트가 저장/커밋을 주장했으나 이번 턴에 커밋된 변경은 없습니다 -- "
            f"위 상태로 실제 반영 여부를 확인하세요.)")


def _git_sync_locked() -> str | None:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR, capture_output=True, text=True)
    if not status.stdout.strip():
        return None

    # 강제 게이트. 에이전트가 메모리 노트를 읽었는지와 무관하게 여기서 막힌다 -- 그것이
    # 요점이다. 2026-08-28에 에이전트는 "push 전에 임포트부터 시켜봐라"를 저장하고 2분 뒤
    # 임포트 불가 코드를 push했다. 진단은 저장소의 마크다운에 있었을 뿐 커밋 경로 위에
    # 없었다. 게이트를 통과 못 하면 커밋하지 않고 위반 목록을 그대로 돌려준다.
    report = gatekeeper.run_gates(Path(REPO_DIR))
    if not report.passed:
        print(f"[git_sync] 게이트 차단 -- 커밋하지 않음\n{report.summary()}")
        return report.summary()

    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
    subprocess.run(
        ["git", "commit", "-m", "SE-agent: Discord 요청 처리 결과 자동 반영"],
        cwd=REPO_DIR, check=True,
    )
    push = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if push.returncode == 0:
        return f"{report.summary()}\n{_verify_pushed()}"

    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True, text=True)
    rebase = subprocess.run(["git", "rebase", "origin/main"], cwd=REPO_DIR, capture_output=True, text=True)
    if rebase.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], cwd=REPO_DIR, capture_output=True, text=True)
        return (f"[git push 실패] origin이 앞서 있어 자동 rebase를 시도했으나 충돌 발생 -- "
                f"수동 확인 필요.\n{push.stderr.strip()}")

    retry = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if retry.returncode != 0:
        return f"[git push 실패] rebase 후에도 실패: {retry.stderr.strip()}"
    return "(rebase 후 재시도) " + _verify_pushed()


def run_admin_agent(prompt: str, thread_id: str) -> str:
    """관리 채널용 -- LangGraph ReAct 에이전트(Gemini, run_shell 전권)로 답한다."""
    print(f"[admin-agent] thread={thread_id} prompt={prompt[:120]!r}")
    # stop 명령이 이 스레드가 띄운 run_shell 서브프로세스를 죽이고 fallback 루프를 멈출 수
    # 있도록, 지금 실행 중인 OS 스레드를 discord thread_id에 등록해둔다.
    register_thread(thread_id)
    try:
        reply = run_with_fallback_pool(ADMIN_AGENT_POOL, _admin_thread_map, thread_id, prompt, "[admin-agent]")
        print(f"[admin-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        print(f"[admin-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류) {e}"
    finally:
        unregister_thread(thread_id)


@client.event
async def on_ready():
    print(
        f"[SE-agent] 로그인됨: {client.user} "
        f"(관리 채널 {ADMIN_CHANNEL_ID}, 공개 채널 {main_public.PUBLIC_CHANNEL_ID} 감시 중)"
    )


ATTACHMENTS_DIR = os.path.join(REPO_DIR, "inbox", "discord_attachments")


async def _save_attachments(message: discord.Message) -> list[str]:
    """스크린샷 등 첨부파일을 로컬에 저장하고 절대경로 목록을 반환한다.
    에이전트는 텍스트 프롬프트만 받으므로, 이미지 자체를 전달할 방법이 없다 -- 대신 파일로
    저장한 뒤 그 경로를 프롬프트에 적어주면 run_shell(cat 등)로 직접 열어볼 수 있다."""
    if not message.attachments:
        return []
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    saved_paths = []
    for att in message.attachments:
        safe_name = f"{message.id}_{att.filename}"
        path = os.path.join(ATTACHMENTS_DIR, safe_name)
        await att.save(path)
        saved_paths.append(path)
    return saved_paths


async def _handle_admin_message(message: discord.Message) -> None:
    """관리 채널: Gemini+LangGraph 에이전트(run_shell 전권) + git sync."""
    if ADMIN_ALLOWED_USER_IDS and message.author.id not in ADMIN_ALLOWED_USER_IDS:
        return
    content = message.content.strip()
    thread_id = f"admin-{message.author.id}"

    if content.lower() == "stop":
        await _handle_stop(message, thread_id)
        return

    attachment_paths = await _save_attachments(message)
    if not content and not attachment_paths:
        return
    if attachment_paths:
        attachments_note = "\n\n첨부 파일(로컬 경로, run_shell로 cat/열어볼 것):\n" + "\n".join(
            f"- {p}" for p in attachment_paths
        )
        content = (content or "(첨부파일 확인)") + attachments_note

    loop = asyncio.get_running_loop()
    _active_tasks[thread_id] = asyncio.current_task()
    _active_prompts[thread_id] = content
    try:
        async with message.channel.typing():
            reply = await loop.run_in_executor(None, run_admin_agent, content, thread_id)
            # 게스트 보안 정책: 차단 목록(agent_context.BLOCKED_USER_IDS, 환경변수
            # GUEST_BLOCKED_USER_IDS로 지정)에 든 사용자는 git sync를 타지 않는다.
            if agent_context.is_blocked(message.author.id):
                sync_note = "[보안 제한] 게스트 사용자의 Git 접근이 제한되었습니다."
            else:
                async with GIT_LOCK:
                    sync_note = await loop.run_in_executor(None, git_sync)
            async with GIT_LOCK:
                integrity_note = await loop.run_in_executor(None, _integrity_note, reply, sync_note)
    except asyncio.CancelledError:
        # "stop"으로 취소됨 -- _handle_stop이 이미 상태 메시지를 보냈으므로 조용히 반환한다.
        return
    finally:
        _active_tasks.pop(thread_id, None)
        _active_prompts.pop(thread_id, None)

    for chunk_start in range(0, len(reply), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)
    if integrity_note:
        await message.channel.send(integrity_note)


async def _handle_public_message(message: discord.Message) -> None:
    """공개 채널: 화이트리스트 없음 -- main_public.py의 에이전트(run_shell 포함)로 답한다.
    유저별로 대화 맥락이 이어진다."""
    content = message.content.strip()
    if not content:
        return

    thread_id = str(message.author.id)

    if content.lower() == "stop":
        await _handle_stop(message, thread_id)
        return

    loop = asyncio.get_running_loop()
    _active_tasks[thread_id] = asyncio.current_task()
    _active_prompts[thread_id] = content
    try:
        async with message.channel.typing():
            reply = await loop.run_in_executor(None, main_public.run_public_agent, content, thread_id)
            # 게스트 보안 정책: 차단 목록(agent_context.BLOCKED_USER_IDS, 환경변수
            # GUEST_BLOCKED_USER_IDS로 지정)에 든 사용자는 git sync를 타지 않는다.
            if agent_context.is_blocked(message.author.id):
                sync_note = "[보안 제한] 게스트 사용자의 Git 접근이 제한되었습니다."
            else:
                async with GIT_LOCK:
                    sync_note = await loop.run_in_executor(None, git_sync)
            async with GIT_LOCK:
                integrity_note = await loop.run_in_executor(None, _integrity_note, reply, sync_note)
    except asyncio.CancelledError:
        return
    finally:
        _active_tasks.pop(thread_id, None)
        _active_prompts.pop(thread_id, None)

    for chunk_start in range(0, len(reply), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)
    if integrity_note:
        await message.channel.send(integrity_note)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id == ADMIN_CHANNEL_ID:
        await _handle_admin_message(message)
    elif message.channel.id == main_public.PUBLIC_CHANNEL_ID:
        await _handle_public_message(message)


if __name__ == "__main__":
    client.run(BOT_TOKEN)
