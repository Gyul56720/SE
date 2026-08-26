"""
국가법령정보센터(law.go.kr) Open API 래퍼. 키 발급 없이 OC=test 게스트 계정으로 접근 가능
(실측 확인됨 -- 검색/본문조회 둘 다 동작). RULE 파이프라인 1단계(법적 근거 수집)의 "이론"
쪽 grounding 소스: 실제 법률 조문 원문을 그대로 가져온다 (판례는 별도 소스 필요, 아직 미구현).

arxiv_source.py/github_source.py와 같은 자리 -- 여기서도 "원문에 없는 조문을 지어내지 않는다"
원칙을 지키기 위해, LLM에는 이 모듈이 가져온 조문 원문만 grounding으로 넘긴다.
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import requests

BASE = "http://www.law.go.kr/DRF"
OC = "test"  # 게스트 접근 -- 국가법령정보센터가 공개적으로 안내하는 테스트 계정


@dataclass
class Article:
    number: str
    title: str
    content: str


@dataclass
class Statute:
    name: str
    mst: str
    law_id: str
    articles: list[Article] = field(default_factory=list)


def find_statute(name: str) -> Statute | None:
    """법령명으로 정확히 일치하는 법령을 찾는다 (검색 API가 부분일치라서 이름을 클라이언트에서
    한 번 더 정확히 걸러야 함 -- 실측: "민법"으로 검색하면 "난민법"도 같이 잡힘)."""
    resp = requests.get(f"{BASE}/lawSearch.do", params={
        "OC": OC, "target": "law", "query": name, "type": "XML", "display": 100,
    }, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    for law in root.findall("law"):
        law_name = (law.findtext("법령명한글") or "").strip()
        if law_name == name:
            return Statute(name=law_name, mst=law.findtext("법령일련번호"), law_id=law.findtext("법령ID"))
    return None


def fetch_articles(statute: Statute) -> list[Article]:
    """법령 전문을 받아 조문 단위로 파싱. statute.articles에 캐싱해서 반환."""
    if statute.articles:
        return statute.articles
    resp = requests.get(f"{BASE}/lawService.do", params={
        "OC": OC, "target": "law", "MST": statute.mst, "type": "XML",
    }, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    articles = []
    for jo in root.iter("조문단위"):
        content = jo.findtext("조문내용")
        if not content:
            continue
        articles.append(Article(
            number=jo.findtext("조문번호") or "",
            title=jo.findtext("조문제목") or "",
            content=content.strip(),
        ))
    statute.articles = articles
    return articles


def get_articles_by_keyword(statute_name: str, keywords: list[str]) -> list[Article]:
    """법령명 + 조문제목/내용에 등장하는 키워드로 관련 조문만 추린다 (전문 다 넘기면
    수천 조문이라 grounding 텍스트가 너무 커짐 -- 관련 조문만 선별)."""
    statute = find_statute(statute_name)
    if not statute:
        return []
    articles = fetch_articles(statute)
    return [a for a in articles if any(k in a.title or k in a.content for k in keywords)]


def format_articles(articles: list[Article]) -> str:
    return "\n\n".join(f"제{a.number}조({a.title})\n{a.content}" for a in articles)


if __name__ == "__main__":
    arts = get_articles_by_keyword("민법", ["법인", "청산", "해산"])
    print(f"{len(arts)}개 조문 발견")
    print(format_articles(arts[:5]))
