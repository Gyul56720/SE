"""
3. 자료 정리 Agent
vault 폴더에 .md 파일을 직접 쓴다 (플러그인 의존성 없음 - Obsidian이 꺼져 있어도 동작).
핵심은 frontmatter의 predecessor:: 필드 - 이게 있어야 Obsidian 그래프뷰가
"발전 과정"을 자동으로 트리로 그려준다.
"""

from __future__ import annotations
import re
from pathlib import Path

from config import OBSIDIAN_VAULT_PATH
from analyzer import Analysis

_NA = "N/A -- 이 항목은 논문에 해당하는 정보가 없음"

# README.md 12섹션 템플릿을 논문 한 편짜리 노트에 맞게 재해석한 것.
# analyzer.py가 실제로 뽑는 5개 필드(one_line_summary/core_claim/upgrades_from/
# key_numbers/limitations)를 의미가 맞는 헤더 하나씩에 배치하고, 소프트웨어 프로젝트
# 전용 개념(설치/API/기술스택/기여가이드/라이선스)처럼 논문에 대응 데이터가 없는
# 섹션은 헤더는 유지하되 본문을 _NA로 채운다.
_TEMPLATE = """---
title: "{title}"
year: {year}
authors: {authors}
citations: {citations}
arxiv_id: "{arxiv_id}"
doi: "{doi}"
{predecessor_line}tags: [paper-pipeline, {keyword_tag}]
---

# {title} ({year})

> {one_line_summary}

## 개요 (Overview)
{overview}

## 주요 특징 (Features)
{key_numbers_list}

## 시작하기 (Getting Started)
{na}

## 사용법 (Usage)
{na}

## 프로젝트 구조 (Project Structure)
{na}

## 기술 스택 & 의존성 (Tech Stack)
{na}

## 결과/성과 (Results/Performance)
{limitations}

## 기여 가이드 (Contributing)
{na}

## 라이선스 (License)
{na}

## 연락처/저자 (Contact/Author)
{authors_list}

## 참고자료 (References)
{pdf_line}
"""


def _slugify(title: str, year: int) -> str:
    slug = re.sub(r"[^\w\s-]", "", title).strip()
    slug = re.sub(r"[\s]+", " ", slug)[:80]
    return f"{slug} ({year})"


def _find_predecessor_link(upgrades_from: str, title_to_slug: dict[str, str], own_title: str) -> str | None:
    """이번 배치에서 함께 처리된 다른 논문 제목이 upgrades_from 텍스트에 등장하면 위키링크로 연결."""
    if not upgrades_from:
        return None
    lower_text = upgrades_from.lower()
    best = None
    for other_title, slug in title_to_slug.items():
        if other_title == own_title:
            continue
        # 제목의 앞 3단어 이상이 겹치면 같은 논문을 가리킨다고 판단 (느슨한 매칭)
        tokens = [t for t in re.findall(r"[a-zA-Z가-힣0-9]+", other_title.lower()) if len(t) > 3][:4]
        if tokens and all(t in lower_text for t in tokens[:2]):
            best = slug
            break
    return best


def write_notes(analyses: list[Analysis], keyword: str, vault_path: Path | None = None) -> list[Path]:
    vault_path = vault_path or OBSIDIAN_VAULT_PATH
    vault_path.mkdir(parents=True, exist_ok=True)

    # 이번 배치 전체의 제목->슬러그 인덱스를 먼저 만들어야 서로를 predecessor로 연결할 수 있다
    title_to_slug = {a.candidate.title: _slugify(a.candidate.title, a.candidate.year) for a in analyses}

    written = []
    for a in analyses:
        c = a.candidate
        slug = title_to_slug[c.title]
        pred_slug = _find_predecessor_link(a.upgrades_from, title_to_slug, c.title)
        predecessor_line = f'predecessor: "[[{pred_slug}]]"\n' if pred_slug else ""

        upgrades_from = a.upgrades_from or "(선행 연구와의 관계 불명확)"
        overview = a.core_claim
        if a.upgrades_from:
            overview += f"\n\n**문제 정의(선행 연구 대비 확장점):** {upgrades_from}"
        authors_list = c.authors[:5]

        content = _TEMPLATE.format(
            title=c.title.replace('"', "'"),
            year=c.year,
            authors=authors_list,
            citations=c.citation_count,
            arxiv_id=c.arxiv_id or "",
            doi=c.doi or "",
            predecessor_line=predecessor_line,
            keyword_tag=re.sub(r"\s+", "-", keyword.lower()),
            one_line_summary=a.one_line_summary,
            overview=overview,
            key_numbers_list="\n".join(f"- {n}" for n in a.key_numbers) or "- (없음)",
            limitations=a.limitations or _NA,
            na=_NA,
            authors_list="\n".join(f"- {au}" for au in authors_list) or "- (저자 정보 없음)",
            pdf_line=f"[PDF]({c.pdf_url})" if c.pdf_url else "(오픈 액세스 링크 없음)",
        )

        out_path = vault_path / f"{slug}.md"
        out_path.write_text(content, encoding="utf-8")
        written.append(out_path)
        print(f"[정리] {out_path.name}" + (f"  <- predecessor: {pred_slug}" if pred_slug else ""))

    return written


if __name__ == "__main__":
    import collector
    import analyzer

    cands = collector.collect_period("roofline model", 2009, 2013, top_n=2)
    analyses = analyzer.analyze_all(cands)
    write_notes(analyses, keyword="roofline model")
