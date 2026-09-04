#!/usr/bin/env bash
# VM 에서 소설 런을 띄운다. Gemini 로 돌고, 셸이 닫혀도 살아남는다.
#
# 왜 스크립트인가. 이 저장소의 CLAUDE.md 가 적어둔 실측이 있다 -- `command &` 로만 띄운
# 백그라운드는 부모가 죽을 때 같이 정리되어, "완료되면 알려드리겠습니다" 라고 답한 뒤에
# 아무것도 생성되지 않은 채 프로세스가 사라져 있었다. setsid + nohup + disown + 표준
# 입출력 리다이렉트를 매번 손으로 쓰면 언젠가 하나를 빠뜨린다.
#
# 사용:
#   scripts/run_novel_vm.sh                       # 새 씨앗 -> 1~3화
#   scripts/run_novel_vm.sh --keep                # 지금 씨앗 그대로 이어서
#   scripts/run_novel_vm.sh --restart             # 돌던 런을 죽이고 다시 (원고는 남는다)
#   scripts/run_novel_vm.sh --episodes 5 --blocks 2
#
# 확인:
#   pgrep -af overnight.py                        # ps -p $! 는 거짓 음성이 난다
#   tail -f logs/novel_seeded.log
#   python3 novel/watch.py --path novel/seeded.json -f
#   python3 novel/read.py  --path novel/seeded.json --ep 1-3
set -u
cd "${SE_DIR:-/home/ubuntu/SE}" || exit 1

NEW_SEED=1
RESTART=0
EPISODES=3
BLOCKS=1
HOURS=6
for a in "$@"; do
  case "$a" in
    --keep) NEW_SEED=0 ;;
    --restart) RESTART=1 ;;
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
  pgrep -f "$PATTERN" 2>/dev/null | grep -vx "$$" | grep -vx "$PPID"
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
      echo "  아직 살아 있다. 손으로 확인해라: pgrep -af $PATTERN"
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

mkdir -p logs
if [ "$NEW_SEED" = "1" ]; then
  python3 -m novel.world_seeded --new || exit 1
fi

LOG="logs/novel_seeded.log"
setsid nohup python3 novel/overnight.py \
    --world seeded --gemini-director \
    --blocks "$BLOCKS" --upto-episode "$EPISODES" \
    --hours "$HOURS" --episode-minutes 120 --no-discord \
    > "$LOG" 2>&1 < /dev/null &
disown

sleep 5
if [ -n "$(running_pids)" ]; then
  echo "시작됐다 -- $(running_pids | tr '\n' ' ')"
  echo "로그: $(pwd)/$LOG"
  echo "원고: $(pwd)/novel/seeded.json"
else
  echo "띄우지 못했다. 로그를 봐라:"
  tail -20 "$LOG"
  exit 1
fi
