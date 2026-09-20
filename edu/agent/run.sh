#!/usr/bin/env bash
# 24시간 회귀 에이전트를 **부모가 죽어도 사는** 방식으로 띄운다.
#
# CLAUDE.md 의 백그라운드 규칙 그대로다: setsid + nohup + disown, 그리고
# stdin/stdout/stderr 를 전부 리다이렉트한다.  claude -p 가 응답 직후 끝나도
# 이 프로세스는 남는다.
#
#   사용:  bash run.sh [--적용] [시간]
#
# 확인은 `ps -p $!` 가 아니라 `pgrep -af agent.py` 로 한다 -- setsid 가 fork 하므로
# $! 는 이미 끝난 래퍼다.  셸 변수명에 한글을 쓰지 않는다 (bash 는 받지 않는다).
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="${SE_AGENT_LOG:-/home/user/SE/logs}"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/verif_agent.log"

APPLY=""
HOURS="24"
for a in "$@"; do
  case "$a" in
    --적용|--apply) APPLY="--적용" ;;
    *) HOURS="$a" ;;
  esac
done

setsid nohup python3 "$HERE/agent.py" --시간 "$HOURS" ${APPLY:+$APPLY} \
       > "$LOG" 2>&1 < /dev/null &
disown

sleep 3
if pgrep -af "agent.py" > /dev/null; then
  echo "살아 있다:"
  pgrep -af "agent.py"
  echo "로그: $LOG"
  sleep 2
  echo "--- 로그 첫 줄 ---"
  head -3 "$LOG"
else
  echo "띄우지 못했다.  로그:"
  cat "$LOG"
  exit 1
fi
