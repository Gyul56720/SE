"""
G018 -- `.gitignore` 에 적어 놓고 **추적은 안 끊은** 파일이 없는가.

`.gitignore` 는 **이미 추적 중인 파일에 아무 힘이 없다.** 규칙을 적어도 그 파일은
계속 커밋되고, 계속 `git pull` 을 충돌시키고, 계속 남의 런타임 상태를 덮어쓴다.
`git rm --cached` 를 따로 해야 실제로 끊긴다.

## 이 저장소가 이것으로 세 번 앓았다

    2026-09-07  mathdrift/ledger.json  추적한 채로 뒀더니 VM 이 낳은 공간 15개가
                `git pull` 한 번에 씨앗만 든 커밋본으로 되돌아갔다
    2026-09-08  mathgen/ledger.json    대청소에서 규칙은 적었는데 추적을 안 끊었다.
                108바이트짜리 초기 상태가 그대로 남아 있었다
    2026-09-08  mathdrift/ledger.json.bak  다른 브랜치에서 병합 충돌을 냈다
                (`1396780 Resolve merge conflict in mathdrift/ledger.json.bak`)

**규칙을 적은 것과 끊은 것은 다른 일이다.** 적기만 하고 끝내면 규칙이 있다는 사실이
오히려 "처리했다" 는 착각을 준다 -- 이 저장소가 가짜 green 이라고 부르는 그것이다.

## 무엇을 건너뛰나

  · `!` 로 시작하는 **부정 규칙.** 그건 "무시하지 마라" 라서 추적이 맞다
  · `.gitkeep` -- 빈 디렉터리를 남기려고 일부러 커밋한 것이다

## 고치는 법

    git rm --cached <파일>      # 파일은 디스크에 남고 추적만 끊긴다
"""
from __future__ import annotations

import subprocess

RULE_ID = "G018"
TITLE = "무시 규칙에 적어 놓고 추적을 안 끊었는가"
ORIGIN = "mathdrift/ledger.json 2026-09-07 · mathgen/ledger.json 2026-09-08"

_KEEP = (".gitkeep", ".gitignore")


def check(ctx) -> "list[str]":
    def git(*args):
        return subprocess.run(["git", *args], cwd=ctx.repo,
                              capture_output=True, text=True)

    ls = git("ls-files", "-z")
    if ls.returncode != 0:
        return []
    files = [f for f in ls.stdout.split("\0") if f]
    if not files:
        return []

    bad: list[str] = []
    # `--no-index` 가 있어야 **추적 중인 파일도** 규칙에 걸리는지 봐 준다.
    # 없으면 git 이 추적 파일을 아예 건너뛰어서 이 검사가 늘 초록이 된다.
    for i in range(0, len(files), 200):
        chunk = files[i:i + 200]
        res = git("check-ignore", "-v", "--no-index", *chunk)
        for line in res.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            where, path = parts[0], parts[1]
            rule = where.rsplit(":", 1)[-1]
            if rule.startswith("!"):
                continue                      # 부정 규칙 -- 추적이 맞다
            if path.endswith(_KEEP):
                continue                      # 빈 디렉터리 표시
            bad.append(
                f"{path} -- 무시 규칙({where.rsplit(':', 2)[0]}:{where.split(':')[1]} "
                f"`{rule}`)에 걸리는데 아직 추적된다. `.gitignore` 는 이미 추적 중인 "
                f"파일에 힘이 없다. `git rm --cached {path}`")
    return bad
