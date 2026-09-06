#!/usr/bin/env bash
# **한 줄로 끝까지 간다.** 준비 검사 -> 표본 재기 -> 목표 갱신 -> 학습 루프 -> 중편 집필.
#
# 중간에 끊기지 않게 하는 것들:
#   · 띄우기 전에 걸릴 것을 전부 걸러 낸다(preflight)
#   · setsid + nohup + disown -- 부모가 죽어도 안 죽는다
#   · **감시자**가 루프를 지켜본다. 죽으면 다시 띄운다(최대 RESTART 번)
#   · 한 단계가 실패해도 다음으로 간다. 실패는 로그에 남는다
#   · 멈추는 길은 STOP 파일 하나
#
#   scripts/run_all.sh --check    준비만 본다
#   scripts/run_all.sh --bg       띄운다  <- 이걸 쓴다
#   scripts/run_all.sh --status   어디까지 왔나
#   scripts/run_all.sh --stop     멈춘다
set -u
SE="${SE_DIR:-/home/ubuntu/SE}"
cd "$SE" || exit 1
LOG="$SE/logs/run_all.log"
STOP="$SE/logs/tune_loop.stop"
RESTART="${RESTART:-20}"          # 루프가 죽으면 몇 번까지 다시 띄우나
FINAL_CHARS="${FINAL_CHARS:-100000}"
mkdir -p "$SE/logs"

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

case "${1:-}" in
  --check)  exec scripts/preflight.sh ;;
  --stop)   touch "$STOP"; scripts/tune_loop.sh --stop; echo "멈추라고 적어 뒀다"; exit 0 ;;
  --status)
    echo "== 감시자"; /usr/bin/pgrep -af "run_all.sh" | grep -v -- --status || echo "  안 돈다"
    scripts/tune_loop.sh --status
    echo "== 원고"; python3 -c "
import json,sys
try:
    b=json.load(open('$SE/novel/drift.json'))
    print(f\"  덩어리 {len(b['chunks'])}개 · {sum(len(c) for c in b['chunks']):,}자\")
except Exception as e: print('  아직 없다')"
    exit 0 ;;
  --bg)
    rm -f "$STOP"
    setsid nohup "$0" >> "$LOG" 2>&1 < /dev/null &
    disown
    sleep 3
    if /usr/bin/pgrep -af "run_all.sh" | grep -qv -- "--bg"; then
      echo "띄웠다. 로그: $LOG"
      echo "  보려면:   scripts/run_all.sh --status"
      echo "  멈추려면: scripts/run_all.sh --stop"
    else
      echo "안 떴다. 로그를 봐라: $LOG" >&2; exit 1
    fi
    exit 0 ;;
esac

rm -f "$STOP"
say "=== 준비 검사"
if ! scripts/preflight.sh >> "$LOG" 2>&1; then
  say "준비가 안 됐다. 멈춘다 -- 로그를 봐라"
  exit 1
fi

say "=== 표본을 재고 목표를 갱신한다 (LLM 호출 0회)"
DRIFT_PROFILE_STRIDE="${STRIDE:-0.5}" python3 scripts/targets_update.py novel/corpus \
  >> "$LOG" 2>&1 || say "목표 갱신 실패 -- 있던 목표로 간다"

say "=== 학습 루프 (감시자가 지켜본다)"
tries=0
while [ "$tries" -le "$RESTART" ]; do
  [ -f "$STOP" ] && { say "멈추라는 표시가 있다"; break; }
  if ! /usr/bin/pgrep -f "tune_loop.sh" | grep -qv "$$"; then
    tries=$((tries + 1))
    [ "$tries" -gt "$RESTART" ] && { say "다시 띄우기 한도($RESTART)를 넘겼다. 선다"; break; }
    say "루프를 띄운다 ($tries/$RESTART)"
    scripts/tune_loop.sh --bg >> "$LOG" 2>&1
    sleep 30
  fi
  # 루프가 끝났는지(바퀴를 다 돌았는지) 본다
  if ! /usr/bin/pgrep -f "tune_loop.sh" > /dev/null; then
    if grep -q "루프 끝" "$SE/logs/tune_loop.log" 2>/dev/null; then
      say "루프가 제 발로 끝났다"
      break
    fi
    say "루프가 죽어 있다 -- 다시 띄운다"
    continue
  fi
  sleep 120
done

say "=== 학습 결과"
python3 novel/score.py novel/drift.json 2>&1 | tail -20 | tee -a "$LOG"
python3 novel/arms.py novel/drift.json 2>&1 | tail -12 | tee -a "$LOG"
python3 novel/tuner.py log 2>&1 | tail -20 | tee -a "$LOG"

[ -f "$STOP" ] && { say "여기서 선다(멈추라는 표시)"; exit 0; }

# **뼈대가 있으면 그 차례를 따라 쓴다.** 없으면 갈래만 뽑아 쓴다.
if [ -n "${SPINE_FROM:-}" ] && [ ! -f "$SE/novel/spine.json" ]; then
  say "=== 뼈대를 뽑는다: $SPINE_FROM (토막당 호출 한 번)"
  python3 novel/spine.py build "$SPINE_FROM" >> "$LOG" 2>&1 \
    || say "뼈대 뽑기 실패 -- 갈래만 뽑아 쓴다"
fi

say "=== 배운 것으로 중편을 쓴다 (${FINAL_CHARS}자)"
# **먼저 남은 집필기를 정리한다.** drift.sh 는 flow.py 가 하나라도 살아 있으면
# 시작을 거부한다(두 벌이 같은 원고를 쓰면 서로 덮어쓴다). 학습 루프가 남긴 것이
# 있으면 여기서 끝날 때까지 기다린다 -- pkill 은 안 쓴다(제 셸까지 죽인다).
left=0
while /usr/bin/pgrep -f "novel/flow.py" > /dev/null; do
  [ -f "$STOP" ] && { say "멈추라는 표시가 있다"; exit 0; }
  left=$((left + 60)); sleep 60
  if [ "$left" -gt 3600 ]; then
    say "남은 집필기가 한 시간째 안 끝난다 -- PID 를 적어 두고 넘어간다"
    /usr/bin/pgrep -af "novel/flow.py" >> "$LOG"
    break
  fi
done
if ! BOOK="$SE/novel/final.json" scripts/drift.sh start "$FINAL_CHARS" >> "$LOG" 2>&1; then
  say "중편 집필을 못 띄웠다 -- 로그를 봐라. 여기서 선다"
  exit 1
fi
# **우리가 띄운 것만 기다린다.** 남의 flow.py 를 붙잡고 열두 시간을 서 있지 않게.
waited=0
while /usr/bin/pgrep -f "novel/final.json" > /dev/null; do
  [ -f "$STOP" ] && { say "멈추라는 표시가 있다 -- 쓰던 데까지 남는다"; break; }
  sleep 60; waited=$((waited + 60))
  if [ "$waited" -gt 43200 ]; then say "열두 시간이 지났다 -- 그만 기다린다"; break; fi
done
if python3 novel/flow.py --read "$SE/novel/final.json" > "$SE/novel/final.txt" 2>>"$LOG"; then
  say "중편: $SE/novel/final.txt ($(wc -m < "$SE/novel/final.txt" 2>/dev/null || echo 0)자)"
else
  # **0자를 성공처럼 찍지 않는다.** 예전에는 원고가 없어도 조용히 빈 파일을 만들고
  # "중편 ... (0자)" 를 찍었다.
  rm -f "$SE/novel/final.txt"
  say "중편이 안 나왔다 -- novel/final.json 이 없거나 비었다. 로그를 봐라"
  exit 1
fi
python3 novel/score.py "$SE/novel/final.json" 2>&1 | tail -20 | tee -a "$LOG"
[ -f "$SE/novel/spine.json" ] && python3 novel/spine.py cover novel/spine.json \
  "$SE/novel/final.json" 2>&1 | tee -a "$LOG"
say "=== 끝. scripts/drift.sh send 로 Discord 에 보낼 수 있다"
