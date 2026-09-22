# 선행조사 — mera1_er

요청: MERA-1 v1.0 Event Recorder Core 를 ASIC 으로 설계한다. 입력은 256-bit canonical AXI4-Stream, 1채널 I/Q 16+16bit = 32bit/sample

## 무엇을 짓기 전인가

256-bit AXI4-Stream 입력을 받아 32-bit I/Q 샘플 데이터를 기록하는 Event Recorder Core

## 찾아본 질의

- `AXI architecture low power CMOS`

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

- 256-bit 데이터 처리 시 내부 클럭 속도가 요구 대역폭을 만족하지 못할 위험
- 외부 아날로그 단에서 입력되는 샘플링 레이트와 시스템 클럭 간의 비동기성으로 인한 데이터 샘플링 오류

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
