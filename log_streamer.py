"""
se-discord-bot 서비스 로그를 실시간으로 Discord 채널(DISCORD_LOG_CHANNEL_ID)에 중계한다.

journalctl -f를 그대로 Discord로 흘려보내는 순수 인프라 스크립트 -- Claude/Gemini API
호출이 전혀 없으므로 토큰을 전혀 쓰지 않는다. se-discord-bot.service와 별개인
se-log-streamer.service로 떠서, 봇이 재배포로 재시작돼도 로그 스트리머는 안 죽는다.

실행: systemd 유닛(deploy/se-log-streamer.service)으로 등록해서 상시 구동할 것.
"""

from __future__ import annotations

import os
import re
import subprocess
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
LOG_CHANNEL_ID = os.environ["DISCORD_LOG_CHANNEL_ID"]
UNIT = "se-discord-bot"

API_BASE = "https://discord.com/api/v10"
HEADERS = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}

# claude -p가 오래 걸리는 동안 discord.gateway가 10~60초마다 같은 트레이스백을 반복
# 출력하던 노이즈를 걸러낸다 (실측 확인됨, run_claude()가 executor로 옮겨간 뒤로는
# 줄었지만 여전히 발생 가능한 패턴이라 계속 필터링한다).
NOISE_PATTERNS = [re.compile(p) for p in [
    r'File "',
    r"await coro",
    r"self\._context\.run",
    r"self\.run_forever\(\)",
    r"self\._run_once\(\)",
    r"handle\._run\(\)",
    r"ready = selector\.select",
    r"fd_event_list = self\._selector\.poll",
    r"Loop thread traceback",
    r"asyncio\.run\(runner\(\)\)",
    r"return runner\.run\(main\)",
    r"return self\._loop\.run_until_complete\(task\)",
    r"stdout, stderr = process\.communicate",
    r"stdout, stderr = self\._communicate",
    r"result = subprocess\.run\(",
    r"^\s*\^+\s*$",
]]

BATCH_INTERVAL = 4.0
MAX_MSG_LEN = 1900


def is_noise(line: str) -> bool:
    return any(p.search(line) for p in NOISE_PATTERNS)


def send_to_discord(text: str) -> None:
    text = text.strip()
    if not text:
        return
    for start in range(0, len(text), MAX_MSG_LEN):
        chunk = text[start:start + MAX_MSG_LEN]
        body = {"content": f"```\n{chunk}\n```"}
        for _attempt in range(3):
            try:
                resp = requests.post(
                    f"{API_BASE}/channels/{LOG_CHANNEL_ID}/messages",
                    headers=HEADERS, json=body, timeout=10,
                )
            except requests.RequestException:
                time.sleep(2.0)
                continue
            if resp.status_code == 429:
                retry_after = 1.0
                try:
                    retry_after = float(resp.json().get("retry_after", 1.0))
                except Exception:
                    pass
                time.sleep(retry_after + 0.5)
                continue
            break


def main() -> None:
    proc = subprocess.Popen(
        ["journalctl", "-u", UNIT, "-f", "-n", "0", "--no-pager", "-o", "cat"],
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    buffer: list[str] = []
    last_flush = time.time()
    send_to_discord("[log-streamer] 실시간 로그 스트리밍 시작됨.")
    while True:
        line = proc.stdout.readline()
        if line:
            line = line.rstrip("\n")
            if line and not is_noise(line):
                buffer.append(line)
        now = time.time()
        should_flush = buffer and (now - last_flush >= BATCH_INTERVAL or not line)
        if should_flush:
            send_to_discord("\n".join(buffer))
            buffer.clear()
            last_flush = now
        if not line:
            time.sleep(0.5)


if __name__ == "__main__":
    main()
