"""`!열쇠` -- 사람만 줄 수 있는 값(비밀번호 · 토큰)을 **딱 그것만** 받아 .env 에 적는다.

"필요한 정보만 묻고, 나머지는 알아서 접속하는 하네스" 의 받는 쪽이다. 도구(mailer 등)가
"이것이 없다" 고 하면 사람은 여기로 준다. 값은 어디에도 되비치지 않는다 -- 답에도,
로그에도. 이름은 대문자·숫자·밑줄만(셸 변수 꼴), 값은 한 줄.

    !열쇠                       있는 이름들(값 없이) · 메일에 없는 것
    !열쇠 SMTP_APP_PASSWORD=abcd efgh ijkl mnop     (관리 채널만)

적으면 os.environ 에도 올려 재시작 없이 바로 쓴다. 봇이 지울 권한이 있으면 그 메시지를
지운다(discord_bot_server) -- 못 지우면 사람에게 지우라고 한다.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

PREFIX = "!열쇠"
REPO = Path(__file__).resolve().parent
_이름꼴 = re.compile(r"[A-Z][A-Z0-9_]{2,40}")

HELP = f"""**열쇠 (keys)** -- 사람만 줄 수 있는 값을 딱 그것만 받는다
`{PREFIX} 이름=값` .env 에 적는다 (관리 채널만 · 값은 되비치지 않는다 · 메시지는 지운다)
`{PREFIX}` 있는 이름들과 메일에 없는 것"""


def 적기(이름: str, 값: str, repo=None) -> str:
    """'적었다' 또는 '바꿨다'. 성하지 않으면 ValueError (값은 예외 글에도 안 넣는다)."""
    if not _이름꼴.fullmatch(이름 or ""):
        raise ValueError(f"이름 꼴이 아니다 (대문자·숫자·밑줄): {이름[:40]!r}")
    값 = (값 or "").strip()
    if not 값 or "\n" in 값 or "\r" in 값:
        raise ValueError("값이 비었거나 여러 줄이다")
    p = Path(repo or REPO) / ".env"
    줄들 = p.read_text(encoding="utf-8", errors="replace").splitlines() if p.is_file() else []
    새 = f"{이름}={값}"
    바꿈 = False
    for i, line in enumerate(줄들):
        s = line.strip()
        if s.startswith("export "):
            s = s[7:].strip()
        if s.startswith(이름 + "="):
            줄들[i] = 새
            바꿈 = True
    if not 바꿈:
        줄들.append(새)
    p.write_text("\n".join(줄들) + "\n", encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    os.environ[이름] = 값
    return "바꿨다" if 바꿈 else "적었다"


def 있는이름들(repo=None) -> "list[str]":
    p = Path(repo or REPO) / ".env"
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith("export "):
            s = s[7:].strip()
        if s and not s.startswith("#") and "=" in s:
            이름 = s.split("=", 1)[0].strip()
            if _이름꼴.fullmatch(이름):
                out.append(이름)
    return out


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()
    if not 말:
        import mailer
        빠진 = mailer.필요한것()
        이름들 = 있는이름들()
        return (f"{HELP}\n\n.env 에 있는 이름 {len(이름들)}개: {', '.join(이름들)[:600]}\n"
                + ("메일: 다 있다" if not 빠진 else f"메일에 없는 것: {', '.join(빠진)}"))
    if "=" not in 말:
        return f"`이름=값` 꼴이어야 한다.\n\n{HELP}"
    if not allow_write:
        return "열쇠는 관리 채널에서만 -- 공개 채널에 적은 값은 이미 새어 나간 것이다. 바꿔라."
    이름, 값 = 말.split("=", 1)
    이름 = 이름.strip()
    try:
        말씀 = (runner or 적기)(이름, 값)
    except ValueError as e:
        return f"거절: {e}"
    return (f"`{이름}` 을 .env 에 {말씀} (값은 안 보여준다). **이 메시지는 지워라** -- "
            "봇이 지울 권한이 있으면 지운다. 이제 방금 막혔던 일을 다시 시켜라.")
