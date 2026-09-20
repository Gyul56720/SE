#!/usr/bin/env bash
# 교재 전체를 한국어로 옮긴다 -- **VM 에서 돈다**(Gemini 키가 거기 있다).
#
#   bash scripts/번역돌리기.sh            배경으로 시작 (PID·로그를 알려 준다)
#   bash scripts/번역돌리기.sh --어림     부르지 않고 값만 잰다 (즉시)
#   bash scripts/번역돌리기.sh --상태     얼마나 갔나
#   bash scripts/번역돌리기.sh T3 T4      그 장만
#
# 왜 스크립트인가: CLAUDE.md 의 배경 실행 규칙(`setsid nohup ... disown`)을 손으로
# 다시 치면 빠뜨린다.  실측으로 이미 한 번 잃었다 -- `command &` 로 띄운 작업이
# 부모와 함께 죽어서, "완료되면 알려드리겠습니다" 라고 답해 놓고 아무것도 안 나왔다.
#
# **셸 변수 이름은 전부 ASCII 다.** bash 는 한글 식별자를 대입으로 안 읽는다
# (실측: `초=25` 가 명령어로 파싱돼 파일이 한 줄도 안 돌았다).
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2
# 로그와 PID 파일 자리는 **환경변수로 바꿀 수 있다.**  검사가 제 자리를 쓰기
# 위해서다: 안 그러면 검사와 사람이 같은 PID 파일을 보고, 한쪽이 돌고 있으면
# 다른 쪽이 "이미 돌고 있다" 로 끝나 **검사 결과가 그때그때 달라진다**
# (실측 2026-09-20: precheck 이 한 번 빨갛고 다음에 초록이었다).
LOG="${SE_TRANSLATE_LOG:-$ROOT/logs/translate.log}"
PIDF="${SE_TRANSLATE_PIDFILE:-$ROOT/logs/translate.pid}"
OUT="$ROOT/edu/번역/한국어"
CACHE="$ROOT/edu/번역/곳간"
mkdir -p "$ROOT/logs" "$OUT" "$(dirname "$LOG")" "$(dirname "$PIDF")"

case "${1:-}" in
  --어림|어림)
    exec python3 edu/번역/translate.py --전부 --어림
    ;;
  --상태|상태)
    echo "옮긴 덩이(캐시): $(ls -1 "$CACHE" 2>/dev/null | wc -l)"
    echo "낸 장:           $(ls -1 "$OUT" 2>/dev/null | wc -l)"
    # **PID 로 본다.** `pgrep -f translate.py` 는 이 스크립트를 편집하거나 인용한
    # 셸에도 걸린다(실측 2026-09-20: 스크립트를 heredoc 으로 쓰던 내 셸이 잡혔다).
    # CLAUDE.md 의 규칙 그대로다 -- 기다릴 때는 PID 로 기다린다.
    if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
        echo "돌고 있다: PID $(cat "$PIDF")"
    else
        echo "지금은 안 돈다"
    fi
    [ -f "$LOG" ] && { echo "--- 로그 끝 12줄 ---"; tail -12 "$LOG"; }
    exit 0
    ;;
esac

# 장을 고르면 그 장만, 아니면 전부
if [ $# -gt 0 ]; then
  ARGS=(--장 "$@")
  WHAT="장 $*"
else
  ARGS=(--전부)
  WHAT="전부"
fi

if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "이미 돌고 있다(PID $(cat "$PIDF")) -- 두 벌이 같은 곳간을 서로 덮는다." >&2
  exit 1
fi

setsid nohup python3 edu/번역/translate.py "${ARGS[@]}" --낼곳 "$OUT" \
    > "$LOG" 2>&1 < /dev/null &
disown

# **살아 있는지 확인하고 나서 말한다.** `$!` 는 setsid 가 fork 해 버린 래퍼일 수 있으므로
# `ps -p $!` 가 아니라 `pgrep -af` 로 본다 (실측: $!=8309 는 없고 실제는 8311 이었다).
sleep 3
# setsid 는 자기가 프로세스 그룹 리더면 fork 하므로 `$!` 는 **이미 끝난 래퍼**일 수 있다.
# 그래서 실제 파이썬의 PID 를 이름으로 찾아 적어 둔다 -- 뒤로는 그 PID 로만 본다.
PID=$(pgrep -f "edu/.*translate.py" | head -1 || true)
if [ -z "$PID" ]; then
  echo "띄웠는데 프로세스가 안 보인다 -- 시작했다고 말하지 않는다. 로그: $LOG" >&2
  tail -20 "$LOG" >&2
  exit 1
fi
echo "$PID" > "$PIDF"
echo "번역 시작($WHAT) -- PID $PID"
echo "로그: $LOG"
echo "진행: bash scripts/번역돌리기.sh --상태"
echo "끊겨도 다시 돌리면 이어서 간다(덩이마다 곳간에 캐시한다)"
