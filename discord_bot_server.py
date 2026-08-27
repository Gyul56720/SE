"""
Oracle VM에서 systemd로 상시 실행되는 Discord 봇 (실시간 Gateway 연결).

기존 .github/workflows/se-agent.yml은 GitHub Actions cron(5분 폴링)으로 동작했으나,
1) 5분 지연이 있고 2) repo가 60일 이상 비활성이면 GitHub이 스케줄을 자동 정지시키는
한계가 있었다. 이 스크립트는 그 대신 상시 실행 서버(Oracle 무료 티어)에서 discord.py의
실시간 Gateway로 메시지를 즉시 받아 처리한다.

허용된 사용자가 메시지를 보내면:
1) `claude -p` CLI를 호출해 요청을 처리시킨다(기존 se-agent.yml과 동일한 방식).
2) 이 저장소(project_furiosa/ 등)에 변경이 생겼으면 자동으로 git commit + push한다.
   -> Obsidian은 obsidian-git 플러그인으로 이 repo를 pull만 하면 되므로, 로컬/iCloud
   작업 없이 서버 -> git -> Obsidian(뷰어)로 파이프라인이 끝난다.
3) 처리 결과를 Discord에 그대로 답장한다.

실행: systemd 유닛(deploy/se-discord-bot.service)으로 등록해서 상시 구동할 것.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid

import discord
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
# 관리자 채널(DM): claude -p 전체 권한 + git sync -- 서버 관리/코드 작업/질의응답 전용.
ADMIN_CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
# 공개 채널(길드, 화이트리스트 없음): claude 토큰을 아끼려고 LangGraph 에이전트로만 답한다 --
# 셸/git 접근 없음, 도구도 없음(추론+대화 메모리만). 백엔드는 openai/gpt-oss-120b(Apache-2.0
# 오픈웨이트, Groq에서 호스팅) -- gemini-3.5-flash-lite는 속도/비용 최적화 경량 모델이라
# 추론력에서 gpt-oss-120b(추론 특화 설계, MoE)가 더 낫다고 판단해 교체함
# (groq_client.py가 이미 이 모델을 검증해 쓰고 있었음).
PUBLIC_CHANNEL_ID = int(os.environ["DISCORD_PUBLIC_CHANNEL_ID"])
PUBLIC_MODEL_NAME = os.getenv("DISCORD_PUBLIC_MODEL", "openai/gpt-oss-120b")

# ReAct 에이전트: 도구는 아직 없지만(공개 채널이라 셸/파일 접근 도구는 의도적으로 안 붙임),
# LangGraph의 사고 루프 + MemorySaver 대화 메모리로 모델 혼자 쓸 때보다 다단계 추론이 낫다.
# thread_id는 Discord 유저 ID로 둬서 사람마다 대화 맥락을 분리한다.
_public_llm = ChatGroq(model=PUBLIC_MODEL_NAME, groq_api_key=os.environ["GROQ_API_KEY"])
# 시스템 프롬프트를 안 주면 Gemini 기본 말투(이모지, 인사치레, 상투적 격려 문구)로 답해서
# 출력 토큰을 불필요하게 먹는다 -- 간결하게 답하도록 명시한다.
PUBLIC_SYSTEM_PROMPT = (
    "간결하게 답하라. 이모지, 인사말, 상투적 격려/감탄 문구를 쓰지 마라. "
    "핵심 정보만 정확하게 전달하고 불필요한 수식어를 붙이지 마라."
)
PUBLIC_AGENT = create_react_agent(
    _public_llm, tools=[], checkpointer=MemorySaver(), prompt=PUBLIC_SYSTEM_PROMPT,
)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_SLUG = REPO_DIR.replace("/", "-")
# 채널마다 고정된 세션 ID를 부여해 대화 맥락을 이어간다 (jsonl 경로: ~/.claude/projects/<slug>/<id>.jsonl).
SESSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, f"discord-channel-{ADMIN_CHANNEL_ID}"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# git_sync()가 동시에 여러 번 돌면 커밋/푸시가 충돌하므로 직렬화한다.
GIT_LOCK = asyncio.Lock()


def run_claude(prompt: str) -> str:
    """동기 블로킹 호출 -- 반드시 run_in_executor로 감싸서 불러야 이벤트 루프가 안 막힌다."""
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
    non-fast-forward로 거부되면 fetch + rebase 후 한 번 더 시도한다."""
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


def _extract_text(content) -> str:
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


def run_public_agent(prompt: str, thread_id: str) -> str:
    """공개 채널용 -- LangGraph ReAct 에이전트(Gemini, 도구 없음)로 답한다.
    thread_id별로 대화가 분리되어 이어진다 (MemorySaver, 프로세스 재시작 시 초기화됨).

    subprocess 없이 순수 인프로세스 호출이라 claude -p/git처럼 stdout이 저절로 journal에
    안 새어나간다 (실측 확인됨: 호출해도 journalctl에 아무 흔적이 안 남았었음) -- 그래서
    print()로 명시적으로 남겨야 log_streamer.py가 중계할 게 생긴다."""
    print(f"[public-agent] thread={thread_id} prompt={prompt[:120]!r}")
    try:
        config = {"configurable": {"thread_id": thread_id}}
        result = PUBLIC_AGENT.invoke({"messages": [("user", prompt)]}, config=config)
        reply = _extract_text(result["messages"][-1].content).strip()
        print(f"[public-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        print(f"[public-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류) {e}"


@client.event
async def on_ready():
    print(f"[SE-agent] 로그인됨: {client.user} (관리 채널 {ADMIN_CHANNEL_ID}, 공개 채널 {PUBLIC_CHANNEL_ID} 감시 중)")


ATTACHMENTS_DIR = os.path.join(REPO_DIR, "inbox", "discord_attachments")


async def _save_attachments(message: discord.Message) -> list[str]:
    """스크린샷 등 첨부파일을 로컬에 저장하고 절대경로 목록을 반환한다.
    claude -p는 텍스트 프롬프트만 받으므로, 이미지 자체를 전달할 방법이 없다 -- 대신 파일로
    저장한 뒤 그 경로를 프롬프트에 적어주면 Claude가 Read 도구로 직접 열어볼 수 있다."""
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
    """관리 채널: claude -p 전체 권한 + git sync (기존 동작 그대로)."""
    content = message.content.strip()
    attachment_paths = await _save_attachments(message)
    if not content and not attachment_paths:
        return
    if attachment_paths:
        attachments_note = "\n\n첨부 파일(로컬 경로, Read 도구로 열어볼 것):\n" + "\n".join(
            f"- {p}" for p in attachment_paths
        )
        content = (content or "(첨부파일 확인)") + attachments_note

    loop = asyncio.get_running_loop()
    async with message.channel.typing():
        reply = await loop.run_in_executor(None, run_claude, content)
        async with GIT_LOCK:
            sync_note = await loop.run_in_executor(None, git_sync)

    for chunk_start in range(0, len(reply), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)


async def _handle_public_message(message: discord.Message) -> None:
    """공개 채널: 화이트리스트 없음 -- 셸/git 접근 없이 LangGraph+Gemini 에이전트로만 답해서
    claude 토큰을 아낀다. 유저별로 대화 맥락이 이어진다."""
    content = message.content.strip()
    if not content:
        return

    loop = asyncio.get_running_loop()
    thread_id = str(message.author.id)
    async with message.channel.typing():
        reply = await loop.run_in_executor(None, run_public_agent, content, thread_id)

    for chunk_start in range(0, len(reply), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id == ADMIN_CHANNEL_ID:
        await _handle_admin_message(message)
    elif message.channel.id == PUBLIC_CHANNEL_ID:
        await _handle_public_message(message)


if __name__ == "__main__":
    client.run(BOT_TOKEN)
