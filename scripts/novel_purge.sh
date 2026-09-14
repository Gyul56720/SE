#!/usr/bin/env bash
# **VM 안의 소설 원고를 치운다.** `.github/workflows/novel-purge.yml` 이 SSH 로 부른다.
#
#   scripts/novel_purge.sh <모드> <범위> [소설디렉터리]
#     모드   list   무엇이 있는지 보기만 한다 (기본)
#            delete 실제로 지운다
#     범위   output 파이프라인이 낳은 원고만 (기본)
#            all    표본 말뭉치(corpus·holdout)까지
#     디렉터리 기본 /home/ubuntu/SE/novel -- 검사가 가짜 나무를 준다
#
# **되돌릴 수 없다.** 원고는 전부 .gitignore 라 깃 어디에도 사본이 없다. 그래서 기본이
# list 이고, 지우는 것은 `delete` 를 명시해야 한다.
#
# 왜 배포에 안 넣었나: 배포에 `rm` 을 넣으면 **배포마다** 지운다. 파이프라인이 다시
# 원고를 낳으면 다음 배포가 또 지운다 -- 한 번 치우는 것과 파이프라인을 무력화하는
# 것은 다르다. 그래서 손으로 켜는 워크플로가 이것을 부른다.
#
# 한글 변수명을 쓰지 않는다 -- bash 는 식별자로 [A-Za-z_][A-Za-z0-9_]* 만 받는다
# (실측 2026-09-09: `scripts/seek.sh` 가 그것 때문에 한 줄도 안 돌았다. CLAUDE.md).
set -eu
mode="${1:-list}"
scope="${2:-output}"
dir="${3:-/home/ubuntu/SE/novel}"

[ -d "$dir" ] || { echo "$dir 가 없다 -- 아무것도 안 한다" >&2; exit 2; }
case "$mode"  in list|delete) ;; *) echo "모드는 list 또는 delete" >&2; exit 2;; esac
case "$scope" in output|all)  ;; *) echo "범위는 output 또는 all"  >&2; exit 2;; esac
cd "$dir"
echo "mode=$mode  scope=$scope  dir=$dir"

# **지키는 것을 먼저 적는다.** 여기 있는 것은 절대 안 지운다.
#   knu/             KnuSentiLex 감성사전 -- 남의 자료. turn.py 가 읽는다
#   targets.json     표본에서 온 수. 없으면 게이트가 옛 짐작으로 물러선다
#                    (실측: '대사 몫 0.35~0.65' 로 떨어져 나흘치 커밋이 전부 빨갰다)
#   directives.json  같은 부류 -- 설정이지 원고가 아니다
#   plan.json        추적되는 파일이다
#   *.py *.md        코드와 설계 문서
#
# 지우는 것은 .gitignore 의 '원고' 규칙과 한 줄씩 맞춘 것이다.
list_output() {
  find . -maxdepth 1 -type f \( \
       -name '*.json'          -o -name '*.scenes.jsonl' -o -name '*.debt.jsonl' \
    -o -name '*.bak'           -o -name '*_drift.txt'    -o -name 'drift.json.*'  \
    -o -name 'baseline_*.txt'  -o -name 'final.txt'      -o -name 'tune.jsonl'    \
    -o -name 'corpus_report.txt' -o -name '*_1-3화.txt' \) \
    ! -name 'targets.json' ! -name 'directives.json' ! -name 'plan.json' -print
}
list_corpus() {
  for d in corpus holdout; do
    [ -d "$d" ] && find "$d" -type f -print
  done
  return 0
}

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
list_output > "$tmp"
[ "$scope" = "all" ] && list_corpus >> "$tmp"
sort -o "$tmp" "$tmp"

n=$(wc -l < "$tmp")
echo "== 걸린 것 ${n}개 =="
if [ "$n" -gt 0 ]; then
  # 크기까지 찍는다 -- 지우고 나면 이 로그가 남는 유일한 기록이다
  xargs -d '\n' -r du -h -- < "$tmp" | sort -h
  echo "-- 합계 --"
  xargs -d '\n' -r du -ch -- < "$tmp" | tail -1
fi

# **안 지우는데 거기 있는 것**도 찍는다. 빠뜨린 원고가 있으면 여기 눈에 보인다.
echo "== 남는 것 (맨 위 칸, 위 목록 밖) =="
find . -maxdepth 1 -mindepth 1 ! -name '__pycache__' -print | sort | grep -vxF -f "$tmp" || true

if [ "$mode" != "delete" ]; then
  echo "== list 모드 -- 아무것도 안 지웠다 =="
  exit 0
fi

xargs -d '\n' -r rm -f -- < "$tmp"
[ "$scope" = "all" ] && { rmdir corpus holdout 2>/dev/null || true; }
echo "== 지웠다 =="
