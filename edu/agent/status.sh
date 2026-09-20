#!/usr/bin/env bash
# 지금 무엇을 하고 있나 -- 기억이 아니라 파일에서 읽는다.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${SE_LEDGER_ROOT:+$SE_LEDGER_ROOT/verif}"
ROOT="${ROOT:-$HERE/ledger}"

echo "== 프로세스 =="
pgrep -af "agent.py" || echo "(돌고 있지 않다)"
echo
echo "== 상태 =="
[ -f "$ROOT/status.json" ] && cat "$ROOT/status.json" || echo "(status.json 없음)"
echo
echo "== 최근 빨간불 =="
if [ -f "$ROOT/regress.jsonl" ]; then
  grep -c '"판정": "초록"' "$ROOT/regress.jsonl" | sed 's/^/초록 바퀴: /'
  grep '빨간불\|믿을 수 없다\|실행 실패\|안 건드렸다' "$ROOT/regress.jsonl" | tail -5
else
  echo "(원장 없음)"
fi
