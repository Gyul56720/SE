---
title: "Benchmarking Large Language Models for Automated Verilog RTL Code Generation"
source_paper: "[[Benchmarking Large Language Models for Automated Verilog RTL Code Generation (2023)]]"
tags: [math-concept, paper-pipeline]
---

# Benchmarking Large Language Models for Automated Verilog RTL Code Generation -- 수학/구조 정리

> 원 논문: [[Benchmarking Large Language Models for Automated Verilog RTL Code Generation (2023)]]

## 핵심 공식 (수치 포함)
### 토큰 다음 단어 확률 분포 (Next-Token Prediction)
$$ P(w_t \mid w_1, w_2, \dots, w_{t-1}) $$

- 의미: 주어진 이전 토큰 시퀀스(프롬프트 또는 생성된 코드)를 바탕으로 어휘 사전에서 다음 토큰 w_t가 등장할 확률 분포를 의미합니다.
- 등장 맥락: 트랜스포머 기반 대형 언어 모델(LLM)이 Verilog 코드나 자연어 프롬프트를 입력받아 순차적으로 다음 코드 토큰을 완성해 나가는 근본적인 확률적 생성 메커니즘을 설명하기 위해 등장합니다.
- 수치 대입 예: CodeGen-16B 모델에서 컨텍스트 길이 2048 토큰과 어휘 사전 내 수만 개의 토큰에 대해 매 스텝마다 확률 분포를 계산하여 다음 Verilog 토큰을 예측합니다.

### Pass@k 평가 지표
$$ \text{Pass}@k := \mathbb{E}_{Problems} \left[ 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}} \right] $$

- 의미: n개의 생성된 후보 샘플 중 적어도 하나가 기능 테스트를 통과할 확률을 측정하는 지표입니다.
- 등장 맥락: LLM이 각 Verilog 코딩 문제에 대해 n개의 후보를 생성하고, 이 중 기능 테스트 벤치를 통과한 비율을 정량적으로 평가하기 위해 사용되었습니다.
- 수치 대입 예: 총 17개의 문제 세트와 문제당 n=10개의 샘플을 생성하여 테스트를 수행할 때(총 k = 17 * 10 = 170), fine-tuned CodeGen-16B 모델은 41.9%의 Pass@k를 달성했습니다.

### Jaccard 유사도 (중복 제거용)
$$ J(A, B) = \frac{|A \cap B|}{|A \cup B|} $$

- 의미: 두 개의 문서(Verilog 파일) 집합 A와 B의 교집합 크기를 합집합 크기로 나눈 값으로, 파일 간의 유사성을 정량화합니다.
- 등장 맥락: Google BigQuery를 통해 수집한 2.8만 개 이상의 GitHub Verilog 저장소에서 MinHash와 함께 사용되어 중복된 소스코드 파일을 필터링하고 정제하는 데 쓰였습니다.
- 수치 대입 예: 두 개의 300MB 규모 Verilog 소스 파일 집합 간의 단어/토큰 공통 비율을 비교하여 유사도가 임계값를 넘는 중복 파일을 제거했습니다.

## 아키텍처 구조
### CodeGen-16B 트랜스포머 아키텍처
- 구조: 34개의 레이어, 256의 헤드 디멘션(embedding size), 2048의 최대 컨텍스트 길이를 가지며, 다중 GPU 환경에서 DeepSpeed를 이용해 모델 병렬화 및 옵티마이저 셔딩을 수행하는 구조입니다.
- 역할: 대규모 Verilog 소스코드와 텍스트 코퍼스로 파인튜닝되어, 자연어 주석 및 프롬프트로부터 구문 및 기능적으로 올바른 Verilog RTL 코드를 생성하는 주력 LLM 역할
- 규격 수치: Layers: 34, Heads: 24, Head Dimension/Embedding: 256, Context Length: 2048, 16-bit precision parameter memory: 30 GB (총 필요 GPU 메모리 약 250 GB)

### Megatron-LM-355M 아키텍처
- 구조: 24개의 트랜스포머 레이어와 16개의 어텐션 헤드로 구성된 비교적 소규모의 언어 모델 구조입니다.
- 역할: 매개변수 크기에 따른 성능 차이를 비교하기 위한 베이스라인 모델 중 하나로 활용됨
- 규격 수치: Layers: 24, Heads: 16, Embedding size: 64, Context Length: 1024

### Icarus Verilog 컴파일 및 평가 파이프라인
- 구조: LLM이 생성한 텍스트 출력을 end 및 endmodule 키워드로 자른 뒤, Icarus Verilog 컴파일러(v11.0)를 통해 구문 검사를 수행하고, 별도로 설계된 테스트 벤치와 시뮬레이션을 통해 기능적 정당성을 판별하는 모듈형 파이프라인입니다.
- 역할: 생성된 Verilog 코드가 문법적으로 컴파일되는지와 의도된 하드웨어 동작을 정확히 수행하는지를 자동으로 판정
- 규격 수치: Compiler: Icarus Verilog v11.0, Max tokens per completion: 300 (J1-Large는 256), 문제 세트 개수: 17개

## 핵심 개념 설명
- **RTL (Register-Transfer Level) 코드 생성**: 하드웨어의 동작을 레지스터 간의 데이터 이동과 조합 논리 회로로 기술하는 Verilog 코드를 인공지능이 자연어 주석이나 프롬프트로부터 자동으로 작성하는 기술입니다.
  - 선행 개념: 디지털 논리회로 기초 (조합/순차 회로, FSM) 및 Verilog 언어 문법
- **파인튜닝 (Fine-tuning)**: 이미 방대한 일반 텍스트와 코드로 사전 학습된 LLM에, 특화된 도메인 데이터셋(여기서는 GitHub와 교재에서 수집한 400MB 규모의 Verilog 코드)을 추가로 학습시켜 해당 분야에 최적화하는 과정입니다.
  - 선행 개념: 전이 학습(Transfer Learning) 개념과 경사 하강법 기반 모델 최적화
- **샘플링 온도 (Sampling Temperature, t)**: 모델이 다음 토큰을 선택할 때 확률 분포의 뾰족한 정도를 조절하는 매개변수입니다. 낮은 온도(t=0.1)에서는 가장 확률이 높은 토큰을 주로 선택하여 안정적이고 정확한 코드를 만들고, 높은 온도에서는 창의적이지만 위험한 코드를 생성합니다.
  - 선행 개념: 확률론 및 소프트맥스(Softmax) 함수

## 사용 방법론
1. 자연어 프롬프트 설계: 하드웨어의 기능과 입출력 인터페이스를 설명하는 주석, 모듈 헤더, 그리고 점진적으로 상세해지는 프롬프트(Low, Medium, High 수준)를 작성합니다. 2. LLM 쿼리 및 샘플링: 파인튜닝된 CodeGen-16B 모델에 프롬프트를 입력하고, 최적의 성능을 보이는 샘플링 온도(t=0.1)와 프롬프트당 생성 수(n=10)를 설정하여 다수의 코드 후보를 생성합니다. 3. 구문 및 컴파일 검증: 생성된 텍스트를 end 및 endmodule 기준으로 자른 후, Icarus Verilog v11.0 컴파일러를 통해 구문 오류가 있는 코드를 필터링합니다. 4. 기능 테스트 벤치 검증: 컴파일을 통과한 코드를 대상 문제별 전용 테스트 벤치 시뮬레이션에 통과시켜 코너 케이스 및 기능적 정확성을 최종 평가합니다.

## 근접 개념 -- 같이 접근하면 좋은 다른 수학
- **High-Level Synthesis (HLS)** (대체 접근 방식)
  - 연관 이유: C나 C++ 같은 고수준 소프트웨어 언어로부터 하드웨어 설계(Verilog/VHDL)를 자동 생성한다는 점에서 LLM 기반 코드 생성과 목적이 유사합니다.
  - 파고들 방향: Vivado HLS 등 상용 HLS 툴의 동작 원리 및 효율성 트레이드오프 연구
- **강화학습 기반 프로그램 합성 (Program Synthesis with RL)** (유사 방법론)
  - 연관 이유: 컴파일러나 테스트 벤치의 피드백(보상)을 이용해 LLM의 코드 생성 능력을 극대화하는 발전된 학습 구조입니다.
  - 파고들 방향: RLHF(Reinforcement Learning from Human Feedback) 및 코드 생성 도메인 적용 사례
- **AST (Abstract Syntax Tree) 기반 코드 분석** (보완 기술)
  - 연관 이유: 단순 문자열 매칭이나 컴파일러 에러 외에, 생성된 Verilog 코드의 구조적 유효성을 심층적으로 검사할 때 활용될 수 있습니다.
  - 파고들 방향: 컴파일러 이론 및 소스코드 AST 순회 알고리즘
- **정적 분석 및 하드웨어 보안 검증 (Static Analysis for HDL)** (응용 분야 확장)
  - 연관 이유: LLM이 자동으로 생성한 Verilog 코드에 내재된 하드웨어 취약점이나 버그를 사전에 탐지하는 기술과 직결됩니다.
  - 파고들 방향: 하드웨어 트로이 및 보안 취약점 탐지 툴 연구
