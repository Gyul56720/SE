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

## 핵심 주장
{core_claim}

## 이 논문이 확장하는 것
{upgrades_from}

## 핵심 수치
{key_numbers_list}

## 한계
{limitations}

## 원문
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

        content = _TEMPLATE.format(
            title=c.title.replace('"', "'"),
            year=c.year,
            authors=[au for au in c.authors[:5]],
            citations=c.citation_count,
            arxiv_id=c.arxiv_id or "",
            doi=c.doi or "",
            predecessor_line=predecessor_line,
            keyword_tag=re.sub(r"\s+", "-", keyword.lower()),
            one_line_summary=a.one_line_summary,
            core_claim=a.core_claim,
            upgrades_from=a.upgrades_from or "(선행 연구와의 관계 불명확)",
            key_numbers_list="\n".join(f"- {n}" for n in a.key_numbers) or "- (없음)",
            limitations=a.limitations,
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
