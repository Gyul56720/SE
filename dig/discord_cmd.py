"""`!수집` -- 밖(GitHub · HF)에서 참고를 끌어오는 고정 명령. 에이전트를 안 거친다.

받는 데는 망이 걸리고 한 바퀴에 수십 초가 갈 수 있으므로 `!평가 전부` 와 같은 규칙으로
**새 세션으로 떼어 백그라운드**로 돌린다(pgrep 으로 확인한 뒤에만 "시작했다"). `틈` 과
`상태` 는 망 없이 그 자리에서 답한다.
"""
from __future__ import annotations

import re
from pathlib import Path

from dig import harvest as H
from eval.discord_cmd import _배경으로   # 같은 규칙(pgrep 확인)을 두 벌 안 짓는다

PREFIX = "!수집"
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "harvest.log"
_말꼴 = re.compile(r"[0-9A-Za-z가-힣_ .,+-]{2,120}")

HELP = f"""**수집 (harvest)** -- 자가 틀린 자리를 GitHub·Hugging Face 에서 채운다 (제2의 뇌)
`{PREFIX} 틈` 자(eval/tasks)가 참고를 줘도 틀린 과제 -> 검색어 (호출 0회)
`{PREFIX} <검색어>` 그 말로 한 바퀴 (백그라운드, 관리 채널만)
`{PREFIX} 틈으로` 틈의 검색어 전부로 한 바퀴 (백그라운드, 관리 채널만)
`{PREFIX} 상태` 원장 요약 · 백그라운드 생사
`{PREFIX} 망` **이 기계에서 바깥이 되나** -- 문마다 코드·까닭 (망을 쓴다, 그 자리에서 답한다)"""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()

    if 말 == "틈":
        틈들 = H.틈찾기()
        if not 틈들:
            return "자가 틀린 것이 없거나 아직 안 쟀다 -- `!평가 과제` 를 먼저."
        return "\n".join(f"{g['갈래']} {g['과제']} -> `{g['말']}`" for g in 틈들)[:1900]

    if 말 == "상태":
        원장 = H.원장읽기()
        색 = sum(1 for r in 원장 if r.get("판정") == "색인")
        거 = sum(1 for r in 원장 if r.get("판정") == "거절")
        lines = [f"원장 {len(원장)}줄 · 색인 {색} · 거절 {거} · 오늘 {H.오늘받은수()}/{H.하루상한()}"]
        for r in 원장[-3:]:
            lines.append(f"  {r.get('때', '')[:16]} {r.get('판정')} {r.get('종류')} {str(r.get('이름', ''))[:40]}"
                         + (f" -- {r.get('까닭', '')[:40]}" if r.get("까닭") else ""))
        if 로그.is_file():
            lines.append("로그 끝: " + (로그.read_text(encoding="utf-8", errors="replace")
                                      .strip().splitlines() or ["(비었다)"])[-1][:120])
        return "\n".join(lines)[:1900]

    if not 말:
        return HELP
    if 말 == "망":
        # 망이 되는지는 **재면 알 수 있다.** 재는 길이 없으면 두뇌가 원인을 지어낸다
        # (실측 2026-09-12: "시스템 내부의 인코딩 제한" · "구글이 차단" -- 둘 다 사실이 아니었다).
        from dig import search as SC
        return SC.망보고(SC.망점검(틈=8.0))[:1900]
    if not allow_write:
        return "수집은 관리 채널에서만 -- 망을 쓰고 원장에 적는다."
    if 말 == "틈으로":
        argv = ["python3", "dig/harvest.py", "--틈"]
    else:
        if not _말꼴.fullmatch(말):
            return f"검색어 꼴이 아니다: {말[:40]!r}\n\n{HELP}"
        argv = ["python3", "dig/harvest.py", "--말", 말]
    return (runner or _배경으로)(argv, 로그, "dig/harvest.py")
