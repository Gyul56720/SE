"""
arXiv 소스. 키 불필요.
공식 arXiv API의 submittedDate 범위 쿼리 문법을 그대로 활용한다:
  search_query=(all:KEYWORD) AND submittedDate:[YYYYMMDDTTTT TO YYYYMMDDTTTT]
파싱은 직접 XML을 만지지 않고 잘 관리되는 `arxiv` 패키지(lukasschwab/arxiv.py)를 쓴다.
"""

from __future__ import annotations
import arxiv
from dataclasses import dataclass, field


@dataclass
class Paper:
    """모든 소스(arXiv/S2/OpenAlex)가 이 공통 포맷으로 결과를 반환한다."""
    title: str
    year: int
    authors: list[str] = field(default_factory=list)
    arxiv_id: str | None = None
    doi: str | None = None
    citation_count: int | None = None  # arXiv 자체엔 인용수가 없어 None으로 둠 (S2/OpenAlex가 채움)
    abstract: str = ""
    pdf_url: str | None = None
    source: str = "arxiv"


def search(keyword: str, year_start: int, year_end: int, max_results: int = 20) -> list[Paper]:
    """지정한 [year_start, year_end] 구간 안에서 keyword로 arXiv를 검색한다."""
    date_range = f"submittedDate:[{year_start}01010000 TO {year_end}12312359]"
    query = f"all:{keyword} AND {date_range}"

    client = arxiv.Client(page_size=max_results, delay_seconds=3.0, num_retries=3)
    search_obj = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []
    for r in client.results(search_obj):
        results.append(
            Paper(
                title=r.title.strip(),
                year=r.published.year,
                authors=[a.name for a in r.authors],
                arxiv_id=r.get_short_id(),
                abstract=(r.summary or "").replace("\n", " ").strip(),
                pdf_url=r.pdf_url,
                source="arxiv",
            )
        )
    return results


if __name__ == "__main__":
    # 단독 실행 시 간단히 동작 확인
    for p in search("roofline model", 2009, 2013, max_results=5):
        print(f"- [{p.year}] {p.title} ({p.arxiv_id})")
