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

import os
import subprocess
import uuid

import discord
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
ALLOWED_USER_IDS = {int(x) for x in os.getenv("DISCORD_ALLOWED_USER_IDS", "").split(",") if x.strip()}
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_SLUG = REPO_DIR.replace("/", "-")
# 채널마다 고정된 세션 ID를 부여해 대화 맥락을 이어간다 (jsonl 경로: ~/.claude/projects/<slug>/<id>.jsonl).
SESSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, f"discord-channel-{CHANNEL_ID}"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


def run_claude(prompt: str) -> str:
    jsonl_path = os.path.expanduser(f"~/.claude/projects/{PROJECT_SLUG}/{SESSION_ID}.jsonl")
    resume_flag = ["--resume", SESSION_ID] if os.path.isfile(jsonl_path) else ["--session-id", SESSION_ID]
    result = subprocess.run(
        ["claude", "-p", *resume_flag, "--permission-mode", "bypassPermissions", prompt],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    return out if out else (err or "(출력 없음)")


def git_sync() -> str | None:
    """작업 트리에 변경이 있으면 커밋 + push. 변경 없으면 None 반환."""
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR, capture_output=True, text=True)
    if not status.stdout.strip():
        return None
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
    subprocess.run(
        ["git", "commit", "-m", "SE-agent: Discord 요청 처리 결과 자동 반영"],
        cwd=REPO_DIR, check=True,
    )
    push = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if push.returncode != 0:
        return f"[git push 실패] {push.stderr.strip()}"
    return "[git push 완료] Obsidian에서 pull하면 반영됩니다."


@client.event
async def on_ready():
    print(f"[SE-agent] 로그인됨: {client.user} (채널 {CHANNEL_ID} 감시 중)")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id != CHANNEL_ID:
        return
    if message.author.id not in ALLOWED_USER_IDS:
        return
    content = message.content.strip()
    if not content:
        return

    async with message.channel.typing():
        reply = run_claude(content)
        sync_note = git_sync()

    for chunk_start in range(0, len(reply), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)


if __name__ == "__main__":
    client.run(BOT_TOKEN)
