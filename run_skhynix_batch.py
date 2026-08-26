"""corp/SK하이닉스/ 배치 실행 -- JD PDF에서 이미 확인한 실제 원문 사용."""
from pathlib import Path
from company_role_report import run

DESIGN_JD = """About Us: 시장과 고객이 필요로 하는 메모리 반도체 제품을 설계하고 실제 제품으로
만드는 일을 합니다. 시스템과 어플리케이션을 이해한 후, 아키텍처 설계, 디지털/아날로그 회로
설계, 레이아웃, 검증 등 다양한 설계 과정과 EDA 방법론 개발을 담당합니다.

주요업무(회로검증): 제품이 요구 사양에 맞게 안정적으로 동작하는지 설계 검증 진행하며, 실제
양산 환경을 고려하여 회로설계에 대한 C code 기반 System 및 RTL level 설계 검증을 수행합니다.
다양한 Test Scenario와 검증 Methodology를 개발하여 Coverage를 확대하고 설계 디자인 완성도를
높입니다.

자격요건(우대): 전자, 전기, 반도체, 컴퓨터, 물리 등 관련 분야에 경험과 역량이 있는 분.
Noise 성분 분석, Design Constraint 설계, Circuit Modeling 등을 경험해보신 분.
Design Sign-off Methodology 개발 및 운영, 3D-IC & Multi-physics CAD 환경 구축 및 해석,
AI 기반 메모리 R&D 솔루션 개발을 경험해 보신 분."""

SOLUTION_SW_JD = """About Us: AI 시대의 Total AI Memory Provider로서 Datacenter/Enterprise SSD 및
차세대 AI Memory 제품의 경쟁력 확보를 위해 System/SSD Architecture와 Firmware Platform을
설계·개발하고, HW-FW-SW 전 영역의 성능·품질을 최적화합니다.

주요업무: SSD/System Architecture 설계 및 최적화, Firmware Platform 및 핵심 Algorithm 개발
(PCIe/NVMe Host Interface부터 NAND Data 처리까지), Firmware 검증 및 개발 Process 고도화,
AI Memory 및 System Software 기술 개발(System SW·Runtime·Compiler·AI Framework).

자격요건(우대): AI, 컴퓨터, 전기, 전자, 반도체, 데이터사이언스 등 관련 분야 경험과 역량.
컴퓨터 구조와 마이크로아키텍처에 대한 깊은 이해. C/C++ 및 Assembly 언어 프로그래밍 경험이
풍부하신 분. 성능 모델링 및 분석. Verilog 또는 System Verilog를 이용한 설계 및 검증 경험.
Compiler의 내부 구조나 최적화 기법에 대한 이해, System Software 연구 경험. ARM 코어 기반
Embedded System 연구 및 개발 경험. Cursor, Claude Code 등 AI 기반 IDE를 활용하여 개발
프로젝트의 생산성을 높여본 경험이 있으신 분."""

PE_JD = """About Us: 설계·소자·공정 전반의 지식을 바탕으로 최고의 특성과 품질을 갖춘 완제품을
개발하며, 평가와 분석을 통해 수율과 경쟁력을 높이고 Test Solution을 고도화합니다.

주요업무: Test Engineering(제품의 특성과 품질, 양산성을 모두 충족할 수 있도록 최적의 테스트
기준을 개발하고 지속적으로 개선), 제품검증(설계·공정 특성을 검증하고 피드백을 제공해 제품
완성도를 높이며, 메모리 제품 동작을 해석하고 주요 불량 분석을 통해 최적화 솔루션 도출),
Test Solution 개발(테스트 프로그램 개선과 빅데이터 분석), 불량분석(제품 불량에 대해 전기적·
물리적 분석을 수행해 소자와 공정적 원인을 규명).

자격요건(우대): 전기, 전자, 반도체 등 관련 분야에 경험과 역량이 있는 분.
Programming 역량을 바탕으로 문제를 해결해본 경험이 있는 분."""


if __name__ == "__main__":
    jobs = [
        ("SK하이닉스", "설계(회로검증)", DESIGN_JD),
        ("SK하이닉스", "Solution SW", SOLUTION_SW_JD),
        ("SK하이닉스", "Product Engineering", PE_JD),
    ]
    for company, role, jd in jobs:
        run(company, role, jd, Path("corp") / company)
