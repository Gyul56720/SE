---
title: "Model Parallelism: Tensor/Pipeline/Data Parallelism"
domain: 03_Furiosa-LLM런타임
tags: [project_furiosa, 이론서, 03_Furiosa-LLM런타임]
killing_fact: "\text{tensor\_parallel\_size} \times \text{pipeline\_parallel\_size} \times \text{data\_parallel\_size} = \text{전체 PE 수}"
sources: ['https://developer.furiosa.ai/v2026.3.0/en/furiosa_llm/model-parallelism.html']
---

# 02. Model Parallelism: Tensor/Pipeline/Data Parallelism

## 1. 왜 알아야 하는가

대형 언어 모델(LLM)은 단일 NPU 디바이스의 메모리 용량을 초과하는 경우가 많기 때문에, 모델을 여러 디바이스에 나누어 실행하는 모델 병렬화 기법이 필수적입니다. 실무와 면접에서는 하드웨어 자원을 효율적으로 활용하고 통신 오버헤드를 최소화하기 위해 Tensor/Pipeline/Data Parallelism의 구조와 제약 조건을 정확히 이해하는 것이 매우 중요합니다. 특히 FuriosaAI SDK 환경에서 하드웨어 스펙과 병렬화 파라미터 간의 정합성을 맞추지 않으면 시스템이 정상 동작하지 않으므로 인과관계를 명확히 알아야 합니다.

## 2. 정의와 구조

### 모델 병렬화(Model Parallelism)의 개요
FuriosaAI LLM 런타임은 대형 모델을 효율적으로 처리하기 위해 세 가지 병렬화 기법을 지원합니다. 각 기법은 모델을 나누는 방식과 목적이 다릅니다.

### 1. Tensor Parallelism (TP)
각 레이어를 특정 차원을 따라 여러 청크로 분할하여, 각 디바이스가 전체 레이어의 1/N만 보유하도록 합니다. 이를 통해 가중치, KV 캐시, 활성화 메모리 요구량이 감소하며, 단일 디바이스 메모리 용량을 넘는 대형 모델을 지원하고 배치 및 시퀀스를 확대할 수 있습니다. 다만, TP 정도가 너무 높으면 통신 오버헤드가 발생하여 성능 저하를 초래합니다.

### 2. Pipeline Parallelism (PP)
모델을 수직으로(일반적으로 레이어 수준에서) 여러 디바이스에 분할하여 각 디바이스가 모델의 다른 부분을 순차 처리합니다. 메모리 절감과 처리량 증대 효과가 있지만, 지연 시간이 증가하는 대가가 따릅니다.

### 3. Data Parallelism (DP)
동일한 모델 복제본을 여러 디바이스에 배치하고 서로 다른 데이터 배치를 나누어 처리합니다.

### 설정 및 핵심 제약 조건
- 설정 인터페이스: ArtifactBuilder API의 `tensor_parallel_size`, `furiosa-llm serve`의 `--pipeline-parallel-size`(`-pp`), `--data-parallel-size`(`-dp`). 또한 LLM, LLMEngine, AsyncLLMEngine에서도 지정할 수 있습니다.
- 제약 조건 (2026.3.0 릴리스 기준): `tensor_parallel_size` 파라미터는 4 또는 8만 가능합니다.
- 핵심 규칙: `tensor_parallel_size x pipeline_parallel_size x data_parallel_size`의 곱은 머신의 전체 PE 수와 같아야 합니다.

## 3. 핵심 사실 (Killing Fact)

$$ \boxed{\ \text{tensor\_parallel\_size} \times \text{pipeline\_parallel\_size} \times \text{data\_parallel\_size} = \text{전체 PE 수}\ } $$

이 공식은 FuriosaAI 런타임에서 다중 디바이스/PE 환경을 구성할 때 반드시 만족해야 하는 하드웨어 자원 매핑의 기본 제약 조건입니다. 전체 PE 수와 병렬화 설정의 곱이 일치해야만 시스템이 각 PE에 정확하게 워크로드를 할당할 수 있습니다.

## 4. 핵심 설계 기법

### 기법 A: Tensor Parallelism (TP)

각 레이어를 특정 차원을 따라 여러 청크로 분할하여 각 디바이스가 전체 레이어의 1/N만 보유하게 동작합니다.

**왜 이렇게 설계했는가:** 단일 디바이스의 메모리 용량을 초과하는 대형 모델을 수용하고 가중치, KV 캐시, 활성화 메모리를 분산시키기 위해 이와 같이 설계되었습니다.

### 기법 B: Pipeline Parallelism (PP)

모델을 수직으로(일반적으로 레이어 수준) 여러 디바이스에 분할하여 각 디바이스가 모델의 다른 부분을 순차 처리합니다.

**왜 이렇게 설계했는가:** 메모리를 절감하고 처리량을 증대시키기 위해서이며, 각 디바이스가 파이프라인 스테이지를 나누어 맡는 구조를 취합니다.

### 기법 C: Data Parallelism (DP)

전체 시스템의 PE 조합 규칙에 따라 데이터 병렬 크기를 설정하여 동일한 모델 구조를 확장합니다.

**왜 이렇게 설계했는가:** 전체 PE 수와 TP, PP, DP의 곱이 정확히 맞아떨어지도록 하여 남는 자원 없이 병렬 처리를 극대화하기 위해 설계되었습니다.

## 5. 자주 하는 오해 / 주의할 점

처음 접할 때 `tensor_parallel_size`를 임의의 값(예: 1, 2, 16 등)으로 설정할 수 있다고 오해하기 쉽습니다. 하지만 2026.3.0 릴리스 기준 `tensor_parallel_size`는 반드시 4 또는 8만 가능하며, 세 병렬 크기의 곱이 머신의 전체 PE 수와 정확히 일치해야 한다는 제약을 놓치는 경우가 많습니다. 또한, 1개 RNGD 칩이 8개의 PE(64+1 슬라이스, 1개 예비)로 구성된다는 점을 고려하지 않고 카드 수와 PE 수를 혼동하는 실수를 주의해야 합니다.

## 6. 대표예제 (추론 연습)

### 예제 1

RNGD 카드 4개(각 카드당 8 PE, 총 32 PE)가 장착된 시스템에서 `tensor_parallel_size=8`, `pipeline_parallel_size=4`로 설정하려 할 때, 올바른 `data_parallel_size`를 구하고 제약 조건을 만족하는지 확인하시오.

**풀이:**

1단계 — 전체 PE 수를 확인한다. 카드 4개 x 카드당 8 PE = 총 32 PE이다. 2단계 — 병렬 크기 곱의 법칙식을 세운다. (tensor_parallel_size) x (pipeline_parallel_size) x (data_parallel_size) = 전체 PE 수 이므로, 8 x 4 x DP = 32이다. 3단계 — 방정식을 풀어 DP 값을 구한다. 32 x DP = 32 이므로 DP = 1이다.

**답: data_parallel_size = 1**

### 예제 2

총 32 PE가 있는 시스템에서 `tensor_parallel_size=4`, `pipeline_parallel_size=2`를 사용할 때, 제약 조건을 만족하는 `data_parallel_size` 값을 도출하시오.

**풀이:**

1단계 — 전체 PE 수가 32임을 인지한다. 2단계 — `tensor_parallel_size (4) * pipeline_parallel_size (2) * data_parallel_size (DP) = 32` 공식을 적용한다. 3단계 — 계산하면 8 * DP = 32 이므로 DP = 4가 된다.

**답: data_parallel_size = 4**

## 7. 유제 (면접 예상 질문)

1. RNGD 카드 4개(총 32 PE) 환경에서 `tensor_parallel_size=2`로 설정하여 모델을 구동하려고 할 때, 2026.3.0 릴리스 기준에서 이 설정이 실패하는 근본적인 이유는 무엇인가? *(힌트: 지원되는 `tensor_parallel_size`의 허용 값 범위를 확인해보세요.)*
2. GPT-OSS-120b 모델을 RNGD 카드 4장(총 32 PE) 환경에서 실행할 때, `tensor_parallel_size=8`, `pipeline_parallel_size=4`, `data_parallel_size=1` 조합 외에 모델 카드와 공식 문서의 제약 조건을 동시에 만족할 수 있는 다른 TP/PP/DP 조합을 찾아보시오. *(힌트: TP는 4 또는 8만 가능하며, 세 값의 곱은 32여야 합니다.)*
3. Tensor Parallelism을 무조건 높게 설정하면 메모리 분산에는 유리하지만 성능 상에 치명적인 부작용이 발생할 수 있습니다. 그 이유는 무엇인가? *(힌트: 분산된 디바이스 간의 데이터 교환 과정에서 발생하는 오버헤드를 생각해보세요.)*

## 8. 다음 챕터와의 연결

모델 병렬화를 통해 대형 모델을 여러 디바이스와 PE에 성공적으로 분산 배치한 이후에는, 실제 추론 요청을 효율적으로 스케줄링하고 처리하기 위한 런타임 엔진 및 서빙 아키텍처(LLMEngine / AsyncLLMEngine)의 동작 원리로 연결됩니다.
