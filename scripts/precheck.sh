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
# CI 를 기다리던 것과 똑같아진다(없애려던 바로 그 기다림이다). 그래서 상한보다
# 빠른 것만 돌리고, 나머지는 CI 가 뒤늦게 알려 주게 둔다.
# `--전부` 를 주면 CI 가 돌리는 것을 그대로 돌린다.
#
# **어느 검사를 돌릴지 여기 적지 않는다.** 예전에는 파일 이름 54개가 이 줄에 늘어서
# 있었고, 검사를 새로 만들 때마다 사람이 거기 또 적어야 했다(이 세션에서만 여덟 번).
# 안 적으면 그 검사는 밀기 전에 **안 돌았다** -- 목록이 곧 구멍이었다.
# 지금은 `testtimes.py` 가 **재서 고른다**: 아직 안 재 본 것은 돌리므로 새 검사가
# 저절로 들어오고, 상한을 넘은 것만 빠지되 몇 개가 왜 빠지는지 말한다.
if [ "${1:-}" = "--전부" ]; then
    bash scripts/tests.sh
    exit $?
fi

# 돌릴 것을 **재서 고른다.** 못 고르면 초록이라고 하지 않는다 -- 모르는 것은 안 된 것으로 다룬다.
# (자기 검사 `tests/test_precheck.py` 만 testtimes 가 빼 준다. 여기서 그것을 돌리면 서로를
#  불러서 그 검사의 '실제로 돌려 보기' 대목이 **빈 검사**가 된다.)
limit="${PRECHECK_LIMIT:-25}"
if ! picked=$(python3 testtimes.py --고르기 --상한 "$limit" --원장저장소 "$root" 2>&1); then
    echo "돌릴 검사를 못 골랐다 -- 모르는 것은 안 된 것으로 다룬다" >&2
    printf '%s\n' "$picked" | tail -5 >&2
    exit 1
fi
skipped=$(python3 testtimes.py --보기 --상한 "$limit" --원장저장소 "$root" 2>/dev/null \
          | sed -n 's/.*돌리고 \([0-9][0-9]*\)개 건너뛴다.*/\1/p' | head -1)
skipped=${skipped:-0}

bad=0
ran=0
redlist=""
while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ -e "$f" ] || continue
    t0=$(date +%s.%N)
    if out=$(timeout "${PRECHECK_TEST_TIMEOUT:-300}" python3 "$f" 2>&1); then rc=0; else rc=$?; fi
    t1=$(date +%s.%N)
    secs=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.2f", b-a}')
    # **잰 것을 진짜 저장소에 남긴다**(여기는 곧 지워질 워크트리다). 다음번엔 이 숫자로 고른다.
    python3 testtimes.py --적기 "$f" "$secs" --원장저장소 "$root" >/dev/null 2>&1 || true
    ran=$((ran + 1))
    if [ "$rc" -eq 0 ]; then
        printf '  OK   %-34s %6ss\n' "$(basename "$f")" "$secs"
    else
        printf '  실패 %-34s %6ss\n' "$(basename "$f")" "$secs"
        printf '%s\n' "$out" | tail -5 | sed 's/^/         /'
        bad=$((bad + 1))
        redlist="$redlist$f
"
    fi
done <<EOF
$picked
EOF
echo
if [ "$bad" -gt 0 ]; then
    # **내가 깬 것인가, 원래 빨갰던 것인가.** 목록에 적어 빼지 않는다 -- 갈림점에서
    # 같은 검사를 실제로 돌려 본다. 빨간 것만 돌리므로 싼다.
    #
    # 왜 필요한가: 돌릴 것을 재서 고르게 되면서 예전 목록에 없던 검사까지 들어왔고,
    # 그중에 **이 커밋과 무관하게 이미 빨간 것**이 있다. 그것 때문에 밀기가 막히면
    # 사람이 다시 목록을 만들게 된다 -- 없애려던 바로 그 목록이다.
    # 그렇다고 조용히 넘기지도 않는다: 몇 개가 왜 빨간지 그대로 적는다.
    base=$(git -C "$root" merge-base HEAD origin/main 2>/dev/null || true)
    if [ -z "$base" ]; then
        echo "빠른 검사에서 $bad 개 실패. 갈림점을 몰라 **전부 내 탓으로 친다** -- 밀지 마라"
        exit 1
    fi
    btmp=$(mktemp -d) || exit 1
    if ! git -C "$root" worktree add --detach "$btmp" "$base" >/dev/null 2>&1; then
        echo "빠른 검사에서 $bad 개 실패. 갈림점 판을 못 꺼냈다 -- 모르는 것은 안 된 것으로 다룬다"
        exit 1
    fi
    mine=0
    old=0
    echo "빨간 $bad 개를 갈림점 $(git -C "$root" rev-parse --short "$base") 에서 다시 돌린다:"
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        if [ ! -e "$btmp/$f" ]; then
            printf '    내 탓 %-34s (갈림점엔 없던 검사다)\n' "$(basename "$f")"
            mine=$((mine + 1)); continue
        fi
        if (cd "$btmp" && timeout "${PRECHECK_TEST_TIMEOUT:-300}" python3 "$f" >/dev/null 2>&1); then
            printf '    내 탓 %-34s (갈림점에선 초록이었다)\n' "$(basename "$f")"
            mine=$((mine + 1))
        else
            printf '    원래  %-34s (갈림점에서도 빨강 -- 이 커밋이 깬 것이 아니다)\n' "$(basename "$f")"
            old=$((old + 1))
        fi
    done <<EOF
$redlist
EOF
    git -C "$root" worktree remove --force "$btmp" >/dev/null 2>&1
    rm -rf "$btmp"
    echo
    if [ "$mine" -gt 0 ]; then
        echo "**내가 깬 것 $mine 개** -- 밀지 마라 (원래 빨갰던 것 $old 개는 따로)"
        exit 1
    fi
    echo "빨간 $old 개는 전부 갈림점에서도 빨강이다 -- 이 커밋이 깬 것은 없다."
    echo "그래도 **초록이라고 말하지 않는다**: 위 목록을 그대로 사람에게 적어라."
fi
echo "빠른 검사 $ran 개 통과. 상한($limit 초)을 넘어 건너뛴 $skipped 개는 CI 가 알려 준다 (--전부 로 여기서 다 돌린다)"
