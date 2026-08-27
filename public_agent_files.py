"""
공개 채널 에이전트가 결과물을 남기는 곳 -- Public_agent/ 폴더 밖으로 못 나가는
쓰기 전용 도구다.

이전에는 main_public.py 규칙 7이 run_shell로 main_testing.py 파일 하나만 읽고 쓰고
커밋하는 걸 허용했다. 화이트리스트 없는 채널에 임의 셸 실행 경로를 열어두는 건 위험해서
치웠고, 대신 이 모듈이 agent_memory.py와 같은 방식으로 경로를 강제한다.

- 쓰기는 OUTPUT_DIR 밖으로 절대 나갈 수 없다 (파일명만 받고, 최종 경로 재확인).
- 파일 개수/크기 상한이 있다.
- 커밋은 OUTPUT_DIR 경로만 대상으로 한다 -- 워킹트리의 다른 변경을 휩쓸어가지 않는다.
- push는 하지 않는다 -- 예전 run_shell 제약("git push 금지, 커밋까지만 허용")과 동일하게
  관리자가 검토 후 push하도록 남겨둔다.
"""

from __future__ import annotations

import re
import subprocess
import threading
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_DIR / "Public_agent"
OUTPUT_REL = "Public_agent"

MAX_CONTENT_CHARS = 20000
MAX_FILES = 200

# agent_memory.py의 git 작업과 워킹트리를 공유하므로 같은 이유로 스레드 간 락이 필요하다.
GIT_MUTEX = threading.Lock()

_NAME_BAD = re.compile(r"[^0-9A-Za-z가-힣_.-]")


def _safe_filename(name: str) -> str:
    name = Path(name or "").name  # 디렉터리 성분(../ 등) 제거
    name = _NAME_BAD.sub("_", name).strip("._") or "output"
    return name[:80]


def _resolve_inside_output(filename: str) -> Path:
    """OUTPUT_DIR 안으로만 해석되는 경로를 반환. 벗어나면 ValueError."""
    path = (OUTPUT_DIR / filename).resolve()
    if path.parent != OUTPUT_DIR.resolve():
        raise ValueError("Public_agent 폴더 밖의 경로는 쓸 수 없다.")
    return path


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_DIR, capture_output=True, text=True)


def _commit(message: str) -> str:
    with GIT_MUTEX:
        _git(["add", "--", OUTPUT_REL])
        staged = _git(["diff", "--cached", "--quiet", "--", OUTPUT_REL])
        if staged.returncode == 0:
            return "변경 없음 (이미 같은 내용)"
        commit = _git(["commit", "-m", message, "--", OUTPUT_REL])
        if commit.returncode != 0:
            return f"커밋 실패: {commit.stderr.strip()[:200]}"
        return "커밋 완료 (push는 하지 않음 -- 관리자 검토 후 push)"


def write_output(filename: str, content: str, author_id: str = "unknown") -> str:
    """공개 에이전트의 답변/결과를 Public_agent/ 아래 파일로 쓰고 커밋한다."""
    content = content or ""
    if len(content) > MAX_CONTENT_CHARS:
        return f"실패: content가 너무 길다 (최대 {MAX_CONTENT_CHARS}자)."

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = [p for p in OUTPUT_DIR.iterdir() if p.is_file()]
    safe_name = _safe_filename(filename)

    try:
        path = _resolve_inside_output(safe_name)
    except ValueError as e:
        return f"실패: {e}"

    if path not in existing and len(existing) >= MAX_FILES:
        return f"실패: 파일 개수가 상한({MAX_FILES}개)에 도달했다. 관리자가 정리해야 한다."

    path.write_text(content, encoding="utf-8")
    result = _commit(f"public-agent output: {safe_name} (by {author_id})")
    print(f"[public-agent-files] wrote {safe_name} by {author_id} -> {result}")
    return f"'{safe_name}' 저장됨. {result}"
