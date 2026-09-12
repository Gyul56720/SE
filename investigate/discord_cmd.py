"""`!조사` -- 긴 호흡으로 끝까지 판다 (배경, 기본 한 시간).

    !조사 <증상>                         판정: 게이트·감사가 끝값 0 이 될 때까지
    !조사 <증상> :: <재현 명령>          재현 명령 끝값 0 까지 (더 정확하다)
    !조사 상태                           원장에서 마지막 조사
    !조사 도움
"""
from __future__ import annotations

from pathlib import Path

from eval.discord_cmd import _배경으로

PREFIX = "!조사"
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "investigate.log"

HELP = f"""**조사 (investigate)** -- 한 턴이 아니라 **한 시간**. 증거를 캐고(모델 안 씀) -> 가설을 끝값으로 확인 -> 고치고 -> 게이트·감사가 초록이 될 때까지 되풀이. 두 바퀴 같으면 갈래를 바꾸고, 세 바퀴 같으면 멈춘다.
`{PREFIX} <증상>` · `{PREFIX} <증상> :: <재현 명령>` (관리 채널, 배경 -- 끝나면 알린다)
`{PREFIX} 목표 <부탁>` **새 기능**: 부탁을 검사로 못박고 그 검사가 지날 때까지 (판정은 끝값)
`{PREFIX} 상태` 마지막 조사 · 해결되면 커밋·PR 까지. **머지는 사람이 누른다**"""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()
    if 말 in ("", "도움"):
        return HELP
    if 말 == "상태":
        from investigate import run as I
        줄들 = I.원장읽기()
        if not 줄들:
            return "조사 원장이 비었다 -- 아직 한 번도 안 돌았다"
        마지막 = [d for d in 줄들 if d.get("조사") == 줄들[-1].get("조사")]
        끝 = next((d for d in reversed(마지막) if d.get("단계") == "끝"), None)
        if 끝:
            return (f"조사 {끝['조사']}: {'**해결**' if 끝.get('해결') else '못 풀었다'} ({끝.get('바퀴')}바퀴)\n"
                    f"  남은 것: {끝.get('남은것') or '없음'}\n  메모: {끝.get('메모', '')}")
        바 = [d for d in 마지막 if d.get("단계") == "바퀴"]
        return f"조사 {마지막[-1]['조사']}: 돌고 있다 -- {len(바)}바퀴 · 마지막 빨강 {(바[-1].get('빨강') if 바 else '?')}"
    if not allow_write:
        return "조사는 관리 채널에서만 -- 저장소를 고치고 커밋·PR 까지 간다."
    목표 = 말.startswith("목표 ")
    if 목표:
        말 = 말[3:].strip()
    증상, _, 명령 = 말.partition("::")
    argv = ["python3", "investigate/run.py", "--증상", 증상.strip()]
    if 목표:
        argv.append("--목표")
    if 명령.strip():
        argv += ["--명령", 명령.strip()]
    return (runner or _배경으로)(argv, 로그, "investigate/run.py")
