#!/usr/bin/env bash
# **끊기지 않는 학습 루프.** 한 바퀴가 사람 손을 안 탄다.
#
#   1) 이어 쓴다        drift 를 CHARS 자만큼   (Gemini · 덩어리당 호출 3회)
#   2) 잰다             score.py               (호출 0)
#   3) 설정을 센다      arms.py                (호출 0 · 덩어리마다 다른 팔이 배정돼 있다)
#   4) 지시문을 고친다  tuner.py try           (claude -p 한 번 · 원문은 안 준다)
#   5) 다시 쓰고 견준다 다음 바퀴의 점수로 채택하거나 되돌린다
#
# **중간에 끊기지 않게** 하는 것들:
#   · setsid + nohup + disown -- 부모(claude -p)가 죽어도 안 죽는다(CLAUDE.md 의 그 규칙)
#   · 한 단계가 실패해도 루프는 안 멈춘다. 실패는 로그에 남기고 다음 바퀴로 간다
#   · 멈추는 길은 하나뿐이다: STOP 파일을 만든다
#   · 바퀴마다 원고와 장부를 백업한다 -- 되돌릴 수 없으면 최적화가 아니다
#
#   scripts/tune_loop.sh              앞에서 돈다(확인용)
#   scripts/tune_loop.sh --bg         백그라운드로 띄운다  <- 이걸 쓴다
#   scripts/tune_loop.sh --stop       멈춘다
#   scripts/tune_loop.sh --status     어디까지 왔나
set -u
SE="${SE_DIR:-/home/ubuntu/SE}"
BOOK="${BOOK:-$SE/novel/drift.json}"
LOG="$SE/logs/tune_loop.log"
STOP="$SE/logs/tune_loop.stop"
CHARS="${CHARS:-8000}"        # 한 바퀴에 이어 쓸 분량
ROUNDS="${ROUNDS:-40}"        # 몇 바퀴까지
KEEP="${KEEP:-8}"             # 원고 백업 몇 개까지 남기나

cd "$SE" || exit 1
mkdir -p "$SE/logs" "$SE/logs/tune"

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

case "${1:-}" in
  --stop)
    touch "$STOP"; echo "멈추라고 적어 뒀다. 이번 바퀴를 마치고 선다: $STOP"; exit 0 ;;
  --status)
    echo "== 살아 있나"; /usr/bin/pgrep -af "tune_loop.sh" | grep -v -- --status || echo "  안 돈다"
    echo "== 최근 로그"; tail -20 "$LOG" 2>/dev/null || echo "  아직 없다"
    echo "== 점수"; python3 novel/score.py "$BOOK" 2>/dev/null | tail -6
    echo "== 설정별 성적"; python3 novel/arms.py "$BOOK" 2>/dev/null | tail -10
    echo "== 한도"; python3 scripts/quota_show.py --brief 2>/dev/null
    exit 0 ;;
  --bg)
    rm -f "$STOP"
    setsid nohup "$0" > "$LOG" 2>&1 < /dev/null &
    disown
    sleep 2
    if /usr/bin/pgrep -af "tune_loop.sh" | grep -qv -- "--bg"; then
      echo "띄웠다. 로그: $LOG"
      echo "  멈추려면: scripts/tune_loop.sh --stop"
      echo "  보려면:   scripts/tune_loop.sh --status"
    else
      echo "안 떴다. 로그를 봐라: $LOG" >&2; exit 1
    fi
    exit 0 ;;
esac

rm -f "$STOP"
say "루프 시작 -- 한 바퀴 ${CHARS}자 · 최대 ${ROUNDS}바퀴"

for round in $(seq 1 "$ROUNDS"); do
  [ -f "$STOP" ] && { say "멈추라는 표시가 있다. 선다."; break; }

  # **쓸 것이 없으면 두드리지 않는다.** 다 소진된 채로 계속 부르면 429 만 쌓이고
  # 로그가 그것으로 덮인다. 자정에 하루치가 풀리므로 기다리는 편이 싸다.
  tries=0
  until python3 scripts/quota_show.py --brief >> "$LOG" 2>&1; do
    tries=$((tries + 1))
    [ -f "$STOP" ] && break
    if [ "$tries" -gt 48 ]; then
      say "[$round] 네 시간을 기다려도 한도가 안 풀린다. 그래도 한 번 해 본다"
      break
    fi
    say "[$round] 쓸 후보가 없다 -- 5분 쉰다 ($tries번째)"
    sleep 300
  done
  [ -f "$STOP" ] && { say "멈추라는 표시가 있다. 선다."; break; }

  say "[$round] 이어 쓴다"
  if [ -f "$BOOK" ]; then
    scripts/drift.sh go "$CHARS" >> "$LOG" 2>&1
  else
    scripts/drift.sh start "$CHARS" >> "$LOG" 2>&1
  fi
  # drift.sh 는 백그라운드로 띄우고 바로 돌아온다. 끝날 때까지 기다린다.
  waited=0
  while /usr/bin/pgrep -f "novel/flow.py" > /dev/null; do
    sleep 20
    waited=$((waited + 20))
    if [ "$waited" -gt 5400 ]; then           # 한 시간 반이면 뭔가 걸린 것이다
      say "[$round] 너무 오래 걸린다. 이번 바퀴는 넘긴다"
      break
    fi
  done

  [ -f "$BOOK" ] || { say "[$round] 원고가 없다. 다음 바퀴"; continue; }
  cp "$BOOK" "$SE/logs/tune/drift.$round.json" 2>/dev/null
  ls -1t "$SE/logs/tune/drift."*.json 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f

  say "[$round] 잰다"
  python3 novel/score.py "$BOOK" >> "$LOG" 2>&1
  python3 novel/arms.py "$BOOK" >> "$LOG" 2>&1

  # 앞 바퀴에서 고친 것이 있으면 여기서 채택하거나 되돌린다.
  python3 novel/tuner.py keep "$BOOK" >> "$LOG" 2>&1

  say "[$round] 지시문 하나를 고친다"
  if ! python3 novel/tuner.py try "$BOOK" >> "$LOG" 2>&1; then
    say "[$round] 고치기가 실패했다 -- 지시문은 그대로 두고 다음 바퀴로 간다"
  fi

  # 팔이 충분히 쌓였으면 이긴 설정을 굳힌다(실패해도 그냥 간다).
  python3 novel/arms.py "$BOOK" --apply >> "$LOG" 2>&1 || true
done

say "루프 끝. 점수:"
python3 novel/score.py "$BOOK" 2>&1 | tail -8 | tee -a "$LOG"
