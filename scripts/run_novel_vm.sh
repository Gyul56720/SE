#!/usr/bin/env bash
# VM 에서 소설 런을 띄운다. Gemini 로 돌고, 셸이 닫혀도 살아남는다.
#
# 왜 스크립트인가. 이 저장소의 CLAUDE.md 가 적어둔 실측이 있다 -- `command &` 로만 띄운
# 백그라운드는 부모가 죽을 때 같이 정리되어, "완료되면 알려드리겠습니다" 라고 답한 뒤에
# 아무것도 생성되지 않은 채 프로세스가 사라져 있었다. setsid + nohup + disown + 표준
# 입출력 리다이렉트를 매번 손으로 쓰면 언젠가 하나를 빠뜨린다.
#
# 사용:
#   scripts/run_novel_vm.sh                       # 새 씨앗 -> 1~5화 (회차 5,000자 = 2만 5천 자)
#   scripts/run_novel_vm.sh --keep                # 지금 씨앗·원고 그대로 이어서 (되살릴 때 이것)
#                                                 (--restart 만 주면 새 씨앗이라 옛 원고는 .bak 로 치워진다)
#   scripts/run_novel_vm.sh --restart             # 돌던 런을 죽이고 다시 (옛 원고는 .bak 로)
#   scripts/run_novel_vm.sh --restart --wipe      # 옛 기록을 .bak 도 없이 **삭제**하고 처음부터
#   scripts/run_novel_vm.sh --persona hardboiled   # 문체를 갈아끼운다
#   scripts/run_novel_vm.sh --episodes 5 --blocks 2
#
# 확인:
#   pgrep -af overnight.py                        # ps -p $! 는 거짓 음성이 난다
#   tail -f logs/novel_seeded.log
#   python3 novel/watch.py --path novel/seeded.json -f
#   python3 novel/read.py  --path novel/seeded.json --ep 1-3
set -u

# **경로는 전부 절대경로로 쓴다.** 상대경로는 사람이 어느 디렉토리에서 쳤느냐에 따라
# 조용히 다른 것을 가리킨다 -- 실측: 홈에서 실행하니 `python3 novel/watch.py` 가
# /home/ubuntu/novel/watch.py 를 찾다 죽었다.
SE="${SE_DIR:-/home/ubuntu/SE}"
LOG="$SE/logs/novel_seeded.log"
BOOK="$SE/novel/seeded.json"
# pgrep 도 절대경로로 부른다. PATH 가 깨진 셸에서 `pgrep` 이 "$SE/pgrep" 으로 해석돼
# "No such file or directory" 가 났다(실측).
PGREP=/usr/bin/pgrep
[ -x "$PGREP" ] || PGREP="$(command -v pgrep 2>/dev/null || echo pgrep)"

cd "$SE" || exit 1

NEW_SEED=1
RESTART=0
WIPE=0
PERSONA=cider
EPISODES=5
BLOCKS=2     # 씨앗 세계는 3+2화 두 블록이다 (5화 x 5,000자 = 2만 5천 자)
HOURS=8     # 5화 x 3씬 = 15씬. 마무리 루프가 남은 예산을 쓴다
for a in "$@"; do
  case "$a" in
    --keep) NEW_SEED=0 ;;
    --restart) RESTART=1 ;;
    --wipe) WIPE=1 ;;
    --persona) shift_next=PERSONA ;;
    --episodes) shift_next=EPISODES ;;
    --blocks) shift_next=BLOCKS ;;
    --hours) shift_next=HOURS ;;
    *) if [ -n "${shift_next:-}" ]; then eval "$shift_next=$a"; shift_next=""; fi ;;
  esac
done

if [ -z "${GEMINI_API_KEY:-}" ] && ! grep -qs '^GEMINI_API_KEY=..' .env; then
  echo "GEMINI_API_KEY 가 없다. .env 에 넣어라 (.env 는 커밋되지 않는다 -- G004 가 막는다)"
  exit 1
fi

# **이미 도는 런이 있으면 띄우지 않는다.** 두 벌이 같은 원고를 쓰면 나중에 저장한 쪽이
# 상대의 산문을 통째로 지운다(실측). overnight.py 안에도 같은 검사가 있지만, 여기서
# 먼저 걸러야 사람이 무엇이 일어났는지 안다.
#
# --restart 는 그것을 죽이고 간다. **원고는 지우지 않는다** -- 죽은 런이 저장해둔
# verified 씬은 그대로 남고, 새 런이 이어서 채운다(재개는 공짜다).
#
# 죽이는 범위에 조심할 것이 두 가지 있다:
#   1. `pkill -f claude` 같은 것을 쓰면 안 된다 -- 이 VM 은 디스코드 봇이 자기 claude -p
#      를 띄우고 있어서 그것까지 죽는다.
#   2. **자기 자신과 부모를 빼야 한다.** pgrep -f 는 명령줄 문자열을 보므로, 이 스크립트를
#      부른 셸의 명령줄에 "overnight.py" 가 들어 있으면 그 셸까지 죽인다 -- 실제로 그렇게
#      제 발을 쐈다(exit 144). overnight.py 의 _refuse_if_running 도 같은 이유로 자기
#      PID 를 뺀다.
PATTERN="novel/overnight.py"

running_pids() {
  "$PGREP" -f "$PATTERN" 2>/dev/null | grep -vx "$$" | grep -vx "$PPID"
}

PIDS="$(running_pids)"
if [ -n "$PIDS" ]; then
  if [ "$RESTART" = "1" ]; then
    echo "돌던 런을 멈춘다:"
    ps -o pid=,etime=,args= -p $(echo "$PIDS" | tr '\n' ' ') 2>/dev/null
    kill $PIDS 2>/dev/null
    for _ in $(seq 1 15); do
      [ -z "$(running_pids)" ] && break
      sleep 1
    done
    LEFT="$(running_pids)"
    if [ -n "$LEFT" ]; then
      echo "  TERM 으로 안 죽는다. KILL 한다"
      kill -9 $LEFT 2>/dev/null
      sleep 2
    fi
    if [ -n "$(running_pids)" ]; then
      echo "  아직 살아 있다. 손으로 확인해라: $PGREP -af $PATTERN"
      exit 1
    fi
    echo "  멈췄다 (원고 novel/seeded.json 은 그대로 남아 있다)"
  else
    echo "이미 도는 런이 있다:"
    ps -o pid=,etime=,args= -p $(echo "$PIDS" | tr '\n' ' ') 2>/dev/null
    echo "죽이고 다시 시작하려면: scripts/run_novel_vm.sh --restart"
    exit 1
  fi
fi

mkdir -p "$SE/logs"
if [ "$NEW_SEED" = "1" ]; then
  # **새 씨앗을 뽑으면 옛 원고를 치운다.** overnight 은 seeded.json 이 있으면 그것을
  # 이어받으므로, 치우지 않으면 옛 인물이 든 원고에 새 세계의 결말이 얹힌다 -- 등장인물
  # 목록에 없는 이름이 척추에 들어가고 V001 이 매 씬을 기각한다(실측: --restart 가
  # 정확히 그 상태를 만들었다).
  #
  # 지우지 않고 **옮긴다.** 몇 시간 쓴 원고를 스크립트가 조용히 지우면 안 된다.
  if [ -f "$BOOK" ] || [ -f "$LOG" ]; then
    if [ "$WIPE" = "1" ]; then
      # 사람이 명시적으로 --wipe 를 줬을 때만 지운다. .bak 까지 전부.
      rm -f "$BOOK" "${BOOK%.json}.scenes.jsonl" "${BOOK%.json}.overnight.json" \
            "$BOOK".*.bak "${BOOK%.json}".*.bak "$LOG" "$LOG".*.bak
      echo "이전 기록을 지웠다 (원고 · 씬 로그 · 요약 · .bak · 실행 로그)"
    else
      STAMP="$(date +%Y%m%d-%H%M%S)"
      for f in "$BOOK" "${BOOK%.json}.scenes.jsonl" "${BOOK%.json}.overnight.json" "$LOG"; do
        [ -f "$f" ] && mv "$f" "$f.$STAMP.bak" && echo "옛 기록을 치웠다: $f.$STAMP.bak"
      done
    fi
  fi
  python3 "$SE/novel/world_seeded.py" --new || exit 1
fi

setsid nohup python3 "$SE/novel/overnight.py" \
    --world seeded --gemini-director --persona "$PERSONA" \
    --blocks "$BLOCKS" --upto-episode "$EPISODES" \
    --hours "$HOURS" --episode-minutes 120 --no-discord \
    > "$LOG" 2>&1 < /dev/null &
disown

sleep 5
if [ -n "$(running_pids)" ]; then
  echo "시작됐다 -- $(running_pids | tr '\n' ' ')"
  echo
  echo "  진행 보기 :  tail -f $LOG"
  echo "  회차별    :  python3 $SE/novel/watch.py --path $BOOK -f"
  echo "  읽기      :  python3 $SE/novel/read.py --path $BOOK --ep 1-10"
  echo "  살아있나  :  $PGREP -af novel/overnight.py"
  echo "  멈추기    :  $SE/scripts/run_novel_vm.sh --restart   (또는 $PGREP -f novel/overnight.py 로 PID 확인 후 kill)"
  echo
  echo "  상태 한 번에:  $SE/scripts/novel_status.sh"
else
  echo "띄우지 못했다. 로그를 봐라:"
  tail -20 "$LOG"
  exit 1
fi
