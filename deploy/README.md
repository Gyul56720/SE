# Oracle VM 배포 가이드

`se-discord-bot.service`를 Oracle 무료 티어 VM에서 systemd로 상시 실행해서,
기존 `.github/workflows/se-agent.yml`(5분 폴링)을 실시간 Discord Gateway 봇으로 대체한다.

## 1. Oracle VM에서 최초 1회 (수동)

```bash
sudo apt update && sudo apt install -y python3 python3-pip git
git clone https://github.com/Gyul56720/SE.git /home/ubuntu/SE
cd /home/ubuntu/SE
pip3 install -r requirements.txt discord.py

# Claude Code CLI 설치 (Node.js 필요)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
npm install -g @anthropic-ai/claude-code
claude setup-token   # CLAUDE_CODE_OAUTH_TOKEN 발급 절차 (콘솔 안내 따라 진행)

cp .env.example .env
# .env에 GEMINI_API_KEY / DISCORD_BOT_TOKEN / DISCORD_CHANNEL_ID /
# DISCORD_ALLOWED_USER_IDS / CLAUDE_CODE_OAUTH_TOKEN 채우기

sudo cp deploy/se-discord-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now se-discord-bot
sudo systemctl status se-discord-bot
```

git push가 되려면 VM에 GitHub 쓰기 권한이 있는 자격증명(예: `gh auth login` 또는
`git remote set-url origin https://<PAT>@github.com/Gyul56720/SE.git`)이 한 번 설정돼 있어야 한다.

## 2. 이후 코드 변경은 GitHub Actions가 자동 배포

`.github/workflows/deploy-oracle.yml`이 `main` push 시 SSH로 접속해
`git pull` + `systemctl restart se-discord-bot`을 수행한다.

**GitHub repo Settings → Secrets and variables → Actions**에 아래를 등록할 것
(로컬 `.env`에 넣어도 GitHub Actions는 그 파일을 볼 수 없으므로 반드시 여기에 등록해야 함):

| Secret 이름 | 값 |
|---|---|
| `ORACLE_SSH_HOST` | `168.110.32.28` |
| `ORACLE_SSH_USER` | Oracle VM의 SSH 유저명 (보통 `ubuntu` 또는 `opc`) |
| `ORACLE_SSH_KEY` | SSH **개인키** 전체 내용 (`cat ~/.ssh/id_rsa` 등) |
| `ORACLE_SSH_PORT` | SSH 포트 (기본 22, 다르면 지정) |

## 3. Obsidian 쪽 (뷰어 전용, 연산 없음)

아무 기기에 Obsidian 설치 후 vault로 이 repo를 열고, `obsidian-git` 커뮤니티 플러그인 설치.
플러그인 설정에서 "자동 pull 주기"를 켜두면 서버가 push한 내용이 그대로 반영된다.
iCloud 동기화는 더 이상 필요 없다.
