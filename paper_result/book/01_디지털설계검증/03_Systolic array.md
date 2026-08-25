---
title: "Systolic array"
domain: 01_디지털설계검증
tags: [book, concept, 01_디지털설계검증]
source_wikipedia: "https://en.wikipedia.org/wiki/Systolic_array"
referenced_repos: ['UCLA-VAST/AutoSA', 'abdelazeem201/Systolic-array-implementation-in-RTL-for-TPU', 'Dazhuzhu-github/systolic-array', 'hngenc/systolic-array', 'VCA-EPFL/FSA', 'ac-optimus/Convolution-using-systolic-arrays']
---

# 03. Systolic array

## 1. 왜 알아야 하는가

시스톨릭 배열(Systolic array)은 오늘날 NPU와 하드웨어 가속기에서 대규모 병렬 연산을 효율적으로 수행하기 위해 필수적으로 사용되는 아키텍처입니다. 폰 노이만 구조와 달리 외부 메모리나 캐시 접근 횟수를 줄이고 데이터가 처리 유닛 간에 직접 흐르도록 하여, 인공지능, 이미지 처리, 행렬 곱셈 등의 연산을 고성능으로 처리할 수 있게 합니다. 따라서 반도체 설계 및 검증 엔지니어라면 이 개념을 이해하고 하드웨어 구현 시 데이터 흐름과 동기화를 검증할 수 있어야 합니다.

## 2. 정의와 이론

병렬 컴퓨터 아키텍처에서 시스톨릭 배열은 셀(cell) 또는 노드(node)라고 불리는, 단단히 결합된 데이터 처리 유닛(DPU)들의 동종 네트워크입니다. 각 노드는 상위 이웃으로부터 받은 데이터의 함수로서 부분 결합 결과를 독립적으로 계산하고, 그 결과를 내부에 저장한 뒤 하위로 전달합니다. 이 구조는 파이프라인 형태의 웨이브 전파가 심장 순환계의 맥박과 유사하다 하여 '시스톨릭(systolic)'이라는 이름이 붙여졌습니다. H. T. Kung과 Charles Leiserson에 의해 독립적으로 발명되었으며, 밴드 행렬에 대한 조밀 선형 대수 연산(행렬 곱, 연립 선형 방정식 해법, LU 분해 등)에 사용됩니다. 플린의 분류(Flynn's taxonomy)에서는 종종 복수 명령어 단일 데이터(MISD) 아키텍처로 분류되지만, 그 분류에 대해서는 학문적으로 논란이 있습니다.

## 3. 핵심 공식

- (근거 자료에 명시된 공식 없음)

## 4. 실제 오픈소스에서의 구현/검증

실제 오픈소스 프로젝트에서는 시스톨릭 배열을 다양한 언어와 도구로 구현하고 검증합니다. UCLA-VAST/AutoSA는 다면체 기반 시스톨릭 배열 컴파일러(Polyhedral-Based Systolic Array Compiler)로 C++로 구현되어 있습니다. abdelazeem201/Systolic-array-implementation-in-RTL-for-TPU와 Dazhuzhu-github/systolic-array는 TPU 등을 위한 시스톨릭 배열 및 컨볼루션 연산 모듈을 Verilog로 구현한 RTL 리포지토리입니다. 또한, hngenc/systolic-array와 VCA-EPFL/FSA는 Scala 언어를 사용하여 각각 시스톨릭 배열용 DSL과 FlashAttention을 융합한 구조를 구현하고 있으며, ac-optimus/Convolution-using-systolic-arrays는 Verilog를 통해 시스톨릭 배열을 이용한 컨볼루션을 구현합니다.

### 참고 리포지토리
- [UCLA-VAST/AutoSA](https://github.com/UCLA-VAST/AutoSA) (C++, ⭐243) -- AutoSA: Polyhedral-Based Systolic Array Compiler
- [abdelazeem201/Systolic-array-implementation-in-RTL-for-TPU](https://github.com/abdelazeem201/Systolic-array-implementation-in-RTL-for-TPU) (Verilog, ⭐370) -- IC implementation of Systolic Array for TPU
- [Dazhuzhu-github/systolic-array](https://github.com/Dazhuzhu-github/systolic-array) (Verilog, ⭐175) -- verilog实现TPU中的脉动阵列计算卷积的module
- [hngenc/systolic-array](https://github.com/hngenc/systolic-array) (Scala, ⭐85) -- A DSL for Systolic Arrays
- [VCA-EPFL/FSA](https://github.com/VCA-EPFL/FSA) (Scala, ⭐194) -- FSA: Fusing FlashAttention within a Single Systolic Array
- [ac-optimus/Convolution-using-systolic-arrays](https://github.com/ac-optimus/Convolution-using-systolic-arrays) (Verilog, ⭐73) -- 

## 5. 실무에서 흔한 함정

시스톨릭 배열을 다룰 때 흔히 하는 실수는 일반적인 폰 노이만 프로세서처럼 프로그램 카운터(PC) 기반의 순차적 명령어 실행 흐름으로 오해하는 것입니다. 시스톨릭 배열은 프로그램 카운터 대신 데이터 카운터에 의해 구동되는 데이터 스트림 방식을 사용하며, 동기식 데이터 전송에 의존합니다. 따라서 비동기적 제어나 메모리 기반 접근 방식을 잘못 적용하면 타이밍 및 데이터 동기화 오류가 발생할 수 있습니다.

## 6. 추론 예시

1. 문제 정의: 하드웨어 가속기에서 대규모 행렬 곱셈 연산을 수행할 때 외부 메모리 병목 현상을 줄이고 고속 연산을 달성해야 하는 상황입니다.
2. 구조 선택: 각 연산 노드가 독립적으로 데이터를 받아 부분 결과를 계산하고 인접 노드로 전달하는 구조가 필요하므로, 폰 노이만 구조 대신 시스톨릭 배열 아키텍처를 선택합니다.
3. 데이터 흐름 분석: 시스톨릭 배열은 데이터 카운터에 의해 구동되는 다중 데이터 스트림을 사용하므로, 입력 벡터들이 하드웨어 노드 네트워크를 통해 파이프라인 형태로 흐르도록 설계합니다.
4. 결과 도출: 외부 메모리나 내부 캐시에 매번 접근할 필요 없이 모든 피연산자와 부분 결과가 프로세서 배열 내부를 통과하며 처리되므로, 순차적 처리의 한계를 극복하고 효율적인 병렬 연산을 수행할 수 있습니다.

## 7. 다음 개념과의 연결

시스톨릭 배열은 웨이브프론트 프로세서(wavefront processors)와 대비되며, 비동기 데이터 전송을 사용하는 웨이브프론트 프로세서나 데이터 스트림 기반의 병렬 처리 구조 학습으로 이어질 수 있습니다.
