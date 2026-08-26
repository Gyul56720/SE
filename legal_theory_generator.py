"""
법 이론서 생성기 -- RULE.md 1단계(법적 근거 수집·이론) 구현.

theory_generator.py(편입수학, grounding 없이 순수 생성)와 다르다: 법 조문은 실무에서 정확도가
생명이라, korean_law.py로 가져온 **실제 조문 원문**을 grounding으로 강제하고 그 밖의 조문
번호/내용을 지어내지 못하게 한다 (book_generator.py와 같은 원칙).

  python legal_theory_generator.py --domain 01_민법총칙_법인편 --topic-index 1
  python legal_theory_generator.py --domain 01_민법총칙_법인편 --all
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path

import gemini_client
from sources import korean_law

BOOK_ROOT = Path("법이론서")

PERSONA = """당신은 대한민국 법학 이론서를 쓰는 실무 경력 있는 법학자입니다. 아래 제공되는
"조문 원문" 밖의 조문 번호나 내용을 지어내지 않습니다. 조문 원문에 없는 내용이 필요하면
"조문 원문에 명시되지 않음, 학설/판례 확인 필요"라고 밝히십시오. 실제 특정 판례를 인용할
때는 사건번호를 모르면 지어내지 말고 "관련 판례 확인 필요"라고 쓰십시오. case_application은
학습용으로 새로 창작한 가상의 사실관계이며 실제 판례가 아님을 명시하십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "motivation": {"type": "STRING", "description": "이 주제를 왜 알아야 하는지 (2-4문장)"},
        "provisions_and_theory": {
            "type": "STRING",
            "description": "제공된 조문 원문을 근거로 한 핵심 이론 설명(마크다운). 조문 번호를 "
                            "인용할 때 반드시 제공된 원문의 번호 그대로 쓸 것.",
        },
        "key_principle": {"type": "STRING", "description": "이 주제의 핵심 법리를 한 문장으로"},
        "key_principle_explanation": {"type": "STRING", "description": "왜 이 법리가 핵심인지, 어떤 조문에서 도출되는지"},
        "interpretation_techniques": {
            "type": "ARRAY", "description": "실무 해석기법 3-6개",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"}, "method": {"type": "STRING"}, "reasoning": {"type": "STRING"},
                },
                "required": ["name", "method", "reasoning"],
            },
        },
        "common_mistakes": {"type": "STRING", "description": "실무에서 흔히 하는 오해/놓치는 예외"},
        "case_applications": {
            "type": "ARRAY", "description": "학습용으로 새로 창작한 가상 사실관계 적용 예시 정확히 2개 (실제 판례 아님)",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "facts": {"type": "STRING"}, "analysis": {"type": "STRING"}, "conclusion": {"type": "STRING"},
                },
                "required": ["facts", "analysis", "conclusion"],
            },
        },
        "practice_scenarios": {
            "type": "ARRAY", "description": "스스로 검토해볼 가상 사실관계 3개(힌트만)",
            "items": {"type": "OBJECT", "properties": {"scenario": {"type": "STRING"}, "hint": {"type": "STRING"}},
                      "required": ["scenario", "hint"]},
        },
        "next_topic_connection": {"type": "STRING"},
    },
    "required": ["motivation", "provisions_and_theory", "key_principle", "key_principle_explanation",
                 "interpretation_techniques", "common_mistakes", "case_applications",
                 "practice_scenarios", "next_topic_connection"],
}

PROMPT_TMPL = PERSONA + """

법 도메인: {domain}
주제: "{topic}"
직전 주제(참고용): {prev_topic}

--- 조문 원문 (이 안의 내용만 근거로 쓸 것) ---
{provisions}
--- 조문 원문 끝 ---

위 조문 원문을 근거로 이 주제의 이론서 챕터를 지정된 JSON 스키마로 작성하라. 반드시 한국어로.
"""

_TEMPLATE = """---
title: "{title}"
domain: {domain}
tags: [법이론서, {domain}]
key_principle: "{key_principle_fm}"
source_statute: "{statute}"
---

# {index:02d}. {title}

## 1. 왜 알아야 하는가

{motivation}

## 2. 조문과 이론

{provisions_and_theory}

## 3. 핵심 법리

> {key_principle}

{key_principle_explanation}

## 4. 해석기법

{techniques_block}

## 5. 실무상 흔한 오해

{common_mistakes}

## 6. 사례 적용 (학습용 창작 사례, 실제 판례 아님)

{cases_block}

## 7. 연습 사실관계

{practice_block}

## 8. 다음 주제와의 연결

{next_topic_connection}
"""


def _techniques_block(items: list[dict]) -> str:
    return "\n\n".join(
        f"### {t.get('name','')}\n{t.get('method','')}\n\n**왜 이 방법이 통하는가:** {t.get('reasoning','')}"
        for t in items
    )


def _cases_block(items: list[dict]) -> str:
    parts = []
    for i, c in enumerate(items, 1):
        parts.append(f"### 사례 {i}\n**사실관계:** {c.get('facts','')}\n\n**검토:** {c.get('analysis','')}\n\n**결론:** {c.get('conclusion','')}")
    return "\n\n".join(parts)


def _practice_block(items: list[dict]) -> str:
    return "\n".join(f"{i}. {p.get('scenario','')} *(힌트: {p.get('hint','')})*" for i, p in enumerate(items, 1))


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\s가-힣-]", "", title).strip()
    return re.sub(r"\s+", " ", slug)


def generate_topic(domain: str, index: int, topic: str, statute_name: str, keywords: list[str],
                    prev_topic: str | None) -> Path:
    print(f"  [조문 수집] {statute_name} -- {keywords}")
    articles = korean_law.get_articles_by_keyword(statute_name, keywords)
    if not articles:
        print(f"  [경고] 조문을 못 찾음 -- grounding 없이 진행 위험, 건너뜀")
        return None
    provisions = korean_law.format_articles(articles[:15])

    print(f"  [Gemini 호출] {domain} #{index} {topic}")
    prompt = PROMPT_TMPL.format(domain=domain, topic=topic, prev_topic=prev_topic or "(첫 주제)",
                                 provisions=provisions)
    data = gemini_client.generate_json(prompt, SCHEMA)

    content = _TEMPLATE.format(
        title=topic, domain=domain, index=index,
        key_principle_fm=data["key_principle"].replace('"', "'"), statute=statute_name,
        motivation=data["motivation"], provisions_and_theory=data["provisions_and_theory"],
        key_principle=data["key_principle"], key_principle_explanation=data["key_principle_explanation"],
        techniques_block=_techniques_block(data["interpretation_techniques"]),
        common_mistakes=data["common_mistakes"],
        cases_block=_cases_block(data["case_applications"]),
        practice_block=_practice_block(data["practice_scenarios"]),
        next_topic_connection=data["next_topic_connection"],
    )
    out_dir = BOOK_ROOT / domain / "이론"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{index:02d}_{_slug(topic)}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  [저장] {out_path}")
    return out_path


# --- Tier 0 토픽 목록: (index, topic, statute_name, keywords) ---

MINBEOB_BEOBIN = [
    (1, "법인의 종류(사단/재단, 영리/비영리)", "민법", ["사단법인", "재단법인", "비영리법인"]),
    (2, "법인의 해산 사유", "민법", ["법인의 해산", "해산사유"]),
    (3, "청산법인의 능력(청산 목적 범위 내로 제한)", "민법", ["청산법인", "목적범위"]),
    (4, "청산인의 지위와 권한", "민법", ["청산인"]),
    (5, "잔여재산의 귀속", "민법", ["잔여재산"]),
    (6, "청산 종결과 등기", "민법", ["청산종결", "청산인의 등기"]),
]

MINBEOB_JOHAP = [
    (1, "조합계약의 법적 성질", "민법", ["조합계약", "조합의 성립"]),
    (2, "조합원의 권리의무", "민법", ["조합원", "출자"]),
    (3, "조합의 해산과 청산", "민법", ["조합의 해산", "조합의 청산"]),
    (4, "업무집행조합원의 책임", "민법", ["업무집행자", "업무집행조합원"]),
]

DOSI_JEONGBI = [
    (1, "정비사업조합의 법적 지위", "도시 및 주거환경정비법", ["조합설립인가", "법인으로 본다"]),
    (2, "조합 해산 및 청산 특별규정", "도시 및 주거환경정비법", ["해산", "청산"]),
    (3, "청산인 선임 및 직무", "도시 및 주거환경정비법", ["청산인"]),
    (4, "조합원 감독권(정보공개청구권 등)", "도시 및 주거환경정비법", ["정보공개", "서류의 공개"]),
]

HYEONGBEOB_JAESAN = [
    (1, "배임죄", "형법", ["배임"]),
    (2, "횡령죄", "형법", ["횡령"]),
    (3, "공범 구조(공동정범)", "형법", ["공동정범"]),
]

DOMAINS = {
    "01_민법총칙_법인편": MINBEOB_BEOBIN,
    "02_채권법각론_조합": MINBEOB_JOHAP,
    "03_도시정비법": DOSI_JEONGBI,
    "04_형법각론_재산범죄": HYEONGBEOB_JAESAN,
}


def run_domain(domain: str):
    topics = DOMAINS[domain]
    prev = None
    for index, topic, statute, keywords in topics:
        try:
            generate_topic(domain, index, topic, statute, keywords, prev)
        except Exception as e:
            print(f"  [실패] {topic}: {e}")
        prev = topic


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="법 이론서 생성기 (조문 grounding)")
    parser.add_argument("--domain", choices=list(DOMAINS.keys()))
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all:
        for d in DOMAINS:
            run_domain(d)
    elif args.domain:
        run_domain(args.domain)
    else:
        parser.print_help()
