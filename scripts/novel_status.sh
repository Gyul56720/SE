#!/usr/bin/env bash
# 소설 런의 상태를 한 번에 본다. **어느 디렉토리에서 쳐도 된다** -- 경로가 전부 절대경로다.
#
# 왜 이 스크립트인가. 안내문에 상대경로를 적어뒀더니 홈에서 실행한 사람이 이걸 만났다:
#   -bash: /home/ubuntu/SE/pgrep: No such file or directory
#   tail: cannot open 'logs/novel_seeded.log'
#   python3: can't open file '/home/ubuntu/novel/watch.py'
# 상대경로는 사람이 어디에 서 있느냐에 따라 조용히 다른 것을 가리킨다.
#
# 사용:
#   /home/ubuntu/SE/scripts/novel_status.sh          # 한 번 보고 끝
#   /home/ubuntu/SE/scripts/novel_status.sh -f       # 로그를 계속 따라간다
#   /home/ubuntu/SE/scripts/novel_status.sh --read   # 지금까지 쓴 원고를 읽는다
set -u

SE="${SE_DIR:-/home/ubuntu/SE}"
LOG="$SE/logs/novel_seeded.log"
BOOK="$SE/novel/seeded.json"
PGREP=/usr/bin/pgrep
[ -x "$PGREP" ] || PGREP="$(command -v pgrep 2>/dev/null || echo pgrep)"

case "${1:-}" in
  -f|--follow)
    [ -f "$LOG" ] || { echo "로그가 없다: $LOG  (아직 한 번도 안 돌렸다)"; exit 1; }
    exec tail -f "$LOG" ;;
  --read)
    [ -f "$BOOK" ] || { echo "원고가 없다: $BOOK"; exit 1; }
    exec python3 "$SE/novel/read.py" --path "$BOOK" --ep "${2:-1-10}" ;;
esac

echo "=== 프로세스 ==="
PIDS="$("$PGREP" -f "novel/overnight.py" 2>/dev/null | grep -vx "$$" | grep -vx "$PPID")"
if [ -n "$PIDS" ]; then
  # etime 은 얼마나 오래 돌았는지다. 로그가 안 늘어나는데 etime 만 늘면 어딘가 매달린 것이다.
  ps -o pid=,etime=,args= -p $(echo "$PIDS" | tr '\n' ' ') 2>/dev/null
else
  echo "  도는 런 없음"
fi

echo
echo "=== 로그 (마지막 12줄) ==="
if [ -f "$LOG" ]; then
  tail -12 "$LOG"
  echo "  ... 전체: tail -f $LOG"
else
  echo "  로그가 없다: $LOG"
fi

echo
echo "=== 원고 ==="
if [ -f "$BOOK" ]; then
  python3 "$SE/novel/watch.py" --path "$BOOK" 2>/dev/null \
    || echo "  (watch.py 가 읽지 못했다. 파일은 있다: $BOOK)"
else
  echo "  아직 없다: $BOOK  -- 산문 단계에 들어가야 처음 저장된다"
fi

echo
echo "읽기: python3 $SE/novel/read.py --path $BOOK --ep 1-10"
echo "병목: python3 $SE/novel/profile.py --path $BOOK"
