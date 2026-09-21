# 선행조사 — edge_npu_mac_accel

요청: 8탭 FIR/MAC 가속기를 AXI4-Stream 데이터 + AXI4-Lite 제어로 감싸서
시스템 버스에 붙는 IP 로 만들고, 그 MAC 을 32/64/128/256 개 PE 어레이로 묶어
INT8 연산을 하는 NPU 코어로 확장해줘. 목표 500MHz, 엣지 저전력.

## 무엇을 짓기 전인가

AXI4-Stream 데이터 인터페이스와 AXI4-Lite 제어 레지스터를 갖추고 32/64/128/256개 INT8 PE 어레이로 확장 가능한 8탭 FIR/MAC 가속기 NPU 코어

## 찾아본 질의

- `FIR architecture low power CMOS`
- `FIR low power design`
- `AXI architecture low power CMOS`
- `AXI low power design`
- `CPU architecture low power CMOS`
- `CPU low power design`

## 가장 가까운 선행연구

| 무엇 | arXiv/DOI | 연도 | 우리가 다른 점 |
|---|---|---|---|
| **(아직 안 채움)** | | | |

> **이 표가 비어 있으면 코드를 쓰면 안 된다.** CLAUDE.md:
> "'없는 것 같다' 를 조사 결과라고 하지 않는다. 어디를 **아직 못 봤는지** 적는다."

## 아직 못 본 곳

- 상용 IP 카탈로그 (Synopsys DesignWare · Cadence · Arm)
- 해당 분야 표준 (자동차면 ISO 26262 · AEC-Q100, 통신이면 해당 규격)
- 특허 (이 구조가 이미 특허일 수 있다)
- 최근 3년 학회 (ISSCC · VLSI · DAC · DATE)

## 아직 못 지운 가능성

- 500MHz 고주파수 달성을 위한 파이프라인 스테이지 부족으로 인한 타이밍(Setup/Hold) 위반
- 256개 PE 어레이 동시 구동 시 발생하는 클럭 분배 및 전력 분배(IR Drop) 문제로 인한 엣지 저전력 목표 초과
- AXI4-Stream과 내부 MAC 연산 유닛 간의 핸드셰이크 지연으로 인한 처리량(Throughput) 저하

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
