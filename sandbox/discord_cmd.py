"""`!실험` -- 깨끗한 판에서 검사를 돌리는 고정 명령. 에이전트를 안 거친다.

`novel/discord_cmd.py` 와 같은 세 규칙을 지킨다: 셸 문자열을 짓지 않는다(argv 배열만),
사용자가 정할 수 있는 값은 좁은 글자꼴 하나뿐이다(테스트 이름 조각), 모르는 말은 None
으로 돌려 에이전트에게 넘긴다.

돌리는 곳은 sandbox/run.py 의 격리 판이다 -- 저장소를 못 다치고, 비밀 변수 없이,
시간 제한 안에서 돈다. 그래도 CPU 를 몇 분씩 쓰므로 **공개 채널(allow_write=False)에는
도움말만 연다** -- `!소설 멈춤` 을 공개에 안 연 것과 같은 자리다.
"""
from __future__ import annotations

import re
from pathlib import Path

from sandbox import run as 격리

PREFIX = "!실험"
REPO = Path(__file__).resolve().parent.parent

# 사용자가 정할 수 있는 유일한 자유값. tests.sh -k 의 이름 조각으로만 쓰이고,
# argv 배열의 한 칸으로만 넘어간다 -- 셸 문자열에 끼지 않는다.
_말꼴 = re.compile(r"[0-9A-Za-z_가-힣.-]{1,40}")

HELP = f"""**실험 (sandbox)** -- 깨끗한 판(HEAD 워크트리)에서 돌린다. 저장소를 안 만진다
`{PREFIX} 게이트` gatekeeper 의 게이트 전부
`{PREFIX} 검사 <말>` 이름에 <말>이 든 테스트만 (예: `{PREFIX} 검사 dig`)
전체 검사(6분)는 여기서 안 돌린다 -- CI 나 에이전트에게 시켜라."""


def parse(text: str) -> "dict | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    # **접두사 뒤는 공백이거나 끝이어야 한다** -- `!실험실` 은 남의 말이지 우리 명령이
    # 아니다 (novel/discord_cmd 가 시험으로 잡은 것과 같은 자리).
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    words = tail.split()
    if not words:
        return {"cmd": "help"}
    if words[0] == "게이트":
        return {"cmd": "게이트"}
    if words[0] == "검사":
        return {"cmd": "검사", "말": words[1] if len(words) > 1 else ""}
    return {"cmd": "help", "몰라": words[0]}


def clip(text: str, limit: int = 1800) -> str:
    """디스코드 한 메시지 상한. **뒤를 남긴다** -- 실패 요약은 끝에 있다."""
    t = (text or "").rstrip()
    if len(t) <= limit:
        return t or "(빈 것)"
    return "…(앞을 줄였다)\n" + t[-limit:]


def _돌리기(argv: list, 초: int) -> "tuple[int, str]":
    r = 격리.실행(argv, 초=초, 메모리MB=4096)
    if not r["돌았나"]:
        return 3, r["메모"] or r["stderr"]
    본문 = (r["stdout"] or "") + (r["stderr"] or "")
    if r["메모"]:
        본문 += f"\n({r['메모']})"
    return r["끝값"], f"[판: {r['판']}]\n{본문}"


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    """한 줄을 받아 답할 말을 돌려준다. **모르는 말이면 None.**"""
    got = parse(text)
    if got is None:
        return None
    if got["cmd"] == "help":
        head = f"`{got['몰라']}` 는 모르는 말이다.\n\n" if got.get("몰라") else ""
        return head + HELP
    if not allow_write:
        return "여기서는 도움말만 된다 -- 검사는 CPU 를 몇 분씩 써서 관리 채널에서만 돌린다."
    if got["cmd"] == "게이트":
        argv, 초 = ["python3", "gatekeeper.py"], 180
    else:
        말 = got.get("말", "")
        if not _말꼴.fullmatch(말):
            return (f"`{PREFIX} 검사 <말>` -- <말>은 글자·숫자·`_-.` 만, 40자까지다. "
                    "전체 검사는 여기서 안 돌린다(6분).")
        argv, 초 = ["bash", "scripts/tests.sh", "-k", 말], 300
    rc, out = (runner or _돌리기)(argv, 초)
    body = clip(out)
    return body if rc == 0 else f"{body}\n\n(끝난 값 {rc})"
