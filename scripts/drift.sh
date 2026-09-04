#!/usr/bin/env bash
# DRIFT -- 자유 연속 집필 오케스트레이션의 트리거.
#
# **어느 디렉토리에서 쳐도 된다** -- 경로가 전부 절대경로다. 상대경로는 사람이 어디에
# 서 있느냐에 따라 조용히 다른 것을 가리킨다(실측: 홈에서 실행한 사람이
# `/home/ubuntu/pgrep: No such file` 을 만났다).
#
#   drift.sh start  [글자수]        새 원고를 시작한다 (기본 8000)
#   drift.sh go     [글자수]        하던 원고를 이어 쓴다 (기본 50000)  ← 가장 많이 쓴다
#   drift.sh status                 살아 있는지 · 어디까지 왔는지
#   drift.sh read                   지금까지 쓴 원고를 읽는다
#   drift.sh save  <파일>           원고를 파일로 뽑는다
#   drift.sh send  [이름]           **원고를 Discord 로 보낸다** -- VM 밖으로 빼는 길
#   drift.sh watch                  로그를 계속 따라간다
#   drift.sh stop                   런을 멈춘다 (원고는 남는다 -- go 로 이어 쓴다)
#   drift.sh world                  세계가 얼마나 자랐는지 (인물·장소·사물·사실·사건)
#
# 환경변수로 바꿀 수 있는 것:
#   SE_DIR   저장소 위치        (기본 /home/ubuntu/SE)
#   BOOK     원고 파일          (기본 $SE_DIR/novel/drift.json)
#   FIRST    첫 문장 (start 에서만)
set -u

SE="${SE_DIR:-/home/ubuntu/SE}"
BOOK="${BOOK:-$SE/novel/drift.json}"
LOG="$SE/logs/drift.log"
FLOW="$SE/novel/flow.py"
PGREP=/usr/bin/pgrep
[ -x "$PGREP" ] || PGREP="$(command -v pgrep 2>/dev/null || echo pgrep)"

die() { echo "$*" >&2; exit 1; }

# 키를 읽어 들인다. SSH 셸은 systemd 의 EnvironmentFile 을 물려받지 않으므로 여기서
# 직접 읽는다 -- 이걸 빼먹으면 첫 호출에서 죽고 로그에만 이유가 남는다.
load_env() {
  [ -f "$SE/.env" ] && { set -a; . "$SE/.env"; set +a; }
  python3 - <<'PY' || die "Gemini 키가 없다. $SE/.env 를 확인해라. (Claude 로 대신 쓰지 않는다)"
import os, sys
sys.exit(0 if any(os.getenv(k) for k in
    ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEYS")) else 1)
PY
}

# **파이썬 프로세스만 센다.** 그냥 `pgrep -af novel/flow.py` 로 하면 이 스크립트를
# 실행하는 셸까지 잡힌다 -- 명령줄에 그 문자열이 들어 있기 때문이다(실측: 이 파일을
# 쓰는 셸이 "돌고 있다" 로 세어졌다). 자기 PID 와 부모도 빼야 한다.
# 키만 읽고 아무 말도 하지 않는다 -- Discord 자격증명은 Gemini 키와 별개라 여기서
# Gemini 를 요구하면 안 된다(원고를 보내는 데 화자는 필요 없다).
load_env_quiet() { [ -f "$SE/.env" ] && { set -a; . "$SE/.env"; set +a; }; return 0; }

alive() {
  "$PGREP" -af "novel/flow\.py" 2>/dev/null \
    | grep -E "^[0-9]+ +([^ ]*/)?python3?(\.[0-9]+)? " \
    | grep -vE "^($$|$PPID) "
}

pids_of() { alive | awk '{print $1}'; }

# **살아 있으면 새로 띄우지 않는다.** 같은 파일에 둘이 쓰면 서로를 덮어쓴다.
refuse_double() {
  if alive >/dev/null; then
    echo "이미 돌고 있다:"; alive
    die "멈추려면: $0 stop   / 진행을 보려면: $0 status"
  fi
}

launch() {   # launch <설명> <인자...>
  local what="$1"; shift
  mkdir -p "$SE/logs"
  setsid nohup python3 "$FLOW" "$@" > "$LOG" 2>&1 < /dev/null &
  disown
  sleep 4
  if alive >/dev/null; then
    echo "$what 시작했다."
    alive
    echo "  원고: $BOOK"
    echo "  로그: $LOG   ($0 watch 로 따라간다)"
  else
    echo "시작하지 못했다. 로그:" >&2
    tail -20 "$LOG" >&2
    exit 1
  fi
}

case "${1:-status}" in
  start)
    refuse_double; load_env
    [ -f "$BOOK" ] && {
      mv "$BOOK" "$BOOK.$(date +%Y%m%d-%H%M%S).bak"
      echo "쓰던 원고를 옮겨 두었다: $BOOK.*.bak"
    }
    set -- --out "$BOOK" --chars "${2:-8000}"
    [ -n "${FIRST:-}" ] && set -- "$@" --first "$FIRST"
    launch "새 원고를" "$@"
    ;;

  go|resume)
    refuse_double; load_env
    [ -f "$BOOK" ] || die "이어 쓸 원고가 없다: $BOOK   (새로 시작하려면: $0 start)"
    cp "$BOOK" "$BOOK.bak"
    launch "이어 쓰기를" --resume "$BOOK" --chars "${2:-50000}" --hours 12
    ;;

  status)
    if alive >/dev/null; then echo "돌고 있다:"; alive; else echo "돌고 있지 않다."; fi
    echo
    if [ -f "$BOOK" ]; then
      python3 - "$BOOK" <<'PY'
import json, sys
b = json.load(open(sys.argv[1], encoding="utf-8"))
n = sum(len(c) for c in b["chunks"])
L = b.get("ledger", {})
print(f"  원고  덩어리 {len(b['chunks'])}개 · {n:,}자 · 사건 {b.get('shocks', 0)}회")
print(f"  세계  인물 {len(L.get('people', {}))} · 장소 {len(L.get('places', {}))} · "
      f"사물 {len(L.get('objects', {}))} · 사실 {len(L.get('facts', {}))}")
PY
    else
      echo "  원고가 아직 없다: $BOOK"
    fi
    echo
    [ -f "$LOG" ] && { echo "  최근 로그:"; tail -6 "$LOG" | sed 's/^/    /'; }
    ;;

  read)   exec python3 "$FLOW" --read "$BOOK" ;;

  # VM 밖으로 빼는 길. 원고는 여기 JSON 안에만 있어서 --read 로는 화면에 쏟아질 뿐
  # 손에 들어오지 않는다. Discord 에 올리면 폰이든 노트북이든 어디서나 받는다.
  send)   load_env_quiet; exec python3 "$SE/novel/deliver.py" --book "$BOOK" \
            ${2:+--name "$2"} ;;
  save)   [ $# -ge 2 ] || die "사용: $0 save <파일>"
          python3 "$FLOW" --read "$BOOK" > "$2" && echo "뽑았다: $2 ($(wc -m < "$2")자)" ;;
  watch)  exec tail -f "$LOG" ;;

  stop)
    pids="$(pids_of || true)"
    [ -n "$pids" ] || { echo "돌고 있지 않다."; exit 0; }
    # pkill -f 는 명령줄에 패턴이 들어 있으면 **자기 셸까지 죽인다**(실측). PID 로만 죽인다.
    for p in $pids; do kill "$p"; done
    sleep 2; echo "멈췄다. 원고는 남아 있다 -- 이어 쓰려면: $0 go"
    ;;

  world)
    [ -f "$BOOK" ] || die "원고가 없다: $BOOK"
    python3 - "$BOOK" <<'PY'
import json, sys
L = json.load(open(sys.argv[1], encoding="utf-8")).get("ledger", {})
for name, card in L.get("people", {}).items():
    if isinstance(card, dict):
        seen = card.get("_seen", 0)
        fields = " · ".join(f"{k} {v}" for k, v in card.items() if not k.startswith("_"))
        print(f"  {'★' if seen >= 3 else ' '} {name} ({seen}회) {fields}")
for b, label in (("places", "장소"), ("objects", "사물"), ("facts", "사실")):
    for k, v in (L.get(b) or {}).items():
        print(f"  [{label}] {k} = {v}")
print("  시간:", " → ".join(L.get("time", [])[-8:]))
PY
    ;;

  *) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
