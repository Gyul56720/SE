#!/usr/bin/env bash
# 밀기 직전 **깨끗한 판**에서 검사를 돌린다.
#
# 왜 있나: CI 를 기다리지 않기로 했는데(CLAUDE.md '## CI 를 기다리지 않는다'),
# CI 가 혼자 잡아 주던 것이 딱 하나 있다 -- **커밋에 안 담긴 파일.**
# `git add` 를 빠뜨려도 내 작업 디렉터리에는 그 파일이 있으므로 `scripts/tests.sh`
# 는 초록불을 낸다. 그런데 남이 받아 가는 것은 커밋된 나무뿐이다. 그러면 사용자가
# "그런 파일 없다" 를 보게 되고, 그것이 이 저장소가 다섯 번 앓은 바로 그 병이다.
#
# 그래서 HEAD 를 임시 워크트리로 꺼내 거기서 돌린다. 작업 디렉터리를 안 본다.
#
#     bash scripts/precheck.sh          # HEAD 를 검사
#
# 0 통과 · 1 실패. **실패면 밀지 마라.**
set -u

# **되돌이를 막는다.** `tests/test_precheck.py` 가 이 스크립트를 실제로 돌려 보는데,
# 이 스크립트는 그 검사를 다시 돌린다 -- 그러면 워크트리를 파며 끝없이 내려간다.
# 실측: 프로세스 넷이 /tmp/tmp.*/ 에 워크트리를 파고 돌다가 죽였다. 검사가 8분
# 넘게 안 끝나는 것으로만 보였지 되돌이라는 것은 안 보였다.
if [ -n "${PRECHECK_RUNNING:-}" ]; then
    echo "precheck 안에서는 precheck 를 안 돌린다 (되돌이 방지)"
    exit 0
fi
export PRECHECK_RUNNING=1

root=$(git rev-parse --show-toplevel) || exit 1
tmp=$(mktemp -d) || exit 1
trap 'git -C "$root" worktree remove --force "$tmp" >/dev/null 2>&1; rm -rf "$tmp"' EXIT

if ! git -C "$root" worktree add --detach "$tmp" HEAD >/dev/null 2>&1; then
    echo "깨끗한 판을 못 꺼냈다 -- 모르는 것은 안 된 것으로 다룬다" >&2
    exit 1
fi

# 커밋 안 된 것이 있으면 먼저 말한다. 담을 생각이었는데 안 담긴 것일 수 있다.
# **변수 이름은 한글로 못 쓴다.** 처음에 `남` 이라 썼다가 bash 가 그 줄을 명령으로
# 읽었다(`남: command not found`). 그런데 `tests.sh` 의 종료 코드로만 판정하고
# 있어서 **스크립트가 반쯤 죽은 채로 초록불을 냈다.**
dirty=$(git -C "$root" status --porcelain | grep -v '^!!' || true)
if [ -n "$dirty" ]; then
    echo "커밋 안 된 것이 있다 (검사는 HEAD 로만 돈다):"
    printf '%s\n' "$dirty" | sed 's/^/    /'
    echo
fi

echo "깨끗한 판에서 검사: $(git -C "$root" rev-parse --short HEAD)"
cd "$tmp" || exit 1

# **기본은 빠른 길이다.** 전체 검사는 6분 넘게 걸린다 -- 그것을 여기서 기다리면
# CI 를 기다리던 것과 똑같아진다(없애려던 바로 그 기다림이다). 그래서 기본은
# 이 저장소에서 내가 손대는 자리인 law · lol · brief · brain · reason · jaso 검사만
# 돌리고, 나머지는 CI 가 뒤늦게
# 알려 주게 둔다. `--전부` 를 주면 CI 가 돌리는 것을 그대로 돌린다.
if [ "${1:-}" = "--전부" ]; then
    bash scripts/tests.sh
    exit $?
fi

bad=0
# **자기 검사는 여기서 안 돌린다.** `tests/test_precheck.py` 가 이 스크립트를 실제로
# 돌려 보므로, 여기서 그것을 돌리면 서로를 부른다. 빗장(PRECHECK_RUNNING)이 깊이를
# 막긴 하지만, 그러면 그 검사의 '실제로 돌려 보기' 대목이 **빈 검사가 된다** --
# 통과했다는 말만 남고 아무것도 안 본 것이다. 그 검사는 따로 돌린다(CI 와 손으로).
for f in tests/test_law_*.py tests/test_lol_*.py tests/test_brief*.py tests/test_jaso_*.py tests/test_coin_*.py tests/test_dig.py tests/test_dig_더캐기.py tests/test_study.py tests/test_channels.py tests/test_discord_check.py tests/test_말과_한것.py tests/test_brain.py tests/test_reason.py tests/test_pr_merged.py; do
    [ -e "$f" ] || continue
    if out=$(python3 "$f" 2>&1); then
        printf '  OK   %s\n' "$(basename "$f")"
    else
        printf '  실패 %s\n' "$(basename "$f")"
        printf '%s\n' "$out" | tail -5 | sed 's/^/         /'
        bad=$((bad + 1))
    fi
done
echo
if [ "$bad" -gt 0 ]; then
    echo "빠른 검사에서 $bad 개 실패 -- **밀지 마라**"
    exit 1
fi
echo "빠른 검사 통과. 나머지는 CI 가 뒤늦게 알려 준다 (--전부 로 여기서 다 돌릴 수 있다)"
