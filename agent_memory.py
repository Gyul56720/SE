"""
공개 채널 에이전트의 장기 기억 -- repo의 public_agent_memory/ 폴더에 마크다운 노트로 쌓고
git commit + push까지 한다. LangGraph의 MemorySaver는 인메모리라 프로세스가 재시작되면
(= 배포할 때마다) 전부 날아가는데, 여기에 쓴 건 git에 남으므로 재시작을 넘어 축적된다.

가중치를 바꾸는 진짜 학습은 아니다 -- 모델은 그대로고, 대신 다음 질문 때 관련 노트를
프롬프트에 끼워넣어서 "쓸수록 아는 게 늘어나는" 효과만 만든다.

보안 주의: 공개 채널은 화이트리스트가 없어서 그 채널을 볼 수 있는 누구나 이 도구를 통해
repo에 쓸 수 있다 (의도된 트레이드오프). 그래서 아래 제약을 코드로 강제한다.
- 쓰기는 MEMORY_DIR 밖으로 절대 나갈 수 없다 (슬러그화 + 최종 경로 재확인).
- 파일 개수/크기 상한이 있다 (repo와 디스크가 무한히 커지는 것 방지).
- 커밋은 MEMORY_DIR 경로만 대상으로 한다 -- 워킹트리의 다른 변경을 휩쓸어가지 않는다.
- 노트에 작성자 Discord ID를 남겨서 나중에 추적/되돌리기가 가능하다.
"""

from __future__ import annotations

import re
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
MEMORY_DIR = REPO_DIR / "public_agent_memory"
MEMORY_REL = "public_agent_memory"

MAX_CONTENT_CHARS = 4000
MAX_TOPIC_CHARS = 120
MAX_FILES = 500
MAX_SEARCH_RESULTS = 5
MAX_SNIPPET_CHARS = 700

# git 작업은 admin 채널의 git_sync()와 같은 워킹트리를 건드린다. 그쪽은 asyncio.Lock으로
# 직렬화되지만 이 함수들은 executor 스레드에서 불리므로, 스레드 간에도 통하는 락이 필요하다.
GIT_MUTEX = threading.Lock()

_SLUG_BAD = re.compile(r"[^0-9A-Za-z가-힣 _-]")
_STOPWORDS = {"그", "이", "저", "것", "수", "등", "및", "the", "a", "an", "is", "of", "to", "and"}


def _slugify(topic: str) -> str:
    slug = _SLUG_BAD.sub("", topic).strip()
    slug = re.sub(r"\s+", "_", slug)
    return slug[:60] or "untitled"


def _resolve_inside_memory(filename: str) -> Path:
    """MEMORY_DIR 안으로만 해석되는 경로를 반환. 벗어나면 ValueError."""
    path = (MEMORY_DIR / filename).resolve()
    if path.parent != MEMORY_DIR.resolve():
        raise ValueError("메모리 폴더 밖의 경로는 쓸 수 없다.")
    return path


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_DIR, capture_output=True, text=True)


def _commit_and_push(message: str) -> str:
    """MEMORY_DIR 경로만 커밋해서 push. origin이 앞서 있으면 rebase 후 재시도한다
    (git_sync()와 같은 이유 -- 이 VM 밖에서도 같은 repo에 push하므로 실제로 발생한다)."""
    with GIT_MUTEX:
        _git(["add", "--", MEMORY_REL])
        staged = _git(["diff", "--cached", "--quiet", "--", MEMORY_REL])
        if staged.returncode == 0:
            return "변경 없음 (이미 같은 내용)"
        commit = _git(["commit", "-m", message, "--", MEMORY_REL])
        if commit.returncode != 0:
            return f"커밋 실패: {commit.stderr.strip()[:200]}"
        push = _git(["push"])
        if push.returncode == 0:
            return "저장 + git push 완료"
        _git(["fetch", "origin"])
        rebase = _git(["rebase", "origin/main"])
        if rebase.returncode != 0:
            _git(["rebase", "--abort"])
            return "커밋은 됐지만 push 실패 (origin과 충돌, 수동 확인 필요)"
        retry = _git(["push"])
        if retry.returncode != 0:
            return f"커밋은 됐지만 push 실패: {retry.stderr.strip()[:200]}"
        return "저장 + git push 완료 (rebase 후 재시도)"


def save_memory(topic: str, content: str, author_id: str = "unknown") -> str:
    """새 기억을 노트로 저장하고 git에 push한다."""
    topic = (topic or "").strip()[:MAX_TOPIC_CHARS]
    content = (content or "").strip()
    if not topic or not content:
        return "실패: topic과 content가 모두 필요하다."
    if len(content) > MAX_CONTENT_CHARS:
        return f"실패: content가 너무 길다 (최대 {MAX_CONTENT_CHARS}자)."

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(MEMORY_DIR.glob("*.md"))
    if len(existing) >= MAX_FILES:
        return f"실패: 메모리 노트가 상한({MAX_FILES}개)에 도달했다. 관리자가 정리해야 한다."

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    try:
        path = _resolve_inside_memory(f"{stamp}_{_slugify(topic)}.md")
    except ValueError as e:
        return f"실패: {e}"

    body = (
        f"---\n"
        f"topic: {topic!r}\n"
        f"saved_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"author_discord_id: {author_id}\n"
        f"source: discord-public-channel-agent\n"
        f"---\n\n"
        f"# {topic}\n\n"
        f"{content}\n"
    )
    path.write_text(body, encoding="utf-8")
    result = _commit_and_push(f"public-agent memory: {topic[:60]}")
    print(f"[agent-memory] saved {path.name} by {author_id} -> {result}")
    return f"'{topic}' 저장됨. {result}"


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[0-9A-Za-z가-힣]+", text.lower())
    return [w for w in words if len(w) > 1 and w not in _STOPWORDS]


def search_memory(query: str) -> str:
    """저장된 기억에서 query와 관련된 노트를 찾아 발췌해 돌려준다."""
    query = (query or "").strip()
    if not query:
        return "실패: query가 필요하다."
    if not MEMORY_DIR.is_dir():
        return "저장된 기억이 아직 없다."

    terms = set(_tokenize(query))
    if not terms:
        return "저장된 기억이 아직 없다."

    scored: list[tuple[int, Path, str]] = []
    for path in MEMORY_DIR.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        haystack = (path.name + "\n" + text).lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((score, path, text))

    if not scored:
        return f"'{query}' 관련해서 저장된 기억이 없다."

    scored.sort(key=lambda item: (-item[0], item[1].name))
    chunks = []
    for score, path, text in scored[:MAX_SEARCH_RESULTS]:
        snippet = text.split("---", 2)[-1].strip()[:MAX_SNIPPET_CHARS]
        chunks.append(f"[{path.name}]\n{snippet}")
    print(f"[agent-memory] search {query[:60]!r} -> {len(scored)} hit(s)")
    return "\n\n".join(chunks)
