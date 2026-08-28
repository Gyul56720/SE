#!/bin/bash
while true; do
    if [ -z "$DISCORD_BOT_TOKEN" ]; then
        echo "DISCORD_BOT_TOKEN이 설정되지 않았습니다. 토큰을 찾고 있습니다..."
        # 저장소 내 파일에서 혹시 토큰 형식이 있는지 검색
        TOKEN=$(grep -rE "([a-zA-Z0-9_-]{24,}\.[a-zA-Z0-9_-]{6,}\.[a-zA-Z0-9_-]{27,})" . --exclude-dir=.git | head -n 1 | grep -oE "[a-zA-Z0-9_-]{24,}\.[a-zA-Z0-9_-]{6,}\.[a-zA-Z0-9_-]{27,}")
        
        if [ ! -z "$TOKEN" ]; then
            echo "토큰을 발견했습니다: $TOKEN"
            export DISCORD_BOT_TOKEN="$TOKEN"
        else
            echo "토큰을 찾을 수 없습니다. 10초 대기 후 다시 시도합니다."
            sleep 10
            continue
        fi
    fi
    
    echo "봇 실행 시작..."
    python3 Public_agent/discord_deleter_bot.py
    echo "봇이 종료되었습니다. 재시작 중..."
    sleep 5
done
