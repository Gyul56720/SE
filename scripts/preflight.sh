#!/usr/bin/env bash
# **밤새 도는 것을 띄우기 전에 걸릴 것을 전부 걸러 낸다.**
#
# 학습이 중간에 끊기는 이유는 대개 셋이다: 키가 없거나, 디스크가 찼거나, 표본·목표가
# 준비가 안 됐거나. 셋 다 시작하고 20분 뒤에 로그에서 발견하면 그 20분이 날아간다.
# 여기서 먼저 본다. **하나라도 걸리면 무엇을 하라고 말하고 0 이 아닌 값으로 끝난다.**
set -u
SE="${SE_DIR:-/home/ubuntu/SE}"
cd "$SE" || exit 1
bad=0
ok()   { printf '  OK   %s\n' "$*"; }
no()   { printf '  실패 %s\n' "$*"; bad=$((bad + 1)); }
warn() { printf '  주의 %s\n' "$*"; }

echo "[준비] 밤새 돌 수 있는 상태인가"

# 1. 키 -- 없으면 첫 호출에서 죽고 로그에만 이유가 남는다
if [ -f "$SE/.env" ]; then
  set -a; . "$SE/.env"; set +a
fi
python3 - <<'PY' && ok "Gemini 키가 있다" || no "Gemini 키가 없다 -- $SE/.env 를 확인해라"
import os, sys
sys.exit(0 if any(os.getenv(k) for k in
    ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEYS")) else 1)
PY

# 2. 한도 -- 지금 부를 수 있는 후보가 있나
if python3 scripts/quota_show.py --brief; then
  ok "쓸 수 있는 후보가 있다"
else
  warn "지금은 다 소진이다 -- 루프가 알아서 기다린다(자정에 풀린다)"
fi

# 3. 디스크 -- 원고와 로그가 쌓인다
avail=$(df -Pk "$SE" | awk 'NR==2 {print $4}')
if [ "${avail:-0}" -gt 1048576 ]; then ok "디스크 여유 $((avail / 1024))MB"
else no "디스크가 모자란다($((${avail:-0} / 1024))MB) -- logs/ 와 옛 원고를 지워라"; fi

# 4. 표본과 목표 -- 학습의 재료
[ -d "$SE/novel/corpus" ] && ok "표본 폴더가 있다" || no "novel/corpus 가 없다"
n=$(find "$SE/novel/corpus" -name '*.txt' 2>/dev/null | wc -l)
[ "$n" -gt 20 ] && ok "잘라 둔 토막 ${n}개" \
  || no "토막이 ${n}개뿐이다 -- python3 novel/corpus.py novel/corpus --write 를 먼저 돌려라"
python3 - <<'PY' && ok "목표값이 표본에서 왔다" || no "targets.json 이 비었다 -- scripts/targets_update.py 를 돌려라"
import sys
sys.path.insert(0, ".")
from novel import targets as T
sys.exit(0 if T.load() and T.source() else 1)
PY

# 5. 프롬프트가 실제로 만들어지나 -- 여기서 죽으면 첫 덩어리부터 못 쓴다
python3 - <<'PY' && ok "프롬프트가 만들어진다" || no "프롬프트를 못 만든다"
import sys
sys.path.insert(0, ".")
from novel import flow
b = flow.blank()
p = flow.write_prompt(b)
b["chunks"] = ["가" * 3000]
q = flow.write_prompt(b)
sys.exit(0 if len(p) > 300 and len(q) > 300 else 1)
PY

# 6. 테스트 -- 깨진 채로 밤새 돌리지 않는다
# 설정이 다 있는 기계에서만 깨지는 검사가 없는지도 같이 본다 -- 네 번 겪었다.
if SE_TEST_AS_CONFIGURED=1 scripts/tests.sh > /tmp/preflight_tests.log 2>&1; then
  ok "테스트 $(grep -c '^  OK' /tmp/preflight_tests.log)개 통과"
else
  no "테스트가 깨져 있다 -- tail -30 /tmp/preflight_tests.log"
fi

# 7. 이미 돌고 있나 -- 두 벌이 같은 원고를 쓰면 서로 덮어쓴다
if /usr/bin/pgrep -af "tune_loop.sh|novel/flow.py" | grep -qv pgrep; then
  no "이미 도는 것이 있다 -- scripts/tune_loop.sh --stop 으로 세우고 다시 해라"
else
  ok "겹쳐 도는 것이 없다"
fi

# 8. 쓸 수 있나
mkdir -p "$SE/logs/tune" 2>/dev/null && touch "$SE/logs/.w" 2>/dev/null \
  && rm -f "$SE/logs/.w" && ok "로그를 쓸 수 있다" || no "logs/ 에 못 쓴다"

echo
if [ "$bad" -gt 0 ]; then
  echo "준비 안 됐다 -- $bad 군데. 위에 적힌 대로 고치고 다시 돌려라."
  exit 1
fi
echo "준비 됐다. scripts/run_all.sh --bg 로 띄워라."
