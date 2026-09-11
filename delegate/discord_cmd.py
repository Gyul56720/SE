"""`!위임 <글롭> :: <물음>` -- 넓은 탐색을 싼 역할에 던지고 대조된 인용만 받는 고정 명령.

물음은 자유 문장이지만 셸에 닿지 않는다(모델 프롬프트로만 간다). 글롭은 저장소 안
경로 꼴만 받는다. 쿼터를 쓰므로 관리 채널에서만 돌린다.
"""
from __future__ import annotations

import re

from delegate import run as _위임기

PREFIX = "!위임"
_글롭꼴 = re.compile(r"[0-9A-Za-z가-힣_./*?\[\]-]{1,80}")

HELP = f"""**위임 (delegate)** -- 파일 묶음을 싼 탐색기에 동시에 던지고, **원문에 실재하는 인용만** 받는다
`{PREFIX} <글롭> [<글롭>...] :: <물음>`   예) `{PREFIX} graph/*.py router/*.py :: 해시를 어디서 대조하나`
지어낸 인용은 코드가 대조해서 버리고 퇴짜로 센다. 관리 채널만."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    tail = tail.strip()
    if not tail:
        return HELP
    if not allow_write:
        return "위임은 쿼터를 써서 관리 채널에서만 돌린다."
    if "::" not in tail:
        return f"`{PREFIX} <글롭> :: <물음>` 꼴이어야 한다 -- `::` 가 없다.\n\n{HELP}"
    범위글, 물음 = tail.split("::", 1)
    범위들 = 범위글.split()
    물음 = 물음.strip()
    나쁜 = [g for g in 범위들 if not _글롭꼴.fullmatch(g) or g.startswith("/") or ".." in g]
    if not 범위들 or 나쁜 or not 물음:
        return f"글롭은 저장소 안 상대경로 꼴만 된다 (거절: {나쁜}) · 물음이 비면 안 된다.\n\n{HELP}"
    r = (runner or _위임기.위임)(물음, 범위들)
    return _위임기.보고(r, 물음)[:1900]
