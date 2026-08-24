"""
6. 수학 개념 추출 Agent (transfer_math_chatbot 연동)

analyzer.py가 "이 논문이 뭘 주장하는지"를 요약한다면, 이 모듈은 그 논문 안에 있는
"수학 논리/공식 자체"를 뽑아서 transfer_math_chatbot과 같은 페르소나(편입수학 전문 튜터가
단계별로 풀어 설명)로 재해설한다. 추가로 각 공식/개념과 "근접한" -- 같이 공부하면
접근하기 좋은 -- 다른 수학 공식/논리를 제안한다.

파이프라인 위치: deep_review.py처럼 배치 파이프라인(main.py)과는 별개로 논문 한 편을
지정해서 돌린다. Survey Notes에서 논문을 "뽑아서" 원문 PDF를 가져오는 부분은
deep_review.py의 resolve_paper/fetch_pdf_text/load_local_pdf_text를 그대로 재사용한다
(같은 로직을 두 번 짜지 않기 위함).

transfer_math_chatbot과의 실질적 연동 지점 두 가지:
  1. 페르소나 이식: transfer_math_chatbot/main.py의 시스템 지시문("편입 수학 전문 튜터,
     단계별 논리 추론, LaTeX 사용")을 MATH_PERSONA로 그대로 가져와서 논문 수식 해설에도 적용.
  2. 이미지 인식 이식: transfer_math_chatbot이 photos/ 폴더의 사진에서 수식을 읽어내던
     기능을 gemini_client의 멀티모달 경로(REST inlineData)로 재구현 -- 논문 캡처본/손글씨
     메모 이미지를 그대로 질의할 수 있다 (extract_math_from_image).
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

import gemini_client
from config import note_folder, OBSIDIAN_VAULT_PATH

MAX_CHARS = 300_000  # deep_review.py와 같은 안전 상한 취지 (원문 전체가 이 안에 들어오는 경우가 대부분)

# transfer_math_chatbot/main.py의 system_instruction을 그대로 이식한 페르소나.
# "편입 수학 전문 튜터"에서 "논문 속 수학 해설"로 적용 범위만 넓혔다.
MATH_PERSONA = """당신은 편입 수학 전문 튜터이자, 논문에 등장하는 수학적 논리/공식을
단계별로 풀어 설명하는 전문가입니다. 수식의 유도 과정과 의미를 논리적으로 추론하여
단계별로 설명하십시오. 수식은 반드시 LaTeX 문법을 사용해서 명확히 기술하십시오."""

MATH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "formulas": {
            "type": "ARRAY",
            "description": "논문에 실제로 등장하는 핵심 수학 공식 3~8개. 원문에 없는 공식을 지어내지 말 것.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "공식 이름 또는 식 번호 (예: 'Operational Intensity (식 2)')"},
                    "latex": {"type": "STRING", "description": "LaTeX 표기"},
                    "meaning": {"type": "STRING", "description": "이 공식이 수학적으로 무엇을 의미하는지"},
                    "context": {"type": "STRING", "description": "논문에서 이 공식이 왜 등장했는지, 어디에 쓰였는지"},
                },
                "required": ["name", "latex", "meaning", "context"],
            },
        },
        "key_concepts": {
            "type": "ARRAY",
            "description": "이 논문의 수학을 이해하는 데 필요한 핵심 개념/논리",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "explanation": {"type": "STRING", "description": "편입수학 튜터가 학생에게 설명하듯 쉽게, 그러나 정확하게"},
                    "prerequisites": {"type": "STRING", "description": "이걸 이해하려면 먼저 알아야 하는 선행 개념. 없으면 빈 문자열"},
                },
                "required": ["name", "explanation", "prerequisites"],
            },
        },
        "usage_methodology": {
            "type": "STRING",
            "description": "이 논문의 수학/공식을 실제 문제에 적용하는 절차를 단계별로 (1. ... 2. ... 형식)",
        },
        "adjacent_concepts": {
            "type": "ARRAY",
            "description": "이 논문의 수학과 근접해서, 함께 파고들면(approach) 좋은 다른 수학 공식/논리 4~6개. "
                            "같은 분야일 필요는 없음 -- 구조적으로 닮은 다른 분야 개념도 포함할 것.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "relation_type": {"type": "STRING", "description": "예: 일반화/특수화/유사 방법론/대체 접근/응용 분야 확장"},
                    "why_relevant": {"type": "STRING", "description": "이 논문의 어느 공식/개념과 어떻게 연결되는지"},
                    "explore_next": {"type": "STRING", "description": "실제로 파고들 때 참고할 구체적 방향 (관련 정리 이름, 표준 교재 챕터, 응용 예 등)"},
                },
                "required": ["name", "relation_type", "why_relevant", "explore_next"],
            },
        },
    },
    "required": ["formulas", "key_concepts", "usage_methodology", "adjacent_concepts"],
}

_EXTRACT_PROMPT = MATH_PERSONA + """

아래는 논문 "{title}"의 원문(또는 원문 일부)입니다. 이 논문에 등장하는 수학 논리/공식을
분석해서 지정된 JSON 스키마로만 답하십시오. 반드시 한국어로 작성하되 수식은 LaTeX로 쓰십시오.

--- 논문 원문 시작 ---
{paper_text}
--- 논문 원문 끝 ---
"""


@dataclass
class MathExtraction:
    title: str
    formulas: list[dict] = field(default_factory=list)
    key_concepts: list[dict] = field(default_factory=list)
    usage_methodology: str = ""
    adjacent_concepts: list[dict] = field(default_factory=list)


def extract_math(paper_text: str, title: str) -> MathExtraction:
    """논문 원문 텍스트에서 수학 논리/공식 + 개념 설명 + 사용 방법론 + 근접 개념을 뽑는다."""
    text = paper_text
    if len(text) > MAX_CHARS:
        print(f"[경고] 원문이 {len(text)}자라 {MAX_CHARS}자로 잘라서 전달함.")
        text = text[:MAX_CHARS]
    prompt = _EXTRACT_PROMPT.format(title=title, paper_text=text)
    data = gemini_client.generate_json(prompt, MATH_SCHEMA)
    return MathExtraction(
        title=title,
        formulas=data.get("formulas", []),
        key_concepts=data.get("key_concepts", []),
        usage_methodology=data.get("usage_methodology", ""),
        adjacent_concepts=data.get("adjacent_concepts", []),
    )


def extract_math_from_image(image_paths: list[Path], question: str | None = None) -> str:
    """transfer_math_chatbot의 사진 속 수식 인식 기능을 그대로 이식한 자유 응답 경로.
    논문을 캡처한 이미지나 손글씨 메모를 그대로 질의할 때 쓴다."""
    prompt = question or "이 이미지에 있는 수식/문제를 인식해서, 논리적으로 단계별로 풀이하고 의미를 설명해줘."
    return gemini_client.generate(MATH_PERSONA + "\n\n" + prompt, images=image_paths)


def _slugify(title: str, year: int | None) -> str:
    slug = re.sub(r"[^\w\s-]", "", title).strip()
    slug = re.sub(r"[\s]+", " ", slug)[:80]
    return f"{slug} ({year})" if year else slug


def _concept_slug(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[\s]+", " ", slug)[:80]


_TEMPLATE = """---
title: "[Math] {title}"
source_paper: "[[{paper_slug}]]"
tags: [math-concept, paper-pipeline]
---

# {title} -- 수학 논리/공식 정리

> 원 논문: [[{paper_slug}]]

## 핵심 공식
{formulas_block}

## 핵심 개념 설명
{concepts_block}

## 사용 방법론
{usage_methodology}

## 근접 개념 -- 같이 접근하면 좋은 다른 수학
{adjacent_block}
"""


def _format_formulas(formulas: list[dict]) -> str:
    if not formulas:
        return "- (추출된 공식 없음)"
    parts = []
    for f in formulas:
        parts.append(
            f"### {f.get('name', '(이름 없음)')}\n"
            f"$$ {f.get('latex', '')} $$\n\n"
            f"- 의미: {f.get('meaning', '')}\n"
            f"- 등장 맥락: {f.get('context', '')}"
        )
    return "\n\n".join(parts)


def _format_concepts(concepts: list[dict]) -> str:
    if not concepts:
        return "- (추출된 개념 없음)"
    parts = []
    for c in concepts:
        prereq = f"\n  - 선행 개념: {c['prerequisites']}" if c.get("prerequisites") else ""
        parts.append(f"- **{c.get('name', '')}**: {c.get('explanation', '')}{prereq}")
    return "\n".join(parts)


def _format_adjacent(adjacent: list[dict], concept_slug_index: dict[str, str]) -> str:
    if not adjacent:
        return "- (근접 개념 없음)"
    parts = []
    for a in adjacent:
        name = a.get("name", "")
        link = f" [[{concept_slug_index[name]}]]" if name in concept_slug_index else ""
        parts.append(
            f"- **{name}**{link} ({a.get('relation_type', '')})\n"
            f"  - 연관 이유: {a.get('why_relevant', '')}\n"
            f"  - 파고들 방향: {a.get('explore_next', '')}"
        )
    return "\n".join(parts)


def write_math_note(extraction: MathExtraction, paper_title: str, paper_year: int | None,
                     domain: str | None = None, topic: str | None = None,
                     vault_path: Path | None = None,
                     concept_slug_index: dict[str, str] | None = None) -> Path:
    """Math Concepts 폴더에 노트를 쓴다. 원 논문 Survey Note로 source_paper 위키링크를 걸고,
    같은 배치에서 이미 처리된 다른 수학 개념 노트가 있으면 근접 개념도 서로 위키링크로 잇는다."""
    if vault_path is None:
        vault_path = note_folder(topic, domain, "Math Concepts") if topic else OBSIDIAN_VAULT_PATH.parent / "Math Concepts"
    vault_path.mkdir(parents=True, exist_ok=True)

    paper_slug = _slugify(paper_title, paper_year)
    concept_slug_index = concept_slug_index or {}

    content = _TEMPLATE.format(
        title=extraction.title.replace('"', "'"),
        paper_slug=paper_slug,
        formulas_block=_format_formulas(extraction.formulas),
        concepts_block=_format_concepts(extraction.key_concepts),
        usage_methodology=extraction.usage_methodology or "(방법론 정보 없음)",
        adjacent_block=_format_adjacent(extraction.adjacent_concepts, concept_slug_index),
    )

    out_path = vault_path / f"[Math] {_concept_slug(extraction.title)}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[수학 정리] {out_path.name}  <- source_paper: {paper_slug}")
    return out_path


def load_existing_concept_index(vault_path: Path) -> dict[str, str]:
    """이미 vault에 쓰인 Math Concept 노트들의 (개념 이름 -> 파일 stem) 매핑.
    adjacent_concepts에서 이름이 겹치면 자동으로 위키링크를 걸어서, 여러 논문에 걸쳐
    Obsidian 그래프뷰에 수학 개념 그래프가 누적되게 한다 (organizer.py의 predecessor
    누적 그래프와 같은 취지)."""
    index: dict[str, str] = {}
    if not vault_path.exists():
        return index
    for f in vault_path.iterdir():
        if not (f.name.startswith("[Math] ") and f.suffix == ".md"):
            continue
        text = f.read_text(encoding="utf-8")
        m = re.search(r'^title:\s*"\[Math\]\s*(.+?)"\s*$', text, re.MULTILINE)
        if m:
            index[m.group(1)] = f.stem
    return index


if __name__ == "__main__":
    import deep_review

    paper = deep_review.resolve_paper("roofline model", None, None, OBSIDIAN_VAULT_PATH)
    text = deep_review.fetch_pdf_text(paper.pdf_url)
    result = extract_math(text, paper.title)
    print(f"\n공식 {len(result.formulas)}개, 근접 개념 {len(result.adjacent_concepts)}개 추출됨")
    write_math_note(result, paper.title, paper.year)
