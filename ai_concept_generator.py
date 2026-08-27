"""
프롬프트/LLM 정보처리, 자가학습, 자가코드수정, 해킹 개념서 생성기.
theory_generator.py의 8단 문법(동기->정의/이론->핵심 사실(killing fact)->기법->흔한 오해->
대표예제->유제->다음 연결)을 그대로 따른다. 이 네 주제는 편입수학처럼 정립된 CS/보안 상식
수준이라 furiosa_theory_generator.py 같은 WebFetch grounding 없이 Gemini 지식만으로 생성해도
사실관계 위험이 낮다 -- 단, "해킹" 챕터는 반드시 방어/개념 설명 수준으로만 작성하고 실제 동작하는
공격 코드나 특정 시스템 대상 실전 침투 절차는 쓰지 않도록 페르소나에 명시한다.

  python ai_concept_generator.py
"""

from __future__ import annotations
import re
from pathlib import Path

import gemini_client

VAULT_ROOT = Path("/Users/cogito/Documents/Obsidian Vault")
BOOK_ROOT = (VAULT_ROOT / "ai_concept") if VAULT_ROOT.exists() else Path(__file__).parent / "ai_concept"

PERSONA = """당신은 LLM 시스템/프롬프트 엔지니어링과 정보보안을 함께 다루는 시니어 엔지니어이자,
후배 엔지니어를 위한 개념서를 쓰는 저자입니다. 처음 배우는 사람도 이해할 수 있도록 쉽고
꼼꼼하게, 그러나 사실관계에 오류나 과장이 없도록 설명합니다. 모든 논리는 "~하기 때문에
~하다"처럼 인과관계를 명확히 밝힙니다.

절대 원칙:
1. 수치나 논문 이름, 벤치마크 결과를 지어내지 않습니다. 정확히 기억나지 않으면 "정확한 수치는
   출처마다 다름"이라고 밝히고 일반적으로 알려진 경향만 설명합니다.
2. "해킹" 관련 챕터는 반드시 방어적/교육적 개념 설명(공격의 원리, 왜 취약한지, 어떻게
   방어하는지)까지만 다룹니다. 특정 실제 서비스/회사를 대상으로 한 공격 절차, 그대로 실행 가능한
   익스플로잇 코드, 악성코드, 실전 침투 스텝바이스텝 가이드는 작성하지 않습니다 -- 개념과
   원리, 대응 방안 중심으로 서술합니다.
3. "자가 코드 수정"/"재귀적 자기개선" 챕터는 실제 존재하는 연구/도구(예: AutoGPT류 에이전트
   루프, 유전 프로그래밍, self-refine 논문들)의 일반적으로 알려진 개념을 설명하되, 실제
   작동하는 자기복제/자기수정 악성코드를 만드는 방법은 다루지 않습니다."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "motivation": {"type": "STRING", "description": "이 개념을 왜 알아야 하는지, 실무/면접에서 왜 중요한지 (2-4문장, 인과관계 명확히)"},
        "definitions_and_theory": {
            "type": "STRING",
            "description": "핵심 정의/구조/동작 원리 설명 (마크다운, 필요시 LaTeX). ### 소제목으로 구분 가능.",
        },
        "killing_fact_latex": {
            "type": "STRING",
            "description": "이 토픽의 핵심을 나타내는 단 하나의 수식/규칙/체크리스트 한 줄(LaTeX 또는 \\text{} 형태). "
                            "수식이 부자연스러운 주제면 가장 핵심적인 원칙 한 문장을 \\text{}로 넣을 것.",
        },
        "killing_fact_explanation": {"type": "STRING", "description": "이 핵심 사실이 왜 이 토픽의 핵심인지 설명"},
        "techniques": {
            "type": "ARRAY",
            "description": "이 토픽의 핵심 기법/메커니즘 3-6개",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "method": {"type": "STRING", "description": "구체적으로 어떻게 동작/적용하는지"},
                    "reasoning": {"type": "STRING", "description": "왜 이렇게 설계/동작하는지 인과적 설명"},
                },
                "required": ["name", "method", "reasoning"],
            },
        },
        "common_mistakes": {
            "type": "STRING",
            "description": "이 토픽을 처음 접할 때 흔히 오해하거나 놓치는 부분, 실무에서 흔한 실수를 빠짐없이 짚어줄 것.",
        },
        "worked_examples": {
            "type": "ARRAY",
            "description": "이 개념을 적용해 실무/면접 상황을 추론하는 대표예제 정확히 2개. 새로 창작.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "problem": {"type": "STRING"},
                    "solution_steps": {"type": "STRING", "description": "'1단계 — ...' 형식, 왜 그런지 논리 포함"},
                    "answer": {"type": "STRING"},
                },
                "required": ["problem", "solution_steps", "answer"],
            },
        },
        "practice_problems": {
            "type": "ARRAY",
            "description": "스스로 생각해볼 유제(면접 예상 질문 형태) 정확히 3개, 풀이 없이 문제+짧은 힌트만.",
            "items": {
                "type": "OBJECT",
                "properties": {"problem": {"type": "STRING"}, "hint": {"type": "STRING"}},
                "required": ["problem", "hint"],
            },
        },
        "next_topic_connection": {"type": "STRING", "description": "이 챕터가 다음 챕터와 구체적으로 어떻게 연결되는지 (1-3문장)"},
    },
    "required": [
        "motivation", "definitions_and_theory", "killing_fact_latex", "killing_fact_explanation",
        "techniques", "common_mistakes", "worked_examples", "practice_problems", "next_topic_connection",
    ],
}

PROMPT_TMPL = PERSONA + """

도메인: {domain}
챕터 주제: "{topic}"
직전 챕터(있다면, 자연스럽게 이어지도록 참고만 할 것): {prev_topic}

위 토픽에 대한 개념서 한 챕터 분량을 지정된 JSON 스키마에 맞춰 작성하라.
반드시 한국어로, 필요한 수식은 LaTeX($$...$$ 또는 $...$)로 작성하라.
"""

_TEMPLATE = """---
title: "{title}"
domain: {domain}
tags: [ai_concept, 이론서, {domain}]
killing_fact: "{killing_fact_frontmatter}"
---

# {index:02d}. {title}

## 1. 왜 알아야 하는가

{motivation}

## 2. 정의와 구조

{definitions_and_theory}

## 3. 핵심 사실 (Killing Fact)

$$ \\boxed{{\\ {killing_fact_latex}\\ }} $$

{killing_fact_explanation}

## 4. 핵심 기법

{techniques_block}

## 5. 자주 하는 오해 / 주의할 점

{common_mistakes}

## 6. 대표예제 (추론 연습)

{examples_block}

## 7. 유제 (면접 예상 질문)

{practice_block}

## 8. 다음 챕터와의 연결

{next_topic_connection}
"""


def _techniques_block(techniques: list[dict]) -> str:
    parts = []
    for i, t in enumerate(techniques, 1):
        parts.append(
            f"### 기법 {chr(64+i)}: {t.get('name','')}\n\n"
            f"{t.get('method','')}\n\n"
            f"**왜 이렇게 설계했는가:** {t.get('reasoning','')}"
        )
    return "\n\n".join(parts)


def _examples_block(examples: list[dict]) -> str:
    parts = []
    for i, ex in enumerate(examples, 1):
        parts.append(
            f"### 예제 {i}\n\n{ex.get('problem','')}\n\n"
            f"**풀이:**\n\n{ex.get('solution_steps','')}\n\n"
            f"**답: {ex.get('answer','')}**"
        )
    return "\n\n".join(parts)


def _practice_block(problems: list[dict]) -> str:
    return "\n".join(f"{i}. {p.get('problem','')} *(힌트: {p.get('hint','')})*" for i, p in enumerate(problems, 1))


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\s가-힣-]", "", title).strip()
    return re.sub(r"\s+", " ", slug)


def _strip_dollar_wrapping(latex: str) -> str:
    s = latex.strip()
    while s.startswith("$$") and s.endswith("$$") and len(s) > 4:
        s = s[2:-2].strip()
    while s.startswith("$") and s.endswith("$") and len(s) > 2:
        s = s[1:-1].strip()
    return s


def generate_chapter(domain: str, index: int, topic: str, prev_topic: str | None) -> Path:
    existing = BOOK_ROOT / domain / f"{index:02d}_{_slug(topic)}.md"
    if existing.exists():
        print(f"  [건너뜀] 이미 존재함: {existing}")
        return existing
    prompt = PROMPT_TMPL.format(domain=domain, topic=topic, prev_topic=prev_topic or "(이 도메인의 첫 챕터)")
    print(f"  [Gemini 호출] {domain} #{index} {topic} ...")
    data = gemini_client.generate_json(prompt, SCHEMA)
    killing_fact_latex = _strip_dollar_wrapping(data["killing_fact_latex"])

    content = _TEMPLATE.format(
        title=topic, domain=domain, index=index,
        killing_fact_frontmatter=killing_fact_latex.replace('"', "'"),
        killing_fact_latex=killing_fact_latex,
        killing_fact_explanation=data["killing_fact_explanation"],
        motivation=data["motivation"],
        definitions_and_theory=data["definitions_and_theory"],
        techniques_block=_techniques_block(data["techniques"]),
        common_mistakes=data["common_mistakes"],
        examples_block=_examples_block(data["worked_examples"]),
        practice_block=_practice_block(data["practice_problems"]),
        next_topic_connection=data["next_topic_connection"],
    )
    out_dir = BOOK_ROOT / domain
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{index:02d}_{_slug(topic)}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  [저장] {out_path}")
    return out_path


CHAPTERS = [
    # --- 01. 프롬프트 엔지니어링과 LLM 정보처리 ---
    dict(domain="01_프롬프트엔지니어링", index=1,
         topic="LLM의 정보 처리 방식: 토큰화, 임베딩, 어텐션과 컨텍스트 윈도우"),
    dict(domain="01_프롬프트엔지니어링", index=2,
         topic="Chain-of-Thought와 추론 유도 프롬프트 기법"),
    dict(domain="01_프롬프트엔지니어링", index=3,
         topic="Few-shot과 In-Context Learning: 프롬프트 구조 설계"),
    dict(domain="01_프롬프트엔지니어링", index=4,
         topic="고급 추론을 위한 프롬프트 최적화: Self-Consistency, ReAct, 구조화된 출력"),
    # --- 02. 자가 학습 ---
    dict(domain="02_자가학습", index=1,
         topic="In-Context Learning과 Fine-tuning: 가중치를 바꾸지 않는 학습과 바꾸는 학습"),
    dict(domain="02_자가학습", index=2,
         topic="RLHF와 RLAIF: 인간·AI 피드백 기반 자가 개선 루프"),
    dict(domain="02_자가학습", index=3,
         topic="Self-Refine과 지속 학습(Continual Learning)의 한계: 왜 모델은 스스로 완벽히 개선되지 못하는가"),
    # --- 03. 자가 코드 수정 ---
    dict(domain="03_자가코드수정", index=1,
         topic="자기 수정 코드(Self-Modifying Code)의 개념과 역사"),
    dict(domain="03_자가코드수정", index=2,
         topic="AI 코딩 에이전트의 자기 개선 루프: 자동 디버깅과 리팩터링"),
    dict(domain="03_자가코드수정", index=3,
         topic="재귀적 자기개선(Recursive Self-Improvement): 이론, 안전성, 한계"),
    # --- 04. 해킹 개념 (방어적/교육적 관점) ---
    dict(domain="04_해킹개념", index=1,
         topic="해킹의 분류와 윤리적 해킹(모의침투) 방법론"),
    dict(domain="04_해킹개념", index=2,
         topic="네트워크 공격의 기초: 정찰, 스캐닝, 스니핑/MITM의 원리와 방어"),
    dict(domain="04_해킹개념", index=3,
         topic="웹 애플리케이션 보안: OWASP Top 10 취약점의 원리와 방어"),
    dict(domain="04_해킹개념", index=4,
         topic="프롬프트 인젝션과 AI 시대의 사회공학: 새로운 공격 표면과 방어 전략"),
]


if __name__ == "__main__":
    prev_by_domain: dict[str, str] = {}
    for ch in CHAPTERS:
        try:
            generate_chapter(ch["domain"], ch["index"], ch["topic"], prev_by_domain.get(ch["domain"]))
            prev_by_domain[ch["domain"]] = ch["topic"]
        except Exception as e:
            print(f"  [실패] {ch['domain']} {ch['topic']}: {e}")
