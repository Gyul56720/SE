#!/bin/bash
# discord_deleter_bot.py 재시작 루프.
#
# 보안 이력(2026-08-28): 이 스크립트는 원래 DISCORD_BOT_TOKEN이 비어 있으면 저장소 전체를
# grep해서 토큰처럼 생긴 문자열을 찾아 `echo "토큰을 발견했습니다: $TOKEN"`으로 출력했다.
# .env는 grep 제외 대상이 아니었고, 이 스크립트의 stdout은 bot_execution.log로 들어가며
# 그 로그는 git에 커밋되어 origin으로 push됐다 -- 즉 봇 토큰을 원격 저장소에 평문으로
# 유출하는 경로였다. 토큰은 오직 환경(.env / systemd EnvironmentFile)에서만 읽는다.
set -u

if [ -z "${DISCORD_BOT_TOKEN:-}" ] && [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

if [ -z "${DISCORD_BOT_TOKEN:-}" ]; then
    echo "DISCORD_BOT_TOKEN이 설정되지 않았습니다. .env 또는 systemd EnvironmentFile에 넣으십시오." >&2
    exit 1
fi

while true; do
    echo "봇 실행 시작..."
    python3 Public_agent/discord_deleter_bot.py
    echo "봇이 종료되었습니다. 재시작 중..."
    sleep 5
done
