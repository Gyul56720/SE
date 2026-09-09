#!/usr/bin/env bash
# coin 파이프라인 러너.
#
#   scripts/coin.sh ask "비트코인 시장 분석해줘"   물어본다
#   scripts/coin.sh look "SOL -12% 왜 이래"        모델 없이 무엇이 잡혔나
#   scripts/coin.sh fill                           원장 채우기 (백그라운드)
#   scripts/coin.sh watch [hours]                  계속 모으기 (기본 24시간, 백그라운드)
#   scripts/coin.sh stop                           모으기 멈추기
#   scripts/coin.sh status                         원장 · 채우기 상태
#   scripts/coin.sh probe                          어느 출처가 답하나
#   scripts/coin.sh grid                           나라 x 층 격자. 빈 칸을 짚는다
#   scripts/coin.sh find                           선언 안 한 출처 찾기 (표엔 안 넣는다)
#
# **변수 이름을 한글로 쓰지 않는다** -- bash 는 식별자로 [A-Za-z_][A-Za-z0-9_]* 만
# 받는다. `초=25` 는 대입이 아니라 명령어로 파싱되고 set -u 아래에서 죽는다
# (CLAUDE.md '## 셸 스크립트에 한글 변수명을 쓰지 마라', 실측 2026-09-09).
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root" || exit 3
log="$root/logs/coin_fill.log"
cmd="${1:-}"

case "$cmd" in
  ask)   shift; exec python3 coin/run.py --물음 "$*" ;;
  look)  shift; exec python3 coin/run.py --물음 "$*" --상황만 ;;
  probe) exec python3 coin/news.py --탐침 ;;
  grid)  exec python3 coin/news.py --격자 ;;
  find)  exec python3 coin/watch.py --찾기 ;;
  fill)
    if pgrep -af "coin/run.py --채우기" >/dev/null 2>&1; then
      echo "이미 돌고 있다:"; pgrep -af "coin/run.py --채우기"; exit 0
    fi
    mkdir -p "$root/logs"
    setsid nohup python3 coin/run.py --채우기 > "$log" 2>&1 < /dev/null &
    disown
    sleep 2
    # **`ps -p $!` 가 아니라 pgrep 이다.** setsid 는 프로세스 그룹 리더면 fork 하므로
    # $! 는 이미 끝난 래퍼의 PID 다 (CLAUDE.md, 실측).
    if pgrep -af "coin/run.py --채우기" >/dev/null 2>&1; then
      echo "떴다:"; pgrep -af "coin/run.py --채우기"; echo "로그: $log"
    else
      echo "못 띄웠다 -- 로그를 봐라: $log" >&2; tail -20 "$log" 2>/dev/null; exit 3
    fi
    ;;
  watch)
    hours="${2:-24}"
    if pgrep -af "coin/watch.py" >/dev/null 2>&1; then
      echo "이미 모으고 있다:"; pgrep -af "coin/watch.py"; exit 0
    fi
    mkdir -p "$root/logs"
    wlog="$root/logs/coin_watch.log"
    setsid nohup python3 coin/watch.py --시간 "$hours" --흐름 \
        > "$wlog" 2>&1 < /dev/null &
    disown
    sleep 3
    if pgrep -af "coin/watch.py" >/dev/null 2>&1; then
      echo "떴다:"; pgrep -af "coin/watch.py"; echo "로그: $wlog"
      echo "--- 로그 첫 줄 ---"; head -3 "$wlog" 2>/dev/null
      echo "**프로세스가 살아 있는 것과 일을 하는 것은 다르다 -- 로그에 줄이 쌓이는지 봐라**"
    else
      echo "못 띄웠다 -- 로그를 봐라: $wlog" >&2; tail -20 "$wlog" 2>/dev/null; exit 3
    fi
    ;;
  stop)
    # **pkill -f 를 쓰지 않는다** -- 명령줄에 그 패턴이 들어 있으면 자기 셸까지 죽는다
    # (CLAUDE.md, 실측). pgrep 으로 PID 를 먼저 보고 그 PID 를 죽인다.
    pids="$(pgrep -f "coin/watch.py" || true)"
    if [ -z "$pids" ]; then echo "모으는 중인 것 없음"; exit 0; fi
    echo "멈춘다: $pids"
    for p in $pids; do kill "$p" 2>/dev/null || true; done
    sleep 2
    pgrep -af "coin/watch.py" || echo "멈췄다"
    ;;
  status)
    if pgrep -af "coin/watch.py" >/dev/null 2>&1; then
      echo "모으는 중:"; pgrep -af "coin/watch.py"
      [ -f "$root/logs/coin_watch.log" ] && tail -3 "$root/logs/coin_watch.log" | sed 's/^/    /'
    else
      echo "모으는 중인 것 없음"
    fi
    if pgrep -af "coin/run.py --채우기" >/dev/null 2>&1; then
      echo "채우는 중:"; pgrep -af "coin/run.py --채우기"
      [ -f "$log" ] && tail -5 "$log" | sed 's/^/    /'
    else
      echo "채우는 중인 것 없음"
    fi
    python3 coin/ledger.py --보기 2>&1 | head -3
    python3 coin/news.py --덮임 2>&1 | head -4
    ;;
  *) sed -n '2,12p' "$0" ;;
esac
