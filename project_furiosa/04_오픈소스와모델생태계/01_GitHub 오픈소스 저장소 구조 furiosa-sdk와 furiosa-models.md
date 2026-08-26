---
title: "GitHub 오픈소스 저장소 구조: furiosa-sdk와 furiosa-models"
domain: 04_오픈소스와모델생태계
tags: [project_furiosa, 이론서, 04_오픈소스와모델생태계]
killing_fact: "\text{furiosa-sdk v0.9.0 (Commits: 1594) } \land \text{ furiosa-models v0.10.2 (Commits: 357)}"
sources: ['https://github.com/furiosa-ai/furiosa-sdk', 'https://github.com/furiosa-ai/furiosa-models']
---

# 01. GitHub 오픈소스 저장소 구조: furiosa-sdk와 furiosa-models

## 1. 왜 알아야 하는가

FuriosaAI NPU를 활용해 딥러닝 추론을 수행하거나 오픈소스 기반으로 모델을 커스터마이징하려면, SDK와 모델 저장소의 디렉토리 구조 및 구성 요소를 정확히 알아야 한다. 실무에서 컴파일러, 프로파일러, Python 바인딩 및 사전학습 모델의 위치를 파악하지 못하면 빌드 오류나 종속성 문제를 해결하기 어렵기 때문이다. 따라서 공식 GitHub 저장소인 furiosa-sdk와 furiosa-models의 물리적 구조와 역할을 명확히 이해해야 한다.

## 2. 정의와 구조

### furiosa-sdk와 furiosa-models의 개요 및 저장소 구조

furiosa-sdk와 furiosa-models는 FuriosaAI NPU를 활용하기 위한 핵심 오픈소스 저장소이다. 이 저장소들이 다루는 범위와 실제 컴파일러 내부 알고리즘의 관계를 명확히 구분해야 한다.

#### 1. furiosa-sdk 저장소 구조와 목적
- **목적**: FuriosaAI NPU 칩을 이용한 딥러닝 추론(deep-neural network inference using FuriosaAI NPU chips)을 지원하기 위해 컴파일러, 프로파일러, CLI 도구, Python 바인딩을 제공한다.
- **주요 디렉토리 및 파일**: 최상위 구조는 `.github/`, `.prow/`, `jenkins/`, `kubernetes/`, `tekton/` (이상 CI/CD 관련), `cpp/` (C++ 코드), `python/` (Python 코드), `docs/`, `examples/`, `tests/`, `Dockerfile`, `README.md`, `LICENSE.txt` (Apache-2.0), `bors.toml`, `CHANGELOG.md`로 구성된다.
- **메타데이터**: 언어는 Python과 C++을 함께 사용하며, 활성 상태(archived 아님, deprecated 문구 없음)이고 총 커밋 수는 1,594개, 최신 릴리스는 v0.9.0이다.

#### 2. furiosa-models 저장소 구조와 포함 모델
- **목적**: FuriosaAI NPU를 위한 공개 모델 동물원(public model zoo)으로, 학습 및 데모용 사전학습·양자화 모델을 제공한다. ONNX 및 tflite 표준을 따르므로 CPU/GPU에서도 실행할 수 있으며, NPU용 최적화 전후처리 유틸리티와 컴파일러 설정을 포함한다.
- **주요 디렉토리 및 파일**: `.dvc`, `.github/workflows`, `docker/`, `docs/`, `licenses/`, `furiosa/models` (핵심 코드), `tekton/`, `tests/`, `pyproject.toml`, `Makefile`로 구성된다.
- **포함 모델 목록**: 이미지 분류(ResNet50, EfficientNetB0, EfficientNetV2-S), 물체 감지(SSDMobileNet, SSDResNet34, YOLOv5M/L), 자세 추정(YOLOv7w6Pose)을 포함한다.
- **메타데이터**: 최신 릴리스는 v0.10.2(2024-05-29)이며, 총 커밋 수는 357개, archived/deprecated 문구는 원문에서 확인되지 않는다. 이 저장소들은 Warboy(1세대, INT8/ONNX/TFLite 중심) 시대의 산물로 보이며, RNGD/Furiosa-LLM 관련 코드는 이 두 저장소에 존재하지 않고 별도의 `furiosa-llm` 패키지/컨테이너 이미지로 배포된다.

#### 3. 공개 저장소 코드와 컴파일러 내부 구조의 관계
- **한계점 명시**: `furiosa-sdk` 저장소가 공개하는 것은 `cpp/`(컴파일러·런타임 C++ 구현으로 추정)와 `python/`(바인딩) 구조뿐이다.
- **근거 자료에 명시되지 않은 부분**: ISCA 2024 논문 "TCP"에 기술된 5단계 컴파일러 파이프라인이나 마이크로아키텍처 세부 사항의 실제 구현 코드는 이 저장소의 공개 파일 목록만으로는 확인되지 않는다. 컴파일러의 스케줄링 알고리즘이나 커맨드 생성 로직이 저장소의 어느 파일에 있는지는 근거 자료에 명시되지 않는다.

## 3. 핵심 사실 (Killing Fact)

$$ \boxed{\ \text{furiosa-sdk v0.9.0 (Commits: 1594) } \land \text{ furiosa-models v0.10.2 (Commits: 357)}\ } $$

두 공개 저장소의 버전과 커밋 수는 각 저장소가 가진 역사적 산물(Warboy 시대 중심의 SDK 및 모델 동물원)과 활성 상태를 나타내는 가장 핵심적인 스펙 수치이다.

## 4. 핵심 설계 기법

### 기법 A: Python 및 C++ 혼합 구조

furiosa-sdk 내부에 C++ 코드(cpp/)와 Python 코드(python/)를 함께 배치하여 컴파일러 및 런타임의 성능 요구사항과 사용자 편의성을 동시에 만족시킨다.

**왜 이렇게 설계했는가:** 고성능 연산 및 하드웨어 제어는 C++로 처리하고, 사용자 인터페이스와 바인딩은 Python으로 제공하기 때문에 두 언어를 혼합하여 설계하였다.

### 기법 B: 표준 포맷(ONNX/tflite) 기반 모델 제공

furiosa-models는 ONNX 및 tflite 표준을 따르는 사전학습·양자화 모델을 제공하여 NPU뿐만 아니라 CPU/GPU에서도 실행할 수 있도록 지원한다.

**왜 이렇게 설계했는가:** 다양한 하드웨어 환경에서의 호환성을 높이고 NPU 최적화 전후처리를 용이하게 적용하기 위해서이다.

### 기법 C: DVC 기반 데이터 관리

furiosa-models 저장소 내에 .dvc 디렉토리를 포함하여 대용량 모델 가중치와 데이터를 관리한다.

**왜 이렇게 설계했는가:** 대용량 모델 파일을 Git 저장소 직접 관리가 아닌 버저닝 도구를 통해 효율적으로 추적하기 위해서이다.

### 기법 D: 철저한 CI/CD 파이프라인 구축

양쪽 저장소 모두 .github/, .prow/, jenkins/, kubernetes/, tekton/ 등의 도구를 활용해 자동화된 빌드 및 테스트를 수행한다.

**왜 이렇게 설계했는가:** 다양한 버전의 컴파일러와 모델 코드의 안정성을 지속적으로 검증하기 위해서이다.

## 5. 자주 하는 오해 / 주의할 점

furiosa-sdk의 공개된 폴더 구조(cpp/, python/)만 보고 ISCA 2024 논문에서 다루는 5단계 컴파일러 파이프라인의 구체적인 소스 코드 파일 위치나 스케줄링 알고리즘의 구현 세부사항을 곧바로 알 수 있다고 오해하는 경우가 많다. 또한, furiosa-models 저장소에 최신 RNGD나 Furiosa-LLM 관련 코드가 포함되어 있을 것이라 혼동하기 쉽으나, 이 저장소들은 Warboy(1세대) 시대의 산물이며 LLM 관련 코드는 별도의 furiosa-llm 패키지/컨테이너 이미지로 배포된다는 점을 놓치지 말아야 한다.

## 6. 대표예제 (추론 연습)

### 예제 1

엔지니어 A가 furiosa-models 저장소에서 최신 LLM(Large Language Model) 실행 코드를 찾으려고 한다. 저장소의 최신 릴리스 버전과 파일 구조를 바탕으로 올바른 접근인지 판단하고 이유를 설명하시오.

**풀이:**

1단계 — furiosa-models 저장소의 특성 확인: 근거 자료에 따르면 furiosa-models는 Warboy 시대의 산물이며 이미지 분류, 물체 감지, 자세 추정 모델을 포함하고 v0.10.2 버전을 가진다.
2단계 — RNGD 및 LLM 코드의 존재 여부 확인: RNGD/Furiosa-LLM 관련 코드는 이 두 저장소에 존재하지 않고 별도의 furiosa-llm 패키지/컨테이너 이미지로 배포된다.
3단계 — 결론 도출: 따라서 furiosa-models에서 LLM 코드를 찾는 것은 잘못된 접근이며, 별도의 패키지나 컨테이너를 확인해야 한다.

**답: 잘못된 접근이다. furiosa-models는 Warboy 시대의 전통적 비전 모델(ResNet, YOLO 등) 중심이며, LLM 관련 코드는 별도의 furiosa-llm 패키지나 컨테이너 이미지로 배포된다.**

### 예제 2

엔지니어 B가 furiosa-sdk 저장소의 소스 코드 구조를 분석하여 컴파일러의 스케줄링 알고리즘 구현 파일을 찾고자 한다. 공개된 저장소 정보만을 바탕으로 어떤 한계에 부딪히는지 설명하시오.

**풀이:**

1단계 — furiosa-sdk의 최상위 디렉토리 확인: cpp/와 python/ 폴더가 존재하며 컴파일러·런타임 C++ 구현 및 Python 바인딩으로 추정된다.
2단계 — 논문 기술 내용과 저장소의 괴리 확인: ISCA 2024 논문의 5단계 컴파일러 파이프라인이나 세부 마이크로아키텍처 구현 코드는 공개된 파일 목록만으로는 확인되지 않는다.
3단계 — 결론 도출: 스케줄링 알고리즘(ILP+유전 알고리즘 혼합 등)의 정확한 파일 위치는 저장소 원문만으로는 알 수 없다.

**답: furiosa-sdk는 cpp/와 python/ 디렉토리를 제공하지만, 내부 스케줄링 알고리즘이나 컴파일러 파이프라인의 구체적인 파일 위치는 공개 파일 목록만으로는 확인되지 않으므로 근거 자료에 명시되지 않는다는 한계가 있다.**

## 7. 유제 (면접 예상 질문)

1. furiosa-sdk 저장소가 지원하는 주요 프로그래밍 언어와 최상위 디렉토리 중 CI/CD 및 인프라 자동화를 위해 포함된 디렉토리들을 나열하시오. *(힌트: Python + C++ 언어 사용 여부와 .github/, kubernetes/ 등의 폴더를 참고할 것.)*
2. furiosa-models 저장소에 포함된 모델들의 표준 포맷은 무엇이며, 이로 인해 얻을 수 있는 장점은 무엇인가? *(힌트: ONNX 및 tflite 표준이라는 점과 CPU/GPU 실행 가능성을 연관지어 생각할 것.)*
3. furiosa-sdk와 furiosa-models 저장소가 주로 어떤 NPU 칩 세대를 겨냥한 산물로 평가되며, LLM 관련 코드는 어디에서 다뤄지는가? *(힌트: Warboy(1세대)와 별도의 furiosa-llm 패키지/컨테이너 이미지 언급을 확인할 것.)*

## 8. 다음 챕터와의 연결

이 챕터에서 파악한 furiosa-sdk와 furiosa-models의 오픈소스 저장소 구조와 디렉토리 배치를 바탕으로, 다음 챕터에서는 실제 소프트웨어 스택 전반에서 컴파일러와 런타임이 어떻게 연동되는지 상세히 다루게 된다.
