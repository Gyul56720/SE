"""
collector.py의 정적 키워드 검색을 '적응형 리서치'로 업그레이드하는 선택 모듈.
(main.py --deep 옵션으로 켠다. 안 켜도 파이프라인은 정상 동작함.)

두 단계를 반복한다:
  1) judge_gaps()    : LLM 호출 1회/iteration. "지금까지 찾은 계보에 빠진 세대가 있는가?"
  2) citation_walk() : LLM 미사용. 각 논문의 forward/backward citation을 따라가서
                        키워드 매칭으론 못 찾는 후속/선행 논문을 찾는다.
"""

from __future__ import annotations
from config import PERIOD_BUCKETS
import gemini_client
import collector
from collector import Candidate
from sources import semantic_scholar, openalex

GAP_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "has_gap": {"type": "BOOLEAN"},
        "reasoning": {"type": "STRING", "description": "왜 빠졌다고/안 빠졌다고 판단했는지 1-2문장"},
        "follow_up_queries": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "빠진 세대를 채우기 위해 검색할 구체적 영문 키워드 0-3개",
        },
    },
    "required": ["has_gap", "reasoning", "follow_up_queries"],
}

GAP_PROMPT_TMPL = """다음은 '{keyword}'에 대해 지금까지 시간순으로 수집한 논문 계보다:

{summary}

이 목록을 개념의 발전 계보(lineage)로 봤을 때, 시간순으로 빠진 세대나 갈래가 있는지 판단하라.
예: 어떤 논문이 명백히 이전 세대를 확장했는데 그 "다음 확장"에 해당하는 후속 논문이 리스트에 없다면 갭이다.
빠진 게 있다면 그걸 찾기 위한 구체적 영문 검색어를 follow_up_queries에 제안하라 (일반적인 키워드 반복 금지).
빠진 게 없다고 판단되면 has_gap=false, follow_up_queries=[]로 답하라.
"""


def _summarize(periods: dict[str, list[Candidate]]) -> str:
    lines = []
    for period, cands in periods.items():
        lines.append(f"[{period}]")
        for c in cands:
            lines.append(f"  - ({c.year}, 인용 {c.citation_count}) {c.title}")
    return "\n".join(lines)


def judge_gaps(keyword: str, periods: dict[str, list[Candidate]]) -> list[str]:
    prompt = GAP_PROMPT_TMPL.format(keyword=keyword, summary=_summarize(periods))
    data = gemini_client.generate_json(prompt, GAP_SCHEMA)
    print(f"[gap 판단] has_gap={data.get('has_gap')} - {data.get('reasoning', '')}")
    return data.get("follow_up_queries", []) or []


def _bucket_for_year(year: int) -> str:
    for start, end in PERIOD_BUCKETS:
        if start <= year <= end:
            return f"{start}-{end}"
    return f"{PERIOD_BUCKETS[0][0]}-{PERIOD_BUCKETS[-1][1]}"


def citation_walk(periods: dict[str, list[Candidate]], max_new_per_paper: int = 3) -> list[Candidate]:
    """LLM 미사용. 이미 찾은 논문들의 인용 그래프를 순회해서 새 후보를 찾는다."""
    existing_titles = {c.title.lower() for cands in periods.values() for c in cands}
    new_candidates: list[Candidate] = []

    for cands in periods.values():
        for c in cands[:2]:  # 구간별 상위 2개만 - 호출 수를 억제
            found_here = []
            if c.s2_paper_id:
                try:
                    forward = semantic_scholar.get_citations(c.s2_paper_id, limit=max_new_per_paper)
                    found_here.extend(forward)
                except Exception as e:
                    print(f"[경고] citation_walk(S2 forward) 실패: {e}")
            if c.openalex_id:
                try:
                    backward = openalex.get_work(c.openalex_id)
                    if backward:
                        for ref_id in backward.referenced_works[:max_new_per_paper]:
                            w = openalex.get_work(ref_id)
                            if w:
                                found_here.append(w)
                except Exception as e:
                    print(f"[경고] citation_walk(OpenAlex backward) 실패: {e}")

            for p in found_here:
                if p.title and p.title.lower() not in existing_titles:
                    existing_titles.add(p.title.lower())
                    new_candidates.append(Candidate(
                        title=p.title, year=getattr(p, "year", 0), authors=getattr(p, "authors", []),
                        arxiv_id=getattr(p, "arxiv_id", None), doi=getattr(p, "doi", None),
                        openalex_id=getattr(p, "openalex_id", None),
                        s2_paper_id=getattr(p, "paper_id", None),
                        citation_count=getattr(p, "citation_count", 0) or 0,
                        abstract=getattr(p, "abstract", ""), pdf_url=getattr(p, "pdf_url", None),
                    ))
    return new_candidates


def deep_collect(keyword: str, max_iterations: int = 2, top_n_per_period: int = 6) -> dict[str, list[Candidate]]:
    periods = collector.collect(keyword, top_n_per_period=top_n_per_period)

    for it in range(max_iterations):
        print(f"\n--- 리서치 루프 iteration {it + 1}/{max_iterations} ---")

        # (a) LLM: 갭 판단 -> 후속 쿼리
        follow_ups = judge_gaps(keyword, periods)
        for q in follow_ups:
            latest_start = PERIOD_BUCKETS[-1][0]
            extra = collector.collect_period(q, latest_start, PERIOD_BUCKETS[-1][1], top_n=3)
            label = f"{latest_start}-{PERIOD_BUCKETS[-1][1]}"
            periods.setdefault(label, [])
            periods[label] = collector._merge(periods[label] + extra)

        # (b) 그래프 순회: citation walk (LLM 미사용)
        new_from_citations = citation_walk(periods)
        for c in new_from_citations:
            label = _bucket_for_year(c.year)
            periods.setdefault(label, [])
            periods[label].append(c)
            print(f"[citation walk] 새 후보 발견: ({c.year}) {c.title}")

        if not follow_ups and not new_from_citations:
            print("더 이상 갭이 없다고 판단, 루프 종료")
            break

    for label in periods:
        periods[label].sort(key=lambda c: c.citation_count, reverse=True)
    return periods


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "roofline model"
    result = deep_collect(kw, max_iterations=1)
    for period, cands in result.items():
        print(f"\n=== {period} ===")
        for c in cands:
            print(f"  [{c.citation_count:>5}] {c.title} ({c.year})")
