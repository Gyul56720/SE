"""
Semantic Scholar Graph API 클라이언트. 키 없이도 동작 (초당 ~1req 제한).
SEMANTIC_SCHOLAR_API_KEY를 .env에 채우면 더 여유로운 한도로 자동 전환된다.

이 모듈이 제공하는 것 두 가지:
  1) search()            -> 키워드+기간으로 논문 검색 (citationCount/influentialCitationCount 포함)
  2) get_references() / get_citations()  -> "이 논문이 인용한 것 / 이 논문을 인용한 것"
     citation_walk(research_graph.py)이 이 두 함수로 계보를 양방향으로 따라간다.
"""

from __future__ import annotations
import time
import requests
from dataclasses import dataclass, field

from config import SEMANTIC_SCHOLAR_API_KEY

BASE = "https://api.semanticscholar.org/graph/v1"
_HEADERS = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}
_MIN_INTERVAL = 1.0 if not SEMANTIC_SCHOLAR_API_KEY else 0.05
_last_call = 0.0

FIELDS = "title,year,authors,citationCount,influentialCitationCount,externalIds,abstract,tldr,openAccessPdf"


@dataclass
class Paper:
    title: str
    year: int
    authors: list[str] = field(default_factory=list)
    arxiv_id: str | None = None
    doi: str | None = None
    citation_count: int | None = None
    influential_citation_count: int | None = None
    abstract: str = ""
    pdf_url: str | None = None
    tldr: str | None = None
    paper_id: str | None = None  # Semantic Scholar 내부 ID (citation_walk용)
    source: str = "semantic_scholar"


def _throttled_get(url: str, params: dict) -> dict:
    global _last_call
    for attempt in range(4):
        wait = _MIN_INTERVAL - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=20)
        _last_call = time.time()
        if resp.status_code == 429 and attempt < 3:
            time.sleep(2 ** attempt * 2)  # 2s, 4s, 8s
            continue
        resp.raise_for_status()
        return resp.json()


def _to_paper(d: dict) -> Paper:
    ext = d.get("externalIds") or {}
    oa = d.get("openAccessPdf") or {}
    tldr = (d.get("tldr") or {}).get("text")
    return Paper(
        title=d.get("title") or "",
        year=d.get("year") or 0,
        authors=[a.get("name", "") for a in (d.get("authors") or [])],
        arxiv_id=ext.get("ArXiv"),
        doi=ext.get("DOI"),
        citation_count=d.get("citationCount"),
        influential_citation_count=d.get("influentialCitationCount"),
        abstract=d.get("abstract") or "",
        pdf_url=oa.get("url"),
        tldr=tldr,
        paper_id=d.get("paperId"),
    )


def search(keyword: str, year_start: int, year_end: int, limit: int = 20) -> list[Paper]:
    data = _throttled_get(
        f"{BASE}/paper/search",
        {"query": keyword, "year": f"{year_start}-{year_end}", "limit": limit, "fields": FIELDS},
    )
    return [_to_paper(d) for d in data.get("data", [])]


def get_references(paper_id: str, limit: int = 30) -> list[Paper]:
    """paper_id가 인용한(선행) 논문들. paper_id는 S2 ID 또는 'ARXIV:1704.04760' 형태 모두 가능."""
    data = _throttled_get(
        f"{BASE}/paper/{paper_id}/references",
        {"fields": FIELDS, "limit": limit},
    )
    return [_to_paper(d["citedPaper"]) for d in data.get("data", []) if d.get("citedPaper")]


def get_citations(paper_id: str, limit: int = 30) -> list[Paper]:
    """paper_id를 인용한(후속) 논문들. 여기서 '발전 과정'의 다음 세대를 찾는다."""
    data = _throttled_get(
        f"{BASE}/paper/{paper_id}/citations",
        {"fields": FIELDS, "limit": limit},
    )
    return [_to_paper(d["citingPaper"]) for d in data.get("data", []) if d.get("citingPaper")]


if __name__ == "__main__":
    for p in search("roofline model", 2009, 2013, limit=5):
        print(f"- [{p.year}] {p.title} (cited={p.citation_count})")
