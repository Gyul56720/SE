"""`!코드화` -- 논문의 수식·알고리즘을 검증된 코드로. 모델을 여러 번 부르므로 배경.

    !코드화 논문 <arxiv id/url>        그 논문의 수식·알고리즘을 차례로 (관리 채널)
    !코드화 상태                       마지막 결과 · 못 한 것
"""
from __future__ import annotations

from pathlib import Path

from eval.discord_cmd import _배경으로
from codify import run as C

PREFIX = "!코드화"
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "codify.log"

HELP = f"""**코드화 (codify)** -- 논문 이론(수식·알고리즘)을 실행 가능한 코드로. 판정은 sandbox 끝값이 한다
`{PREFIX} 논문 <arxiv id>` 그 논문을 코드화 (관리 채널, 배경) · `{PREFIX} 상태` 마지막 결과
수식·예시가 있으면 값까지 검증, 없으면 약한 검증(import·호출)으로 정직히 표시한다."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()
    if not 말:
        return HELP
    if 말 == "상태":
        원장 = C.원장읽기()
        성 = sum(1 for r in 원장 if r.get("꼴") == "코드화" and r.get("성공"))
        전 = sum(1 for r in 원장 if r.get("꼴") == "코드화")
        미 = C.미해결들()
        lines = [f"코드화 원장 {전}건 · 성공 {성}"]
        for r in [x for x in 원장 if x.get("꼴") == "코드화"][-3:]:
            lines.append(f"  {'✓' if r.get('성공') else '✗'} {r.get('이름', '')[:40]} {r.get('종류', '')}"
                         + (f" -> {r.get('파일', '')}" if r.get("성공") else f" ({r.get('남은것', '')[:50]})"))
        if 미:
            lines.append("못 한 것(수집기의 틈이 된다): " + ", ".join(미[:5]))
        return "\n".join(lines)[:1900]
    words = 말.split(maxsplit=1)
    if words[0] != "논문" or len(words) < 2:
        return f"`{PREFIX} 논문 <arxiv id/url>` 꼴이어야 한다.\n\n{HELP}"
    if not allow_write:
        return "코드화는 관리 채널에서만 -- 모델을 여러 번 부르고 sandbox 를 돌린다."
    아이디 = words[1].strip()
    url = 아이디 if "arxiv" in 아이디 else f"https://arxiv.org/abs/{아이디}"
    return (runner or _배경으로)(["python3", "codify/run.py", "--논문", url], 로그, "codify/run.py")
