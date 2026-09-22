# 선행조사 — fir_filter_64t

요청: ### 3. FIR Functional Requirements

본 IP는 AXI4-Stream 기반의 실시간 FIR 필터 IP이며, 입력 샘플에 대해 고정 계수 FIR 연산을 수행하여 출력 스트림을 생성해야 합니다.

**6. 계수 (Coefficient) 비트 폭 및 값**

계수는 **16-bit signed fixed-point** 형식을 사용합니다.

* Coefficient width: **16-bit**
* Signed: **2's complement**
* Fixed-point format: **Q1.15**
* Coefficient range: `-1.0 ≤ h[k] < 1.0`
* 계수는 RTL 내부에 parameter 또는 ROM 형태로 저장할 수 있어야 합니다.
* v1.0에서는 runtime coefficient update 기능은 요구하지 않습니다.
* 실제 coefficient 값은 최종 FIR tap specification에서 별도로 전달합니다.

**7. 필터 탭 (Tap) 수**

v1.0의 FIR filter는 **64 taps**로 고정합니다.

* Number of taps: **64**
* Filter order: **63**
* 입력 샘플은 signed fixed-point 데이터로 처리합니다.
* 64개의 coefficient를 이용하여 하나의 출력 샘플을 계산합니다.
* Tap 수는 향후 parameterization을 고려하여 RTL 구조상 확장 가능하도록 작성하되, v1.0 sign-off configuration은 64 taps로 고정합니다.

**8. 파이프라인 구조**

본 IP는 **fully pipelined MAC datapath**를 사용합니다.

목표는 FIR 연산의 critical path를 단일 cycle에 몰아넣지 않고 pipeline stage로 분할하여 높은 Fmax를 확보하는 것입니다.

* Architecture: **pipelined FIR MAC**
* Input throughput: **1 sample/cycle**
* Target initiation interval: **II = 1**
* 목표 clock frequency: **250 MHz**
* Output latency: 구현 결과에 따라 결정하되, 고정된 pipeline latency를 가져야 합니다.
* `TVALID/TREADY` backpressure가 발생하더라도 데이터 순서가 보존되어야 합니다.
* Pipeline 내부의 valid propagation을 명확하게 정의해야 합니다.
* Reset 이후 pipeline에 stale data가 출력되지 않아야 합니다.

단순히 Fmax를 높이기 위해 throughput을 희생하는 구조는 허용하지 않습니다. 본 IP의 기본 요구사항은 **1 sample/cycle sustained throughput**입니다.

## 무엇을 짓기 전인가

AXI4-Stream 기반 64탭 고정계수 실시간 FIR 필터 IP

## 찾아본 질의

- `FIR architecture low power CMOS`
- `FIR high speed design`
- `FIR high resolution design`
- `엣지추론 FIR ASIC power reduction`
- `AXI architecture low power CMOS`
- `AXI high speed design`
- `AXI high resolution design`
- `엣지추론 AXI ASIC power reduction`

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

- 고속(250 MHz) 타이밍 제약 만족 실패로 인한 STA(Static Timing Analysis) 타이밍 비참조(Timing Violation)
- 파이프라인 단계 수와 AXI4-Stream 핸드셰이크(TVALID/TREADY) 제어 로직의 불일치로 인한 데이터 오염 또는 유실

---
_이 파일은 `house/arch.py` 가 틀만 만든 것이다. 표를 채우는 것은 사람이나
`!연구` 기관의 몫이고, **채우기 전에는 RTL 을 짓지 않는다.**_
