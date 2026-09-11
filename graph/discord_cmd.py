"""`!기억` -- 깃발 색인을 보고, 밤일을 돌리는 고정 명령.

찾기는 읽기만 하므로 공개 채널에도 연다(`!소설 읽기` 와 같은 자리). `밤`(간추리기)은
원장에 쓰므로 관리 채널 화이트리스트 안에서만 듣는다 -- 다만 간추리기는 원본을 안
건드리고 색인 줄만 붙이는 일이라, 무거운 것이 아니라 좁은 것이다.
"""
from __future__ import annotations

from graph import ask as _ask
from graph import night as _night

PREFIX = "!기억"

HELP = f"""**기억 (graph)** -- 간추린 색인에서 깃발로 찾는다. 원본은 git 에 그대로 있다
`{PREFIX} <말...>` 깃발·요약에서 찾는다 (예: `{PREFIX} 코인 실측`)
`{PREFIX} 밤` 쌓인 노트·보고서를 간추려 색인에 넣는다 (관리 채널만)"""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None                       # `!기억력` 은 남의 말이다
    words = tail.split()
    if not words:
        return HELP
    if words[0] == "밤":
        if not allow_write:
            return "밤일(간추리기)은 관리 채널에서만 돌린다. 찾기는 여기서도 된다: " \
                   f"`{PREFIX} <말>`"
        r = _night.간추리기()
        lines = [f"간추림 {len(r['적음'])}개 · 이미 있음 {r['그대로']}개 · 거절 {len(r['거절'])}개"]
        lines += [f"+ {rel}" for rel in r["적음"][:10]]
        lines += [f"! {why}" for why in r["거절"][:5]]
        return "\n".join(lines)
    물음 = " ".join(words)
    hits = _ask.찾기(물음)
    if not hits:
        return (f"`{물음}` 깃발에 걸린 것이 없다. 간추린 적이 없으면 `{PREFIX} 밤` 부터. "
                "노트 전문 검색은 에이전트의 search_memory 가 한다.")
    out = []
    for s, n in hits[:3]:
        out.append(_ask.한줄(s, n))
        경고, _ = _ask.원문(n)
        if 경고:
            out.append(f"! {경고}")
    return "\n".join(out)[:1900]
