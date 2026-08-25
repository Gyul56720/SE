---
title: "Clock domain crossing"
domain: 01_디지털설계검증
tags: [book, concept, 01_디지털설계검증]
source_wikipedia: "https://en.wikipedia.org/wiki/Clock_domain_crossing"
referenced_repos: ['verification-explorer/systemverilog-clocking-blocks-tutorial', 'omid2021n/Design_Clk_generator_for_UART']
---

# 01. Clock domain crossing

## 1. 왜 알아야 하는가

반도체 설계 및 검증 시 비동기 클록 도메인 간의 신호 전송 과정에서 메타스테이빌리티(metastability) 등의 문제가 발생할 수 있으므로, 올바른 설계와 검증을 위해 Clock Domain Crossing(CDC) 개념을 반드시 이해해야 합니다. 실무에서는 서로 다른 주파수나 위상을 가진 도메인 사이의 신호 누락, 글리치(glitch), 메타스테이빌리티로 인한 시스템 오작동을 방지하기 위해 CDC 검증이 매우 중요합니다.

## 2. 정의와 이론

디지털 전자 설계에서 Clock Domain Crossing(CDC, 또는 clock crossing)은 동기식 디지털 회로 내의 신호가 한 클록 도메인에서 다른 클록 도메인으로 넘어가는 것을 의미합니다. 서로 다른 클록 도메인은 서로 다른 주파수, 서로 다른 위상(클록 지연이나 다른 클록 소스로 인함), 또는 둘 다를 가질 수 있으며, 두 도메인 간의 클록 에지 관계를 신뢰할 수 없습니다. 메타스테이빌리티(metastability) 문제를 피하기 위해 목적지 클록 도메인에는 최소 2단 이상의 재동기화 플립플롭(re-synchronization flip-flops)이 포함됩니다. 단일 비트 신호를 더 느린 주파수의 클록 도메인으로 동기화하는 것은 더 까다로우며, 일반적으로 신호가 감지되었음을 나타내는 목적지 도메인에서 소스 도메인으로의 피드백 형태와 함께 각 클록 도메인의 레지스터가 필요합니다. 그 외의 잠재적인 CDC 설계 오류로는 글리치와 데이터 손실이 있습니다.

## 3. 핵심 공식

- (근거 자료에 명시된 공식 없음)

## 4. 실제 오픈소스에서의 구현/검증

제공된 리포지토리 중 verification-explorer/systemverilog-clocking-blocks-tutorial 리포지토리는 SystemVerilog에서 클로킹 블록(clocking blocks)을 사용하는 방법과 이유에 대한 튜토리얼을 제공합니다. omid2021n/Design_Clk_generator_for_UART 리포지토리는 UART를 위한 시스템베릴로그 클록 제너레이터 설계를 다룹니다. (기타 상세 구현 내용은 근거 자료에 명시되지 않음)

### 참고 리포지토리
- [verification-explorer/systemverilog-clocking-blocks-tutorial](https://github.com/verification-explorer/systemverilog-clocking-blocks-tutorial) (Verilog, ⭐3) -- SystemVerilog tutorial on how and why to use clocking blocks
- [omid2021n/Design_Clk_generator_for_UART](https://github.com/omid2021n/Design_Clk_generator_for_UART) (?, ⭐0) -- Design  systemverilog clock generator  for UART 

## 5. 실무에서 흔한 함정

신호가 충분히 오래 유지되지 않고 레지스터에 저장되지 않으면 들어오는 클록 경계에서 비동기적으로 보일 수 있습니다. 목적지 클록 도메인에서 CDC 메타스테이빌리티 문제를 방지하기 위한 최소 2단 이상의 재동기화 플립플롭을 누락하거나, 글리치 및 데이터 손실 위험을 고려하지 않는 실수가 발생할 수 있습니다.

## 6. 추론 예시

1. 문제 상황: 신호가 한 클록 도메인에서 다른 클록 도메인으로 이동할 때 클록 에지의 관계를 신뢰할 수 없는 상태가 발생합니다.
2. 원인 분석: 두 도메인의 주파수나 위상이 다르며 신호가 충분히 유지되지 않고 등록되지 않으면 비동기적으로 보이고 메타스테이빌리티 이슈가 생길 수 있습니다.
3. 해결 판단: 목적지 도메인에 최소 2단 이상의 재동기화 플립플롭을 포함시켜 메타스테이빌리티 문제를 방지하고, 더 느린 도메인으로 갈 때는 피드백 형태를 고려하여 설계합니다.

## 7. 다음 개념과의 연결

Metastability in electronics, Crosstalk (electronics), Gray code
