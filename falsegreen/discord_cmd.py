"""`!거짓초록` -- 조용히 틀린 값으로 바꿔도 초록인 검사를 **시한까지** 찾는다 (배경).

    !거짓초록                 1시간 사냥 -- **거짓 빨강 먼저, 거짓 초록 그다음** (배경)
    !거짓초록 24             24시간
    !거짓초록 빨강만 / 초록만  한쪽만
    !거짓초록 <파일.py>      그 파일만 (초록 쪽)
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

HELP = f"""**거짓 판정 사냥 (mutate)** -- 한 번에 둘을 본다.
**거짓 빨강** 먼저: 깨끗한 판에서 두 번 돌려 `상태오염`, 작업 트리와 견줘 `환경의존` 을 가른다. 그 빨강은 검사 대상의 잘못이 아니다.
**거짓 초록** 그다음: 코드를 조용히 틀리게 바꿔도 초록이면 그 검사는 부르기만 하고 보지 않는다(Survived = 증거).
순서가 그런 까닭: 환경 때문에 빨간 검사는 초록 사냥의 **바탕을 무효로** 만든다(T(P)=PASS 가 깨진다).
`{PREFIX}` 1시간 · `{PREFIX} 24` 24시간 (배경 -- 끝나면 알린다) · `{PREFIX} 빨강만` · `{PREFIX} 초록만` · `{PREFIX} <파일.py>`
`{PREFIX} 보고` 원장(logs/거짓초록.jsonl) 요약 -- 사냥 안 하고 바로 답한다
`{PREFIX} 요약` D_0 -> D_1 점수 추이 (falsegreen/요약.jsonl -- **추적된다**. 원장은 logs/ 라 저장소에 안 남는다)
`{PREFIX} 순차` 병렬을 끈다 (기본은 코어수-1 일꾼으로 병렬 -- 실측 3일꾼 2.99배, 판정은 안 바뀐다)
`{PREFIX} 먼검사` 전체 검사를 주기로 돌린 기록 · `{PREFIX} 먼검사 돌려` 한 바퀴 (배경)
  -- 빠른 precheck 은 먼 검사를 안 본다. 그 사각지대에서 **며칠씩 안 들킨 빨강**이 난다(실측: test_law_hwp)."""


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
        return mutate.둘다보고(REPO)
    if 말 in ("요약", "추이"):
        # 추적되는 요약(falsegreen/요약.jsonl) -- 원장은 logs/ 라 저장소에 안 남는다
        return mutate.요약보고(REPO)
    if 말.startswith("먼검사"):
        import farcheck
        뒤 = 말[3:].strip()
        if 뒤 not in ("돌려", "돌려라", "시작"):
            return farcheck.보고(REPO)
        return (runner or _배경으로)(["python3", "farcheck.py", "--밀기"],
                                  REPO / "logs" / "farcheck.log", "먼 검사 한 바퀴")
    argv = ["python3", "mutate.py"]
    한쪽 = None
    # **기본이 병렬이다**(코어 수 - 1 -- 봇에게 한 코어는 남긴다). 실측 2026-09-13: 일꾼 3으로
    # 2.99배이고 **판정은 한 건도 안 바뀐다**(tests/test_mutate.py 가 순차와 병렬을 대조한다).
    # 파일 단위로 나누고 일꾼마다 제 판·제 원장·제 HOME 을 쓴다. `순차` 라고 쓰면 한 줄로 돈다.
    일꾼 = "1" if "순차" in 말 else "0"
    말 = 말.replace("순차", "").strip()
    if 말.startswith("빨강만"):
        한쪽, 말 = "--거짓빨강", 말[3:].strip()
    elif 말.startswith("초록만"):
        한쪽, 말 = "--사냥", 말[3:].strip()
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
        무엇 = f"거짓판정 {시간}시간"
    # 기본은 **둘 다**(거짓 빨강 -> 거짓 초록). 한쪽만 고르면 그쪽만.
    argv += [한쪽] if 한쪽 == "--거짓빨강" else ([] if 한쪽 == "--사냥" else ["--둘다"])
    if 한쪽 != "--거짓빨강":                        # FR 은 순차로 둔다 -- 두 번 돌려 상태오염을 보는 판정이다
        argv += ["--일꾼", 일꾼]
    # **주입된 runner 를 쓴다** -- 안 쓰면 검사가 실제 프로세스를 띄워야 하고, `_돌고있나` 의 pgrep 이
    # 검사 자신의 명령줄에 걸려 "이미 돌고 있다" 를 낸다(실측 2026-09-12). 다른 명령 모듈은 다 이 꼴이다.
    return (runner or _배경으로)(argv, 로그, 무엇)
