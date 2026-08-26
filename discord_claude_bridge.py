"""
폰 Discord DM -> GitHub Actions(클라우드) Claude Code 브릿지.

동작:
  1. 화이트리스트 유저의 DM 채널을 폴링 (REST, gateway 불필요)
  2. 새 메시지 오면 GitHub Actions workflow_dispatch로 트리거
     (`gh workflow run discord-agent.yml`) -> 클라우드 러너에서 repo 체크아웃 후
     `claude -p` 실행
  3. 워크플로 자체가 끝나면 Discord로 직접 회신 (이 프로세스는 결과를 기다리지 않음)

주의:
  - 로컬 맥은 이 폴링 루프만 돌리면 됨 (가벼움). 실제 agent 실행은 클라우드에서.
  - 클라우드 러너는 매 실행마다 새 컨테이너 -> 대화 세션 연속성 없음 (매번 새 대화).
  - 클라우드 워크플로는 `--permission-mode bypassPermissions`로 돎 (승인 물어볼 사람 없어서).
    ephemeral 컨테이너 + 이 repo 범위로 blast radius 한정됨.
  - 이 프로세스 켜져 있는 동안만 트리거 가능. 종료하면 브릿지 끊김.
"""

import os
import time
import subprocess
import requests

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
REPO = "Gyul56720/SE"
WORKFLOW = "se-agent.yml"


def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
BOT_TOKEN = ENV["DISCORD_BOT_TOKEN"]
ALLOWED_IDS = {x.strip() for x in ENV["DISCORD_ALLOWED_USER_IDS"].split(",") if x.strip()}
API = "https://discord.com/api/v10"
HEADERS = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
POLL_SECONDS = 3


def open_dm(user_id: str) -> str:
    r = requests.post(f"{API}/users/@me/channels", headers=HEADERS, json={"recipient_id": user_id})
    r.raise_for_status()
    return r.json()["id"]


def send(channel_id: str, content: str):
    for i in range(0, len(content), 1900):
        chunk = content[i:i + 1900] or "(빈 응답)"
        requests.post(f"{API}/channels/{channel_id}/messages", headers=HEADERS, json={"content": chunk})


def trigger_cloud_agent(prompt: str, channel_id: str) -> str:
    """GitHub Actions workflow_dispatch 트리거. 결과는 워크플로가 직접 Discord로 회신."""
    cmd = [
        "gh", "workflow", "run", WORKFLOW,
        "--repo", REPO,
        "-f", f"prompt={prompt}",
        "-f", f"channel_id={channel_id}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"트리거 실패: {result.stderr.strip()}"
        return "클라우드 실행 시작함, 완료되면 회신 옴 (보통 1~2분)."
    except Exception as e:
        return f"트리거 오류: {e}"


def main():
    channels = {uid: open_dm(uid) for uid in ALLOWED_IDS}
    last_seen = {}
    for uid, ch in channels.items():
        r = requests.get(f"{API}/channels/{ch}/messages?limit=1", headers=HEADERS)
        msgs = r.json()
        last_seen[ch] = msgs[0]["id"] if msgs else "0"

    print(f"브릿지 시작. 감시 대상: {list(ALLOWED_IDS)}")

    while True:
        for uid, ch in channels.items():
            r = requests.get(
                f"{API}/channels/{ch}/messages?after={last_seen[ch]}&limit=20",
                headers=HEADERS,
            )
            if r.status_code != 200:
                time.sleep(POLL_SECONDS)
                continue
            msgs = sorted(r.json(), key=lambda m: int(m["id"]))
            for m in msgs:
                last_seen[ch] = m["id"]
                if m["author"]["id"] != uid:
                    continue  # 봇 자기 메시지 무시
                content = m["content"].strip()
                if not content:
                    continue
                print(f"[수신] {uid}: {content}")
                ack = trigger_cloud_agent(content, ch)
                print(f"[ack] {ack}")
                send(ch, ack)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
