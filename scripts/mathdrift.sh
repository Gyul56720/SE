#!/usr/bin/env bash
# MATHDRIFT -- 수학적 지평을 소설처럼 넓히는 오케스트레이션의 트리거.
#
# 소설의 drift.sh 와 같은 꼴이다. 다른 것은 낳는 것이 원고가 아니라 **식**이라는 것뿐이다.
# 어느 디렉토리에서 쳐도 된다 -- 경로가 전부 절대경로다.
#
#   mathdrift.sh start [개수]     새 원장으로 시작한다 (기본 50). 쓰던 것은 .bak 으로
#   mathdrift.sh go    [개수]     하던 원장을 이어 넓힌다 (기본 100)  ← 가장 많이 쓴다
#   mathdrift.sh status           살아 있는지 · 어디까지 왔는지
#   mathdrift.sh show             원장 -- 공간마다 식 한 줄
#   mathdrift.sh diff  <id>       **연산자가 식에 무엇을 했나** (기호 단위. 호출 0회)
#   mathdrift.sh card  <id>       공간 하나를 칸째로, 부모와 나란히
#   mathdrift.sh lineage <id>     씨앗까지의 사슬
#   mathdrift.sh recall           ①재현 -- 코드 칸을 채운 것만, 호출 0회. **시키면 한다**
#   mathdrift.sh check            지금 무엇을 쓸 수 있나 (호출 0회)
#   mathdrift.sh watch            로그를 계속 따라간다
#   mathdrift.sh stop             멈춘다 (원장은 남는다 -- go 로 이어 넓힌다)
#   mathdrift.sh quota            쿼터 장부
#
# 환경변수:
#   SE_DIR    저장소 위치      (기본 /home/ubuntu/SE)
#   LEDGER    원장 파일        (기본 $SE_DIR/mathdrift/ledger.json)
#   BATCH     호출 하나가 낳는 식의 수 (기본 5). RPM 이 병목이라 이것이 곧 시간이다
#
# **발산에는 게이트가 없다.** 이 스크립트는 아무것도 거르지 않는다. 검증(recall)은 따로
# 있고, 그것도 시켰을 때만 돈다. 낱말로 재는 자는 두 번 뒤집혀서 판정에서 뗐다 -- 식은
# `diff` 로 기호 단위로 본다.
set -u

SE="${SE_DIR:-/home/ubuntu/SE}"
LEDGER="${LEDGER:-$SE/mathdrift/ledger.json}"
LOG="$SE/logs/mathdrift.log"
ROSTER="${GEMINI_ROSTER:-$SE/logs/roster.json}"
export GEMINI_ROSTER="$ROSTER"
export MATHDRIFT_LEDGER="$LEDGER"
SPREAD="$SE/mathdrift/spread.py"
RECALL="$SE/mathdrift/recall.py"
PGREP=/usr/bin/pgrep
[ -x "$PGREP" ] || PGREP="$(command -v pgrep 2>/dev/null || echo pgrep)"

die() { echo "$*" >&2; exit 1; }

# 키를 읽어 들인다. SSH 셸은 systemd 의 EnvironmentFile 을 물려받지 않는다.
load_env() {
  [ -f "$SE/.env" ] && { set -a; . "$SE/.env"; set +a; }
  python3 - <<'PY' || die "Gemini 키가 없다. $SE/.env 를 확인해라. (Claude 로 대신 짓지 않는다)"
import os, sys
sys.exit(0 if any(os.getenv(k) for k in
    ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEYS")) else 1)
PY
}

# **파이썬 프로세스만 센다.** `pgrep -af mathdrift/spread.py` 만 하면 이 스크립트를
# 실행하는 셸까지 잡힌다 -- 명령줄에 그 문자열이 들어 있기 때문이다(drift.sh 실측).
alive() {
  "$PGREP" -af "mathdrift/spread\.py" 2>/dev/null \
    | grep -E "^[0-9]+ +([^ ]*/)?python3?(\.[0-9]+)? " \
    | grep -vE "^($$|$PPID) "
}

pids_of() { alive | awk '{print $1}'; }

refuse_double() {
  if alive >/dev/null; then
    echo "이미 돌고 있다:"; alive
    die "멈추려면: $0 stop   / 진행을 보려면: $0 status"
  fi
}

launch() {   # launch <설명> <개수>
  local what="$1" n="$2"
  mkdir -p "$SE/logs"
  setsid nohup python3 "$SPREAD" --n "$n" --batch "${BATCH:-5}" >> "$LOG" 2>&1 < /dev/null &
  disown
  sleep 4
  if alive >/dev/null; then
    echo "$what 시작했다. 식 $n 개."
    alive
    echo "  원장: $LEDGER"
    echo "  로그: $LOG   ($0 watch 로 따라간다)"
  else
    # 짧은 런은 4초 안에 끝나기도 한다 -- 죽은 것과 끝난 것을 로그로 가른다.
    if tail -3 "$LOG" 2>/dev/null | grep -q "원장에 올렸다"; then
      echo "$what -- 벌써 끝났다."; tail -3 "$LOG"
    else
      echo "시작하지 못했다. 로그:" >&2; tail -20 "$LOG" >&2; exit 1
    fi
  fi
}

case "${1:-status}" in
  start)
    refuse_double; load_env
    if [ -f "$LEDGER" ]; then
      mv "$LEDGER" "$LEDGER.bak"
      echo "쓰던 원장을 $LEDGER.bak 으로 옮겨 뒀다."
    fi
    launch "새 원장" "${2:-50}"
    ;;
  go)
    refuse_double; load_env
    launch "이어 넓히기" "${2:-100}"
    ;;
  status)
    if alive >/dev/null; then echo "돌고 있다:"; alive; else echo "안 돌고 있다."; fi
    echo
    python3 "$SPREAD" --show 2>/dev/null | tail -4
    echo
    [ -f "$LOG" ] && { echo "최근 로그:"; tail -5 "$LOG"; }
    ;;
  show)     python3 "$SPREAD" --show ;;
  diff)     [ -n "${2:-}" ] || die "어느 공간? 예: $0 diff S10"; python3 "$SPREAD" --diff "$2" ;;
  card)     [ -n "${2:-}" ] || die "어느 공간? 예: $0 card S10"; python3 "$SPREAD" --card "$2" ;;
  lineage)  [ -n "${2:-}" ] || die "어느 공간? 예: $0 lineage S10"; python3 "$SPREAD" --lineage "$2" ;;
  recall)   shift; python3 "$RECALL" "$@" ;;
  check)    load_env; python3 "$SPREAD" --check ;;
  watch)    [ -f "$LOG" ] || die "로그가 아직 없다: $LOG"; tail -f "$LOG" ;;
  quota)    shift; python3 "$SE/scripts/quota_show.py" "$@" ;;
  stop)
    P="$(pids_of)"
    [ -n "$P" ] || { echo "안 돌고 있다."; exit 0; }
    echo "멈춘다: $P"; kill $P 2>/dev/null; sleep 2
    P2="$(pids_of)"; [ -z "$P2" ] || { echo "아직 남아서 -9: $P2"; kill -9 $P2 2>/dev/null; }
    echo "멈췄다. 원장은 남아 있다: $LEDGER   (이어 넓히려면 $0 go)"
    ;;
  *) sed -n '2,32p' "$0"; exit 1 ;;
esac
