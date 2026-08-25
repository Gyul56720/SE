"""
개념/공식집 생성기 (theory_generator.py의 "고급 추론용" 버전).

차이점이 핵심이다:
  theory_generator.py -- 편입수학처럼 이미 완전히 정립된 저학년 개념은 grounding 없이
                          Gemini 지식만으로 생성해도 사실관계 위험이 낮다.
  book_generator.py   -- 반도체 설계/검증(CDC, FIFO, 시스톨릭 어레이 등)처럼 실무 디테일이
                          중요한 고급 주제는 "지어낸 설명"의 위험이 커서, 반드시 두 종류의
                          실존 자료로 grounding한 뒤에만 Gemini가 종합하게 한다:
                            1. concept_sites.py(Wikipedia) -- 정의/이론 산문
                            2. github_source.py            -- 실제 동작하는 오픈소스 구현체 목록
                          math_extractor.py가 "논문 원문에서만 뽑고 지어내지 않는다"는
                          원칙을 편 것과 같은 원칙을, 여기서는 "출처 2종 밖의 내용을 지어내지
                          않는다"로 적용한다.

  python book_generator.py --test "Clock domain crossing" --domain 01_디지털설계검증
  python book_generator.py --topic "FIFO design and verification" --domain 01_디지털설계검증 --index 2
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path

import gemini_client
from sources import concept_sites, github_source

BOOK_ROOT = Path("paper_result/book")

PERSONA = """당신은 반도체 설계/검증(Design Verification) 분야의 시니어 엔지니어이자,
후배 엔지니어를 위한 개념/공식집을 쓰는 저자입니다. 실무에서 바로 쓸 수 있는 정확한 개념
설명과, 실제 오픈소스에서 이 개념이 어떻게 구현되는지를 함께 정리합니다.

절대 원칙: 아래 "근거 자료" 두 종류(Wikipedia 발췌, 실존 GitHub 리포지토리 목록) 밖의
사실을 지어내지 않습니다. 근거 자료에 없는 수치/API/리포지토리 이름을 만들어내지 말고,
부족하면 "근거 자료에 명시되지 않음"이라고 밝히십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "motivation": {"type": "STRING", "description": "이 개념을 왜 알아야 하는지, 실무에서 왜 중요한지 (2-4문장)"},
        "definition_and_theory": {
            "type": "STRING",
            "description": "Wikipedia 발췌를 근거로 한 핵심 정의/이론 설명 (마크다운, 필요시 LaTeX). "
                            "발췌에 없는 내용을 추가하지 말 것.",
        },
        "key_formulas": {
            "type": "ARRAY",
            "description": "이 개념과 관련된 핵심 공식/조건식 (근거 자료에 등장하거나, 업계 표준으로 "
                            "명확히 알려진 것만). 없으면 빈 배열.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "latex": {"type": "STRING"},
                    "meaning": {"type": "STRING"},
                },
                "required": ["name", "latex", "meaning"],
            },
        },
        "real_world_practice": {
            "type": "STRING",
            "description": "제공된 GitHub 리포지토리 목록을 근거로, 이 개념이 실제 오픈소스에서 "
                            "어떻게 구현/검증되는지 설명. 목록에 없는 리포지토리를 언급하지 말 것. "
                            "각 리포를 언급할 때 리포 이름을 정확히 그대로 쓸 것.",
        },
        "common_pitfalls": {"type": "STRING", "description": "실무에서 이 개념을 다룰 때 흔히 하는 실수/함정"},
        "reasoning_example": {
            "type": "STRING",
            "description": "이 개념을 적용해서 문제를 해결하는 논리적 추론 과정 예시 1개 (단계별, 왜 그렇게 "
                            "판단하는지 인과관계 명시). 특정 회사의 비공개 정보를 지어내지 말 것.",
        },
        "connections": {"type": "STRING", "description": "이 개념과 연결되는 다른 개념/다음 학습 방향 (1-3문장)"},
    },
    "required": ["motivation", "definition_and_theory", "key_formulas",
                 "real_world_practice", "common_pitfalls", "reasoning_example", "connections"],
}

PROMPT_TMPL = PERSONA + """

주제: "{topic}"

--- 근거 자료 1: Wikipedia 발췌 ---
{wiki_text}

--- 근거 자료 2: 실존 GitHub 리포지토리 목록 (이름/설명/언어/스타 수) ---
{repo_list}

위 두 근거 자료만 바탕으로, 지정된 JSON 스키마에 맞춰 개념/공식집 챕터 하나를 작성하라.
반드시 한국어로, 수식은 LaTeX로 작성하라.
"""

_TEMPLATE = """---
title: "{title}"
domain: {domain}
tags: [book, concept, {domain}]
source_wikipedia: "{wiki_url}"
referenced_repos: {repo_names}
---

# {index:02d}. {title}

## 1. 왜 알아야 하는가

{motivation}

## 2. 정의와 이론

{definition_and_theory}

## 3. 핵심 공식

{formulas_block}

## 4. 실제 오픈소스에서의 구현/검증

{real_world_practice}

### 참고 리포지토리
{repo_block}

## 5. 실무에서 흔한 함정

{common_pitfalls}

## 6. 추론 예시

{reasoning_example}

## 7. 다음 개념과의 연결

{connections}
"""


def _formulas_block(formulas: list[dict]) -> str:
    if not formulas:
        return "- (근거 자료에 명시된 공식 없음)"
    return "\n\n".join(
        f"### {f.get('name','')}\n$$ {f.get('latex','')} $$\n\n- 의미: {f.get('meaning','')}"
        for f in formulas
    )


def _repo_block(repos: list) -> str:
    if not repos:
        return "- (검색된 참고 리포지토리 없음)"
    return "\n".join(f"- [{r.full_name}]({r.url}) ({r.language or '?'}, ⭐{r.stars}) -- {r.description}" for r in repos)


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\s가-힣-]", "", title).strip()
    return re.sub(r"\s+", " ", slug)


def generate_chapter(topic: str, domain: str, index: int, repo_query: str | None = None,
                      repo_limit: int = 6) -> Path:
    print(f"[근거 수집] Wikipedia: '{topic}'")
    concept = concept_sites.fetch_concept(topic)
    wiki_text = concept.extract if concept else "(Wikipedia에서 문서를 찾지 못함 -- 근거 자료 1 없음)"
    wiki_url = concept.url if concept else ""

    print(f"[근거 수집] GitHub repos: '{repo_query or topic}'")
    repos = github_source.search_repos(repo_query or topic, limit=repo_limit)
    repo_list_text = "\n".join(
        f"- {r.full_name} ({r.language or '?'}, ⭐{r.stars}): {r.description}" for r in repos
    ) or "(검색된 리포지토리 없음)"

    prompt = PROMPT_TMPL.format(topic=topic, wiki_text=wiki_text[:6000], repo_list=repo_list_text)
    print("[Gemini 호출] 챕터 종합 중...")
    data = gemini_client.generate_json(prompt, SCHEMA)

    content = _TEMPLATE.format(
        title=topic, domain=domain, index=index,
        wiki_url=wiki_url, repo_names=[r.full_name for r in repos],
        motivation=data["motivation"],
        definition_and_theory=data["definition_and_theory"],
        formulas_block=_formulas_block(data["key_formulas"]),
        real_world_practice=data["real_world_practice"],
        repo_block=_repo_block(repos),
        common_pitfalls=data["common_pitfalls"],
        reasoning_example=data["reasoning_example"],
        connections=data["connections"],
    )
    out_dir = BOOK_ROOT / domain
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{index:02d}_{_slug(topic)}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[저장] {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="근거 기반(Wikipedia + GitHub) 개념/공식집 생성기")
    parser.add_argument("--topic", help="개념 주제 (Wikipedia 문서 제목과 최대한 일치시킬 것)")
    parser.add_argument("--test", metavar="TOPIC", help="주제 1개 테스트 (--topic과 동일하게 동작)")
    parser.add_argument("--domain", default="01_디지털설계검증", help="저장 폴더명")
    parser.add_argument("--index", type=int, default=1, help="챕터 번호")
    parser.add_argument("--repo-query", default=None, help="GitHub 검색어 (생략 시 topic 그대로 씀)")
    args = parser.parse_args()

    topic = args.test or args.topic
    if not topic:
        parser.print_help()
    else:
        generate_chapter(topic, args.domain, args.index, repo_query=args.repo_query)
