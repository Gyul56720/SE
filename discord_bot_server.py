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

load_dotenv()

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_SLUG = REPO_DIR.replace("/", "-")
# 채널마다 고정된 세션 ID를 부여해 대화 맥락을 이어간다 (jsonl 경로: ~/.claude/projects/<slug>/<id>.jsonl).
SESSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, f"discord-channel-{CHANNEL_ID}"))

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


@client.event
async def on_ready():
    print(f"[SE-agent] 로그인됨: {client.user} (채널 {CHANNEL_ID} 감시 중)")


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


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id != CHANNEL_ID:
        return
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


if __name__ == "__main__":
    client.run(BOT_TOKEN)
