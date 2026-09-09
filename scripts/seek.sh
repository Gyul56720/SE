#!/usr/bin/env bash
# seek 한 바퀴를 **끝까지** 돈다 -- 훑기 · 보고서 · 커밋 · 밀기.
#
# 왜 한 파일인가. 여러 줄로 된 명령을 보내면 **중간에 몇 줄이 빠진다**(실측
# 2026-09-09, 네 번: 원장 커밋 · sweep 두 번 · 표 옮기기). 빠진 줄이 sweep 이면
# 답이 0개인 원장으로 보고서가 나오고, 그 보고서의 0%를 성적으로 읽게 된다.
#
# 그래서 줄을 하나로 줄인다. 이 파일이 순서를 들고 있다.
#
#     mkdir -p logs
#     setsid nohup bash scripts/seek.sh > logs/seek.log 2>&1 < /dev/null &
#     disown
#     pgrep -af scripts/seek.sh          # ← ps -p $! 가 아니다
#
# 인자: [한문제당초 [본것상한]]   기본 25초 · 400000개
set -u
cd "$(dirname "$0")/.." || exit 1

초=${1:-25}
본것=${2:-400000}
BR=$(git rev-parse --abbrev-ref HEAD)

echo "=== [1/4] 훑기 -- 한 문제당 최대 ${초}초 · ${본것}개 (호출 0회)"
python3 seek/sweep.py --초 "$초" --tries "$본것" || {
    echo "훑기가 실패했다 -- 여기서 멈춘다. 보고서를 안 만든다"
    exit 1
}

echo
echo "=== [2/4] 보고서"
python3 seek/report.py --쓰기 || exit 1

echo
echo "=== [3/4] 커밋"
git add seek/report.md
if git diff --cached --quiet -- seek/report.md; then
    echo "보고서가 그대로다 -- 커밋할 것이 없다"
    exit 0
fi
푼것=$(python3 -c "
import json, os, sys
sys.path.insert(0, '.')
from seek import problem as PR
led = PR.load()
ps = led.get('problems') or []
print(f\"{sum(1 for p in ps if p.get('답') is not None)}/{len(ps)}\")
" 2>/dev/null || echo "?")
git commit -q -m "seek 결과 -- 푼 것 ${푼것}" || exit 1

echo
echo "=== [4/4] 밀기 (${BR})"
# **merge 다. rebase 도 --force 도 아니다** -- 이 저장소의 브랜치는 봇이 같이 쓴다.
for 번 in 1 2 3 4; do
    git fetch origin "$BR" && git merge --no-edit "origin/$BR" || {
        git merge --abort 2>/dev/null
        echo "origin/$BR 와 충돌 -- 사람이 봐야 한다. **--force 는 쓰지 마라**"
        exit 1
    }
    if git push -u origin "$BR"; then
        echo
        echo "끝났다. 푼 것 ${푼것}"
        exit 0
    fi
    잠=$((2 ** 번))
    echo "밀기 실패 -- ${잠}초 뒤 다시 (${번}/4)"
    sleep "$잠"
done
echo "네 번 다 실패했다"
exit 1
