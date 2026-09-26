r"""origin 이 앞섰을 때 따라잡는 법. **한 군데에만 있다.**

전에는 `discord_bot_server.py` 와 `agent_memory.py` 에 같은 로직이 두 벌 있었고,
**두 벌 다 틀렸다.** 한 벌을 고쳐도 다른 벌이 계속 브랜치를 깨뜨린다. 그래서 뺀다.

의존성이 없다 -- `discord` 를 안 끌고 온다. 검사가 봇 모듈을 임포트하지 않고
이것만 부를 수 있어야 하기 때문이다(실측: 검사가 `ModuleNotFoundError: discord` 로
터졌다. 그 기계에만 있는 것에 기대면 안 된다는 것을 오늘 이미 한 번 배웠다).
"""
from __future__ import annotations

import os


def _토큰(repo=None) -> str:
    """`.env` 의 GITHUB_TOKEN (github_write 와 같은 자리). 없으면 빈 문자열."""
    try:
        from dig.harvest import env값
        return (env값("GITHUB_TOKEN", repo) or "").strip()
    except Exception:                                  # noqa: BLE001
        return (os.environ.get("GITHUB_TOKEN") or "").strip()


def _인증url(원격: str, 토큰: str) -> "str | None":
    """https origin URL 에 토큰을 심은 URL. https 이고 토큰이 있을 때만(아니면 None).
    **git 설정(remote URL)은 안 바꾼다** -- 이 URL 은 push 한 번에만 쓰고 버린다."""
    if not 토큰 or not 원격.startswith("https://"):
        return None
    나머지 = 원격[len("https://"):]
    if "@" in 나머지.split("/", 1)[0]:                 # 기존 자격증명 제거
        나머지 = 나머지.split("@", 1)[1]
    return f"https://x-access-token:{토큰}@{나머지}"


def _적출(글: str, 토큰: str) -> str:
    """반환 메시지에서 토큰을 지운다 -- git 이 실패 시 URL 을 그대로 뱉기 때문."""
    return 글.replace(토큰, "***") if 토큰 else 글


def 인증푸시(git, 브랜치: str = "", repo=None, 토큰=None) -> tuple:
    """지금 브랜치를 origin 에 민다. **토큰이 있으면 인증 URL 로**(없으면 평범한 push).

    실측 2026-09-26(재발방지): VM 봇의 `git push` 가
    `fatal: could not read Username for 'https://github.com'` 로 계속 실패했다.
    origin 이 자격증명 없는 https 라 git 이 대화형으로 username 을 물었고, TTY 가 없어
    죽었다. 이 모듈은 API 호출엔 토큰을 쓰면서 **git push 엔 안 썼다** -- 그 구멍을 메운다.

    · 토큰은 push URL 에만 심고 git 설정엔 안 남긴다(디스크·로그 유출 최소화).
    · `--force` 는 없다 -- reconcile 과 같은 결(남의 일을 안 지운다).
    · 반환 메시지에서 토큰을 적출한다(git 이 실패 시 URL 을 뱉는다).

    돌려주는 것: (returncode, 토큰이 지워진 메시지).
    """
    br = 브랜치 or git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    tok = _토큰(repo) if 토큰 is None else (토큰 or "")
    원격 = git(["remote", "get-url", "origin"]).stdout.strip()
    url = _인증url(원격, tok)
    if url:
        p = git(["push", url, f"HEAD:refs/heads/{br}"])
    else:
        p = git(["push", "-u", "origin", br])
    msg = _적출((p.stderr or p.stdout or "").strip(), tok)
    if p.returncode != 0 and not tok and not url:
        msg += " (GITHUB_TOKEN 이 없다 -- `.env` 에 넣거나 `!열쇠 GITHUB_TOKEN=<값>`)"
    return p.returncode, msg


# **검사가 낳는 다섯 원장.** test_되돌이_끊기.py 의 '다섯 원장' 과 같은 목록이다
# (codify 1 · eval답 4 · improve 4 · router 10 · secaudit 4 로 실측된 그 다섯).
검사원장 = (
    "codify/ledger.jsonl", "eval/ledger.jsonl", "improve/ledger.jsonl",
    "router/ledger.jsonl", "secaudit/ledger.jsonl",
)


def 검사원장_스테이지에서빼기(git) -> list:
    """`git add -A` 로 스테이지된 것 중 **검사가 낳는 원장**을 스테이지에서만 뺀다.

    실측 2026-09-25(재발방지): 봇이 한 턴 안에서 `eval/run.py`·`gatekeeper.py` 같은
    하네스를 **직접** 돌렸다. wire 를 안 타서 `SE_LEDGER_ROOT` 이 안 섰고, 그 검사들이
    추적되는 원장(eval·improve·router)에 줄을 쌓았다. `git add -A` 가 그것을 자동
    커밋('SE-agent: … 자동 반영')에 쓸어 담았다. `ledgerroot` 는 **wire 로 부른 검사만**
    막으므로(test_되돌이_끊기.py), 직접 돌린 것은 안 막힌다. 그래서 **커밋 문턱에서 한 번
    더** 막는다 -- 검사는 재는 것이지 남기는 것이 아니다(CLAUDE.md §303).

    **`--worktree` 는 쓰지 않는다.** 이 나무는 improve_agent(별 프로세스)가 같이 쓴다.
    워크트리를 HEAD 로 되돌리면 그 프로세스가 아직 커밋 안 한 원장 작업이 통째로
    사라진다 -- reconcile 이 `--force` 를 안 쓰는 것과 같은 결(남의 일을 안 지운다).
    스테이지에서만 빼면: 커밋엔 안 담기고, 워크트리의 줄은 그 원장의 임자(improve 등)가
    제 손으로 커밋하거나, 순수 검사 흔적이면 그대로 남았다가 다음 턴에 또 빠진다.

    HEAD 를 안 건드리므로 G020(원장은 지울 수 없다)에도 안 걸린다 -- 이미 커밋된 줄은
    그대로 있고, 아직 커밋 안 한 줄만 스테이지에서 뺄 뿐이다.

    돌려주는 것: 실제로 스테이지에서 뺀 원장 목록(순서는 `검사원장` 순).
    """
    staged = set(git(["diff", "--cached", "--name-only"]).stdout.split())
    대상 = [f for f in 검사원장 if f in staged]
    if 대상:
        git(["restore", "--staged", "--", *대상])
    return 대상


def reconcile(git) -> tuple:
    """origin 이 앞섰을 때 따라잡는다. **rebase 가 아니라 merge 다. 그리고 origin/main
    이 아니라 지금 브랜치의 origin 이다.**

    실측 2026-09-08~09, 같은 브랜치에서 여섯 번:
    `claude/light-novel-dopamine-elements-w6gtdg` 로 밀 때마다 non-fast-forward 가
    났고, 여기가 `git rebase origin/main` 을 걸었다. 둘 다 틀렸다.

      · **origin/main 이 아니다.** 지금 브랜치가 main 이 아니면 밑동이 통째로 바뀐다.
        그 브랜치는 main 보다 41 커밋 앞서 있었고, 그것을 main 위로 다시 쓰려다
        충돌이 났다("자동 rebase 를 시도했으나 충돌 발생").
      · **rebase 가 아니다.** 이 저장소의 브랜치에는 봇이 같이 쓴다
        (`SE-agent: Discord 요청 처리 결과 자동 반영` 이 그 브랜치에만 열 개가 넘는다).
        원격이 움직인 뒤에 내 커밋을 새로 쓰면 fast-forward 가 **영영 안 된다.**

    같은 일이 네 번 나고 네 번 다 사람이 merge 로 풀었다(2c1bafa · 847935d · 9a953a4 ·
    6f3f985). CLAUDE.md 에 규칙을 적었는데도 계속 난 이유가 이것이다 -- **규칙은
    사람에게 적혔고 이 줄이 봇에게 적혀 있었다.**

    돌려주는 것: (따라잡았나, 무슨 일이 났나)
    """
    br = git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() or "HEAD"
    if not br or br == "HEAD":
        return False, "지금 어느 브랜치도 아니다 (detached HEAD)"
    git(["fetch", "origin", br])
    merged = git(["merge", "--no-edit", f"origin/{br}"])
    if merged.returncode != 0:
        git(["merge", "--abort"])
        return False, (f"origin/{br} 와 충돌 -- 사람이 봐야 한다. "
                       f"**--force 는 쓰지 마라**(봇 커밋과 남의 일이 사라진다)")
    return True, f"origin/{br} 를 merge 했다"
