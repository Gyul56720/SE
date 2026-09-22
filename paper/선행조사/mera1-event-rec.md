# 선행조사 — mera1_event_rec

요청: 계측·시험장비용 MERA-1 v1.0 Event Recorder Core 를 ASIC 으로 설계한다. 256-bit AXI4-Stream 입력, 1채널 I/Q 16+16bit 32bit 샘플, 한 beat 에 8 샘플. 목표 500 MHz, 0.8V, 동작온도 -40~105도. PRE 4096 POST 16384 샘플 환형버퍼 채널당 80 KiB, 64bit 타임스탬프, 32bit event ID, 64 byte 헤더, AXI4-MM 128bit 64 beat burst 로 DDR 에 쓴다. 트리거는 external 과 software 둘만, alignment 는 bypass. 속도가 문제다 — 트리거 시점 기준 정확한 샘플 윈도우를 잘라내는 결정성이 핵심이다. 온칩 80 KiB 를 플립플롭으로 할지 SRAM 매크로로 할지 면적으로 비교해줘.

## 무엇을 짓기 전인가

계측·시험장비용 MERA-1 v1.0 Event Recorder Core ASIC 설계

## 찾아본 질의

- `AXI architecture low power CMOS`
- `AXI high speed design`
- `AXI area efficient design`
- `AXI high resolution design`
- `FIFO architecture low power CMOS`
- `FIFO high speed design`
- `FIFO area efficient design`
- `FIFO high resolution design`

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

- 500 MHz 고주파수 및 0.8V 저전압 조건에서 PVT variation으로 인한 셋업/홀드 타이밍 위반
- 트리거 인가 시점부터 링버퍼 읽기 제어 로직 간의 파이프라인 지연으로 인한 결정성(Determinism) 상실
- 플립플롭으로 80 KiB 구현 시 과도한 면적 및 동적 전력 소모 발생
- AXI4-MM 128-bit 64 beat burst 쓰기 과정에서 내부 FIFO 오버플로우 발생 가능성

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
