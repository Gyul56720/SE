"""
"GPA보다 포트폴리오를 우선시하는 채용" 조사기 (career_planner.py와 같은 grounding 원칙).

이것도 collector.py(학술논문)나 book_generator.py(Wikipedia/GitHub)가 커버 못하는 영역이다 --
채용 관행(HR practice)은 회사 공식 블로그/뉴스/블라인드 후기에 흩어져 있어서, WebSearch로
직접 모은 실제 정보를 근거로 주고 Gemini에게 "회사/직무별로 분류"만 시킨다.

  python portfolio_first_hiring.py
"""

from __future__ import annotations
from pathlib import Path

import gemini_client

PERSONA = """당신은 국내 반도체/AI/IT 기업 채용 전형을 분석하는 커리어 리서처입니다.
아래 "근거 자료" 밖의 회사/전형 정보를 지어내지 않습니다. 근거에 없는 회사를 추가하지
말고, 근거의 뉘앙스(예: "일부 공고만 해당", "직무별로 다름")를 그대로 반영하십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "companies": {
            "type": "ARRAY",
            "description": "GPA/학력보다 포트폴리오·실무역량을 우선하는 정도가 확인된 회사/직무",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "company": {"type": "STRING"},
                    "target_role": {"type": "STRING", "description": "이 근거가 적용되는 구체적 직무 (모르면 '전반적')"},
                    "evidence": {"type": "STRING", "description": "근거 자료에 있는 구체적 사실만 (전형 방식, 인용문)"},
                    "confidence": {"type": "STRING", "description": "확정/직무별상이/일부공고만 중 하나 -- 과장하지 말 것"},
                },
                "required": ["company", "target_role", "evidence", "confidence"],
            },
        },
        "pattern_summary": {
            "type": "STRING",
            "description": "근거 자료 전체를 관통하는 공통 패턴 (예: 어떤 유형의 회사/직무가 이런 전형을 쓰는지)",
        },
        "user_fit_note": {
            "type": "STRING",
            "description": "사용자의 실존 포트폴리오(rtl-lab RTL검증, capstone SAR레이더, LLM-RTL 리서치)가 "
                            "이런 전형에서 왜 유리한지, 근거 자료 기준으로만 설명",
        },
    },
    "required": ["companies", "pattern_summary", "user_fit_note"],
}

GROUNDING = """
[WebSearch로 확인된 실제 채용 전형 정보]

- SK하이닉스 Talent hy-way(신입) 2026년 하반기 공식 JD: "지원자격 - 연령·학력과 무관하게
  Full-time 근무 가능한 자"로 명시. 설계/Solution SW 등 전 직무 공통 지원자격이며, 서류는
  자기소개서 폐지하고 "AI 활용 역량과 반도체 직무 전문성" 중심 신규 서식으로 대체(2026년 하반기
  개편). 즉 학력/학점 자체를 지원자격에서 아예 빼고 직무 전문성(포트폴리오성 서술)로 대체.

- 카카오 신입 개발자 공채: 서류전형 자체를 폐지. 프로그래밍 테스트(코딩테스트) + 인터뷰로만
  선발. 블라인드 전형이라 지원 접수 시점에 신원 정보 수준만 받고, 코딩테스트 합격 이후
  작성하는 지원서에도 학력 정보 기재란이 아예 없음.

- 네이버 기술직군 신입채용: 별도의 서류 합격 단계가 없음. 코딩테스트 결과와 서류를 종합해
  면접 대상자를 정하되, "서류에 큰 신경 쓰지 않아도 되고, 뛰어난 스펙이나 화려한 자소서가
  필요 없다"는 것이 특징으로 알려짐.

- AI 스타트업(국내, 회사명 특정 안 됨) 해커톤 채용: 제한시간 내 조건에 맞는 솔루션을 개발하는
  AI 해커톤을 채용 전형으로 활용. 여기서 수상하면 학력·전공과 무관하게 서류전형이나 별도
  테스트 과제 없이 채용하는 사례가 있음.

- 퓨리오사AI: 채용공고마다 다름 -- 일부 공고는 "학력무관" 명시, 다른 공고는 "학사 이상" 요구.
  직무별로 학력 요구 기준이 상이함 (통일된 정책 아님).

- 잡코리아 2026 리포트: 구글부터 컬리까지 국내외 기업들에서 "AI 활용 코딩테스트"가 확산되는
  추세로 확인됨 -- 이력서/학력보다 실시간 문제해결력 평가 비중이 커지는 산업 전반의 흐름.

[사용자 실존 포트폴리오 -- 이미 채점 완료]
- rtl-lab: NVDLA CMAC 모듈 RTL 검증 파이프라인, "정직한 FAIL" 보고 원칙
- capstone(94점): FMCW SAR 레이더, TDBP 알고리즘 전환 근거화, 실측-이론 오차 원인 분리규명
- LLM-RTL 리서치: Icarus Verilog 기반 LLM Verilog 생성 검증 연구 grounding 추출 완료

목표: 위 근거만 바탕으로, GPA/학력보다 포트폴리오·실무역량을 우선시하는 것으로 확인된
회사/직무를 정리하고, 사용자 포트폴리오가 이런 전형에서 왜 유리한지 근거 기반으로 설명하라.
"""


def run() -> Path:
    print("[Gemini 호출] 포트폴리오 우선 채용 전형 종합 중...")
    data = gemini_client.generate_json(PERSONA + "\n\n" + GROUNDING, SCHEMA)

    lines = []
    for c in data["companies"]:
        lines.append(
            f"### {c['company']} — {c['target_role']} [{c['confidence']}]\n"
            f"{c['evidence']}"
        )
    company_block = "\n\n".join(lines)

    content = f"""---
title: "GPA보다 포트폴리오를 우선하는 채용 전형 조사"
tags: [career-plan, hiring-practice, portfolio-first]
---

# GPA보다 포트폴리오를 우선하는 채용 전형

> 근거: WebSearch로 확인된 실제 채용 전형 정보. Gemini API가 이 근거만 분류/정리함
> (근거에 없는 회사·과장된 확정 표현 없음 -- confidence 표시로 구분).

## 공통 패턴

{data['pattern_summary']}

## 회사/직무별 근거

{company_block}

## 사용자 포트폴리오와의 적합성

{data['user_fit_note']}
"""
    out_dir = Path("result/portfolio-first-hiring")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "GPA보다 포트폴리오 우선 채용 전형.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[저장] {out_path}")
    return out_path


if __name__ == "__main__":
    run()
