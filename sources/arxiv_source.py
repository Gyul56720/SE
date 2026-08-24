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


def search(keyword: str | list[str], year_start: int, year_end: int, max_results: int = 20) -> list[Paper]:
    """지정한 [year_start, year_end] 구간 안에서 keyword로 arXiv를 검색한다.

    keyword를 따옴표 없이 여러 단어로 그대로 `all:` 필드에 박으면 arXiv 쿼리 파서가
    깨져서 submittedDate 범위 필터가 무시되는 버그가 있었다 (예: 20단어짜리 키워드를
    2005-2013 구간으로 검색했는데 2025/2026년 논문이 나옴 -- 실측 확인됨). 그래서 각 구를
    큰따옴표로 감싸 `all:"phrase"`로 명시적 phrase 매치를 걸고, 여러 구는 OR로 묶는다."""
    terms = keyword if isinstance(keyword, list) else [keyword]
    date_range = f"submittedDate:[{year_start}01010000 TO {year_end}12312359]"
    phrase_query = " OR ".join(f'all:"{t}"' for t in terms)
    if len(terms) > 1:
        phrase_query = f"({phrase_query})"
    query = f"{phrase_query} AND {date_range}"

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


def get_by_id(arxiv_id: str) -> Paper | None:
    """arXiv ID로 논문 한 편을 직접 조회한다 (id_list 사용 -- 텍스트 검색이 아니라 정확한 조회라
    빠르고 신뢰성 있음). deep_review.py의 --arxiv-id 옵션이 이걸 쓴다.
    예전엔 search(arxiv_id, ...)로 "all:" 필드에 ID 문자열을 텍스트 검색하듯 넣어서 썼는데,
    date-range 쿼리 버그를 고치며 각 구를 큰따옴표로 감싸는 phrase 매치로 바꾼 뒤로는
    ID가 논문 본문에 그대로 안 나타나는 경우 매치가 안 되는 문제가 생겨 별도 함수로 뺐다."""
    client = arxiv.Client(page_size=1, delay_seconds=3.0, num_retries=3)
    search_obj = arxiv.Search(id_list=[arxiv_id])
    for r in client.results(search_obj):
        return Paper(
            title=r.title.strip(),
            year=r.published.year,
            authors=[a.name for a in r.authors],
            arxiv_id=r.get_short_id(),
            abstract=(r.summary or "").replace("\n", " ").strip(),
            pdf_url=r.pdf_url,
            source="arxiv",
        )
    return None


if __name__ == "__main__":
    # 단독 실행 시 간단히 동작 확인
    for p in search("roofline model", 2009, 2013, max_results=5):
        print(f"- [{p.year}] {p.title} ({p.arxiv_id})")
