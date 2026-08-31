"""
요청 하나를 처리하는 동안 유지되는 호출자 맥락 -- 그리고 그 맥락에 걸린 접근 제한.

왜 별도 모듈인가 (실측 확인됨, 2026-08-28): 원래 `_current_author`가 bot_tools.py 안에
있었고, agent_memory.py와 public_agent_files.py가 그걸 top-level에서 임포트했다. 그런데
bot_tools.py는 그 두 모듈을 자기보다 위쪽에서 임포트하므로 순환이 생겼고, `_current_author`
정의가 그 임포트들보다 아래에 있어서 아래 에러로 봇 전체가 기동 불가가 됐다:

    ImportError: cannot import name '_current_author' from partially initialized
    module 'bot_tools' (most likely due to a circular import)

이 모듈은 표준 라이브러리 말고는 아무것도 임포트하지 않는다 -- 그래서 누가 먼저 임포트되든
순환이 생기지 않는다. 여기에 새 임포트를 추가하지 마라.
"""

from __future__ import annotations

import contextvars
import os

# 도구 함수는 모델이 인자를 만들어 부르므로 호출자 ID를 인자로 실어보낼 수 없다 --
# 요청 단위로 여기에 담아두고 도구가 꺼내 쓴다.
current_author: contextvars.ContextVar[str] = contextvars.ContextVar("current_author", default="unknown")

# 예전 이름. bot_tools.py가 이 이름으로 재수출하고 있어서 외부 코드가 깨지지 않게 남겨둔다.
_current_author = current_author

# 게스트 차단 목록. 원래 Discord ID가 5개 파일에 리터럴로 박혀 있었다 -- revert 커밋
# 276ab13이 "Discord ID는 하드코딩하지 말고 환경변수로 뺄 것"이라고 명시했는데도 재적용 때
# 다시 박혔다. 기본값으로 기존 ID를 남겨서 환경변수를 안 채워도 보안 정책이 조용히 풀리지
# 않게 하되, GUEST_BLOCKED_USER_IDS로 덮어쓸 수 있게 한다.
_DEFAULT_BLOCKED = ""
BLOCKED_USER_IDS: frozenset[str] = frozenset(
    x.strip() for x in os.getenv("GUEST_BLOCKED_USER_IDS", _DEFAULT_BLOCKED).split(",") if x.strip()
)


def is_blocked(author_id: str | None = None) -> bool:
    """이 호출자가 쓰기/실행 도구를 못 쓰는 게스트인지. 인자를 안 주면 현재 요청 맥락을 본다."""
    return (current_author.get() if author_id is None else str(author_id)) in BLOCKED_USER_IDS
