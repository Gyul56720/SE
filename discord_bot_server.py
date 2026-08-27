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

import discord
from dotenv import load_dotenv

# main_public/bot_tools가 모듈 임포트 시점에 os.environ을 바로 읽으므로, 그것들을 import하기
# 전에 .env를 먼저 로드해야 한다 (실측 확인됨: 순서를 바꾸면 KeyError로 임포트 자체가 실패함).
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402

import agent_memory  # noqa: E402
import main_public  # noqa: E402
from bot_tools import REPO_DIR, run_shell, search_memory, save_memory, invoke_with_recovery  # noqa: E402

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
# 관리자 채널(화이트리스트 있음, DISCORD_ALLOWED_USER_IDS): run_shell 전권 + git sync.
ADMIN_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1542081266315427912"))
ADMIN_ALLOWED_USER_IDS = {int(x) for x in os.getenv("DISCORD_ALLOWED_USER_IDS", "").split(",") if x.strip()}
ADMIN_MODEL_NAME = os.getenv("DISCORD_ADMIN_MODEL", "gemini-3.5-flash-lite")
# public과 API 쿼터를 분리하려고 별도 fallback 키를 쓴다 -- 한쪽이 무제한 루프를 돌려도(self
# -modification 특성상 발생 가능) 다른 채널까지 같이 막히지 않게. 다만 fallback 키를 못 챙겨서
# 비어있는 채로 배포되면 admin 채널 전체가 KeyError로 기동 자체를 못 하고 죽었다(실측 확인됨,
# 2026-08-27) -- 이러면 정작 API 문제를 고쳐야 할 admin 에이전트가 죽어서 아무것도 못 하게
# 되므로, 없거나 비어있을 땐 크래시 대신 GEMINI_API_KEY를 그대로 재사용한다(쿼터 분리 이점은
# 없어지지만 admin 채널은 최소한 살아있게).
ADMIN_GEMINI_KEY = os.getenv("GEMINI_API_KEY_FALLBACK") or os.environ["GEMINI_API_KEY"]

ADMIN_TOOLS = [run_shell, search_memory, save_memory]
ADMIN_SYSTEM_PROMPT = (
    "너는 이 저장소(SE)를 관리하는 전권을 가진 에이전트다. run_shell로 파일을 읽고 쓰고,\n"
    "git commit/push하고, 네 자신의 코드(discord_bot_server.py, main_public.py, "
    "bot_tools.py 등)를 수정할 수 있다.\n"
    "run_shell 권한은 사용자가 명시적으로 요청한 것이다 -- 에러가 나도 스스로 이 도구를 "
    "제거하거나 권한을 축소하지 마라. 대신 에러 원인을 파악해서 고쳐라.\n"
    "요청받은 작업을 run_shell로 직접 수행하고, 명령 결과를 근거로 다음 행동을 결정하라.\n"
    "코드를 고쳤으면 그 결과를 run_shell로 git add/commit/push까지 해서 반영하라.\n"
    "무엇을 했는지 간결하게 보고하라."
)
_admin_llm = ChatGoogleGenerativeAI(model=ADMIN_MODEL_NAME, google_api_key=ADMIN_GEMINI_KEY)
ADMIN_AGENT = create_react_agent(
    _admin_llm, tools=ADMIN_TOOLS, checkpointer=MemorySaver(), prompt=ADMIN_SYSTEM_PROMPT,
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


def _git_sync_locked() -> str | None:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR, capture_output=True, text=True)
    if not status.stdout.strip():
        return None
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
    subprocess.run(
        ["git", "commit", "-m", "SE-agent: Discord 요청 처리 결과 자동 반영"],
        cwd=REPO_DIR, check=True,
    )
    push = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if push.returncode == 0:
        return "[git push 완료] Obsidian에서 pull하면 반영됩니다."

    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True, text=True)
    rebase = subprocess.run(["git", "rebase", "origin/main"], cwd=REPO_DIR, capture_output=True, text=True)
    if rebase.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], cwd=REPO_DIR, capture_output=True, text=True)
        return (f"[git push 실패] origin이 앞서 있어 자동 rebase를 시도했으나 충돌 발생 -- "
                f"수동 확인 필요.\n{push.stderr.strip()}")

    retry = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if retry.returncode != 0:
        return f"[git push 실패] rebase 후에도 실패: {retry.stderr.strip()}"
    return "[git push 완료 (rebase 후 재시도)] Obsidian에서 pull하면 반영됩니다."


def run_admin_agent(prompt: str, thread_id: str) -> str:
    """관리 채널용 -- LangGraph ReAct 에이전트(Gemini, run_shell 전권)로 답한다."""
    print(f"[admin-agent] thread={thread_id} prompt={prompt[:120]!r}")
    try:
        reply = invoke_with_recovery(ADMIN_AGENT, _admin_thread_map, thread_id, prompt, "[admin-agent]")
        print(f"[admin-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        print(f"[admin-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류) {e}"


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
    attachment_paths = await _save_attachments(message)
    if not content and not attachment_paths:
        return
    if attachment_paths:
        attachments_note = "\n\n첨부 파일(로컬 경로, run_shell로 cat/열어볼 것):\n" + "\n".join(
            f"- {p}" for p in attachment_paths
        )
        content = (content or "(첨부파일 확인)") + attachments_note

    loop = asyncio.get_running_loop()
    thread_id = f"admin-{message.author.id}"
    async with message.channel.typing():
        reply = await loop.run_in_executor(None, run_admin_agent, content, thread_id)
        async with GIT_LOCK:
            sync_note = await loop.run_in_executor(None, git_sync)

    for chunk_start in range(0, len(reply), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)


async def _handle_public_message(message: discord.Message) -> None:
    """공개 채널: 화이트리스트 없음 -- main_public.py의 에이전트(run_shell 포함)로 답한다.
    유저별로 대화 맥락이 이어진다."""
    content = message.content.strip()
    if not content:
        return

    loop = asyncio.get_running_loop()
    thread_id = str(message.author.id)
    async with message.channel.typing():
        reply = await loop.run_in_executor(None, main_public.run_public_agent, content, thread_id)
        async with GIT_LOCK:
            sync_note = await loop.run_in_executor(None, git_sync)

    for chunk_start in range(0, len(reply), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)


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
