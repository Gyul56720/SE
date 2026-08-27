---
title: "Training a Helpful and Harmless Assistant with Reinforcement Learning from Human Feedback"
year: 2022
authors: ['Yuntao Bai', 'Andy Jones', 'Kamal Ndousse', 'Amanda Askell', 'Anna Chen']
citations: 390
arxiv_id: ""
doi: "10.48550/arxiv.2204.05862"
tags: [paper-pipeline, rlhf-기반-품질-향상]
---

# Training a Helpful and Harmless Assistant with Reinforcement Learning from Human Feedback (2022)

> 주 단위 온라인 반복 RLHF 정렬을 통해 유용하고 무해한 AI 비서를 구축하고 강화학습 보상의 강건성을 규명한 연구

## 개요 (Overview)
인간 피드백 기반 강화학습(RLHF)과 선호도 모델링을 사용하여 유용하고 무해한 AI 비서 모델을 구축하는 방법론을 제안합니다. 특히 매주 축적되는 신규 인간 피드백을 반영하여 선호도 모델과 RL 정책을 실시간으로 갱신하는 온라인 반복 훈련 체계를 구축하여 모델을 효율적으로 정렬시켰습니다.

**문제 정의(선행 연구 대비 확장점):** 기존의 정적 또는 오프라인 기반 RLHF 정렬 프레임워크를 매주 신규 피드백을 반영하여 모델과 선호도 체계를 동적으로 업데이트하는 '온라인 반복 훈련(iterated online mode)' 방식으로 확장하였습니다.

## 주요 특징 (Features)
- weekly (1주일 단위 피드백 데이터 갱신 주기)
- linear relation (RL 보상과 KL 발산 제곱근 간의 1차 선형 관계)
- square root (정책과 초기 모델 간의 KL 발산 제곱근)

## 결과/성과 (Results/Performance)
유용성과 무해성이라는 상충되는 목표(competing objectives) 간의 정밀한 조정이 필요하며, 분포 외(OOD) 데이터 감지 및 정렬 모델의 캘리브레이션 측면에서 강건성 한계가 존재합니다.

## 연락처/저자 (Contact/Author)
- Yuntao Bai
- Andy Jones
- Kamal Ndousse
- Amanda Askell
- Anna Chen

## 참고자료 (References)
[PDF](https://arxiv.org/pdf/2204.05862)
