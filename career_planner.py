"""
자격증/포트폴리오 로드맵 생성기 (book_generator.py와 같은 grounding 원칙).

이 모듈도 book_generator.py처럼 "근거 자료 밖 내용을 지어내지 않는다" 원칙을 따른다.
차이점: 근거가 Wikipedia/GitHub가 아니라, 실제 WebSearch로 확인한 자격증·트레이닝
정보와 사용자의 실존 포트폴리오 요약(메모리에 저장된 채점 결과)이다. Gemini는 이 실존
정보를 "취업(DV/DS+AI) + GIST 대학원 진학" 두 목표에 동시에 맞게 재배열/우선순위화만 한다.

  python career_planner.py
"""

from __future__ import annotations
from pathlib import Path

import gemini_client

PERSONA = """당신은 반도체 설계검증(DV) 및 AI반도체 분야 채용/대학원 입시 컨설턴트입니다.
아래 "근거 자료" 밖의 자격증, 시험, 대학원 정보를 지어내지 않습니다. 근거에 없는 내용이
필요하면 "확인 필요"라고 명시하십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "certifications": {
            "type": "ARRAY",
            "description": "우선순위 순으로 정렬된 자격증/트레이닝 목록",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "category": {"type": "STRING", "description": "국가기술자격/데이터/검증전문트레이닝/어학 중 하나"},
                    "why_relevant": {"type": "STRING", "description": "DV/DS+AI 목표와 왜 연결되는지, 근거자료 인용"},
                    "priority": {"type": "STRING", "description": "1(최우선)~4"},
                    "prep_time": {"type": "STRING"},
                },
                "required": ["name", "category", "why_relevant", "priority", "prep_time"],
            },
        },
        "portfolio_roadmap": {
            "type": "ARRAY",
            "description": "기존 프로젝트(rtl-lab, capstone, smart antenna, LLM-RTL 리서치)를 발전시키는 다음 단계 프로젝트 4-6개. "
                            "취업용과 GIST 대학원용 두 목적에 각각 어떻게 기여하는지 구분해서 명시할 것.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "project_name": {"type": "STRING"},
                    "builds_on": {"type": "STRING", "description": "어떤 기존 프로젝트를 발전시키는지"},
                    "goal": {"type": "STRING"},
                    "new_skill_filled": {"type": "STRING", "description": "이 프로젝트로 채워지는 역량 갭"},
                    "job_relevance": {"type": "STRING", "description": "DV/DS+AI 취업에 어떻게 쓰이는지, JD 문구와 연결"},
                    "gist_relevance": {"type": "STRING", "description": "GIST 대학원(반도체공학과) 진학에 어떻게 쓰이는지 -- "
                                                                          "연구실적/OPEN Lab 지원 관점에서"},
                    "timeline": {"type": "STRING"},
                },
                "required": ["project_name", "builds_on", "goal", "new_skill_filled",
                             "job_relevance", "gist_relevance", "timeline"],
            },
        },
        "summary": {"type": "STRING", "description": "전체 전략 3-5문장 요약"},
    },
    "required": ["certifications", "portfolio_roadmap", "summary"],
}

GROUNDING = """
[자격증/트레이닝 근거 자료 -- WebSearch로 확인된 실제 정보]
- 반도체설계기사: 폐지된 자격증, 취득 불가.
- 전자기사: "반도체 설계 직무의 가장 직접적인 국가기술자격"으로 다수 출처에서 확인됨.
- 정보처리기사: IT 직군 기본 스펙, 개발자/데이터엔지니어 지원 시 활용.
- SQLD(SQL개발자): 데이터 관련 채용공고 45%가 SQL 역량 요구, 검증/불량 데이터 분석 역량 증빙.
- ADsP(데이터분석준전문가): 한국전력공사 등 공기업에서 정보처리기사와 동급 가산점 처리 사례 확산 중.
- Siemens Verification Academy: UVM/SystemVerilog 온라인 트레이닝(무료 모듈 포함), 8만명+ 회원,
  인증 보유자가 비보유자 대비 검증직군 연봉 7.5% 높다는 통계 존재. 코스: SystemVerilog for
  Verification(기초) -> UVM Intermediate(중급).
- Cadence 공식 트레이닝(유료): "Essential SystemVerilog for UVM", "SystemVerilog Accelerated
  Verification with UVM" -- 상용 EDA 툴체인 경험 보강용.
- 오픽/토익: SK하이닉스/삼성 공통 기본 스펙 (미달 시 감점 요인, 별도 우대 아님).

[GIST 대학원 근거 자료 -- WebSearch로 확인된 실제 정보]
- GIST 반도체공학과(semi.gist.ac.kr) 대학원 존재, 2026년 가을학기 신입생 모집 중.
- "반도체 첨단패키징 전문인력 양성과정" 운영.
- 입시 준비자 대상 OPEN Lab 설명회 개최 (관심 연구실 직접 컨택 권장).
- 학부생/대학원생 대상 하계 인턴십 프로그램 운영.

[사용자 기존 포트폴리오 요약 -- 이미 채점/분석 완료된 실존 프로젝트]
- rtl-lab: NVDLA CMAC 모듈 3개 RTL 검증 파이프라인(Verible 문법검증 -> facts_extract.py 구조분석
  -> Icarus elaborate -> 자체 제작 테스트벤치 -> PASS/FAIL). Booth 곱셈기는 "정직한 FAIL"로 보고,
  golden model 필요성 명시. 다만 UVM/공식 커버리지 도구는 미사용 -- 오픈소스 툴로 직접 구현.
- capstone(SAR 레이더, 포트폴리오 최고점 94점): TI IWR1843BOOST 기반 FMCW SAR, RMA->TDBP 알고리즘
  전환을 문헌 근거로 정당화, 실측-이론 2배 오차의 원인을 이론적으로 분리규명(Stop-and-Go 근사
  유효성 검증), 정량 목표 130~167% 달성. 참고문헌 8편 인용한 정식 연구보고서 형태.
- smart antenna: Dolph-Chebyshev 배열안테나 설계 + 최소자승 고장보상 알고리즘, 수식 직접 유도.
- LLM-RTL 리서치(이번 세션에 새로 발견): "Benchmarking LLMs for Verilog RTL Code Generation"
  논문을 Icarus Verilog 검증 파이프라인까지 grounding 추출함 -- rtl-lab과 검증 툴체인이 겹침.
- 갭: SI/PI, formal verification(SVA/assertion 기반 커버리지), 상용 EDA 툴(Cadence/Synopsys)
  실습 경험 없음. UVM 미사용.

목표: 위 근거만 바탕으로, "DV/DS(삼성 Device Solutions 계열) + AI반도체" 취업과 "GIST 대학원
반도체공학과 진학" 두 목표에 동시에 기여하는 자격증 우선순위와 포트폴리오 로드맵을 제시하라.
"""


def run() -> Path:
    print("[Gemini 호출] 자격증+포트폴리오 로드맵 종합 중...")
    data = gemini_client.generate_json(PERSONA + "\n\n" + GROUNDING, SCHEMA)

    cert_lines = []
    for c in sorted(data["certifications"], key=lambda x: x.get("priority", "9")):
        cert_lines.append(
            f"### [{c['priority']}순위] {c['name']} ({c['category']})\n"
            f"- 왜 필요한가: {c['why_relevant']}\n"
            f"- 준비기간: {c['prep_time']}"
        )

    portfolio_lines = []
    for p in data["portfolio_roadmap"]:
        portfolio_lines.append(
            f"### {p['project_name']}\n"
            f"- 발전시키는 기존 프로젝트: {p['builds_on']}\n"
            f"- 목표: {p['goal']}\n"
            f"- 채워지는 역량 갭: {p['new_skill_filled']}\n"
            f"- 취업(DV/DS+AI) 연결점: {p['job_relevance']}\n"
            f"- GIST 대학원 연결점: {p['gist_relevance']}\n"
            f"- 예상 기간: {p['timeline']}"
        )

    cert_block = "\n\n".join(cert_lines)
    portfolio_block = "\n\n".join(portfolio_lines)
    content = f"""---
title: "DV/DS + AI 취업 및 GIST 대학원 진학 자격증·포트폴리오 로드맵"
tags: [career-plan, DV, AI, GIST, certification]
---

# DV/DS + AI 취업 및 GIST 대학원 진학 로드맵

> 근거: 실제 WebSearch 확인된 자격증/GIST 정보 + 기존 채점된 포트폴리오(rtl-lab/capstone/smart
> antenna/LLM-RTL 리서치). Gemini API가 이 근거만 바탕으로 재배열/우선순위화함(지어낸 내용 없음).

## 전략 요약

{data['summary']}

## 1. 자격증/트레이닝 우선순위

{cert_block}

## 2. 포트폴리오 로드맵 (취업 + GIST 대학원 동시 기여)

{portfolio_block}
"""
    out_dir = Path("result/career-plan")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "DV_DS_AI 취업 및 GIST 대학원 진학 로드맵.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[저장] {out_path}")
    return out_path


if __name__ == "__main__":
    run()
