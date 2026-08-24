"""
1. 자료 수집 Agent
LLM을 전혀 쓰지 않는다 - 순수 API 호출 + 정렬/중복제거 로직이라 무료 한도 걱정이 없다.
arXiv + Semantic Scholar + OpenAlex를 기간(config.PERIOD_BUCKETS)별로 병렬 조회한 뒤
DOI/arXiv ID로 중복을 제거하고, 구간별 citation_count 내림차순으로 정리한다.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from config import PERIOD_BUCKETS
from sources import arxiv_source, semantic_scholar, openalex


@dataclass
class Candidate:
    """세 소스의 결과를 하나로 합친 최종 후보. analyzer.py/organizer.py는 이 포맷만 본다."""
    title: str
    year: int
    authors: list[str] = field(default_factory=list)
    arxiv_id: str | None = None
    doi: str | None = None
    openalex_id: str | None = None
    s2_paper_id: str | None = None
    citation_count: int = 0
    abstract: str = ""
    pdf_url: str | None = None
    tldr: str | None = None


def _normalize_title(title: str) -> str:
    return "".join(ch for ch in title.lower() if ch.isalnum())


def _key(c: Candidate) -> str:
    """중복 제거용 키.
    소스마다 arXiv/S2/OpenAlex 중 어느 식별자를 채워주는지가 달라서
    (예: arXiv 결과엔 arxiv_id만, OpenAlex 결과엔 doi만 있는 식) ID 우선으로 키를 잡으면
    같은 논문인데도 서로 다른 키로 갈려서 병합이 안 되는 문제가 생긴다.
    그래서 모든 소스가 공통으로 주는 (정규화된 제목, 연도)를 1차 키로 쓴다.
    """
    return f"{_normalize_title(c.title)}:{c.year}"


def _merge(records: list[Candidate]) -> list[Candidate]:
    """같은 논문이 여러 소스에서 잡히면, citation_count가 더 큰 쪽 정보로 병합한다."""
    merged: dict[str, Candidate] = {}
    for c in records:
        k = _key(c)
        if k not in merged:
            merged[k] = c
            continue
        existing = merged[k]
        # 필드별로 비어있는 쪽을 채워주고, citation_count는 더 큰 값을 채택
        existing.citation_count = max(existing.citation_count, c.citation_count)
        existing.arxiv_id = existing.arxiv_id or c.arxiv_id
        existing.doi = existing.doi or c.doi
        existing.openalex_id = existing.openalex_id or c.openalex_id
        existing.s2_paper_id = existing.s2_paper_id or c.s2_paper_id
        existing.pdf_url = existing.pdf_url or c.pdf_url
        existing.tldr = existing.tldr or c.tldr
        if len(c.abstract) > len(existing.abstract):
            existing.abstract = c.abstract
    return list(merged.values())


def _is_relevant(c: Candidate, keyword: str) -> bool:
    """제목/초록에 키워드가 실제로 등장하는지 체크.
    OpenAlex/S2는 느슨한 검색이라 관련 없는 고인용 논문이 섞여 들어오는데,
    이걸 citation_count로만 정렬하면 그런 논문이 상위를 차지해버린다.
    """
    kw = keyword.lower()
    return kw in c.title.lower() or kw in c.abstract.lower()


def collect_period(keyword: str, year_start: int, year_end: int, top_n: int = 6) -> list[Candidate]:
    """한 기간 구간에 대해 3개 소스를 조회. 키워드가 실제 등장하는 후보를 우선하고,
    그 안에서 citation_count 내림차순으로 상위 top_n개를 반환."""
    records: list[Candidate] = []

    for p in arxiv_source.search(keyword, year_start, year_end, max_results=15):
        records.append(Candidate(title=p.title, year=p.year, authors=p.authors,
                                  arxiv_id=p.arxiv_id, abstract=p.abstract, pdf_url=p.pdf_url))

    try:
        for p in semantic_scholar.search(keyword, year_start, year_end, limit=15):
            records.append(Candidate(title=p.title, year=p.year, authors=p.authors,
                                      arxiv_id=p.arxiv_id, doi=p.doi, s2_paper_id=p.paper_id,
                                      citation_count=p.citation_count or 0, abstract=p.abstract,
                                      pdf_url=p.pdf_url, tldr=p.tldr))
    except Exception as e:
        print(f"[경고] Semantic Scholar 조회 실패({year_start}-{year_end}): {e}")

    try:
        for p in openalex.search(keyword, year_start, year_end, per_page=15):
            records.append(Candidate(title=p.title, year=p.year, authors=p.authors,
                                      doi=p.doi, openalex_id=p.openalex_id,
                                      citation_count=p.citation_count or 0, abstract=p.abstract,
                                      pdf_url=p.pdf_url))
    except Exception as e:
        print(f"[경고] OpenAlex 조회 실패({year_start}-{year_end}): {e}")

    merged = _merge(records)
    relevant = [c for c in merged if _is_relevant(c, keyword)]
    rest = [c for c in merged if c not in relevant]
    relevant.sort(key=lambda c: c.citation_count, reverse=True)
    rest.sort(key=lambda c: c.citation_count, reverse=True)
    ranked = relevant + rest  # 키워드 매칭 안 된 후보는 보충용으로만 뒤에 붙임
    return ranked[:top_n]


def collect(keyword: str, top_n_per_period: int = 6) -> dict[str, list[Candidate]]:
    """config.PERIOD_BUCKETS 전체 구간에 대해 수집. {'2009-2013': [...], ...} 형태로 반환."""
    out: dict[str, list[Candidate]] = {}
    for start, end in PERIOD_BUCKETS:
        label = f"{start}-{end}"
        print(f"[수집] {label} 구간에서 '{keyword}' 검색 중...")
        out[label] = collect_period(keyword, start, end, top_n=top_n_per_period)
    return out


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "roofline model"
    for period, cands in collect(kw).items():
        print(f"\n=== {period} ===")
        for c in cands:
            print(f"  [{c.citation_count:>5}] {c.title} ({c.year})")
