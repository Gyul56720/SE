"""`!평가` -- 면역계 러너의 고정 명령. 에이전트를 안 거친다.

빠른 갈래는 그 자리에서 돌고, `전부`(검사전부 6분 + 래칫)는 CLAUDE.md 의 규칙대로
**새 세션으로 떼어 백그라운드**로 돌린다: 확인은 pgrep 으로 하고(setsid 뒤의 $! 는
거짓 음성을 낸다), 살아 있는 것을 확인한 뒤에만 "시작했다" 고 답한다. 이미 돌고
있으면 또 띄우지 않는다 -- 두 벌이 같은 원장에 쓰면 서로를 덮는다.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from eval import run as _러너

PREFIX = "!평가"
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "eval_전부.log"

HELP = f"""**평가 (eval)** -- 면역계를 한 러너로: 게이트 · 답 회귀 · 기준선 · 검사 · 래칫
`{PREFIX}` 빠른 갈래를 지금 돌린다 (후퇴가 있으면 크게 말한다)
`{PREFIX} 전부` 느린 갈래까지 백그라운드로 (관리 채널만)
`{PREFIX} 과제` 절대 기준 과제를 참고 없음·있음으로 풀어 이득을 잰다 (백그라운드, 관리 채널만)
`{PREFIX} 상태` 마지막 판정과 백그라운드 런 생사"""
과제로그 = REPO / "logs" / "eval_과제.log"


def _돌고있나(무엇: str = "eval/run.py") -> str:
    p = subprocess.run(["pgrep", "-af", 무엇], capture_output=True, text=True)
    줄들 = [ln for ln in p.stdout.splitlines() if "pgrep" not in ln]
    return 줄들[0] if 줄들 else ""


def _배경으로(argv: "list[str]", 로그파일: Path, 무엇: str) -> str:
    """새 세션으로 떼어 띄우고 pgrep 으로 살아 있는지 본 뒤에만 '시작했다' 고 말한다."""
    살아 = _돌고있나(무엇)
    if 살아:
        return f"이미 돌고 있다 -- 또 띄우면 같은 원장을 서로 덮는다.\n{살아[:120]}"
    로그파일.parent.mkdir(parents=True, exist_ok=True)
    with open(로그파일, "ab") as f:
        subprocess.Popen(argv, cwd=str(REPO), stdout=f, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    살아 = _돌고있나(무엇)
    if not 살아:
        return f"띄웠는데 pgrep 에 안 보인다 -- 시작했다고 말하지 않는다. 로그를 보라: {로그파일}"
    import relay
    relay.배경등록(무엇, str(로그파일), " ".join(argv))
    return (f"백그라운드로 시작했다 (pgrep 확인됨): {살아[:100]}\n"
            f"로그: {로그파일} · **끝나면 이 채널에 알린다**")


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    words = tail.split()

    if words and words[0] == "상태":
        lines = []
        마지막 = _러너.마지막판정()
        for 갈래 in _러너.갈래들:
            r = 마지막.get(갈래["이름"])
            lines.append(f"{갈래['이름']}: " + (f"{r['판정']} ({r['때'][:10]})" if r else "잰 적 없음"))
        from eval import tasks as _과제
        for 참고 in _과제.참고조건들:
            m = _과제.마지막묶음(참고)
            lines.append(f"과제(참고 {참고}): " + (f"맞음 {m['맞음']}/{m['전체']} ({m['때'][:10]})"
                                            + (f" ** {m['흐름']} **" if m.get("흐름") else "")
                                            if m else "잰 적 없음"))
        살아 = _돌고있나() or _돌고있나("eval/tasks.py")
        lines.append(f"백그라운드: {'돌고 있다 -- ' + 살아[:80] if 살아 else '없음'}")
        if 로그.is_file():
            lines.append("로그 끝: " + (로그.read_text(encoding="utf-8", errors="replace")
                                      .strip().splitlines() or ["(비었다)"])[-1][:120])
        return "\n".join(lines)[:1900]

    if words and words[0] == "전부":
        if not allow_write:
            return "전부 돌리기는 관리 채널에서만 -- 6분 넘게 CPU 를 쓴다."
        return _배경으로(["python3", "eval/run.py", "--전부"], 로그, "eval/run.py")

    if words and words[0] == "과제":
        if not allow_write:
            return "과제 풀기는 관리 채널에서만 -- 모델을 과제 수 x 2 번 부른다(쿼터)."
        return _배경으로(["python3", "eval/tasks.py", "--참고", "둘다"], 과제로그, "eval/tasks.py")

    if words:
        return f"`{words[0]}` 는 모르는 말이다.\n\n{HELP}"
    if not allow_write:
        return "평가는 관리 채널에서만 돌린다 -- 게이트·검사가 CPU 를 쓴다."
    이름들 = [g["이름"] for g in _러너.갈래들 if g["무게"] == "빠름"]
    결과 = (runner or _러너.돌리기)(이름들)
    return _러너.보고(결과)[:1900]
