"""
비밀값 유출 차단 -- run_shell 출력/저장 내용 마스킹과 공개 채널 자식 환경 정리.

왜 별도 모듈인가: bot_tools.py는 langchain/discord가 설치된 환경에서만 임포트된다.
이 로직은 그 의존성 없이도 테스트되고 게이트로 검사돼야 하므로, agent_context.py와 같은
이유로 표준 라이브러리(+agent_context)만 쓰는 모듈로 분리한다. 여기에 서드파티 임포트를
추가하지 마라 -- 추가하는 순간 게이트/테스트가 이 파일을 검사할 수 없게 된다.
"""

from __future__ import annotations

import base64
import os
import re

import agent_context

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 비밀값 유출 차단 -------------------------------------------------------------
#
# 사고 유형(2026-09-02 분석): 공개 채널은 화이트리스트가 없는데 run_shell은 임의 셸을
# 그대로 실행한다. 그래서 누구나 `cat .env`, `printenv` 한 줄로 Discord 봇 토큰과 Gemini
# 키를 채널에 뿌리게 만들 수 있었다. G004는 '커밋되는 파일'의 자격증명만 보므로 stdout으로
# 나가는 이 경로를 막지 못한다.
#
# run_shell 도구를 없애는 것은 선택지가 아니다 -- 사용자가 명시적으로 요청한 권한이고,
# ADMIN_SYSTEM_PROMPT도 스스로 권한을 축소하지 말라고 못박고 있다. 그래서 권한은 그대로
# 두고 비밀값이 나가는 경로만 좁힌다. 두 겹이다.
#
#   1. 공개 채널의 자식 프로세스 환경에서 비밀 변수를 아예 지운다 -> `printenv`,
#      `echo $GEMINI_API_KEY`, 비밀을 읽는 스크립트가 값을 얻지 못한다.
#   2. 모든 채널의 도구 출력/저장 내용에서 알려진 비밀값을 마스킹한다 -> `cat .env`,
#      로그 파일, 설정 파일 경유로 값이 흘러도 채널과 저장소에는 남지 않는다.
#      base64/hex 인코딩된 형태도 함께 지운다(`base64 .env` 같은 우회를 막는다).
#
# 한계를 분명히 적어둔다: 이건 완전한 격리가 아니다. 셸을 가진 상대가 값을 잘게 쪼개거나
# 다른 방식으로 인코딩해 내보내는 것까지는 막지 못한다. 진짜 격리는 별도 사용자/컨테이너로
# 프로세스를 분리해야 얻어진다. 여기서 막는 것은 "한 줄로 새는" 경로다.
_SECRET_NAME_RE = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|APIKEY|CREDENTIAL|PRIVATE_KEY|WEBHOOK)", re.I)
# 너무 짧은 값은 마스킹 대상에서 뺀다 -- 흔한 단어가 비밀값으로 설정돼 있으면 출력 전체가
# 별표로 뒤덮여 도구가 쓸모없어진다.
_MIN_SECRET_LEN = 8
_REDACTED = "***REDACTED***"
_DOTENV_PATH = os.path.join(REPO_DIR, ".env")


def _dotenv_secret_values() -> "set[str]":
    """.env 파일에 적힌 비밀값들. load_dotenv가 os.environ에 올려주지만, 봇이 아닌 다른
    경로로 추가된 줄이나 주석 처리된 이전 키까지 함께 막으려고 파일도 직접 본다."""
    values: set[str] = set()
    try:
        with open(_DOTENV_PATH, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                if _SECRET_NAME_RE.search(name) and len(value) >= _MIN_SECRET_LEN:
                    values.add(value)
    except OSError:
        pass
    return values


def secret_names() -> "set[str]":
    """환경변수 중 비밀값을 담고 있다고 봐야 하는 이름들."""
    return {name for name in os.environ if _SECRET_NAME_RE.search(name)}


def _is_maskable(value: str) -> bool:
    """마스킹할 만한 값인가. 이름은 비밀처럼 보여도 값이 경로나 숫자인 변수가 실제로 있다
    (CLAUDE_SESSION_INGRESS_TOKEN_FILE=/tmp/..., MAX_THINKING_TOKENS=31999). 그런 값까지
    지우면 출력에서 멀쩡한 경로와 숫자가 사라져 도구를 못 믿게 된다."""
    if len(value) < _MIN_SECRET_LEN:
        return False
    if value.startswith(("/", "./", "~/")):
        return False
    return not value.isdigit()


def secret_values() -> "set[str]":
    """마스킹 대상 문자열 전체 -- 환경변수 값 + .env 파일 값."""
    values = {os.environ[name] for name in secret_names()}
    return {v for v in values | _dotenv_secret_values() if _is_maskable(v)}


def redact_secrets(text: str) -> str:
    """알려진 비밀값(및 그 base64/hex 표현)을 마스킹한다. 비밀이 없으면 원문 그대로."""
    if not text:
        return text
    for value in secret_values():
        raw = value.encode("utf-8", "replace")
        for form in (value,
                     base64.b64encode(raw).decode(),
                     base64.b64encode(raw).decode().rstrip("="),
                     raw.hex(), raw.hex().upper()):
            if form and form in text:
                text = text.replace(form, _REDACTED)
    return text


def child_env() -> "dict[str, str] | None":
    """공개 채널에서 run_shell이 띄울 자식 프로세스의 환경. 비밀 변수를 제거한 사본을
    돌려준다. admin 채널은 None(부모 환경 그대로) -- 화이트리스트가 있고, 배포·탐색
    스크립트가 실제로 이 키들을 필요로 한다."""
    if not agent_context.is_public_channel():
        return None
    env = dict(os.environ)
    for name in secret_names():
        env.pop(name, None)
    return env
