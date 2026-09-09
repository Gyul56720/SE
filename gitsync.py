r"""origin 이 앞섰을 때 따라잡는 법. **한 군데에만 있다.**

전에는 `discord_bot_server.py` 와 `agent_memory.py` 에 같은 로직이 두 벌 있었고,
**두 벌 다 틀렸다.** 한 벌을 고쳐도 다른 벌이 계속 브랜치를 깨뜨린다. 그래서 뺀다.

의존성이 없다 -- `discord` 를 안 끌고 온다. 검사가 봇 모듈을 임포트하지 않고
이것만 부를 수 있어야 하기 때문이다(실측: 검사가 `ModuleNotFoundError: discord` 로
터졌다. 그 기계에만 있는 것에 기대면 안 된다는 것을 오늘 이미 한 번 배웠다).
"""
from __future__ import annotations


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
