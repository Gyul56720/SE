---
title: "Cost effective LLM inference solution using SK hynix's AiM (Accelerator-in-Memory)"
source_paper: "[[Cost effective LLM inference solution using SK hynixs AiM Accelerator-in-Memory (2023)]]"
tags: [math-concept, paper-pipeline]
---

# Cost effective LLM inference solution using SK hynix's AiM (Accelerator-in-Memory) -- 수학/구조 정리

> 원 논문: [[Cost effective LLM inference solution using SK hynixs AiM Accelerator-in-Memory (2023)]]

## 핵심 공식 (수치 포함)
### 총 소유 비용 (TCO, Total Cost of Ownership)
$$ TCO \approx \text{CapEx} + 3 \times \text{OpEx} $$

- 의미: 초기 자본 지출(CapEx)과 3년 동안의 운영 비용(OpEx)을 합산하여 대규모언어모델(LLM) 인프라 구축 및 운영의 전체 비용을 추정하는 수식입니다.
- 등장 맥락: 생성형 AI 서비스의 유지가 시간이 지날수록 비용이 증가함을 설명하고, 인프라 비용 효율성을 평가하기 위해 도입되었습니다.

### 행렬-행렬 곱셈 (GEMM)
$$ C = \alpha AB + \beta C $$

- 의미: 두 개의 2차원 행렬 A와 B를 곱하여 결과 행렬 C를 생성하는 연산입니다.
- 등장 맥락: 트랜스포머 모델의 입력 토큰 처리(Prompt) 단계에서 사용되며, 데이터 재사용성이 높아 연산 집중적(compute-bound) 특성을 보입니다.
- 수치 대입 예: 입력 단어 수 9개 처리 시 사용됨

### 행렬-벡터 곱셈 (GEMV)
$$ y = \alpha Ax + \beta y $$

- 의미: 행렬 A와 벡터 x의 곱셈으로, LLM의 디코더에서 자가회귀(autoregressive) 방식으로 토큰을 하나씩 생성할 때 핵심적으로 수행되는 연산입니다.
- 등장 맥락: 응답 생성(Response) 단계에서 주로 발생하며, 낮은 산술 강도와 방대한 메모리 읽기로 인해 메모리 대역폭 한계(memory BW-bound)를 유발합니다.
- 수치 대입 예: 출력 단어 수 261개 생성 시 모델 데이터 Read 261회 발생

### GPU 시스템 처리 시간 추정
$$ T_{\text{proc}} = \frac{\text{Model Size}}{\text{Bandwidth}} $$

- 의미: 모델 전체 크기를 메모리 대역폭으로 나누어 단일 토큰 또는 전체 응답 생성 시 소요되는 처리 시간을 구하는 수식입니다.
- 등장 맥락: SOTA GPU 시스템(80GB, 3TB/s) 환경에서 350GB 크기의 모델을 처리할 때의 병목 현상을 정량적으로 증명하기 위해 사용되었습니다.
- 수치 대입 예: Model Size = 350 GB, Bandwidth = 15 TB/s 일 때 1 token 처리 시간은 350GB / 15TB/s = 23 mSec, 261 token 처리 시간은 6.0 Sec

### GPU 활용률 및 성능 효율
$$ E_{\text{perf}} = \frac{\text{Achieved Performance}}{\text{Peak Performance}} $$

- 의미: 최신 GPU의 이론적 최대 성능 대비 실제 LLM 추론(GEMV 중심)에서 달성되는 성능의 비율을 측정합니다.
- 등장 맥락: SOTA GPU에서 HBM을 사용할 때 인프라가 극도로 낮은 효율(0.3%)로 동작함을 보여주어 PIM 아키텍처 도입의 정당성을 부여합니다.
- 수치 대입 예: Peak 990 TFLOPS, Achieved 3 TFLOPS 일 때 3 TFLOPS / 990 TFLOPS = 0.3%

## 아키텍처 구조
### GDDR6-AiM 다이 (Die)
- 구조: 16개의 뱅크(Bank 0 ~ 15) 내부에 각각 독립된 처리 유닛(PU, Processing Unit)이 배치되어 칩 내부에서 동시 다발적인 연산이 가능하도록 설계된 True All-Bank Parallelism 구조입니다.
- 역할: 메모리 셀 내부에서 대규모 GEMV 연산을 병렬로 처리하여 데이터 이동을 최소화하고 성능을 극대화합니다.
- 규격 수치: Memory Density: 4Gb, 조직: X16, IO Data rate: 16 Gbps/pin, 외부 대역폭: 32 GB/s, 동작 속도: 1 GHz, 내부 대역폭: 512 GB/s, 처리량: 512 GFLOPS, 수치 정밀도: BF16

### AiMX (AiM-centric Accelerator) 카드
- 구조: 호스트 인터페이스(PCIe Gen3 x8x8), 2개의 FPGA(Xilinx Virtex Ultrascale+ VU9P) 제어 허브, 그리고 16개의 GDDR6-AiM 패키지가 다중화(Multicast Interconnect) 방식으로 연결된 스케일아웃 시스템 구조입니다.
- 역할: 여러 개의 AiM 패키지를 통합 제어하여 대규모 LLM 추론을 위한 고성능·저비용 시스템을 구성합니다.
- 규격 수치: Capacity: 16 GB, Bandwidth: 170 GB/s (@2.67Gbps), 폼팩터: FHFL

### AiM 제어 허브 (ACH, AiM-Control Hub)
- 구조: FPGA 기반으로 구현되었으며, 인스턴스 시퀀서(Instruction Sequencer), ALU, C2C Router, 멀티캐스트 인터커넥트로 구성되어 있습니다.
- 역할: SoftMax, Layer Norm 등 AiM에서 처리하기 번거롭거나 유연성이 요구되는 소규모 연산을 유연하게 처리합니다.

### 하이브리드 추론 시스템 (GPU + AiMX)
- 구조: 입력 토큰 처리를 담당하는 GPU 카드 군과 응답 토큰 생성을 담당하는 AiMX 카드 군이 상호 연동되는 이종 시스템 구조입니다.
- 역할: 컴퓨팅 집약적인 프롬프트 단계는 GPU로 처리하고, 메모리 집약적인 응답 생성 단계는 AiMX로 처리하여 전체 LLM 추론 효율을 극대화합니다.

## 핵심 개념 설명
- **메모리 대역폭 병목 (Memory Bandwidth Bound)**: 프로세서의 연산 능력이 아무리 뛰어나도 메모리에서 데이터를 가져오는 속도가 느리면 전체 속도가 메모리 전송 속도에 의해 결정되는 현상입니다. LLM의 GEMV 연산은 매번 엄청난 양의 가중치(Weight)를 메모리에서 읽어와야 하므로 이 병목 현상이 극심해집니다.
  - 선행 개념: 산술 강도(Arithmetic Intensity), Roofline 모델
- **프로세싱 인 메모리 (PIM, Processing-in-Memory)**: 데이터를 메모리에서 프로세서로 가져와서 연산하던 기존 방식에서 벗어나, 메모리 칩 내부(뱅크 내부)에 연산 장치(PU)를 직접 집어넣어 데이터 이동을 최소화하고 병렬 처리 성능을 극대화하는 기술입니다.
  - 선행 개념: DRAM 구조, 뱅크 병렬성
- **프롬프트 단계 vs 응답 생성 단계 (Prompt vs Response Stage)**: 프롬프트 단계는 입력 단어들을 한꺼번에 처리하므로 연산 집약적(Computing-intensive)이며 모델 읽기가 단 1회 발생합니다. 반면 응답 생성 단계는 토큰을 하나씩 순차적으로 생성하므로 매번 모델 전체를 읽어야 하여 극도로 메모리 집약적(Memory-intensive)입니다.
  - 선행 개념: 자가회귀(Autoregressive) 생성 방식

## 사용 방법론
1. LLM 추론 요청이 들어오면 프롬프트(입력 토큰) 단계는 GPU 시스템을 통해 병렬로 고속 처리합니다. 2. 응답 생성 단계로 넘어가면 자가회귀 방식으로 토큰을 하나씩 생성하므로 메모리 대역폭이 극도로 중요해집니다. 3. 이 단계에서 연산을 SK hynix AiMX 카드로 오프로딩합니다. 4. GDDR6-AiM 내부의 16개 뱅크 PU를 활용하여 칩 내부 고대역폭(512 GB/s)으로 GEMV 연산을 수행합니다. 5. SoftMax 및 Layer Norm 등 비선형 연산이나 소규모 유연성 연산은 AiM Control Hub(ACH)에서 처리하여 최종 출력을 완성합니다.

## 근접 개념 -- 같이 접근하면 좋은 다른 수학
- **Roofline 모델** (성능 분석 방법론)
  - 연관 이유: 하드웨어의 연산 성능 한계와 메모리 대역폭 한계를 2차원 그래프로 표현하여 LLM 추론이 왜 메모리 바운드인지 증명할 때 사용됩니다.
  - 파고들 방향: 컴퓨터 구조 교재의 'Roofline Model and Arithmetic Intensity' 챕터
- **시스톨릭 배열 (Systolic Array)** (대체 하드웨어 구조)
  - 연관 이유: GEMM 연산과 같은 행렬 곱셈을 가속하기 위해 TPU나 GPU 등에서 주로 사용하는 2차원 프로세서 그리드 구조로, AiM의 내부 PU 구조와 비교하여 이해하기 좋습니다.
  - 파고들 방향: Google TPU 아키텍처 관련 논문 및 고성능 컴퓨팅 구조
- **대역폭 한계 GPU 가속기 (예: NVIDIA H100 / A100)** (비교 대상 아키텍처)
  - 연관 이유: 논문에서 SOTA GPU 시스템의 한계(0.3% 활용률)를 지적하며 PIM의 필요성을 역설하는 직접적인 배경이 됩니다.
  - 파고들 방향: NVIDIA H100 Whitepaper의 HBM3 대역폭 및 Tensor Core 구조
- **근사 연산 및 룩업 테이블 (Lookup Table, LUT)** (응용 함수 구현 방식)
  - 연관 이유: AiM이 Sigmoid, Tanh, GELU 등 다양한 활성화 함수를 효율적으로 지원하기 위해 사용하는 내부 하드웨어 구현 기법입니다.
  - 파고들 방향: 디지털 신호 처리(DSP) 및 하드웨어 함수 근사화 기법
