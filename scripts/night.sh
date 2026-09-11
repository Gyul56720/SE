#!/usr/bin/env bash
# 밤일 한 바퀴: 간추리기 -> 게이트 -> 커밋 -> merge -> 밀기.
#
#     bash scripts/night.sh
#
# 밤새 돌리려면 CLAUDE.md 의 setsid 패턴으로 띄우고 pgrep -af 로 확인한다:
#     setsid nohup bash scripts/night.sh > /home/ubuntu/SE/logs/night.log 2>&1 < /dev/null &
#     disown
#
# 규칙(scripts/seek.sh 와 같다): 변수 이름에 한글을 쓰지 않는다(bash 가 명령으로
# 읽는다) · rebase 도 --force 도 쓰지 않는다(이 브랜치는 봇이 같이 쓴다) ·
# 게이트가 빨간불이면 커밋하지 않는다.
set -u
cd "$(dirname "$0")/.."

echo "=== [1/4] 간추리기 (graph/night.py) ==="
if ! python3 graph/night.py; then
    echo "간추리기가 실패했다 -- 커밋하지 않는다"
    exit 1
fi

echo "=== [1.5/4] 다섯 꼴 판정 (graph/link.py --전부) ==="
if ! python3 graph/link.py --전부; then
    echo "판정에 어긋남이 있다 -- 지우지 않고 그대로 커밋해 남긴다 (어긋남은 보는 것이다)"
fi

echo "=== [1.7/4] 요지문 다시 짓기 (graph/digest.py) ==="
python3 graph/digest.py || echo "요지문을 못 지었다 -- 색인·간선은 그대로 커밋한다"

if git diff --quiet -- graph/ledger.jsonl graph/edges.jsonl graph/digest.md && \
   [ -z "$(git ls-files --others --exclude-standard -- graph/ledger.jsonl graph/edges.jsonl graph/digest.md)" ]; then
    echo "색인에 새로 적힌 것이 없다 -- 여기서 끝"
    exit 0
fi

echo "=== [2/4] 게이트 ==="
if ! python3 gatekeeper.py; then
    echo "게이트 빨간불 -- 커밋하지 않는다"
    exit 1
fi

echo "=== [3/4] 커밋 ==="
git add -- graph/ledger.jsonl graph/edges.jsonl graph/digest.md
if ! git commit -m "night: 기억 간추리기 -- 색인·간선·요지문 갱신"; then
    echo "커밋할 것이 없거나 실패했다"
    exit 1
fi

echo "=== [4/4] 밀기 (merge, rebase 아님 · --force 는 쓰지 마라) ==="
BR=$(git rev-parse --abbrev-ref HEAD)
TRY=0
while [ "$TRY" -lt 4 ]; do
    if git push -u origin "$BR"; then
        echo "night 결과 -- 밀었다"
        exit 0
    fi
    git fetch origin "$BR" || true
    if ! git merge --no-edit origin/"$BR"; then
        git merge --abort || true
        echo "충돌 -- 사람에게 넘긴다 (아무것도 지우지 않았다)"
        exit 1
    fi
    TRY=$((TRY + 1))
    sleep $((2 ** TRY))
done
echo "네 번 밀어도 안 됐다"
exit 1
