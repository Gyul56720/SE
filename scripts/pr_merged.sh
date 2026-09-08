#!/usr/bin/env bash
# **머지됐는지만 묻는다.** 명령을 주기 직전에 이것을 통과해야 한다.
#
# 왜 있나(실측 2026-09-08, 같은 날 다섯 번): PR #57·#62·#64·#66·#67 을 머지하지 않은
# 채 "git pull 하고 돌려 보세요" 라고 답했다. 사용자는 다섯 번 다 바뀌지 않은 숫자를
# 보았고, 그 숫자로 잘못된 판단을 했다. 기억으로 "머지했다" 고 여기지 말고 물어라.
#
#   scripts/pr_merged.sh 67
#     0  머지됨      -- 명령을 줘도 된다
#     1  머지 안 됨  -- 명령을 주지 마라
#     2  **모르겠다** -- 조회 실패. 모르는 것은 안 된 것으로 다룬다
#
# 첫 판은 `"merged":true` 로만 찾다가 **머지된 PR 을 안 됐다고 답했다** -- 깃허브가
# `"merged": true` 처럼 공백을 넣어 보낸다. 거짓 음성을 내는 장치는 없느니만 못하다.
set -u
n="${1:-}"
[ -z "$n" ] && { echo "쓰기: $0 <PR번호>" >&2; exit 2; }
repo="${SE_REPO:-Gyul56720/SE}"
j=$(curl -sS -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$repo/pulls/$n" 2>/dev/null)

merged=$(printf '%s' "$j" | grep -oE '"merged"[[:space:]]*:[[:space:]]*(true|false)' | head -1)
if [ -z "$merged" ]; then
  echo "PR #$n 을 조회하지 못했다 -- **모르는 것은 안 된 것으로 다룬다.** 명령을 주지 마라" >&2
  exit 2
fi
case "$merged" in
  *true*) echo "PR #$n 머지됨 -- 명령을 줘도 된다"; exit 0;;
esac
state=$(printf '%s' "$j" | grep -oE '"state"[[:space:]]*:[[:space:]]*"[a-z]+"' | head -1 |
        grep -oE '"[a-z]+"$' | tr -d '"')
echo "PR #$n **머지 안 됨** (state=${state:-?}) -- 명령을 주지 마라" >&2
exit 1
