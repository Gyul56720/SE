"""
Oracle VM에서 systemd로 상시 실행되는 Discord 봇 (실시간 Gateway 연결).

관리 채널(admin, 화이트리스트 있음)과 공개 채널(public, 화이트리스트 없음) 둘 다 이제
Gemini + LangGraph 에이전트로 처리한다.

[보안 업데이트 2026-08-28]:
게스트 김희섭(ID: 249746307877437450)에 대한 Git 접근 제한 정책 적용.
공개 채널에서 해당 게스트의 Git 관련 명령(push/pull 등)을 원천 차단하고 답변만 제공.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid

import discord
from dotenv import load_dotenv

load_dotenv()

from langgraph.checkpoint.memory import MemorySaver

import agent_memory
import main_public
from bot_tools import (
    REPO_DIR, run_shell, search_memory, save_memory, build_agent_pool, run_with_fallback_pool,
)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ADMIN_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1542081266315427912"))
ADMIN_ALLOWED_USER_IDS = {int(x) for x in os.getenv("DISCORD_ALLOWED_USER_IDS", "").split(",") if x.strip()}
ADMIN_MODEL_NAME = os.getenv("DISCORD_ADMIN_MODEL", "gemini-3.5-flash-lite")

GIT_LOCK = asyncio.Lock()

def git_sync() -> str:
    """주기적인 변경 사항 자동 반영."""
    pull = subprocess.run(["git", "pull", "--ff-only", "origin", "main"], cwd=REPO_DIR, capture_output=True, text=True)
    if pull.returncode == 0:
        return ""
    
    # 충돌 시 rebase 시도
    subprocess.run(["git", "rebase", "--abort"], cwd=REPO_DIR, capture_output=True)
    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True)
    rebase = subprocess.run(["git", "rebase", "origin/main"], cwd=REPO_DIR, capture_output=True, text=True)
    
    if rebase.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], cwd=REPO_DIR, capture_output=True)
        return (f"[git push 실패] 충돌 발생 -- 수동 확인 필요.\n{rebase.stderr.strip()}")

    retry = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if retry.returncode != 0:
        return f"[git push 실패] rebase 후에도 실패: {retry.stderr.strip()}"
    return "[git push 완료 (rebase 후 재시도)]"

def run_admin_agent(prompt: str, thread_id: str) -> str:
    return run_with_fallback_pool(None, {}, thread_id, prompt, "[admin-agent]")

@client.event
async def on_ready():
    print(f"[SE-agent] 로그인됨: {client.user}")

async def _handle_admin_message(message: discord.Message) -> None:
    if ADMIN_ALLOWED_USER_IDS and message.author.id not in ADMIN_ALLOWED_USER_IDS:
        return
    
    content = message.content.strip()
    loop = asyncio.get_running_loop()
    thread_id = f"admin-{message.author.id}"
    
    async with message.channel.typing():
        reply = await loop.run_in_executor(None, run_admin_agent, content, thread_id)
        async with GIT_LOCK:
            sync_note = await loop.run_in_executor(None, git_sync)

    await message.channel.send(reply[:1900])
    if sync_note: await message.channel.send(sync_note)

async def _handle_public_message(message: discord.Message) -> None:
    content = message.content.strip()
    if not content: return

    # 게스트 보안 정책: 김희섭(249746307877437450) Git 제한
    is_guest_restricted = (message.author.id == 249746307877437450)
    
    loop = asyncio.get_running_loop()
    thread_id = str(message.author.id)
    
    async with message.channel.typing():
        # main_public 로직 수정 필요시 여기를 통제
        reply = await loop.run_in_executor(None, main_public.run_public_agent, content, thread_id)
        
        # 게스트인 경우 Git 동기화 무시
        if not is_guest_restricted:
            async with GIT_LOCK:
                sync_note = await loop.run_in_executor(None, git_sync)
        else:
            sync_note = None

    await message.channel.send(reply[:1900])
    if sync_note: await message.channel.send(sync_note)

@client.event
async def on_message(message: discord.Message):
    if message.author.bot: return
    if message.channel.id == ADMIN_CHANNEL_ID:
        await _handle_admin_message(message)
    elif message.channel.id == main_public.PUBLIC_CHANNEL_ID:
        await _handle_public_message(message)

client = discord.Client(intents=discord.Intents.default())
client.run(BOT_TOKEN)
