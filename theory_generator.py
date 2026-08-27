"""
편입수학 이론서 생성기 (math_extractor.py와 같은 패턴: 프롬프트 + JSON 스키마 강제 + Gemini
무료 호출 하나로 구조화 추출). math_extractor.py가 "이미 존재하는 논문"에서 수학을 뽑는다면,
이건 반대로 "존재하지 않는 새 콘텐츠"를 표준 정리/공식만 갖고 처음부터 작성하게 만든다.

절대 원칙(프롬프트에도 명시): 특정 교재(수학의 정석/RPM 등)나 특정 기출문제를 인용·각색하지
않는다. 표준적으로 알려진 정의/정리/공식(저작권 대상 아님)과, 이 스크립트가 매번 새로
생성시키는 예제 문제만 사용한다.

  python theory_generator.py --test        토픽 1개로 품질 테스트만 (파일 안 씀, 콘솔 출력)
  python theory_generator.py --domain 02_선형대수학 --from 4   지정 과목의 --from번 토픽부터 끝까지 생성
  python theory_generator.py --all         모든 남은 토픽 순서대로 생성
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path

import gemini_client

VAULT_ROOT = Path("/Users/cogito/Documents/Obsidian Vault")
# 로컬 맥(iCloud vault 마운트됨)이 아닌 환경(예: 클라우드 원격 세션)에서 돌리면 vault 경로가
# 존재하지 않으므로, 그럴 때만 저장소 로컬 경로로 폴백한다 (furiosa_theory_generator.py와 동일 원칙).
BOOK_ROOT = (VAULT_ROOT / "편입수학 이론서") if VAULT_ROOT.exists() else Path(__file__).parent / "편입수학 이론서"

PERSONA = """당신은 한국 편입수학 전문 강사이자 수십 년간 미적분학/선형대수학을 가르쳐온
교육자입니다. 처음 배우는 학생도 이해할 수 있도록 쉽고 꼼꼼하게, 그러나 수학적으로 한 치의
오류나 부정확성도 없이 설명합니다. 모든 논리는 "~하기 때문에 ~하다"처럼 인과관계를 명확히
밝힙니다. 절대로 특정 교재(수학의 정석, RPM, 하이탑 등)나 특정 대학의 기출문제를 그대로
인용하거나 살짝 바꿔서 재현하지 않습니다 -- 표준적으로 알려진 정의/정리/공식만 쓰고, 예제와
연습문제는 전부 당신이 새로 창작합니다."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "motivation": {
            "type": "STRING",
            "description": "이 개념을 왜 배우는지, 이전 단원과 어떻게 연결되는지 동기 부여 (2-4문장, 인과관계 명확히)",
        },
        "definitions_and_theorems": {
            "type": "STRING",
            "description": "핵심 정의와 정리를 마크다운(LaTeX 포함)으로 정확하게 서술. 각 정리마다 "
                            "'왜 이게 성립하는가'를 반드시 인과적으로 설명할 것. 여러 개념이면 ### 소제목으로 구분.",
        },
        "killing_equation_latex": {
            "type": "STRING",
            "description": "이 토픽의 핵심 공식/정리를 나타내는 단 하나의 LaTeX 수식 (가장 결정적인 것)",
        },
        "killing_equation_explanation": {
            "type": "STRING",
            "description": "이 killing equation이 왜 이 토픽의 핵심인지, 어떻게 유도/성립하는지 설명",
        },
        "techniques": {
            "type": "ARRAY",
            "description": "이 토픽에서 실제로 쓰이는 계산 테크닉 3-6개. killing equation 유무와 무관하게 "
                            "반복적으로 쓰이는 풀이 요령을 전부 포함할 것 (계산 테크닉 나열도 중요함).",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "테크닉 이름"},
                    "method": {"type": "STRING", "description": "구체적으로 어떻게 적용하는지 (수식 포함 가능)"},
                    "reasoning": {"type": "STRING", "description": "왜 이 방법이 통하는지 인과적 설명"},
                },
                "required": ["name", "method", "reasoning"],
            },
        },
        "common_mistakes": {
            "type": "STRING",
            "description": "학생들이 이 토픽에서 자주 놓치거나 헷갈리는 부분, 빠뜨리기 쉬운 특수 케이스나 "
                            "부정형/예외 상황을 빠짐없이 짚어줄 것 (이 항목이 이론서의 빈틈을 막는 핵심 검증 장치임).",
        },
        "worked_examples": {
            "type": "ARRAY",
            "description": "새로 창작한 대표예제 정확히 2개, 실제 편입수학 시험 난이도. 특정 기출/교재 문제를 "
                            "베끼거나 숫자만 바꾸지 말 것 -- 완전히 새로 만든 문제여야 함.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "problem": {"type": "STRING", "description": "문제 (LaTeX 포함)"},
                    "solution_steps": {
                        "type": "STRING",
                        "description": "단계별 상세 풀이. 각 단계마다 '왜 이렇게 하는지' 논리를 반드시 설명. "
                                        "'1단계 — ...', '2단계 — ...' 형식으로 번호를 매길 것.",
                    },
                    "answer": {"type": "STRING", "description": "최종 답 (LaTeX 가능)"},
                },
                "required": ["problem", "solution_steps", "answer"],
            },
        },
        "practice_problems": {
            "type": "ARRAY",
            "description": "학생이 스스로 풀어볼 유제 정확히 5개 (풀이 없이 문제와 짧은 힌트만). 새로 창작할 것.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "problem": {"type": "STRING"},
                    "hint": {"type": "STRING", "description": "어떤 테크닉을 쓰면 되는지 짧은 힌트"},
                },
                "required": ["problem", "hint"],
            },
        },
        "next_topic_connection": {
            "type": "STRING",
            "description": "이 단원의 내용이 다음 단원과 구체적으로 어떻게 연결되는지 (1-3문장)",
        },
    },
    "required": [
        "motivation", "definitions_and_theorems", "killing_equation_latex",
        "killing_equation_explanation", "techniques", "common_mistakes",
        "worked_examples", "practice_problems", "next_topic_connection",
    ],
}

PROMPT_TMPL = PERSONA + """

과목: {subject}
이 토픽: "{topic}"
직전 토픽(있다면, 자연스럽게 이어지도록 참고만 할 것): {prev_topic}

위 토픽에 대한 편입수학 이론서 한 챕터 분량을 지정된 JSON 스키마로만 작성하라. 반드시 한국어로,
수식은 LaTeX($$...$$ 또는 $...$)로 작성하라. 쉽고 꼼꼼하고 자세하게, 논리적 오류나 내용적
부정확성이 전혀 없도록 각별히 신경 쓸 것. common_mistakes 항목에서 이 토픽에 흔히 빠지는
부정형/특수 케이스/예외 상황을 반드시 빠짐없이 점검할 것.
"""

_TEMPLATE = """---
title: "{title}"
subject: {subject}
tags: [편입수학, 이론서, {subject}]
killing_equation: "{killing_eq_frontmatter}"
---

# {index:02d}. {title}

## 1. 왜 배우는가

{motivation}

## 2. 정의와 정리

{definitions_and_theorems}

## 3. 핵심 공식 (Killing Equation)

$$ \\boxed{{\\ {killing_equation_latex}\\ }} $$

{killing_equation_explanation}

## 4. 계산 테크닉

{techniques_block}

## 5. 자주 하는 실수 / 주의할 점

{common_mistakes}

## 6. 대표예제

{examples_block}

## 7. 유제

{practice_block}

## 8. 다음 단원과의 연결

{next_topic_connection}
"""


def _techniques_block(techniques: list[dict]) -> str:
    parts = []
    for i, t in enumerate(techniques, 1):
        parts.append(
            f"### 테크닉 {chr(64+i)}: {t.get('name','')}\n\n"
            f"{t.get('method','')}\n\n"
            f"**왜 이 방법이 통하는가:** {t.get('reasoning','')}"
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
    parts = []
    for i, p in enumerate(problems, 1):
        parts.append(f"{i}. {p.get('problem','')} *(힌트: {p.get('hint','')})*")
    return "\n".join(parts)


def _filename_slug(title: str) -> str:
    slug = re.sub(r"[^\w\s가-힣-]", "", title).strip()
    return re.sub(r"\s+", " ", slug)


def generate_topic(subject: str, index: int, topic: str, prev_topic: str | None) -> dict:
    prompt = PROMPT_TMPL.format(subject=subject, topic=topic, prev_topic=prev_topic or "(이 과목의 첫 토픽)")
    print(f"  [Gemini 호출] {subject} #{index} {topic} ...")
    return gemini_client.generate_json(prompt, SCHEMA)


def write_topic_note(domain_folder: str, index: int, topic: str, data: dict) -> Path:
    subject = domain_folder.split("_", 1)[1] if "_" in domain_folder else domain_folder
    content = _TEMPLATE.format(
        title=topic,
        subject=subject,
        killing_eq_frontmatter=data["killing_equation_latex"].replace('"', "'"),
        index=index,
        motivation=data["motivation"],
        definitions_and_theorems=data["definitions_and_theorems"],
        killing_equation_latex=data["killing_equation_latex"],
        killing_equation_explanation=data["killing_equation_explanation"],
        techniques_block=_techniques_block(data["techniques"]),
        common_mistakes=data["common_mistakes"],
        examples_block=_examples_block(data["worked_examples"]),
        practice_block=_practice_block(data["practice_problems"]),
        next_topic_connection=data["next_topic_connection"],
    )
    out_dir = BOOK_ROOT / domain_folder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{index:02d}_{_filename_slug(topic)}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  [저장] {out_path.name}")
    return out_path


# --- 토픽 목록 (도메인별) ---

LINEAR_ALGEBRA_REMAINING = [
    (4, "행렬의 계수(rank)와 해의 존재성"),
    (5, "역행렬과 그 계산법"),
    (6, "행렬식의 정의와 성질"),
    (7, "여인수전개와 크래머 공식"),
    (8, "벡터공간과 부분공간"),
    (9, "일차독립과 일차종속"),
    (10, "생성(span), 기저와 차원"),
    (11, "선형변환과 표현행렬"),
    (12, "핵과 상, 차원정리(rank-nullity)"),
    (13, "고유값과 고유벡터"),
    (14, "대각화"),
    (15, "행렬의 거듭제곱(멱승): 대각화와 케일리-해밀턴 정리를 이용한 계산"),
    (16, "내적공간과 노름, 코시-슈바르츠 부등식"),
    (17, "그람-슈미트 직교화"),
    (18, "직교행렬과 대칭행렬의 직교대각화"),
    (19, "이차형식과 그 응용"),
    (20, "벡터의 외적과 기하학적 응용"),
    (21, "선형대수학 종합 정리"),
]

MULTIVARIABLE_CALCULUS = [
    (1, "다변수함수와 등위선/등위면"),
    (2, "다변수함수의 극한과 연속"),
    (3, "편미분의 정의와 계산"),
    (4, "전미분과 선형근사"),
    (5, "다변수 연쇄법칙"),
    (6, "그래디언트 벡터"),
    (7, "방향도함수"),
    (8, "접평면"),
    (9, "임계점과 극값 판정 (헤시안)"),
    (10, "라그랑주 승수법"),
    (11, "이중적분의 정의와 계산"),
    (12, "이중적분의 적분순서 바꾸기"),
    (13, "극좌표에서의 이중적분"),
    (14, "삼중적분"),
    (15, "원통좌표계에서의 삼중적분"),
    (16, "구면좌표계에서의 삼중적분"),
    (17, "벡터장, 발산과 회전"),
    (18, "선적분"),
    (19, "그린정리"),
    (20, "면적분과 스토크스정리"),
    (21, "발산정리"),
]

CALCULUS_REMAINING = [
    (2, "미분의 정의와 기본 미분법"),
    (3, "합성함수 미분(연쇄법칙)과 음함수 미분법"),
    (4, "매개변수함수의 미분과 고차도함수"),
    (5, "평균값 정리와 로피탈의 정리"),
    (6, "부정형 극한 (0^0, 1^∞, ∞-∞) 처리"),
    (7, "함수의 증가/감소와 극값 (1계 도함수 판정법)"),
    (8, "오목성과 변곡점 (2계 도함수 판정법)"),
    (9, "그래프 개형과 점근선"),
    (10, "최적화 응용문제"),
    (11, "부정적분과 기본 적분공식"),
    (12, "치환적분법"),
    (13, "부분적분법"),
    (14, "삼각치환"),
    (15, "부분분수분해를 이용한 적분"),
    (16, "정적분과 미적분의 기본정리"),
    (17, "정적분을 이용한 넓이 계산"),
    (18, "정적분을 이용한 부피 계산 (원판법, 셸법)"),
    (19, "곡선의 길이와 회전체의 겉넓이"),
    (20, "이상적분"),
    (21, "수열의 극한"),
    (22, "급수의 수렴판정법 I (비교판정법, 적분판정법)"),
    (23, "급수의 수렴판정법 II (비율판정법, 근판정법, 교대급수판정법)"),
    (24, "거듭제곱급수와 수렴반경"),
    (25, "테일러 급수와 매클로린 급수"),
    (26, "극좌표계와 극좌표 그래프"),
    (27, "극좌표에서의 넓이와 길이"),
    (28, "매개변수곡선의 미적분"),
    (29, "미적분학 종합 정리"),
]

ENGINEERING_MATH = [
    (1, "1계 상미분방정식 - 변수분리형"),
    (2, "1계 상미분방정식 - 동차형"),
    (3, "1계 선형미분방정식과 적분인자"),
    (4, "완전미분방정식"),
    (5, "베르누이 방정식"),
    (6, "2계 선형 동차 상미분방정식 (특성방정식)"),
    (7, "2계 선형 비동차 상미분방정식 (미정계수법)"),
    (8, "매개변수변환법"),
    (9, "오일러-코시 방정식"),
    (10, "연립 미분방정식 기초"),
    (11, "급수해법 개요"),
    (12, "라플라스 변환의 정의와 기본성질"),
    (13, "라플라스 역변환"),
    (14, "라플라스 변환을 이용한 미분방정식 풀이"),
    (15, "단위계단함수와 임펄스함수"),
    (16, "복소수와 복소평면"),
    (17, "복소함수와 오일러공식"),
    (18, "푸리에 급수"),
    (19, "푸리에 변환 기초"),
    (20, "공학수학 종합 정리"),
]


def run_batch(domain_folder: str, topics: list[tuple[int, str]], start_from: int = 1):
    prev_topic = None
    for index, topic in topics:
        if index < start_from:
            prev_topic = topic
            continue
        out_path = BOOK_ROOT / domain_folder / f"{index:02d}_{_filename_slug(topic)}.md"
        if out_path.exists():
            print(f"  [건너뜀] 이미 존재: {out_path.name}")
            prev_topic = topic
            continue
        try:
            data = generate_topic(domain_folder.split('_',1)[1], index, topic, prev_topic)
            write_topic_note(domain_folder, index, topic, data)
        except Exception as e:
            print(f"  [실패] {topic}: {e}")
        prev_topic = topic


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="편입수학 이론서 자동 생성 (Gemini)")
    parser.add_argument("--test", action="store_true", help="토픽 1개로 품질 테스트 (파일 안 씀)")
    parser.add_argument("--domain", choices=["01_미적분학", "02_선형대수학", "03_다변수미적분학", "04_공학수학"], help="생성할 과목 폴더")
    parser.add_argument("--from", dest="from_idx", type=int, default=1, help="이 번호부터 생성")
    parser.add_argument("--all", action="store_true", help="4과목 전체(이미 있는 파일은 건너뜀)")
    args = parser.parse_args()

    if args.test:
        data = generate_topic("선형대수학", 4, "행렬의 계수(rank)와 해의 존재성", "가우스 소거법과 연립일차방정식")
        import json
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
    elif args.all:
        run_batch("01_미적분학", CALCULUS_REMAINING, start_from=2)
        run_batch("02_선형대수학", LINEAR_ALGEBRA_REMAINING, start_from=4)
        run_batch("03_다변수미적분학", MULTIVARIABLE_CALCULUS, start_from=1)
        run_batch("04_공학수학", ENGINEERING_MATH, start_from=1)
    elif args.domain == "01_미적분학":
        run_batch("01_미적분학", CALCULUS_REMAINING, start_from=args.from_idx)
    elif args.domain == "02_선형대수학":
        run_batch("02_선형대수학", LINEAR_ALGEBRA_REMAINING, start_from=args.from_idx)
    elif args.domain == "03_다변수미적분학":
        run_batch("03_다변수미적분학", MULTIVARIABLE_CALCULUS, start_from=args.from_idx)
    elif args.domain == "04_공학수학":
        run_batch("04_공학수학", ENGINEERING_MATH, start_from=args.from_idx)
    else:
        parser.print_help()
