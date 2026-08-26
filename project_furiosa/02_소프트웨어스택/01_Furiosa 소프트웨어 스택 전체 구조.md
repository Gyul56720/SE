---
title: "Furiosa 소프트웨어 스택 전체 구조"
domain: 02_소프트웨어스택
tags: [project_furiosa, 이론서, 02_소프트웨어스택]
killing_fact: "\text{Total Layers} = 6"
sources: ['https://developer.furiosa.ai/v2026.3.0/en/overview/software_stack.html']
---

# 01. Furiosa 소프트웨어 스택 전체 구조

## 1. 왜 알아야 하는가

FuriosaAI 소프트웨어 스택은 NPU 하드웨어가 딥러닝 모델을 고성능으로 실행할 수 있도록 저수준 드라이버부터 응용 계층까지 체계적으로 연결하는 6개 레이어의 종합 인프라입니다. 이 구조를 정확히 이해해야 PyTorch나 LLM 모델을 NPU 상에서 최적의 성능으로 배포하고, 메모리 할당 및 스케줄링 문제를 효과적으로 디버깅할 수 있습니다. 실무와 면접에서는 하드웨어 가속기와 소프트웨어 스택 간의 유기적 동작 원리를 묻는 질문이 빈출되므로 반드시 숙지해야 합니다.

## 2. 정의와 구조

### Furiosa 소프트웨어 스택 6개 레이어 구조
FuriosaAI 소프트웨어 스택은 하드웨어를 직접 제어하는 최하층부터 모델 배포 및 응용 계층인 최상층까지 총 6개의 계층으로 구성되어 있습니다.

1. **커널 디바이스 드라이버 + 펌웨어 + PE 런타임(PERT)**: Linux 운영체제가 NPU를 인식하고 장치 파일로 노출할 수 있도록 하며, PERT는 저수준 API 제공 및 PE 리소스를 관리합니다.
2. **Furiosa 컴파일러**: 모델 그래프를 최적화하고 NPU용 실행 프로그램을 생성합니다. 그래프 레벨 최적화, 연산자 융합(operator fusion), 메모리 할당 최적화 등을 수행합니다.
3. **Furiosa 런타임**: 컴파일러가 생성한 실행 파일을 로드하고 NPU에서 실행합니다. NPU 프로그램 스케줄링, 메모리 할당, 다중 NPU 인터페이스를 담당합니다.
4. **Furiosa 모델 컴프레서**: 모델 보정(calibration)과 양자화를 위한 툴킷으로, BF16(W16A16), FP8(W8A8), INT8/INT4 등을 지원합니다.
5. **Furiosa-LLM**: Llama, GPT-J 등의 LLM을 위한 고성능 추론 엔진으로 vLLM 호환 API, PagedAttention, continuous batching을 지원합니다.
6. **Kubernetes 지원**: 쿠버네티스 클러스터가 FuriosaAI NPU를 인식하고 워크로드에 스케줄링할 수 있는 디바이스 플러그인을 제공합니다.

### 컴파일러 내부 5단계 동작 원리 (ISCA 2024 TCP 논문 기준)
Furiosa 컴파일러는 내부적으로 다음 5단계를 거쳐 바이너리를 생성합니다.
* 1단계 (Primitive Operator Conversion): 다양한 PyTorch 연산자를 소수의 primitive operator로 분해합니다.
* 2단계 (Tensor Kernel Generation): primitive operator들을 융합하여 데이터 재사용성을 극대화하는 커널을 생성합니다.
* 3단계 (Low-Level Operator Generation): 저수준 연산자로 변환하며 shape 불일치 시 bridge operator를 삽입합니다.
* 4단계 (Command Generation): 하드웨어 서브유닛에 대응하는 커맨드 리스트로 변환합니다.
* 5단계 (Binary Creation): 휴리스틱, ILP, 유전 알고리즘을 활용해 스케줄링 및 SRAM/RF 매핑을 수행합니다.

## 3. 핵심 사실 (Killing Fact)

$$ \boxed{\ \text{Total Layers} = 6\ } $$

FuriosaAI 소프트웨어 스택은 커널 드라이버부터 쿠버네티스 배포 계층까지 총 6개의 명확한 계층(Layer)으로 분리되어 있으며, 각 레이어는 하드웨어와 프레임워크 사이의 가교 역할을 담당하기 때문에 이 전체 레이어 구조를 파악하는 것이 시스템 아키텍처 이해의 핵심입니다.

## 4. 핵심 설계 기법

### 기법 A: Operator Fusion (연산자 융합)

Tensor Kernel Generation 단계에서 여러 primitive operator들을 클러스터링하여 하나의 커널로 묶습니다.

**왜 이렇게 설계했는가:** 중간 텐서의 메모리 입출력(memory round-trip)을 줄이고 데이터 재사용성을 극대화하기 위해 이 방식을 설계했습니다.

### 기법 B: PagedAttention 및 Continuous Batching

Furiosa-LLM 응용 계층에서 vLLM 호환 API를 통해 구현되어 대규모 언어 모델 추론을 처리합니다.

**왜 이렇게 설계했는가:** LLM 추론 시 발생하는 메모리 단편화를 방지하고 GPU/NPU 자원 활용률을 높이기 위해 채택되었습니다.

### 기법 C: 혼합 최적화 스케줄링 (Binary Creation)

휴리스틱(Heuristics), 정수 선형 계획법(ILP, Integer Linear Programming), 유전 알고리즘(Genetic Algorithms)을 조합하여 스케줄링합니다.

**왜 이렇게 설계했는가:** 복잡한 하드웨어 자원(SRAM, RF) 위에서 커맨드 실행 시점과 메모리 오버랩을 최적화하여 성능을 극대화하기 위함입니다.

### 기법 D: Bridge Operator 삽입

Low-Level Operator Generation 단계에서 인접 레이어 간 lowered shape 불일치가 발생할 때 브리지 연산자를 삽입합니다.

**왜 이렇게 설계했는가:** 서로 다른 연산자 간의 데이터 형태(shape) 차이로 인한 오류를 방지하고 원활한 데이터 흐름을 보장하기 위해 설계되었습니다.

## 5. 자주 하는 오해 / 주의할 점

처음 개발자들이 오해하는 지점은 Furiosa 소프트웨어 스택을 단순히 하나의 거대한 컴파일러 라이브러리로만 생각한다는 것입니다. 하지만 실제로는 커널 디바이스 드라이버 및 펌웨어를 포함하는 최하층(PERT)부터, 모델 컴프레서, LLM 전용 추론 엔진(Furiosa-LLM), 그리고 쿠버네티스 디바이스 플러그인에 이르는 6개의 독립적이면서도 유기적인 레이어로 구성된 종합 스택입니다. 또한 컴파일러가 단순히 코드 변환만 하는 것이 아니라 ISCA 논문에서 밝혀진 바와 같이 ILP와 유전 알고리즘 등 복잡한 최적화 기법을 거쳐 바이너리를 생성한다는 점을 놓치기 쉽습니다.

## 6. 대표예제 (추론 연습)

### 예제 1

PyTorch로 작성된 대형 언어 모델(LLM)을 Furiosa NPU에서 효율적으로 서빙하고자 합니다. 소프트웨어 스택의 어떤 레이어들을 거치게 되며, 각 레이어의 역할은 무엇인가요?

**풀이:**

1단계 — 응용 계층인 Furiosa-LLM을 통해 vLLM 호환 API와 PagedAttention 기반의 요청을 받습니다. 2단계 — Furiosa 모델 컴프레서를 통해 모델을 양자화(예: BF16 또는 FP8)합니다. 3단계 — Furiosa 컴파일러를 통해 모델 그래프를 최적화하고 NPU용 실행 프로그램으로 변환합니다. 4단계 — Furiosa 런타임을 통해 생성된 실행 프로그램을 로드하고 NPU 메모리에 할당하여 실행합니다. 5단계 — 최하층의 커널 디바이스 드라이버와 PERT를 통해 하드웨어 자원이 최종 구동됩니다.

**답: Furiosa-LLM -> 모델 컴프레서 -> 컴파일러 -> 런타임 -> 커널 드라이버/PERT의 5단계 흐름을 거쳐 실행됩니다.**

### 예제 2

Furiosa 컴파일러가 PyTorch 연산자를 NPU 바이너리로 변환할 때 거치는 5가지 주요 내부 동작 단계를 순서대로 설명하세요.

**풀이:**

1단계 — Primitive Operator Conversion 단계를 거쳐 PyTorch의 수많은 연산자들을 소수의 primitive operator로 분해합니다. 2단계 — Tensor Kernel Generation 단계를 통해 이들을 묶어 데이터 재사용성을 높이는 커널을 생성합니다. 3단계 — Low-Level Operator Generation 단계를 거쳐 저수준 연산자로 변환하며 shape 불일치 시 bridge operator를 삽입합니다. 4단계 — Command Generation 단계를 거쳐 하드웨어 서브유닛에 대응하는 커맨드 리스트로 변환합니다. 5단계 — Binary Creation 단계에서 ILP, 휴리스틱 등을 통해 스케줄링 및 자원 매핑을 수행하여 최종 실행 파일을 만듭니다.

**답: Primitive Operator Conversion -> Tensor Kernel Generation -> Low-Level Operator Generation -> Command Generation -> Binary Creation**

## 7. 유제 (면접 예상 질문)

1. Furiosa 소프트웨어 스택의 6개 레이어 중, Linux 운영체제가 NPU를 인식하고 장치 파일로 노출하는 역할을 담당하는 최하층 레이어의 구성 요소 3가지를 쓰시오. *(힌트: 근거 자료의 첫 번째 레이어 설명을 참고하세요 (드라이버, 펌웨어, 런타임).)*
2. Furiosa 컴파일러가 바이너리를 생성할 때(5단계) 최적화 스케줄링을 위해 사용하는 알고리즘 및 기법 3가지를 쓰시오. *(힌트: ISCA 2024 TCP 논문 기반 컴파일러 동작의 5단계 중 마지막 단계 설명에 등장합니다.)*
3. Furiosa-LLM 응용 계층이 LLM 추론을 고성능으로 처리하기 위해 지원하는 핵심 기능이나 API 3가지를 쓰시오. *(힌트: Furiosa-LLM 설명 부분에 등장하는 vLLM, PagedAttention 등을 떠올려 보세요.)*

## 8. 다음 챕터와의 연결

이 챕터에서 Furiosa 소프트웨어 스택의 전체적인 6개 레이어 구조와 컴파일러의 동작 원리를 파악했으므로, 다음 챕터에서는 이 스택의 핵심인 'Furiosa 컴파일러 및 최적화 기법'에 대해 더 깊이 있게 다루며 연산자 융합과 메모리 할당의 상세 메커니즘을 학습하게 됩니다.
