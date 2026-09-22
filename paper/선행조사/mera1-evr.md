# 선행조사 — mera1_evr

요청: MERA-1 v1.0 Event Recorder Core 를 ASIC 으로 설계한다.
입력은 256-bit canonical AXI4-Stream, 1채널 I/Q 16+16bit = 32bit/sample,
한 beat 에 8 sample. 목표 500 MHz, 0.8V, 동작온도 -40~105도.
PRE 4096 / POST 16384 sample 환형버퍼(채널당 80 KiB), 64-bit free-running
timestamp, 32-bit event ID, 64 byte record header, AXI4-MM 128-bit 64-beat
burst 로 DDR 에 쓴다. 트리거는 external 과 software 둘만, alignment 는 bypass.
FSM 은 IDLE/ARMED/TRIGGERED/POST_CAPTURE/COMMIT/DMA_WAIT/DONE/ERROR.
핵심 정확성 조건은 Record = {x[t-4096] … x[t] … x[t+16383]} 를 트리거 시점
기준으로 정확히 잘라내는 것이다. 속도보다 결정성이 중요하다.
온칩 80 KiB 메모리를 어떻게 구현할지(플립플롭 vs SRAM 매크로)와 그 면적 비용을
선택지로 비교해서 제안서로 내줘.

## 무엇을 짓기 전인가

MERA-1 v1.0 Event Recorder Core for AXI4-Stream I/Q data capture and AXI4-MM DDR transfer

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

- 500 MHz timing closure at 0.8V in target process node may fail due to tight setup/hold margins, requiring careful pipelining.
- Simultaneous SRAM read/write port contention for circular buffer access at 500 MHz could cause data corruption if arbitration is flawed.
- AXI4-MM bus latency during DMA_WAIT could overflow internal commit buffers if DDR bandwidth is insufficient.

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
