"""`!고치기` -- 고치기 루프의 고정 명령. 모델 호출과 망이 걸려 몇 분 갈 수 있으므로 백그라운드.

    !고치기 <재현 명령> :: <증상>      (관리 채널만)
    !고치기 상태                       마지막 결과 · 못 푼 증상 · 백그라운드 생사
"""
from __future__ import annotations

from pathlib import Path

from eval.discord_cmd import _배경으로
from repair import run as RP
import toolgate

PREFIX = "!고치기"
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "repair.log"

HELP = f"""**고치기 (repair)** -- 실측→제2의 뇌→시도→실측 루프. 사람에게는 남은 한 가지만
`{PREFIX} <재현 명령> :: <증상>` 예: `{PREFIX} python3 mailer.py --진단 :: 5.7.8 not accepted`
`{PREFIX} 상태` 마지막 결과와 못 푼 증상"""


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
        원장 = RP.원장읽기()
        끝들 = [r for r in 원장 if r.get("꼴") == "끝"]
        lines = [f"원장 {len(원장)}줄 · 끝 {len(끝들)}건 · 해결 {sum(1 for r in 끝들 if r.get('해결'))}"]
        for r in 끝들[-3:]:
            lines.append(f"  {r.get('때', '')[:16]} {'해결' if r.get('해결') else '못 풂'} "
                         f"{str(r.get('증상', ''))[:40]} (바퀴 {r.get('바퀴')})"
                         + (f" -- 남은: {r.get('남은것', '')[:60]}" if not r.get("해결") else ""))
        미 = RP.미해결증상들()
        if 미:
            lines.append("못 푼 증상(수집기의 틈이 된다): " + " | ".join(x[:40] for x in 미[:4]))
        if 로그.is_file():
            lines.append("로그 끝: " + (로그.read_text(encoding="utf-8", errors="replace")
                                      .strip().splitlines() or ["(비었다)"])[-1][:120])
        return "\n".join(lines)[:1900]
    if "::" not in 말:
        return f"`<재현 명령> :: <증상>` 꼴이어야 한다.\n\n{HELP}"
    if not allow_write:
        return "고치기는 관리 채널에서만 -- 작업 트리를 고치고 모델을 부른다."
    명령, 증상 = (x.strip() for x in 말.split("::", 1))
    if not 명령:
        return "재현 명령이 비었다."
    막힘 = toolgate.검사(명령)
    if 막힘:
        return f"[도구 게이트 차단] {막힘}"
    argv = ["python3", "repair/run.py", "--명령", 명령, "--증상", 증상]
    return (runner or _배경으로)(argv, 로그, "repair/run.py")
