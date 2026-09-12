"""`!거짓초록` -- 조용히 틀린 값으로 바꿔도 초록인 검사를 **시한까지** 찾는다 (배경).

    !거짓초록                 1시간 사냥 (배경 -- 끝나면 알린다)
    !거짓초록 24             24시간 사냥
    !거짓초록 <파일.py>      그 파일만
    !거짓초록 보고           원장 요약 (사냥 안 함, 즉시)
    !거짓초록 도움

왜 따로 있나: `rehearsal.절제검사` 는 몸통을 `raise` 로 바꾸므로 **그 함수를 부르기만 하는
검사도** 빨개진다 -- '부른다' 는 증명하고 '본다' 는 증명하지 못한다. 여기서는 터뜨리지 않고
틀린 값을 돌려준다. 그래도 초록이면 그 검사는 보지 않는 것이고, 그것이 **증명된 거짓 초록**이다.
"""
from __future__ import annotations

from pathlib import Path

from eval.discord_cmd import _배경으로

PREFIX = "!거짓초록"
별칭 = ("!거짓초록", "!거짓")
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "falsegreen.log"

HELP = f"""**거짓 초록 사냥 (mutate)** -- 코드를 **조용히 틀리게** 바꿔도 검사가 초록이면, 그 검사는 부르기만 하고 보지 않는다. 살아남은 변형 하나하나가 증거다.
`{PREFIX}` 1시간 · `{PREFIX} 24` 24시간 (배경 -- 끝나면 알린다) · `{PREFIX} <파일.py>` 그 파일만
`{PREFIX} 보고` 원장(logs/거짓초록.jsonl) 요약 -- 사냥 안 하고 바로 답한다
절제(raise)는 '부른다' 를 보고, 변형은 '본다' 를 본다 -- 둘은 다른 것이다."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    쓴것 = next((x for x in 별칭 if text.startswith(x)), None)
    if 쓴것 is None:
        return None
    tail = text[len(쓴것):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()
    if 말 in ("도움", "help", "?"):
        return HELP
    import mutate
    if 말 == "보고":
        return mutate.보고(REPO)
    argv = ["python3", "mutate.py"]
    if 말.endswith(".py"):
        argv += ["--파일", 말]
        무엇 = f"거짓초록 {말}"
    else:
        시간 = 24 if 말 in ("24", "24시간") else None
        try:
            시간 = 시간 if 시간 else (int(말) if 말 else 1)
        except ValueError:
            시간 = 1
        시간 = max(1, min(시간, 24))
        argv += ["--시한", str(시간 * 3600)]
        무엇 = f"거짓초록 {시간}시간"
    return _배경으로(argv, 로그, 무엇)
