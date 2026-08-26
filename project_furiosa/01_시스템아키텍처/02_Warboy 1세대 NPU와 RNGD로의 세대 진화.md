---
title: "Warboy 1세대 NPU와 RNGD로의 세대 진화"
domain: 01_시스템아키텍처
tags: [project_furiosa, 이론서, 01_시스템아키텍처]
killing_fact: "\text{Warboy Peak Performance: } 64 \text{ TOPS (INT8), Memory Bandwidth: } 66 \text{ GB/s}"
sources: ['http://developer.furiosa.ai/docs/latest/en/npu/warboy.html']
---

# 02. Warboy 1세대 NPU와 RNGD로의 세대 진화

## 1. 왜 알아야 하는가

Warboy 1세대 NPU와 차세대 NPU인 RNGD 간의 진화 과정을 이해하는 것은, AI 가속기 설계가 전통적인 2D 행렬 연산 및 CNN 중심에서 대규모 언어 모델(LLM) 및 멀티모달 처리를 위한 텐서 축약 프로세서(TCP) 아키텍처로 어떻게 전환되었는지 파악하기 위해 필수적입니다. 실무와 면접에서 아키텍처의 세대별 한계와 진화 방향(메모리 대역폭, 연산 정밀도, 코어 구조 등)을 명확히 설명할 수 있어야 하기 때문에 중요합니다.

## 2. 정의와 구조

### 1. Warboy 1세대 NPU의 아키텍처와 특징
Warboy는 이미지 분류, 객체 검출, OCR 등 CNN 모델 처리에 최적화된 고성능 AI NPU입니다. 5억 개의 트랜지스터와 $180\text{mm}^2$의 다이 면적을 가지며, 2.0 GHz의 클럭으로 동작합니다.
- **PE 구조**: 2개의 Processing Element(PE)로 구성되며, 각 PE는 32 TOPS의 성능을 제공하여 독립적으로 운영되거나 응답 시간을 최소화하기 위해 단일 PE로 융합(fused)될 수 있습니다.
- **메모리 및 대역폭**: 16 GB(최대 32 GB)의 LPDDR4X DRAM을 탑재하며, 피크 메모리 대역폭은 $66\text{GB/s}$입니다. 온칩 SRAM은 32MB를 제공합니다.
- **정밀도 및 지원 형식**: INT8 양자화 체계를 표준 지원하며, Post Training Quantization 도구를 통해 부동소수점 모델을 변환합니다. 모델 형식은 TFLite와 ONNX를 지원합니다.

### 2. RNGD로의 세대 진화
Warboy가 CNN 중심의 2D GEMM 기반(문서에 TCP라는 명시적 표현 없음) 및 INT8 고정 정밀도 연산에 최적화되었다면, RNGD는 텐서 축약(Tensor Contraction)을 하드웨어 기본 연산으로 삼는 TCP 아키텍처를 도입하여 LLM과 멀티모달 워크로드까지 지원하도록 진화했습니다.
- **스펙 비교**: RNGD는 TSMC 5nm 공정, 1.0 GHz, 256 TFLOPS(BF16)/512 TFLOPS(FP8)/1024 TOPS(INT4)를 지원하며, HBM3 48GB(대역폭 $1.5\text{TB/s}$), 256MB의 SRAM, 그리고 8개 PE와 64개 슬라이스를 탑재합니다. 반면 Warboy는 공정 노드가 문서에 명시되지 않았고, 2.0 GHz, 64 TOPS(INT8 전용), LPDDR4X 16-32GB($66\text{GB/s}$ 대역폭), 32MB SRAM, 2개의 PE로 구성됩니다.

## 3. 핵심 사실 (Killing Fact)

$$ \boxed{\ \text{Warboy Peak Performance: } 64 \text{ TOPS (INT8), Memory Bandwidth: } 66 \text{ GB/s}\ } $$

Warboy는 2개의 PE 각각 32 TOPS씩 총 64 TOPS의 INT8 성능과 66 GB/s의 LPDDR4X 대역폭을 제공하며, 이는 CNN 중심 워크로드 처리를 위한 1세대 아키텍처의 핵심 하드웨어 제약 및 성능 지표를 나타냅니다.

## 4. 핵심 설계 기법

### 기법 A: 독립 및 융합 PE 구조 (Independent & Fused PE)

Warboy는 2개의 PE가 각각 32 TOPS 성능을 내어 독립적으로 배포되거나, 응답 시간을 최소화하기 위해 단일 PE처럼 융합(fused)되어 동작할 수 있습니다.

**왜 이렇게 설계했는가:** 다양한 크기의 CNN 모델과 실시간 추론 요구사항에 맞춰 연산 유연성을 높이고 지연 시간을 최소화하기 위해서입니다.

### 기법 B: Depthwise/Group Convolution 최적화

하드웨어 수준에서 depthwise 및 group convolution 연산 경로를 최적화하여 CNN 모델 처리 효율을 극대화합니다.

**왜 이렇게 설계했는가:** 모바일 및 엣지 환경에서 자주 사용되는 경량 CNN 모델들의 연산 병목을 해결하기 위해서입니다.

### 기법 C: Post Training Quantization (PTQ)

학습이 완료된 부동소수점 모델을 INT8 양자화 체계로 변환하는 툴을 지원하여 가속기에서 효율적으로 실행할 수 있게 합니다.

**왜 이렇게 설계했는가:** 하드웨어 자원이 제한된 환경에서 메모리 사용량을 줄이고 연산 속도를 극대화하기 위해서입니다.

## 5. 자주 하는 오해 / 주의할 점

Warboy가 INT8 전용의 CNN 최적화 칩이라는 점을 간과하고, RNGD의 TCP(텐서 축약 프로세서) 아키텍처나 LLM/멀티모달 지원 능력이 Warboy에도 동일하게 적용된다고 오해하는 경우가 많습니다. 또한 Warboy 문서에는 공정 노드(예: TSMC 몇 nm인지)가 명시되어 있지 않으므로 임의로 공정 버전을 지어내지 않도록 주의해야 합니다.

## 6. 대표예제 (추론 연습)

### 예제 1

Warboy NPU를 사용하여 64 TOPS의 성능이 필요한 INT8 기반 객체 검출 모델을 구동하려고 합니다. 이때 2개의 PE를 어떻게 활용해야 하며, 메모리 대역폭 제약($66\text{GB/s}$) 속에서 응답 시간을 최소화하려면 어떤 설계적 고려가 필요한가요?

**풀이:**

1단계 — Warboy는 2개의 PE로 구성되어 있으며 각각 32 TOPS를 제공하므로, 64 TOPS를 달성하기 위해 2개의 PE를 단일 PE처럼 융합(fused)하여 배치합니다.
2단계 — LPDDR4X 메모리의 피크 대역폭이 $66\text{GB/s}$이므로, 메모리 바운드 연산이 발생하지 않도록 32MB 온칩 SRAM에 가중치와 중간 피처맵을 최대한 캐싱하여 대역폭 병목을 줄입니다.

**답: 2개의 PE를 융합(fused)하여 64 TOPS 성능을 내도록 배포하고, 32MB 온칩 SRAM을 활용해 66 GB/s 대역폭 한계를 극복합니다.**

### 예제 2

부동소수점으로 학습된 모델을 Warboy NPU에 배포하고자 할 때, 지원되는 정밀도와 모델 형식을 맞추기 위해 어떤 변환 과정이 필요한가요?

**풀이:**

1단계 — Warboy는 INT8 양자화 체계를 표준으로 지원하므로, 부동소수점 모델을 INT8로 변환해야 합니다.
2단계 — 공식 지원되는 'Post Training Quantization' 도구를 사용하여 모델을 변환하고, 지원 모델 형식인 TFLite 또는 ONNX 포맷으로 내보냅니다.

**답: Post Training Quantization 도구를 사용하여 부동소수점 모델을 INT8 정밀도의 TFLite 또는 ONNX 형식으로 변환합니다.**

## 7. 유제 (면접 예상 질문)

1. Warboy의 2개 PE가 독립적으로 운영되는 모드와 융합(fused)되어 운영되는 모드는 각각 어떤 유스케이스에 적합한가요? *(힌트: 응답 시간 최소화와 처리량(Throughput) 관점의 차이를 생각해보세요.)*
2. Warboy 1세대(INT8 CNN 최적화)에서 RNGD(TCP 아키텍처, BF16/FP8/INT4 지원)로 세대가 진화하면서 하드웨어 기본 연산 모델에 어떤 근본적인 변화가 생겼나요? *(힌트: 2D GEMM 기반과 다차원 텐서 직접 축약(Tensor Contraction)의 차이를 떠올려보세요.)*
3. Warboy 문서에 명시된 LPDDR4X 메모리의 대역폭과 SRAM 용량은 각각 얼마이며, 이들이 CNN 추론 성능에 미치는 영향은 무엇인가요? *(힌트: 근거 자료에 제시된 66 GB/s와 32MB 수치를 참고하세요.)*

## 8. 다음 챕터와의 연결

Warboy 1세대 NPU의 CNN 및 INT8 중심 아키텍처와 한계를 이해한 후에는, 이를 극복하기 위해 다차원 텐서 축약을 하드웨어로 직접 처리하는 RNGD의 TCP 아키텍처 및 세부 메모리 서브시스템(HBM3) 구조 분석으로 연결됩니다.
