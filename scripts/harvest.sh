#!/usr/bin/env bash
# 제2의 뇌 한 바퀴 -- systemd timer(deploy/se-harvest.timer)가 두 시간마다 부른다.
#   1) 자(eval/tasks)가 참고를 줘도 틀린 과제의 깃발로 GitHub·HF 에서 참고를 받아 검증·색인
#   2) 새로 색인된 것이 있으면 값을 하는지 재는 것은 사람이 `!평가 과제` 로 (모델 호출 40회+)
# 변수 이름은 영문만 (CLAUDE.md: 셸 스크립트에 한글 변수명을 쓰지 마라).
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
{
  echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) harvest (github/hf + arxiv via 관심·틈)"
  python3 dig/harvest.py --틈 --상한 "${HARVEST_ROUND_CAP:-20}"
  echo "== harvest exit $?"
  # 가장 최근 arxiv 논문 한 편을 코드화해 둔다 -- 수식·알고리즘을 검증된 코드로(약한 검증 포함).
  last=$(python3 -c "import sys; sys.path.insert(0,'.'); from dig import harvest as h; \
rows=[r for r in h.원장읽기() if r.get('종류')=='arxiv-paper']; print(rows[-1]['url'] if rows else '')" 2>/dev/null)
  if [ -n "$last" ]; then
    echo "== codify $last"
    python3 codify/run.py --논문 "$last"
    echo "== codify exit $?"
  fi
} >> logs/harvest.log 2>&1
exit 0
