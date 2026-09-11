"""`!점검` -- 로컬 호스트 보안 자가점검(읽기 전용). find 가 디스크를 훑어 몇 초~분 걸리므로 배경.

    !점검           점검만 (수집·대조 없이)
    !점검 뇌        dig 수집 + search_memory 대조까지 (관리 채널, network)
    !점검 상태      마지막 점검의 심각도 합계
"""
from __future__ import annotations

from pathlib import Path

from eval.discord_cmd import _배경으로
from secaudit import run as R

PREFIX = "!점검"
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "secaudit.log"

HELP = f"""**점검 (secaudit)** -- 이 호스트의 열린 포트·권한·SUID·키 노출을 읽기 전용으로 본다
`{PREFIX}` 점검만 (배경) · `{PREFIX} 뇌` dig 수집 + 기억 대조까지 (관리 채널) · `{PREFIX} 상태` 마지막 합계
남의 기계를 공격하지 않는다 -- 돌고 있는 호스트 자신만 읽는다."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()

    if 말 == "상태":
        원장 = R.원장읽기()
        if not 원장:
            return "아직 점검한 적이 없다 -- `!점검` 으로 한 번 돌려라."
        마지막 = 원장[-1]
        s = 마지막.get("셈", {})
        높 = [f["제목"] for f in 마지막.get("낱낱", []) if f.get("심각도") == "높음"]
        return (f"마지막 점검({마지막.get('때', '')[:16]}): 높음 {s.get('높음', 0)} · 중간 {s.get('중간', 0)} · "
                f"정보 {s.get('정보', 0)} · 못잼 {s.get('못잼', 0)}"
                + (f"\n높음: {', '.join(높)}" if 높 else ""))[:1900]

    if 말 and 말 != "뇌":
        return f"`{말}` 은 모르는 말이다.\n\n{HELP}"
    if not allow_write:
        return "점검은 관리 채널에서만 -- find 가 디스크를 훑고 CPU 를 쓴다."
    argv = ["python3", "secaudit/run.py"] + (["--뇌"] if 말 == "뇌" else [])
    return (runner or _배경으로)(argv, 로그, "secaudit/run.py")
