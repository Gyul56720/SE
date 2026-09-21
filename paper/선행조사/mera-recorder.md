# 선행조사 — mera_recorder

요청: 차량·방산 RF 시험장비에 들어가는 MERA v1.0 Multi-channel Deterministic
RF Event Recorder IP 를 구상해줘. FPGA(AMD Versal VR1952) PL 에 올라가는 IP 다.
AXI4-Stream 으로 8채널 I/Q(16+16 bit) 를 128 bit 버스로 받아, 트리거 기준으로
pre-trigger 65536 샘플 / post-trigger 262144 샘플을 보존하고, 64 bit timestamp ·
event ID · channel alignment 결과 · status 를 64 byte record header 에 넣어
AXI4-MM 으로 DDR 에 쓴다. 제어는 AXI4-Lite.
목표 동작 주파수 250 MHz, 공급 전압 0.8 V, 동작온도 -40~105도.
FSM 은 IDLE/ARMED/TRIGGERED/POST_CAPTURE/COMMIT/DMA_WAIT/DONE/ERROR 8상태.
제일 어려운 것은 0-sample residual channel alignment 이고, 제일 비싼 것은
pre-trigger 온칩 버퍼 2 MiB 다. 속도보다 결정성(determinism)이 중요하다.
먼저 이 둘에 대한 구조 선택지와 비용을 비교해서 제안서로 내줘.

## 무엇을 짓기 전인가

Multi-channel Deterministic RF Event Recorder IP for AMD Versal VR1952 PL

## 찾아본 질의

- `AXI architecture low power CMOS`
- `AXI high speed design`
- `AXI area efficient design`
- `automotive AXI ASIC power reduction`
- `FIFO architecture low power CMOS`
- `FIFO high speed design`
- `FIFO area efficient design`
- `automotive FIFO ASIC power reduction`

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

- BRAM/URAM resource congestion on Versal VR1952 when implementing the 2 MiB pre-trigger buffer at 250 MHz timing closure.
- Clock domain crossing (CDC) or routing delay skew causing non-deterministic channel alignment violating the 0-sample residual requirement.
- AXI4-MM write bandwidth bottleneck leading to internal FIFO overflow during POST_CAPTURE to COMMIT transition.

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
