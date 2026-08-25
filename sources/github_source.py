"""
GitHub 소스. 키 불필요 -- 이미 `gh auth login`된 로컬 gh CLI를 서브프로세스로 그대로 쓴다
(별도 GITHUB_TOKEN을 .env에 추가로 안 받아도 됨, gh가 keyring에서 알아서 인증 붙임).

arxiv_source.py/semantic_scholar.py/openalex.py가 "논문"을 반환하듯, 이 모듈은 "리포지토리"를
공통 포맷(Repo)으로 반환한다. book_generator.py가 개념 챕터에 "실제 동작하는 참고 코드"를
붙일 때 이 결과를 근거로 쓴다 -- Gemini가 코드를 지어내지 않도록, 실존 리포/파일 경로만 준다.
"""

from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass


@dataclass
class Repo:
    full_name: str
    description: str
    url: str
    stars: int
    language: str | None
    updated_at: str


def _run_gh(args: list[str]) -> list[dict]:
    """gh CLI를 서브프로세스로 호출. gh 자체가 없거나 인증이 안 됐으면 빈 리스트로 조용히
    폴백한다 (이 소스가 없어도 나머지 파이프라인은 동작해야 하므로 예외로 전체를 죽이지 않음)."""
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def search_repos(query: str, limit: int = 15, language: str | None = None) -> list[Repo]:
    """리포지토리 검색 (README/설명/이름 매칭). Verilog/SystemVerilog처럼 언어 필터가
    의미 있는 검색은 language 인자로 좁힌다 (예: language="Verilog").

    GitHub 검색은 다어절 쿼리를 전부 AND로 묶어서, 4단어 이상 쿼리는 실측상 0건이
    나오는 경우가 잦았다(예: "systemverilog FIFO verification testbench" -> 0건,
    "systemverilog FIFO" -> 다수). 그래서 첫 시도가 비면 앞 2단어로 자동 축소해
    한 번 더 시도한다 -- 결과 없음과 쿼리가 너무 좁았음을 구분하기 위함."""
    def _search(q: str) -> list[dict]:
        args = ["search", "repos", q, "--limit", str(limit),
                "--json", "fullName,description,url,stargazersCount,language,updatedAt"]
        if language:
            args += ["--language", language]
        return _run_gh(args)

    raw = _search(query)
    words = query.split()
    if not raw and len(words) > 2:
        raw = _search(" ".join(words[:2]))
    return [
        Repo(
            full_name=r.get("fullName", ""),
            description=r.get("description") or "",
            url=r.get("url", ""),
            stars=r.get("stargazersCount", 0),
            language=r.get("language"),
            updated_at=r.get("updatedAt", ""),
        )
        for r in raw
    ]


@dataclass
class CodeHit:
    """코드 검색 결과 한 건 -- 리포 전체가 아니라 특정 파일 하나. book_generator.py가
    '이 개념이 실제로 어떤 파일에서 어떻게 쓰이는지' 인용할 때 repo보다 이쪽이 더 구체적이다."""
    repo_full_name: str
    path: str
    url: str
    fragment: str = ""


def search_code(query: str, limit: int = 10, language: str | None = None) -> list[CodeHit]:
    """코드 검색 (파일 내용 매칭). gh search code는 GitHub code search API를 그대로 쓰므로
    비공개 리포는 안 잡히고(정상), rate limit이 repos 검색보다 낮다 -- limit을 낮게 잡을 것."""
    args = ["search", "code", query, "--limit", str(limit),
            "--json", "repository,path,url"]
    if language:
        args += ["--language", language]
    raw = _run_gh(args)
    return [
        CodeHit(
            repo_full_name=(r.get("repository") or {}).get("fullName", ""),
            path=r.get("path", ""),
            url=r.get("url", ""),
        )
        for r in raw
    ]


if __name__ == "__main__":
    repos = search_repos("verilog clock domain crossing", limit=5, language="SystemVerilog")
    for r in repos:
        print(f"[{r.stars:>5}⭐] {r.full_name} ({r.language}) -- {r.description[:60]}")
        print(f"         {r.url}")
