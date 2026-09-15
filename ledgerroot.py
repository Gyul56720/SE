"""원장을 **어디에 쓸 것인가**. 한 자리에서 정한다.

## 왜 있나 (실측 2026-09-15)

`eval/wire.py` 의 배선 점검은 각 기관을 **진짜로 돌려 본다** -- 그것이 이 점검의 값이다
(임포트만 보면 안 도는 것을 도는 줄 안다). 그런데 돌려 보면 그 기관이 **추적되는
원장에 줄을 쓴다.** 한 번 돌 때마다 다섯 원장에 스물두 줄이 쌓였다:

    codify 1 · eval답 4 · improve 4 · router 10 · secaudit 4

사람은 그것을 못 보고 `git add -A` 로 커밋에 쓸어 담았고, 그 판이 다른 갈래와
충돌했다. **점검은 "도는가" 만 보면 되고, 도는 것을 보려고 판정의 역사를 더럽힐
이유가 없다.**

## 어떻게

`SE_LEDGER_ROOT` 가 서 있으면 원장을 거기 쓴다. 안 서 있으면 지금까지와 똑같다.
**부르는 쪽이 준 `repo` 가 늘 이긴다** -- 검사들이 임시 저장소를 주고 돌리는데,
환경 변수가 그것을 덮으면 그 검사들이 남의 자리를 보게 된다.

    뿌리(repo, 기본)   repo -> SE_LEDGER_ROOT -> 기본

읽기도 같은 자리를 본다. 쓰기만 옮기면 점검이 **제가 쓴 줄을 못 읽어** 엉뚱한
판정을 낸다.
"""
from __future__ import annotations

import os
from pathlib import Path

환경이름 = "SE_LEDGER_ROOT"


def 뿌리(repo=None, 기본=None) -> Path:
    """원장을 둘 뿌리. **다른 데를 가리킨 repo > 환경 변수 > 기본.**

    `repo` 가 있으면 무조건 이기게 두면 안 된다 -- 실측 2026-09-15: `secaudit.점검하기`
    가 맨 앞에서 `repo = Path(repo or REPO)` 로 **인자를 덮어쓰고** 원장 쓰는 데까지
    들고 간다. 그러면 repo 는 늘 참이라 환경 변수가 영영 안 먹는다. 실제로 배선 점검
    한 바퀴에 `secaudit/ledger.jsonl` 이 두 줄 늘었다 -- 다른 넷은 멀쩡한데 그것만.
    그 꼴이 여섯 파일에 **열여덟 군데** 있어서 하나씩 고치는 것은 다시 빠뜨릴 길이다.

    그래서 여기서 가른다: **repo 가 기본과 같으면 '안 준 것'으로 본다.** 검사들이
    임시 저장소를 줄 때는 기본과 다르므로 그대로 이긴다 -- 그 쪽이 깨지면 안 된다.
    """
    기본 = Path(기본 or ".")
    if repo and Path(repo) != 기본:
        return Path(repo)
    옮긴데 = os.environ.get(환경이름)
    if 옮긴데:
        return Path(옮긴데)
    return Path(repo) if repo else 기본
