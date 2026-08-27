---
title: "Why Is RLHF Alignment Shallow? A Gradient Analysis"
year: 2026
authors: ['Robin Young']
citations: 0
arxiv_id: "2603.04851v1"
doi: ""
tags: [paper-pipeline, rlhf-기반-품질-향상]
---

# Why Is RLHF Alignment Shallow? A Gradient Analysis (2026)

> RLHF 정렬이 초기 토큰에만 얕게 발생하는 원인을 그라디언트 분석으로 증명하고 복구 페널티 기반의 해결책을 제시한 연구

## 개요 (Overview)
본 논문은 그라디언트 기반 정렬이 위해성이 결정되는 특정 토큰 위치에만 집중되고 그 이후 위치에서는 소실된다는 것을 마팅게일 분해를 통해 수학적으로 증명합니다. 표준 정렬 목적 함수의 한계를 극복하기 위해 위해 정보 개념을 도입하고, 모든 위치에서 그라디언트 신호를 활성화하는 복구 페널티 기반의 새로운 목적 함수를 제안합니다.

**문제 정의(선행 연구 대비 확장점):** 기존의 표준 RLHF 정렬 목적 함수를 확장하여 시퀀스 수준 위해성에 대한 마팅게일 분해(martingale decomposition) 분석 기법을 도입하고, 그라디언트 소실 문제를 해결하는 복구 페널티(recovery penalties) 기반 목적 함수로 발전시켰습니다.

## 주요 특징 (Features)
- (없음)

## 결과/성과 (Results/Performance)
이론적 증명과 새로운 목적 함수 도출에 초점을 맞추고 있어 실제 대규모 언어 모델(LLM) 환경에서의 계산 복잡도나 구체적인 벤치마크 평가 수치가 초록에 언급되지 않았습니다.

## 연락처/저자 (Contact/Author)
- Robin Young

## 참고자료 (References)
[PDF](https://arxiv.org/pdf/2603.04851v1)
