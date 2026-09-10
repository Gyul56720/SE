"""**디스코드에서 소설을 돌린다 -- 에이전트를 거치지 않는 고정 명령.**

## 왜 있나

봇은 지금 **모든 메시지를 임의 셸을 가진 에이전트에 넘긴다**(`discord_bot_server.py` 의
`run_shell` 전권). 그래서 "라노벨 상황극 써 줘" 한마디가 `scripts/drift.sh` 를 20줄짜리
`echo` 촌극으로 덮었다 -- 실측 2026-09-10, 커밋 `4cd4473`. 287줄이 20줄이 됐고 열 곳
넘는 참조가 한꺼번에 끊겼다.

**그 위에서는 배포를 못 한다.** 배포판이란 남이 같은 말을 쳤을 때 같은 일이 나는 것이고,
에이전트는 그것을 보장하지 않는다. 매번 다르게 알아듣고, 때로는 저장소를 고친다.

그래서 여기 있는 명령은 **에이전트를 안 거친다.** 문장을 파싱해서 `scripts/drift.sh` 를
부르고 끝이다. 아래 셋을 지킨다.

1. **셸 문자열을 짓지 않는다.** argv 배열로만 부른다 -- 사용자 글이 명령줄에 끼지 않는다.
2. **사용자가 정할 수 있는 값은 화이트리스트와 정수뿐이다.** 문체 · 갈래는 아는 이름만,
   글자수는 int 로만 받는다.
3. **모르는 말은 처리하지 않는다.** `None` 을 돌려주면 봇이 예전처럼 에이전트로 넘긴다 --
   이 파일이 기존 동작을 뺏지 않는다.

## 무엇을 못 막나

이것은 **명령의 길**을 만드는 것이지 에이전트의 셸을 막는 장치가 아니다. `!소설` 로
시작하지 않는 말은 그대로 에이전트로 간다. 저장소가 또 덮이는 것을 막으려면 봇이 미는
길에 `scripts/tests.sh` 를 물려야 한다(여기 밖의 일).

## 쓰기

    !소설                     무엇을 할 수 있는지
    !소설 상태                돌고 있나 · 어디까지 왔나
    !소설 시작 만화 라노벨 8000  새 원고 (문체 · 갈래 · 글자수는 생략 가능)
    !소설 이어 50000           하던 원고를 이어 쓴다
    !소설 읽기 / 보내기 / 멈춤
    !소설 각본 / 세계 / 남은것 / 설정집
    !소설 재기                만화 식으로 나왔는지 눈금을 찍는다
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

PREFIX = "!소설"
REPO = Path(__file__).resolve().parent.parent

# 화이트리스트. **여기 없는 이름은 안 넘긴다** -- 사용자 글이 환경변수로 새는 길을 막는다.
STYLES = {"만화": "manga", "로판": "ropan", "사이다": "cider", "하드보일드": "hardboiled",
          "manga": "manga", "ropan": "ropan", "cider": "cider", "hardboiled": "hardboiled"}
GENRES = {"라노벨": "lanobe", "로판": "ropan", "로맨스": "romance", "직업": "job", "청춘": "youth",
          "lanobe": "lanobe", "romance": "romance", "job": "job", "youth": "youth"}

# 말 -> drift.sh 아래 명령. 값이 None 이면 drift.sh 가 아니라 따로 부른다.
VERBS = {
    "상태": "status", "시작": "start", "이어": "go", "읽기": "read", "보내기": "send",
    "멈춤": "stop", "각본": "card", "세계": "world", "남은것": "open", "설정집": "codex",
    "재기": None,
}
# 글자수를 받는 명령.
TAKES_CHARS = ("start", "go")

# **읽기만 하는 명령.** 공개 채널은 화이트리스트가 없어 아무나 친다. 남의 원고를 보는 것과
# 남의 원고를 멈추는 것은 다른 일이다 -- `멈춤` 하나로 밤새 도는 런이 죽는다.
READONLY = ("status", "read", "card", "world", "open", "codex", "재기")

HELP = f"""**소설 (DRIFT)** -- 줄거리 없이 첫 문장에서 이어 쓴다

`{PREFIX} 상태` 돌고 있나 · 어디까지 왔나
`{PREFIX} 시작 [문체] [갈래] [글자수]` 새 원고
`{PREFIX} 이어 [글자수]` 하던 원고를 이어 쓴다
`{PREFIX} 읽기` 원고를 본다 · `{PREFIX} 보내기` 파일로 받는다 · `{PREFIX} 멈춤`
`{PREFIX} 각본` 이번 회차 · `{PREFIX} 세계` · `{PREFIX} 남은것` · `{PREFIX} 설정집`
`{PREFIX} 재기` 만화 식으로 나왔는지 눈금

문체: {' · '.join(k for k in STYLES if not k.isascii())}
갈래: {' · '.join(k for k in GENRES if not k.isascii())}

예) `{PREFIX} 시작 만화 라노벨 8000`

산문은 Gemini 가 쓴다. 무엇을 쓸 것인가만 Claude 가 정한다."""


def parse(text: str) -> "dict | None":
    """`!소설 ...` 을 뜯는다. **모르는 말이면 None** -- 봇이 예전처럼 에이전트로 넘긴다."""
    if not isinstance(text, str):
        return None
    body = text.strip()
    if not body.startswith(PREFIX):
        return None
    # **접두사 뒤는 공백이거나 끝이어야 한다.** 안 그러면 `!소설이야기` 같은 말이
    # 명령으로 걸린다(시험이 이것을 잡았다). 붙여 쓴 것은 남의 말이지 우리 명령이 아니다.
    tail = body[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    rest = tail.strip()
    if not rest:
        return {"cmd": "help"}
    words = rest.split()
    verb = words[0]
    if verb not in VERBS:
        return {"cmd": "help", "몰라": verb}
    got = {"cmd": VERBS[verb] or "재기", "문체": "", "갈래": "", "글자수": 0}
    for w in words[1:]:
        if w in STYLES:
            got["문체"] = STYLES[w]
        elif w in GENRES:
            got["갈래"] = GENRES[w]
        elif re.fullmatch(r"\d{3,7}", w):
            got["글자수"] = int(w)
    return got


def argv(got: dict) -> "tuple[list, dict]":
    """부를 것과 얹을 환경변수. **셸 문자열을 짓지 않는다.**"""
    cmd = got["cmd"]
    if cmd == "재기":
        return ["python3", "-m", "novel.manga", "--book", "novel/drift.json"], {}
    args = [str(REPO / "scripts" / "drift.sh"), cmd]
    if cmd in TAKES_CHARS and got.get("글자수"):
        args.append(str(int(got["글자수"])))
    env = {}
    if got.get("문체"):
        env["STYLE"] = got["문체"]
    if got.get("갈래"):
        env["GENRE"] = got["갈래"]
    return args, env


def _shell(args: list, env: dict, timeout: int = 120) -> "tuple[int, str]":
    e = dict(os.environ)
    e.update(env)
    try:
        p = subprocess.run(args, cwd=str(REPO), env=e, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"{timeout}초 안에 안 끝났다. `{PREFIX} 상태` 로 확인해라"
    except OSError as ex:                                             # noqa: BLE001
        # **예외의 종류만 옮긴다.** 문구를 옮기면 경로나 값이 딸려 온다(deliver.py 와 같은 규율).
        return 1, f"못 돌렸다: {type(ex).__name__}"


def clip(text: str, limit: int = 1900) -> str:
    """디스코드 한 메시지 상한. **뒤를 남긴다** -- 결과는 끝에 있다."""
    t = (text or "").rstrip()
    if len(t) <= limit:
        return t or "(빈 것)"
    return "…(앞을 줄였다)\n" + t[-limit:]


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    """한 줄을 받아 답할 말을 돌려준다. **모르는 말이면 None.**

    `allow_write=False` 면 읽는 명령만 듣는다 -- 공개 채널이 그것이다."""
    got = parse(text)
    if got is None:
        return None
    if got["cmd"] == "help":
        head = f"`{got['몰라']}` 는 모르는 말이다.\n\n" if got.get("몰라") else ""
        return head + HELP
    if not allow_write and got["cmd"] not in READONLY:
        return (f"여기서는 읽는 것만 된다. 되는 것: "
                + " · ".join(f"`{k}`" for k, v in VERBS.items()
                             if (v or "재기") in READONLY))
    args, env = argv(got)
    rc, out = (runner or _shell)(args, env)
    body = clip(out)
    return body if rc == 0 else f"{body}\n\n(끝난 값 {rc})"
