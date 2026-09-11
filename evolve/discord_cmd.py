"""`!진화` -- 자기 개조 경로의 현황. 읽기만 하므로 공개 채널에도 연다.

여기서 진화를 '실행' 하지는 않는다 -- 승격은 self_challenge 의 RED/GREEN 증명만이
하고, 그것은 CLI 의 일이다(사고 트리를 지어야 한다). 이 명령은 그 경로가 성한지를
보여줄 뿐이다: 게이트가 몇이고, 최근에 무엇이 승격됐고, 상한이 무엇인지.
"""
from __future__ import annotations

from pathlib import Path

PREFIX = "!진화"
REPO = Path(__file__).resolve().parent.parent

HELP = f"""**진화 (evolve)** -- 새 경로가 아니라 기존 승격 경로가 진화다
`{PREFIX}` 현황: 게이트 수 · 최근 승격 · 상한
승격은 CLI 만 한다: `python3 self_challenge.py prove --candidate <후보> --broken-tree <사고>`
PROVEN=1 이어야 gates/ 로 간다 -- 증명 안 된 진단은 노트로도 안 남긴다."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    if tail.split():
        return HELP
    게이트들 = sorted((REPO / "gates").glob("G*.py"))
    최근 = sorted(게이트들, key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    lines = [f"게이트 {len(게이트들)}개 -- 모든 커밋이 전부를 통과해야 한다"]
    lines += [f"최근: {p.name}" for p in 최근]
    lines.append("상한: G008(자가수정 심판) · G009(탐색 심판) · "
                 "G020(판정 원장 삭제·게이트 삭제 금지)")
    try:
        from eval import run as _러너
        마지막 = _러너.마지막판정()
        r = 마지막.get("게이트")
        if r:
            lines.append(f"eval 의 게이트 갈래 마지막 판정: {r['판정']} ({r['때'][:10]})")
    except Exception:
        pass
    return HELP + "\n\n" + "\n".join(lines)
