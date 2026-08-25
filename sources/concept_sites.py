"""
수학/물리/공학 "개념" 소스. arXiv가 최신 연구 논문을 주는 것과 달리, 이 모듈은 이미 정립된
표준 개념/정의/공식의 산문 설명을 준다 -- book_generator.py가 Gemini에게 "이 실존 텍스트를
근거로 챕터를 써라"라고 grounding 시킬 재료.

Wikipedia REST API를 쓴다: 키 불필요, rate limit 관대함, 수학/공학 문서 커버리지가 넓고
사실관계 오류가 상대적으로 적은 2차 출처로 널리 인정됨(원 정의/정리 자체는 저작권 대상이
아니므로 theory_generator.py의 "특정 교재 인용 금지" 원칙과도 충돌 없음).
"""

from __future__ import annotations
import requests
from dataclasses import dataclass

SUMMARY_ENDPOINT = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
EXTRACT_ENDPOINT = "https://en.wikipedia.org/w/api.php"


@dataclass
class ConceptText:
    title: str
    summary: str
    extract: str  # 전체 산문 발췌 (섹션 헤더 포함, plaintext)
    url: str


def fetch_concept(title: str, max_chars: int = 8000) -> ConceptText | None:
    """제목(예: "Clock domain crossing", "Systolic array")으로 Wikipedia 문서를 가져온다.
    문서가 없으면 None -- 호출부가 "이 개념은 grounding 없이 LLM 지식만으로 쓴다"고
    프롬프트에 명시해야 하므로, 빈 문자열이 아니라 명시적으로 None을 돌려준다."""
    try:
        summary_resp = requests.get(
            SUMMARY_ENDPOINT.format(title=title.replace(" ", "_")),
            headers={"User-Agent": "paper-research-pipeline/1.0"}, timeout=15,
        )
    except requests.RequestException:
        return None
    if summary_resp.status_code != 200:
        return None
    summary_data = summary_resp.json()
    if summary_data.get("type") == "disambiguation":
        return None

    extract_resp = requests.get(
        EXTRACT_ENDPOINT,
        params={
            "action": "query", "prop": "extracts", "explaintext": 1,
            "titles": summary_data.get("title", title), "format": "json",
        },
        headers={"User-Agent": "paper-research-pipeline/1.0"}, timeout=15,
    )
    extract = ""
    if extract_resp.status_code == 200:
        pages = extract_resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            extract = page.get("extract", "")
            break

    return ConceptText(
        title=summary_data.get("title", title),
        summary=summary_data.get("extract", ""),
        extract=extract[:max_chars],
        url=summary_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    )


if __name__ == "__main__":
    c = fetch_concept("Clock domain crossing")
    if c:
        print(f"{c.title}\n{c.url}\n\n{c.extract[:1000]}")
    else:
        print("문서를 찾지 못함")
