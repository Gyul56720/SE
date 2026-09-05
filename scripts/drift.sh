#!/usr/bin/env bash
# DRIFT -- 자유 연속 집필 오케스트레이션의 트리거.
#
# **어느 디렉토리에서 쳐도 된다** -- 경로가 전부 절대경로다. 상대경로는 사람이 어디에
# 서 있느냐에 따라 조용히 다른 것을 가리킨다(실측: 홈에서 실행한 사람이
# `/home/ubuntu/pgrep: No such file` 을 만났다).
#
#   drift.sh start  [글자수]        새 원고를 시작한다 (기본 8000)
#   drift.sh go     [글자수]        하던 원고를 이어 쓴다 (기본 50000)  ← 가장 많이 쓴다
#
#   세기를 조절한다 (기본: 급발진 매 덩어리 · 사건 2,000자마다 · 소재 축은 꺼짐):
#     DRIFT=0.5  drift.sh go    # 급발진·사건을 반으로
#     MATTER=0.3 drift.sh go    # 갈래·매체를 조금만 섞는다 (기본 0 = 안 섞음)
#   drift.sh status                 살아 있는지 · 어디까지 왔는지
#   drift.sh read                   지금까지 쓴 원고를 읽는다
#   drift.sh save  <파일>           원고를 파일로 뽑는다
#   drift.sh send  [이름]           **원고를 Discord 로 보낸다** -- VM 밖으로 빼는 길
#   drift.sh watch                  로그를 계속 따라간다
#   drift.sh stop                   런을 멈춘다 (원고는 남는다 -- go 로 이어 쓴다)
#   drift.sh world                  세계가 얼마나 자랐는지 (인물·장소·사물·사실·사건)
#   drift.sh open                   아직 안 닫힌 것들 -- 이 이야기가 갚지 않은 빚
#
# 환경변수로 바꿀 수 있는 것:
#   DRIFT    표류 계수 0~1     (기본 1.0 -- 낮추면 급발진·사건이 줄어든다)
#   MATTER   소재 축 0~1       (기본 0.0 -- 켜면 갈래·매체가 섞인다)
#   BODY     몸의 사실 0~1     (기본 0.35)
#   BOND     관계 0~1          (기본 0.4)
#
#   설정은 **원고가 아니라 코드가 정한다.** 이어 쓸 때마다 지금 기본값으로 맞춰지고,
#   위 환경변수를 주면 그것이 이긴다. 옛 원고가 옛 설정으로 계속 도는 일은 없다.
#   SE_DIR   저장소 위치        (기본 /home/ubuntu/SE)
#   BOOK     원고 파일          (기본 $SE_DIR/novel/drift.json)
#   FIRST    첫 문장 (start 에서만)
set -u

SE="${SE_DIR:-/home/ubuntu/SE}"
BOOK="${BOOK:-$SE/novel/drift.json}"
LOG="$SE/logs/drift.log"
# 명부 -- start 때 탐침 한 바퀴로 "지금 답하는 모델" 만 적어 두고 런 내내 그것만 쓴다.
ROSTER="${GEMINI_ROSTER:-$SE/logs/roster.json}"
export GEMINI_ROSTER="$ROSTER"
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
    # **시작할 때 한 번만 고른다.** 일일 잔량은 남았는데 분당 한도에 걸리는 모델이
    # 후보에 섞여 있으면, 호출마다 그것을 두드려 429 를 받고서야 성한 것으로 넘어간다 --
    # 그 왕복을 매번 다시 문다. 열 글자짜리 탐침 한 바퀴로 걸러 두면 런 내내 그만큼 아낀다.
    echo "후보를 고른다 (탐침 한 바퀴)..."
    rm -f "$ROSTER"
    python3 "$SE/scripts/pool_probe.py" --parallel --roster "$ROSTER" | tail -4
    [ -f "$BOOK" ] && {
      mv "$BOOK" "$BOOK.$(date +%Y%m%d-%H%M%S).bak"
      echo "쓰던 원고를 옮겨 두었다: $BOOK.*.bak"
    }
    set -- --out "$BOOK" --chars "${2:-8000}" ${DRIFT:+--drift "$DRIFT"} ${MATTER:+--matter "$MATTER"} \
           ${BODY:+--body "$BODY"} ${BOND:+--bond "$BOND"}
    [ -n "${FIRST:-}" ] && set -- "$@" --first "$FIRST"
    launch "새 원고를" "$@"
    # **정말 새 원고인지 확인한다.** 앞 런이 살아 있으면 같은 파일에 계속 쓰므로 옛
    # 인물·장소가 그대로 남는다(실측: "이야기가 바뀌었는데 이전 소설 내역이 남아 있다").
    sleep 2
    python3 - "$BOOK" <<'INNER' || true
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if p.exists():
    b = json.loads(p.read_text(encoding="utf-8"))
    L = b.get("ledger", {})
    n = sum(len(L.get(k) or {}) for k in ("people", "places", "objects", "facts"))
    if n or b.get("chunks"):
        print("  * 새 원고인데 세계가 비어 있지 않다"
              f" (항목 {n}개, 덩어리 {len(b.get('chunks', []))}개).")
        print("    앞 런이 같은 파일에 쓰고 있을 수 있다:")
        print("      /usr/bin/pgrep -af 'novel/flow.py'   <- 둘 이상이면 옛 PID 를 kill")
    else:
        print("  세계는 비어 있다 -- 처음부터 시작한다.")
INNER
    ;;

  go|resume)
    refuse_double; load_env
    [ -f "$BOOK" ] || die "이어 쓸 원고가 없다: $BOOK   (새로 시작하려면: $0 start)"
    cp "$BOOK" "$BOOK.bak"
    launch "이어 쓰기를" --resume "$BOOK" --chars "${2:-50000}" --hours 12 \
           ${DRIFT:+--drift "$DRIFT"} ${MATTER:+--matter "$MATTER"} \
           ${BODY:+--body "$BODY"} ${BOND:+--bond "$BOND"}
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
print(f"  원고  덩어리 {len(b['chunks'])}개 · {n:,}자 · 사건 {b.get('shocks', 0)}회 · "
      f"표류 {b.get('drift', '?')} · 소재 {b.get('matter', 0)} · "
      f"설정 {b.get('trait', b.get('body', '?'))} · 관계 {b.get('bond', '?')}")
print(f"  열린 것 {len((L.get('open') or {}))}개  (drift.sh open 으로 본다)")
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

  open)
    [ -f "$BOOK" ] || die "원고가 없다: $BOOK"
    python3 - "$BOOK" <<'INNER'
import json, sys
L = json.load(open(sys.argv[1], encoding="utf-8")).get("ledger", {})
o = L.get("open") or {}
if not o:
    print("  열린 것이 없다. (아직 안 나왔거나, 전부 닫혔다)")
for k, v in o.items():
    print(f"  · {k} -- {v}")
print(f"\n  모두 {len(o)}개")
INNER
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
