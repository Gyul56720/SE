"""
OpenAlex API 클라이언트. 키 불필요 (Google Scholar에는 공식 무료 API가 없어서, 이게 실질적 대체재).
mailto 파라미터를 채우면 "polite pool"로 더 빠르고 안정적으로 응답받는다.
"""

from __future__ import annotations
import requests
from dataclasses import dataclass, field

from config import OPENALEX_MAILTO

BASE = "https://api.openalex.org"


@dataclass
class Paper:
    title: str
    year: int
    authors: list[str] = field(default_factory=list)
    doi: str | None = None
    citation_count: int | None = None
    abstract: str = ""
    pdf_url: str | None = None
    openalex_id: str | None = None  # citation_walk용 (W로 시작하는 ID)
    referenced_works: list[str] = field(default_factory=list)
    source: str = "openalex"


def _common_params() -> dict:
    return {"mailto": OPENALEX_MAILTO} if OPENALEX_MAILTO else {}


def _reconstruct_abstract(inv_index: dict | None) -> str:
    """OpenAlex는 저작권 이슈로 abstract를 inverted index(단어->위치리스트)로만 준다. 원문으로 복원."""
    if not inv_index:
        return ""
    positions: dict[int, str] = {}
    for word, idxs in inv_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def _to_paper(d: dict) -> Paper:
    loc = d.get("best_oa_location") or d.get("primary_location") or {}
    return Paper(
        title=d.get("title") or d.get("display_name") or "",
        year=d.get("publication_year") or 0,
        authors=[
            (a.get("author") or {}).get("display_name", "")
            for a in (d.get("authorships") or [])
        ],
        doi=(d.get("doi") or "").replace("https://doi.org/", "") or None,
        citation_count=d.get("cited_by_count"),
        abstract=_reconstruct_abstract(d.get("abstract_inverted_index")),
        pdf_url=(loc or {}).get("pdf_url"),
        openalex_id=(d.get("id") or "").replace("https://openalex.org/", ""),
        referenced_works=[w.replace("https://openalex.org/", "") for w in (d.get("referenced_works") or [])],
    )


def search(keyword: str, year_start: int, year_end: int, per_page: int = 20) -> list[Paper]:
    params = {
        "search": keyword,
        "filter": f"publication_year:{year_start}-{year_end}",
        "per_page": per_page,
        **_common_params(),
    }
    resp = requests.get(f"{BASE}/works", params=params, timeout=20)
    resp.raise_for_status()
    return [_to_paper(d) for d in resp.json().get("results", [])]


def get_work(openalex_id: str) -> Paper | None:
    """단건 조회. referenced_works(이 논문이 인용한 것)가 응답에 바로 포함된다."""
    resp = requests.get(f"{BASE}/works/{openalex_id}", params=_common_params(), timeout=20)
    if resp.status_code != 200:
        return None
    return _to_paper(resp.json())


def get_citing_works(openalex_id: str, per_page: int = 20) -> list[Paper]:
    """이 논문을 인용한(후속) 논문들. OpenAlex는 이걸 work 객체에 안 담아주고 별도 필터 쿼리로만 준다."""
    params = {"filter": f"cites:{openalex_id}", "per_page": per_page, **_common_params()}
    resp = requests.get(f"{BASE}/works", params=params, timeout=20)
    resp.raise_for_status()
    return [_to_paper(d) for d in resp.json().get("results", [])]


if __name__ == "__main__":
    for p in search("roofline model", 2009, 2013, per_page=5):
        print(f"- [{p.year}] {p.title} (cited={p.citation_count}, id={p.openalex_id})")
