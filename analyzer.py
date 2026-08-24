"""
2. 자료 분석 Agent
선정된 후보 논문마다 Gemini를 1회 호출해서 구조화 추출한다.
가장 중요한 필드는 'upgrades_from' - 이게 있어야 organizer.py가 Obsidian에
predecessor:: 링크를 심어서 "발전 과정"을 그래프로 만들 수 있다.
"""

from __future__ import annotations
from dataclasses import dataclass

from collector import Candidate
import gemini_client

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "core_claim": {"type": "STRING", "description": "이 논문의 핵심 주장/기여 (2-3문장)"},
        "upgrades_from": {"type": "STRING", "description": "이 논문이 구체적으로 어떤 선행 개념/논문의 무엇을 확장하는지. 없으면 빈 문자열"},
        "key_numbers": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "핵심 수치 3-5개, 단위 포함"},
        "limitations": {"type": "STRING", "description": "이 논문/방법의 한계"},
        "one_line_summary": {"type": "STRING", "description": "한 줄 요약 (제목 아래 붙일 부제 느낌)"},
    },
    "required": ["core_claim", "upgrades_from", "key_numbers", "limitations", "one_line_summary"],
}

PROMPT_TMPL = """다음 논문 정보를 분석해서 지정된 JSON 스키마로만 답하라. 반드시 한국어로 작성.

제목: {title}
연도: {year}
초록: {abstract}
{tldr_line}

분석 시 특히 신경 쓸 것:
- upgrades_from: 막연히 "선행 연구를 발전시켰다"가 아니라, 구체적으로 무엇을(예: "operational intensity 정의를 FLOP/byte에서 integer op/weight byte로 바꿈") 바꿨는지 적을 것.
- key_numbers: 초록에 실제로 등장하는 숫자만 쓸 것. 지어내지 말 것.
"""


@dataclass
class Analysis:
    candidate: Candidate
    core_claim: str
    upgrades_from: str
    key_numbers: list[str]
    limitations: str
    one_line_summary: str


def analyze(candidate: Candidate) -> Analysis:
    tldr_line = f"TLDR: {candidate.tldr}" if candidate.tldr else ""
    prompt = PROMPT_TMPL.format(
        title=candidate.title, year=candidate.year,
        abstract=candidate.abstract[:3000] or "(초록 없음 - 제목만으로 추정하지 말고 알 수 없다고 표시할 것)",
        tldr_line=tldr_line,
    )
    data = gemini_client.generate_json(prompt, SCHEMA)
    return Analysis(
        candidate=candidate,
        core_claim=data.get("core_claim", ""),
        upgrades_from=data.get("upgrades_from", ""),
        key_numbers=data.get("key_numbers", []),
        limitations=data.get("limitations", ""),
        one_line_summary=data.get("one_line_summary", ""),
    )


def analyze_all(candidates: list[Candidate]) -> list[Analysis]:
    results = []
    for i, c in enumerate(candidates, 1):
        print(f"[분석 {i}/{len(candidates)}] {c.title[:60]}...")
        try:
            results.append(analyze(c))
        except Exception as e:
            print(f"  실패: {e}")
    return results


if __name__ == "__main__":
    import collector
    cands = collector.collect_period("roofline model", 2009, 2013, top_n=2)
    for a in analyze_all(cands):
        print(f"\n### {a.candidate.title}\n{a.one_line_summary}\nupgrades_from: {a.upgrades_from}")
