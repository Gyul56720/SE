---
title: "Improving alignment of dialogue agents via targeted human judgements"
year: 2022
authors: ['Amelia Glaese', 'Nat McAleese', 'Maja Trębacz', 'John Aslanides', 'Vlad Firoiu']
citations: 133
arxiv_id: ""
doi: "10.48550/arxiv.2209.14375"
tags: [paper-pipeline, rlhf-기반-품질-향상]
---

# Improving alignment of dialogue agents via targeted human judgements (2022)

> 자연어 규칙 세분화 평가와 출처 제공 방식으로 안전성과 정확성을 정교하게 조율한 대화 에이전트 Sparrow

## 개요 (Overview)
본 논문은 인간 피드백 기반 강화학습(RLHF)을 사용하여 기존 언어 모델 대비 더 안전하고 정확하며 유용한 대화 에이전트인 Sparrow를 제안합니다. 대화 가이드를 구체적인 자연어 규칙으로 세분화해 사용자 평가를 수집하고 사실적 주장에 대한 신뢰할 수 있는 출처를 제공하는 방식을 도입했습니다.

**문제 정의(선행 연구 대비 확장점):** 기존 프롬프트 기반 언어 모델 및 일반적인 RLHF 방식에서 나아가, 대화 요구사항을 개별 자연어 규칙으로 세분화해 판단하는 '규칙 조건부 보상 모델'과 답변 생성 시 '출처 증거 제공' 메커니즘을 추가 적용했습니다.

## 주요 특징 (Features)
- 78%
- 8%

## 결과/성과 (Results/Performance)
규칙을 준수하도록 모델을 학습시켰음에도 불구하고 특정 데이터 분포상에서 편향(distributional biases)이 여전히 나타날 수 있다는 한계가 존재합니다.

## 연락처/저자 (Contact/Author)
- Amelia Glaese
- Nat McAleese
- Maja Trębacz
- John Aslanides
- Vlad Firoiu

## 참고자료 (References)
[PDF](https://arxiv.org/pdf/2209.14375)
