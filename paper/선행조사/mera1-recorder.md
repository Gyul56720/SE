# 선행조사 — mera1_recorder

요청: 계측·시험장비용 MERA-1 v1.0 Event Recorder Core. AMD Versal RF VR1952 의 RF Data Converter 가 내보내는 AXI4-Stream 을 받아, 트리거 전후 구간을 하나의 record 로 잘라 DDR 에 저장하는 독립 IP 다. 단순 DMA 나 ADC capture 가 아니다. 1채널, I/Q 각 16-bit container = complex sample 32-bit. 내부 canonical interface 는 256-bit AXI4-Stream 이고 RFDC 폭과 그 사이는 adapter 가 packing 한다. RFDC TDATA 폭과 I/Q 비트 정렬은 Vivado 생성 결과를 봐야 하므로 TBD 로 남긴다. 평상시 circular buffer 로 유지하다 트리거가 오면 post-trigger capture 를 하고 record 를 완성한다. PRE 4096 POST 16384 complex sample, payload 80 KiB. 트리거는 external hardware 와 software 둘만. RFDC 데이터 인터페이스와 capture core 를 같은 클럭 도메인에 두어 CDC 를 만들지 않고 외부 트리거만 synchronizer 를 거친다. timestamp 는 내부 free-running counter 이고 RF ADC sample clock 과 같다고 가정하지 않는다 — 관계는 sample counter 와 configuration 으로 record metadata 에 남긴다. header 64 byte 고정: event ID, channel mask, timestamp, pre/post sample 수, sample width, sample format, alignment status, payload size. DDR 은 AXI4-MM master 64-bit address 128-bit data 64-beat burst. 제어는 AXI4-Lite. 가장 중요한 것은 트리거 시점의 sample ordering 이다 — circular buffer 가 wrap 해도 pre 구간이 정확한 순서로 들어가야 하고, DDR 이 순간 stall 해도 capture 가 안 깨지게 capture buffer 와 DDR writer 를 분리한다. 나중에 4/8 채널로 늘리므로 채널 간 sample index alignment 를 처음부터 구조에 넣고 채널별 고정 offset 을 레지스터로 보정한다. overflow 와 DDR write error 는 조용히 버리지 말고 sticky flag 로 남긴다. junction 0~100도 Extended, functional safety 인증은 없다. 목표 주파수 500 MHz, 공급 전압 0.8 V. 속도보다 결정성이 중요하다. 온칩 80 KiB 를 플립플롭으로 할지 SRAM 매크로로 할지 면적으로 비교해서 제안서로 내줘.

## 무엇을 짓기 전인가

AMD Versal RFDC 데이터를 입력받아 정밀 트리거 시점 전후 구간을 DDR로 저장하는 Event Recorder IP

## 찾아본 질의

- `ADC architecture low power CMOS`
- `ADC high speed design`
- `ADC area efficient design`
- `ADC high resolution design`
- `ADC fault tolerant design`
- `계측/시험장비 ADC ASIC power reduction`
- `AXI architecture low power CMOS`
- `AXI high speed design`

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

- RFDC 데이터 폭(TBD)에 따른 Packing Adapter의 타이밍 마진 부족
- AXI4-MM 지연 시간에 따른 캡처 버퍼 용량 초과(Overflow)
- 온칩 메모리(Flip-Flop vs SRAM) 선택에 따른 면적/전력 비효율

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
