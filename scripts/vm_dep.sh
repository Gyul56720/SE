#!/usr/bin/env bash
# **VM 에 그 꾸러미가 깔렸는지만 묻는다.** 사람에게 `pip install` 을 시키기 전에.
#
# 왜 있나(실측 2026-09-14): "VM 에 반영하려면 pip install -r requirements.txt 가
# 필요하다" 고 답했다. **틀렸다.** `deploy-oracle.yml` 이 배포마다
# `pip3 install --break-system-packages -r requirements.txt` 를 돌린다. 12:55:51Z 에
# 이미 `Successfully installed numpy-2.5.3 scipy-1.18.1` 이 찍혀 있었다.
#
# 사용자는 같은 말을 세 번 했고(2026-09-12) 그래서 G021 이 생겼다 --
# "사람 몫으로 넘기는 건 최종이라고." · "그 판단을 왜 스스로 못하냐고."
# G021 은 apt 만 본다. pip 은 "배포가 이미 깐다" 며 안 본다. 그 말은 맞지만,
# **깔렸는지 확인할 길이 없었다.** 없으니 기억으로 답했고 틀렸다. 여기가 그 길이다.
#
#   scripts/vm_dep.sh scipy
#     0  깔렸다      -- 사람에게 설치를 시키지 마라
#     1  안 깔렸다   -- requirements.txt 에 넣고 main 에 머지해라. 그래도 사람은 안 시킨다
#     2  **모르겠다** -- 조회 실패. 모르는 것은 안 된 것으로 다룬다
#
# ## 어떻게 아나 -- 로그를 안 읽는다
#
# 첫 판은 배포 로그에서 `Successfully installed` 를 찾았다. **두 가지가 틀렸다.**
# 하나, 그 로그는 토큰이 있어야 읽히고 없으면 늘 '모르겠다' 가 나온다 -- 늘 모르겠다고
# 답하는 장치는 없느니만 못하다. 둘, pip 의 출력 글꼴에 기대는 것이라 `already
# satisfied` 와 `Successfully installed` 를 둘 다 맞혀야 한다(pr_merged.sh 의 첫 판이
# `"merged":true` 공백 하나에 걸려 거짓 음성을 낸 것과 같은 부류다).
#
# 지금은 로그를 안 본다. 대신 이 사슬을 쓴다:
#
#   마지막으로 **성공한** 배포의 head_sha 를 묻는다      (공개 메타데이터 -- 토큰 불필요)
#   그 커밋의 requirements.txt 를 git 으로 꺼낸다        (이 저장소가 이미 갖고 있다)
#   그 안에 꾸러미가 있나
#
# 있으면 그 배포가 `pip3 install -r requirements.txt` 를 그 파일로 돌렸고, **그 단계가
# 실패했으면 실행이 성공으로 안 끝난다**(ssh-action 은 비영 종료를 그대로 실패로 낸다).
# 그러니 '성공한 배포 + 그 파일에 있음' 은 깔렸다는 뜻이다. 글꼴에 안 기댄다.
#
# 한계를 그대로 적는다: 이것은 **마지막 배포 시점**의 사실이다. 그 뒤에 사람이 VM 에서
# 무엇을 지웠는지는 여기서 모른다. 그 차이가 문제되면 답은 배포를 한 번 더 돌리는 것이지
# 사람에게 설치를 시키는 것이 아니다.
set -u
pkg="${1:-}"
[ -z "$pkg" ] && { echo "쓰기: $0 <꾸러미이름>" >&2; exit 2; }
repo="${SE_REPO:-Gyul56720/SE}"
wf="${SE_DEPLOY_WF:-deploy-oracle.yml}"
req="${SE_REQ:-requirements.txt}"

# SE_DEPLOY_SHA 를 주면 조회를 건너뛴다 -- 검사가 이 스크립트를 **실제로 돌려** 보려고
# 두었다(`bash -n` 은 아무것도 안 잡는다. 실측 2026-09-09 seek.sh 가 한 줄도 안 돌았다).
sha="${SE_DEPLOY_SHA:-}"
if [ -z "$sha" ]; then
  runs=$(curl -sS -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$repo/actions/workflows/$wf/runs?status=success&per_page=1" 2>/dev/null)
  sha=$(printf '%s' "$runs" | grep -oE '"head_sha"[[:space:]]*:[[:space:]]*"[0-9a-f]{40}"' | head -1 |
        grep -oE '[0-9a-f]{40}')
fi
if [ -z "$sha" ]; then
  echo "성공한 배포를 조회하지 못했다 -- **모르는 것은 안 된 것으로 다룬다**" >&2
  exit 2
fi

git cat-file -e "$sha^{commit}" 2>/dev/null || git fetch -q origin "$sha" 2>/dev/null || true
body=$(git show "$sha:$req" 2>/dev/null)
if [ -z "$body" ]; then
  echo "배포 커밋 ${sha:0:7} 의 $req 를 못 꺼냈다 (git fetch 실패) -- **모르겠다**" >&2
  exit 2
fi

# 꾸러미 이름의 - 와 _ 는 pip 이 섞어 쓴다. 주석 줄(#)은 세지 않는다 --
# requirements.txt 에는 왜 핀했는지가 주석으로 길게 적혀 있고, 거기에도 이름이 나온다.
pat=$(printf '%s' "$pkg" | sed 's/[-_]/[-_]/g')
if printf '%s\n' "$body" | grep -vE '^[[:space:]]*#' |
   grep -qiE "^[[:space:]]*$pat([[:space:]]*[<>=!~]|[[:space:]]*$|\[)"; then
  echo "$pkg -- 마지막 성공 배포(${sha:0:7})의 $req 에 있다. **깔렸다** -- 사람에게 설치를 시키지 마라"
  exit 0
fi
echo "$pkg -- 마지막 성공 배포(${sha:0:7})의 $req 에 **없다.** 사람에게 시키지 말고 거기 넣어 main 에 머지해라" >&2
exit 1
