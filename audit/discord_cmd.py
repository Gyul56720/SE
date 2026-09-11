"""`!감사` -- 변경을 실제로 돌려 보는 감사의 고정 명령. 에이전트를 안 거친다.

돌리는 것은 audit/run.py 그대로다. CPU 를 쓰므로(검사마다 격리 판을 깐다) 관리 채널
화이트리스트 안에서만 듣고, 공개 채널에는 도움말만 연다.
"""
from __future__ import annotations

from audit import run as _감사기

PREFIX = "!감사"

HELP = f"""**감사 (audit)** -- 바뀐 파일을 붙드는 검사를 찾아 격리 판에서 끝까지 돌린다
`{PREFIX}` 미커밋 변경을 (커밋하기 전에 버그를 잡는 자리)
`{PREFIX} 커밋` 마지막 커밋(HEAD~1..HEAD)을
검사 없는 .py 변경은 없는 대로 크게 말한다 -- 그 자리가 버그가 새는 자리다."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    words = tail.split()
    if words and words[0] not in ("커밋",):
        return f"`{words[0]}` 는 모르는 말이다.\n\n{HELP}"
    if not allow_write:
        return "감사는 CPU 를 몇 분씩 써서 관리 채널에서만 돌린다."
    커밋 = bool(words)
    r = (runner or _감사기.감사)(커밋=커밋)
    out = _감사기.보고(r)
    return out[:1900] if len(out) <= 1900 else "…(앞을 줄였다)\n" + out[-1800:]
