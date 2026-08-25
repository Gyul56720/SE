"""
기업 직무별 JD 대조 리포트 생성기 (career_planner.py와 같은 grounding 원칙).

실제 채용공고 원문(WebFetch로 확인)과 사용자 실존 포트폴리오만 근거로 주고, Gemini가
"이 직무에 뭐가 맞고 뭐가 비는지"만 정리하게 한다. 안 맞는 부분을 억지로 끼워맞추지
않도록 프롬프트에 명시한다.

  python company_role_report.py
"""

from __future__ import annotations
from pathlib import Path

import gemini_client

PERSONA = """당신은 반도체/AI 기업 채용 JD와 지원자 포트폴리오를 대조하는 커리어 분석가입니다.
아래 "JD 원문"과 "포트폴리오" 밖의 사실을 지어내지 않습니다. 포트폴리오가 JD 요구사항과
안 맞으면 억지로 끼워맞추지 말고 "갭"으로 명시하십시오. 과장하지 마십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "core_requirements": {
            "type": "ARRAY", "description": "JD의 핵심 요구사항 4-8개, JD 원문 문구 그대로",
            "items": {"type": "STRING"},
        },
        "matching_evidence": {
            "type": "ARRAY",
            "description": "포트폴리오 중 이 JD 요구사항과 실제로 맞는 것만. 없으면 빈 배열.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "requirement": {"type": "STRING"},
                    "project": {"type": "STRING"},
                    "why_matches": {"type": "STRING"},
                },
                "required": ["requirement", "project", "why_matches"],
            },
        },
        "gaps": {
            "type": "ARRAY", "description": "포트폴리오에 없는, 채워야 할 JD 요구사항",
            "items": {"type": "STRING"},
        },
        "verdict": {"type": "STRING", "description": "이 직무 지원 적합도에 대한 솔직한 종합 판단 2-4문장"},
    },
    "required": ["core_requirements", "matching_evidence", "gaps", "verdict"],
}

PROMPT_TMPL = PERSONA + """

회사: {company}
직무: {role}

--- JD 원문 (WebFetch로 확인) ---
{jd_text}

--- 지원자 포트폴리오 (이미 채점 완료된 실존 프로젝트) ---
- rtl-lab: NVDLA CMAC 모듈 3개 RTL 검증 파이프라인(Verible 문법검증 -> facts_extract.py 구조분석
  -> Icarus elaborate -> 자체 제작 테스트벤치 -> PASS/FAIL). UVM/공식 커버리지 도구는 미사용.
  Booth 곱셈기는 "정직한 FAIL"로 보고.
- capstone(94점): TI IWR1843BOOST 기반 FMCW SAR 레이더, RMA->TDBP 알고리즘 전환 근거화,
  실측-이론 오차 원인 분리규명, MATLAB 신호처리, 정량목표 130~167% 달성.
- smart antenna: Dolph-Chebyshev 배열안테나 설계, 최소자승 고장보상 알고리즘 직접 유도(MATLAB).
- LLM-RTL 리서치: "Benchmarking LLMs for Verilog RTL Code Generation" 논문을 Icarus Verilog
  검증 파이프라인까지 grounding 추출.
- embedded-lab: STM32 드론 비행제어 펌웨어, README에 "동작 가능한 스켈레톤"이라 명시 -- 실기판
  검증 안 됨.
- 갭(이미 확인됨): UVM 미사용, SI/PI/PCIe/UCIe/DDR 등 고속 인터페이스 검증 경험 없음, ARM/RISC-V
  서브시스템 검증 경험 없음, Chisel/Rust 경험 없음, 상용 EDA 툴(Cadence/Synopsys) 실습 없음.

위 두 근거만 바탕으로 지정된 JSON 스키마로 답하라. 반드시 한국어로.
"""


def run(company: str, role: str, jd_text: str, out_dir: Path) -> Path:
    print(f"[Gemini 호출] {company} - {role} 대조 중...")
    prompt = PROMPT_TMPL.format(company=company, role=role, jd_text=jd_text)
    data = gemini_client.generate_json(prompt, SCHEMA)

    req_block = "\n".join(f"- {r}" for r in data["core_requirements"])
    match_block = "\n\n".join(
        f"### {m['requirement']}\n- 근거 프로젝트: {m['project']}\n- 왜 맞는가: {m['why_matches']}"
        for m in data["matching_evidence"]
    ) or "- (직접 대응되는 근거 없음)"
    gap_block = "\n".join(f"- {g}" for g in data["gaps"]) or "- (확인된 갭 없음)"

    content = f"""---
title: "{company} - {role}"
tags: [career-plan, jd-match, {company.lower().replace(' ', '-')}]
---

# {company} — {role}

## JD 핵심 요구사항

{req_block}

## 매칭되는 포트폴리오 근거

{match_block}

## 갭 (채워야 할 것)

{gap_block}

## 종합 판단

{data['verdict']}
"""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{role.replace('/', '-')}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  -> {out_path}")
    return out_path


if __name__ == "__main__":
    out = Path("result/furiosa")

    dv_jd = """The Role: Design Verification Engineer will define and implement verification plans, develop tests, debug designs, and collaborate with cross-functional teams to ensure high design quality.

Responsibilities:
- Block/IP/SoC 검증 계획 수립 및 실행, 검증 테스트벤치 구축
- 검증 테스트 계획 기반 기능 테스트 개발
- 정의된 검증 지표에 따라 설계 검증 완료 추진
- 설계 기능 장애 디버깅 및 근본 원인 해결
- 설계, 모델, 에뮬레이션, 실리콘 검증 팀과의 협업

Minimum Qualifications:
- Bachelor's degree in Electrical Engineering, Computer Science or other technically related fields
- 3+ years experience in block/IP/sub-system and/or SoC level verification based on SystemVerilog/UVM
- EDA 도구 및 스크립팅 경험 (Python, TCL, Perl, Shell)
- 검증 인프라 설계 및 전체 검증 사이클 실행 경험

Preferred:
- 석사 학위
- UVM 기반 검증 환경 개발 경험
- PCIe, UCIe, DDR 같은 고속 인터페이스 검증 경험
- ARM/RISC-V 기반 서브시스템 또는 SoC 검증 경험
- Chisel 경험
- Python 프로그래밍 능력
- 뛰어난 소통 능력"""

    sw_jd = """Basic Qualifications: Bachelor's degree in Computer Science and more than 5-years practical experience.
Programming: C/C++, Python, Rust 등 범용 프로그래밍 언어 경험.
Preferred (다음 중 2개 이상): Secure System(attestation, encryption, TEE, secure boot),
Virtualization(kvm/qemu, virtio, sriov), Linux/Windows Device Driver(PCIe driver, power/thermal
management), Firmware(host interface layer), Distributed/Parallel Systems.
Advanced degree(Master/PhD in CS) also considered.
Responsibilities: Furiosa 디바이스용 firmware 설계/구현, device driver 설계/구현.
NPU device driver 및 firmware 개발, PCIe driver 개발 포함 system software 스택."""

    run("FuriosaAI", "Hardware - Design Verification Engineer", dv_jd, out)
    run("FuriosaAI", "System SW - System Software Engineer", sw_jd, out)
