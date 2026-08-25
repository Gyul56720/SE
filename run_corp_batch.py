"""corp/(기업)/(직무) 배치 실행 -- company_role_report.run()을 여러 실제 JD에 대해 돌린다."""
from pathlib import Path
from company_role_report import run

LX_DV_JD = """직무상세: UVM(Universal Verification Methodology)을 활용한 Digital IP 설계 검증,
SystemVerilog을 활용한 Assertion based Verification / Coverage Based Verification,
Display Driver IC / Gate Driver IC / VR/TCON 제품군에 대한 설계 검증,
Real Number Modeling을 통한 AMS 검증.

자격요건: 경력 기준(학사 5년 이상/석사 3년 이상), 해외여행 결격사유 없음,
남자일 경우 병역 필수 또는 면제자, R&D 직무는 TOEIC Speaking 또는 OPIc IL 이상.

우대사항: SystemVerilog 및 UVM 사용 경험자, C 또는 Python 언어 활용 우수자,
eDP, MIPI_DSI Protocol 업무 경험자, 영어 능통자."""

HYUNDAI_DV_JD = """주요업무 - 설계 검증: 마이크로 아키텍처 기반 검증 계획 작성, UVM 기반 테스트벤치 작성,
Test 시나리오 작성, 기능/성능 검증 수행 및 분석, 커버리지 측정, 검증 문서 작성.
검증 환경 개발: 신규 SoC/IP에 대한 UVM 검증 환경 개발, 스크립팅 언어로 검증 환경 자동화.

자격요건: 학사 이상, 3년 이상 디지털 설계 검증 경력, 전기전자/CS 전공,
설계팀·아키텍트·검증엔지니어와의 협업 능력, Verilog/SystemVerilog/C/C++/Python 역량.

우대사항: 고성능 SoC 개발 참여 경험, ARM CPU/AMBA bus/CAN/PCIe/Ethernet spec 검증 경험,
FPGA/Emulator 활용 경험, ISO26262(차량 기능안전) 이해 및 문서작성 경험, 비즈니스 영어/중국어."""

REBELLIONS_FW_JD = """주요업무: Rebellions AI 서버용 BMC(Baseboard Management Controller) 펌웨어 개발/유지보수,
OpenBMC 기반 플랫폼 관리 스택 구축(전원/리셋 시퀀싱, 열/팬 제어, 센서 모니터링),
IPMI/PLDM/MCTP/Redfish 등 표준 관리 인터페이스 구현, PCIe/USB 등 고속 인터페이스 제어,
펌웨어 업데이트/롤백 및 RAS 기능 설계, 하드웨어 bring-up 중 HW/SoC 팀과 디버깅 협업.

자격요건: 컴퓨터과학/전자공학 등 관련 학위(학사 이상), 임베디드/시스템레벨 펌웨어 개발 4년 이상,
C/C++ 개발 및 디버깅 역량, OS 기초/부트플로우/IPC/장치통신 이해, Linux 커널 아키텍처 및
디바이스 드라이버 깊은 이해, 하드웨어 데이터시트/회로도 해석 능력, 오실로스코프/로직분석기/JTAG 경험."""

SAMSUNG_SW_JD = """자격요건: 프로그래밍 언어(C/C++/C#/Python/Java 등) 및 알고리즘 문제해결 역량 보유자.
우대사항: 웹 개발, 데이터베이스, AI/ML 경험, SW 테스팅 인증, S/W 아키텍처 분석 경험."""


if __name__ == "__main__":
    jobs = [
        ("LX세미콘(LG계열)", "Design Verification 전문가", LX_DV_JD),
        ("현대자동차", "차량용 반도체 SoC 검증 담당자", HYUNDAI_DV_JD),
        ("Rebellions(리벨리온)", "Server BMC Firmware Engineer", REBELLIONS_FW_JD),
        ("삼성전자 DS부문", "S-W개발", SAMSUNG_SW_JD),
    ]
    for company, role, jd in jobs:
        run(company, role, jd, Path("corp") / company)
