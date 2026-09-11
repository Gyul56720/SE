"""`!연구` -- 목표 하나를 추상 질의로 풀어 제2의 뇌를 돌린다. 모델을 여러 번 부르므로 배경.

    !연구 <목표>            그 목표를 수집->코드화->결론 메모까지 (관리 채널, 배경)
    !연구 상태              마지막 연구 원장 요약
"""
from __future__ import annotations

from pathlib import Path

from eval.discord_cmd import _배경으로
from research import run as Rs

PREFIX = "!연구"
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "research.log"

HELP = f"""**연구 (research)** -- 목표를 **추상 방법론 질의**로 풀어 제2의 뇌가 넓게 모으고, 막히면
그 막힘을 다시 추상화해 더 넓게 모으기를 되풀이한다(3~5 바퀴). 모은 방법론은 코드화로 검증하고,
과정->결과를 압축해 `public_agent_memory` 에 결론으로 남긴다. 도메인 무관.
`{PREFIX} <목표>` 그 목표를 연구 (관리 채널, 배경) · `{PREFIX} 보기` 마지막 메모 전문 · `{PREFIX} 상태` 원장"""


def _원장():
    import json
    p = REPO / Rs.원장상대
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


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
    if 말 in ("보기", "메모"):
        메모들 = sorted((REPO / "public_agent_memory").glob("*_연구_*.md"))
        if not 메모들:
            return "아직 연구 메모가 없다 -- `!연구 <목표>` 로 시작하라."
        본 = 메모들[-1].read_text(encoding="utf-8")
        머리 = f"📄 `{메모들[-1].name}` ({len(본)}자)\n"
        return 머리 + (본 if len(본) <= 1800 else 본[:1800] + f"\n… (잘렸다 -- 전문은 {메모들[-1].relative_to(REPO)})")
    if 말 == "상태":
        원장 = [r for r in _원장() if r.get("꼴") == "연구끝"]
        if not 원장:
            return "연구 원장이 비었다 -- `!연구 <목표>` 로 시작하라."
        lines = [f"연구 {len(원장)}건"]
        for r in 원장[-3:]:
            lines.append(f"  {'✓' if r.get('충분') else '·'} {r.get('목표', '')[:50]} "
                         f"({r.get('바퀴수', 0)}바퀴)" + (f" -> {r.get('메모', '')}" if r.get("메모") else ""))
        return "\n".join(lines)[:1900]
    if not allow_write:
        return "연구는 관리 채널에서만 -- 모델을 여러 번 부르고 수집·sandbox 를 돌린다."
    return (runner or _배경으로)(["python3", "research/run.py", "--목표", 말], 로그, "research/run.py")
