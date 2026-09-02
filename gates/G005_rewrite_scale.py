"""
G005 -- 요청의 크기와 변경의 크기를 맞춰라 (자기 재작성 붕괴 방지).

사고: 1a82685 (2026-08-28). 게스트 1명의 git 접근을 막아달라는 요청에 대해
discord_bot_server.py에서 190줄을 삭제하고 46줄로 다시 썼다. 정작 요청받은 제한 로직은
11줄이었고 실제로 11줄이면 충분했다. 나머지 179줄은 요청과 무관한 삭제였다.

원인 진단이 중요하다. 메모리를 못 찾아서가 아니다 -- 위반된 가장 강한 제약은
ADMIN_SYSTEM_PROMPT에 있었고 매 턴 컨텍스트에 강제로 들어가 있었다. 추론 능력 문제도
아니다 -- 요청받은 제한 로직 자체는 정확했다. 원인은 편집 방식이다. 재생성은 지금 과업과
무관한 불변식을 조용히 버린다.

그래서 이 게이트는 "무엇이 지워졌는가"를 판정하지 않고(그건 G003이 한다) "한 번에 얼마나
지웠는가"만 본다. 핵심 파일에서 임계치를 넘는 삭제가 일어나면 재작성으로 간주하고 막는다.
정당한 대규모 삭제라면 사람이 SE_GATE_ALLOW_REWRITE=1 로 명시적으로 통과시킨다 --
조용히 지나가는 경로가 없다는 것이 요점이다.
"""
from __future__ import annotations

import os
import re

RULE_ID = "G005"
TITLE = "핵심 파일의 대량 삭제(재작성) 차단"
ORIGIN = "1a82685"
EVIDENCE = "public_agent_memory/20260828-202743_자기_코드_수정은_재작성이_아니라_패치로.md"

# 에이전트 자신을 이루는 파일들. 여기서의 대량 삭제가 곧 자기 재작성이다.
CRITICAL_FILES = {
    "discord_bot_server.py", "main_public.py", "bot_tools.py", "agent_memory.py",
    "public_agent_files.py", "agent_context.py", "gatekeeper.py", "self_challenge.py",
    # 2026-09-02 추가. 앞의 목록은 이 파일들이 생기기 전에 만들어졌고, 그동안 새로 생긴
    # 안전장치들이 대량 삭제 보호를 못 받고 있었다 -- 목록이 낡으면 게이트도 낡는다.
    "secret_filter.py",   # 비밀값 마스킹 + 공개 채널 자식 환경 정리 (G011 이 검사한다)
    "quota_tracker.py",   # 키/모델 가용성 상태 -- 지워지면 폴백이 매번 처음부터 두드린다
    "memory_hygiene.py",  # 기억 위생 절차
}
MAX_DELETED_LINES = 40

_NUMSTAT = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")


def check(ctx) -> "list[str]":
    if os.getenv("SE_GATE_ALLOW_REWRITE") == "1":
        return []
    violations: list[str] = []
    for line in ctx.diff_numstat().splitlines():
        m = _NUMSTAT.match(line)
        if not m:
            continue
        added, deleted, path = m.group(1), m.group(2), m.group(3)
        if deleted == "-" or path not in CRITICAL_FILES:
            continue
        if int(deleted) > MAX_DELETED_LINES:
            violations.append(
                f"{path}: 이번 변경에서 {deleted}줄이 삭제됐다 (임계치 {MAX_DELETED_LINES}줄, "
                f"추가 {added}줄). 파일 전체 재작성이면 요청과 무관한 불변식이 함께 사라진다 -- "
                f"바꿀 줄만 고쳐라. 의도한 대규모 삭제라면 SE_GATE_ALLOW_REWRITE=1 로 명시하라"
            )
    return violations
