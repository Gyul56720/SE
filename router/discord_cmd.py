"""`!경로` -- 역할표와 비용 원장을 보는 고정 명령. 읽기만 하므로 공개 채널에도 연다."""
from __future__ import annotations

from router import call as _길
from router import check as _심판

PREFIX = "!경로"

HELP = f"""**경로 (router)** -- 역할이 모델을 고른다: 디렉터만 비싸게, 토큰은 싼 풀로, 판정은 코드로
`{PREFIX}` 역할표
`{PREFIX} 요약` 비용 원장 -- 역할별 호출·성공·바탕·채택률
`{PREFIX} 심판` 비싼 길이 죽어 있지 않은가 (eval 의 '경로' 갈래와 같은 판정)"""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    words = tail.split()
    if not words:
        lines = [f"{이름}: {표['바탕']}"
                 + (f" (막히면 {표['물러설곳']})" if 표.get("물러설곳") else "")
                 + f" -- {표['왜']}" for 이름, 표 in _길.역할들.items()]
        return HELP + "\n\n" + "\n".join(lines)
    if words[0] == "요약":
        s = (runner or _길.요약)()
        if not s:
            return "원장이 비어 있다 -- 아직 아무도 router 로 안 불렀다."
        lines = []
        for 역할, v in s.items():
            채택 = f" · 채택 {v['채택분자']}/{v['채택분모']}" if v["채택분모"] else ""
            lines.append(f"{역할}: 호출 {v['호출']} · 성공 {v['성공']} · "
                         f"평균 {v['초합'] / max(1, v['호출']):.1f}초 · {v['바탕']}{채택}")
        return "\n".join(lines)[:1900]
    if words[0] == "심판":
        끝값, lines = _심판.심판()
        표 = {0: "성하다", 1: "빨강", 3: "재료 부족"}[끝값]
        return (f"[{표}]\n" + "\n".join(lines))[:1900]
    return f"`{words[0]}` 는 모르는 말이다.\n\n{HELP}"
