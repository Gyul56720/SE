"""`!목표` -- 목표 원장의 고정 명령. **승인은 관리 채널 화이트리스트 안에서만.**

읽기(목록·보기·다음)는 공개 채널에도 연다. 쓰기(제안·승인·끝·버림)는 allow_write --
관리 채널 화이트리스트 -- 안에서만 듣는다. "승인 주체가 사람이다" 를 지키는 자리가
바로 이 갈림이다: 공개 채널의 누구도, 에이전트의 어떤 말도 여기로는 승인을 못 넣는다.
"""
from __future__ import annotations

from intent import store as _원장

PREFIX = "!목표"

HELP = f"""**목표 (intent)** -- 제안은 쌓이고, **집히는 것은 승인된 것만**
`{PREFIX}` / `{PREFIX} 목록` 전부 본다
`{PREFIX} 다음` 지금 집을 수 있는(승인된 미완) 목표
`{PREFIX} 제안 <문장>` 목표를 제안한다 (관리 채널만 · 판정명령이 필요하면 CLI 로)
`{PREFIX} 승인 <id>` / `{PREFIX} 끝 <id>` / `{PREFIX} 버림 <id>` (관리 채널만)
끝은 판정명령이 있으면 그 명령의 exit 0 이 정한다 -- 말이 아니라."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    words = tail.split()
    누가 = "discord-admin" if allow_write else "discord-public"

    if not words or words[0] == "목록":
        골들 = sorted(_원장.상태표().values(), key=lambda g: g["때"])
        if not 골들:
            return f"목표가 하나도 없다.\n\n{HELP}"
        줄들 = [_원장.한줄(g) for g in 골들[-15:]]
        return ("\n".join(줄들) + "\n\n집히는 것은 '승인됨' 뿐이다")[:1900]
    if words[0] == "다음":
        골들 = _원장.집기()
        if not 골들:
            return "승인된 미완 목표가 없다 -- 제안은 있어도 승인 없이는 안 집힌다."
        return "\n".join(_원장.한줄(g) for g in 골들[:5])[:1900]

    if not allow_write:
        return "여기서는 읽기만 된다(목록·다음). 제안·승인·끝·버림은 관리 채널에서 -- " \
               "승인 주체가 사람인 것을 그 화이트리스트가 지킨다."

    if words[0] == "제안":
        문장 = " ".join(words[1:])
        if not 문장:
            return f"`{PREFIX} 제안 <문장>` -- 문장이 비었다."
        기록id = _원장.제안(문장, 누가=누가)
        return (f"제안됨 [{기록id}] -- **승인 전에는 집히지 않는다.**\n"
                f"`{PREFIX} 승인 {기록id}` 로 승인하라. 끝을 코드로 재려면 CLI 로 "
                f"판정명령을 달아 다시 제안하라.")
    if words[0] == "승인" and len(words) > 1:
        return _원장.승인(words[1], 누가=누가)
    if words[0] == "끝" and len(words) > 1:
        _, 말 = _원장.끝(words[1], 누가=누가)
        return 말[:1900]
    if words[0] == "버림" and len(words) > 1:
        return _원장.버림(words[1], 왜=" ".join(words[2:]), 누가=누가)
    return f"`{words[0]}` 는 모르는 말이다.\n\n{HELP}"
