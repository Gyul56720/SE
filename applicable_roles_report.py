"""지원 가능 직무 종합 리포트 -- 이번 세션 전체에서 WebSearch로 확인된 실제 채용/프리랜서
정보를 모아 Gemini에게 "즉시 지원 가능 / 경력 필요(타겟) / 프리랜서·대안" 3단으로
분류시킨다. 근거 밖 회사·직무를 추가하지 않는다."""

from __future__ import annotations
from pathlib import Path

import gemini_client

PERSONA = """당신은 반도체/임베디드/AI 분야 신입 지원자를 위한 채용 리서처입니다.
아래 근거 자료 밖의 회사·직무를 지어내지 않습니다. 경력 요구가 있으면 절대 "신입 가능"으로
왜곡하지 말고 그대로 반영하십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "immediately_applicable": {
            "type": "ARRAY",
            "description": "신입/학력무관/경력무관으로 확인된, 지금 바로 지원 가능한 곳",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "company": {"type": "STRING"}, "role": {"type": "STRING"},
                    "evidence": {"type": "STRING"}, "note": {"type": "STRING", "description": "만료여부 등 주의사항"},
                },
                "required": ["company", "role", "evidence", "note"],
            },
        },
        "experience_required_targets": {
            "type": "ARRAY",
            "description": "3년 이상 등 경력 요구가 확인된, 포트폴리오 더 쌓은 뒤 노릴 타겟",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "company": {"type": "STRING"}, "role": {"type": "STRING"},
                    "years_required": {"type": "STRING"}, "evidence": {"type": "STRING"},
                },
                "required": ["company", "role", "years_required", "evidence"],
            },
        },
        "freelance_alternatives": {
            "type": "ARRAY",
            "description": "프리랜서/즉시 실행 가능한 대안 (플랫폼, 어떤 서비스로 등록 가능한지)",
            "items": {
                "type": "OBJECT",
                "properties": {"platform": {"type": "STRING"}, "service_idea": {"type": "STRING"}, "evidence": {"type": "STRING"}},
                "required": ["platform", "service_idea", "evidence"],
            },
        },
        "summary": {"type": "STRING"},
    },
    "required": ["immediately_applicable", "experience_required_targets", "freelance_alternatives", "summary"],
}

GROUNDING = """
[대기업/공채 -- 이미 확인]
- SK하이닉스 Talent hy-way(신입): 지원자격 연령·학력 무관. 설계(회로검증)/Solution SW 등 전직무 공통.
- 삼성전자 DS부문: 3급 신입사원 공채 있음(회로설계/평가및분석/SW개발 등 세부 트랙), S/W개발 자격요건은
  C/C++/C#/Python/Java 일반 수준.
- LX세미콘(LG계열) Design Verification 전문가: 경력 학사5년/석사3년 이상 -- 신입 불가.
- 현대자동차 차량용 반도체 SoC 검증 담당자: 경력 3년 이상 -- 신입 불가.
- FuriosaAI Design Verification Engineer: 경력 3년 이상. System Software Engineer: 5년 이상.
  Agent System Developer: 명시적 연차는 없으나 "real-world/large-scale 환경에서의 proven track
  record" 요구 -- 사실상 경력직 수준.
- Rebellions Server BMC Firmware Engineer: 경력 4년 이상.

[중소/스타트업 반도체·임베디드 -- 신입 문호 확인됨]
- 아이코어(안양, 검사장비 부품): FPGA RTL설계/VHDL·Verilog, "신입부터 경력 3년까지 모두 지원 가능"
  명시. 단, 확인된 공고 마감일이 2022.12.31로 만료됨 -- 이 회사 자체보다 "이런 유형의 회사가
  신입을 받는다"는 카테고리 증거로 볼 것.
- 리버트론: FPGA/임베디드SW/AI반도체설계 정규직, 신입 및 경력 대상 명시, 대학교 4년졸업, 수습 3개월.
- 아소테크: 회로설계 및 FPGA 개발, 신입 및 경력 대상.
- 엠큐브테크놀로지: 2026년 상반기 신입/경력 채용 진행 중(세부 직무 미확인).

[AI 에이전트/LLM 개발 -- 시장 전반]
- 국내 LangChain/LangGraph/RAG 기반 "AI 에이전트 개발자" 채용은 검색 범위에서 대부분 경력 4~5년
  이상 요구(예: LLM 애플리케이션/Function Calling 기반 시스템 연동 경험 요구).
- 신입 채용은 명확한 자격요건 확인 안 됨 -- 부트캠프(예: 솔트룩스 AI캠퍼스) 경유가 현실적 경로로
  보이나 이는 채용이 아니라 교육과정.
- 멋쟁이사자처럼(likelion) AI Agent 개발자 공고 존재 확인되었으나 원문 접근 차단(403)됨 -- 상세
  자격요건 확인 불가.

[프리랜서 플랫폼 -- 실행 가능한 대안]
- 크몽(kmong.com): 전문가 서비스 등록형 마켓플레이스. RTL 검증/Python 자동화 스크립트 작성
  같은 기술 서비스도 카테고리 존재 확인.
- 업계 자료(Medium/VLSI 블로그) 확인: "Python 기반 RTL 검증 자동화 스크립트"가 실무에서 실제
  수요 있는 서비스 영역으로 언급됨(시뮬레이션/합성 자동화, Makefile+Python+TCL 스크립트).

[사용자 포트폴리오 -- 이미 채점 완료]
- rtl-lab: NVDLA CMAC 검증 파이프라인(Verible+facts_extract.py+Icarus+Gemini), Python 자동화
  스크립트(resim.py 등) 다수 보유.
- capstone(94점): FMCW SAR 레이더, MATLAB 신호처리.
- LLM-RTL 리서치, career-intelligence 파이프라인(Claude Code+Gemini API 오케스트레이션).
- 갭: UVM 미사용, 실무 경력 0년, 상용 EDA 툴 경험 없음.

목표: 위 근거만으로 "즉시 지원 가능/경력 필요 타겟/프리랜서 대안" 3단 분류하라.
"""


def run() -> Path:
    print("[Gemini 호출] 지원 가능 직무 종합 분류 중...")
    data = gemini_client.generate_json(PERSONA + "\n\n" + GROUNDING, SCHEMA)

    imm = "\n\n".join(
        f"### {x['company']} — {x['role']}\n- 근거: {x['evidence']}\n- 주의: {x['note']}"
        for x in data["immediately_applicable"]
    ) or "- (확인된 곳 없음)"
    exp = "\n\n".join(
        f"### {x['company']} — {x['role']} (경력 {x['years_required']})\n- 근거: {x['evidence']}"
        for x in data["experience_required_targets"]
    )
    free = "\n\n".join(
        f"### {x['platform']}\n- 서비스 아이디어: {x['service_idea']}\n- 근거: {x['evidence']}"
        for x in data["freelance_alternatives"]
    )

    content = f"""---
title: "지원 가능 직무 종합 (IT대기업/스타트업/벤처/프리랜서)"
tags: [career-plan, job-search, summary]
---

# 지원 가능 직무 종합

> 근거: 이번 세션 WebSearch로 확인된 실제 채용정보 전체. Gemini API가 분류만 함
> (경력요구 왜곡 없음).

## 요약

{data['summary']}

## 1. 즉시 지원 가능 (신입/학력무관 확인)

{imm}

## 2. 경력 필요 -- 포트폴리오 더 쌓은 뒤 타겟

{exp}

## 3. 프리랜서/즉시 실행 가능한 대안

{free}
"""
    out_dir = Path("corp/_지원가능직무_종합")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "지원가능직무_종합.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[저장] {out_path}")
    return out_path


if __name__ == "__main__":
    run()
