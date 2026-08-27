---
title: "Internet-augmented language models through few-shot prompting for open-domain question answering"
year: 2022
authors: ['Angeliki Lazaridou', 'Elena Gribovskaya', 'Wojciech Stokowiec', 'Nikolai Grigorev']
citations: 0
arxiv_id: "2203.05115v2"
doi: ""
tags: [paper-pipeline, 사용자-친화적-퓨샷-설계]
---

# Internet-augmented language models through few-shot prompting for open-domain question answering (2022)

> 추가 학습 없이 퓨샷 프롬프팅과 구글 검색, 추론 연산량 최적화를 통해 구현한 웹 증강 언어 모델

## 개요 (Overview)
본 논문은 대형 언어 모델(LSLM)의 퓨샷 능력을 활용하여 파인튜닝 없이 Google 검색 결과를 모델에 반영하는 프롬프팅 방법을 제안합니다. 또한, 여러 검색 결과를 기반으로 다수의 답변을 생성하고 이를 재순위화하는 방식을 통해 추론 단계의 계산량을 늘려 소형 모델의 성능도 크게 개선할 수 있음을 보여줍니다.

**문제 정의(선행 연구 대비 확장점):** 외부 검색 정보를 활용하는 기존 세미 파라메트릭 언어 모델(Semi-parametric LMs)의 방식을 확장하여, 별도의 미세조정(Fine-tuning)이나 파라미터 추가 없이 오직 Google 검색 결과와 퓨샷 프롬프팅(Few-shot prompting)만을 결합하는 방식으로 개선함

## 주요 특징 (Features)
- (없음)

## 결과/성과 (Results/Performance)
실시간 웹 검색 및 다중 답변 생성 후 재순위화(Reranking) 단계를 거치기 때문에 추론 시 계산 비용과 시간이 증가할 수 있으며, 구글 검색 결과의 품질에 의존적입니다.

## 연락처/저자 (Contact/Author)
- Angeliki Lazaridou
- Elena Gribovskaya
- Wojciech Stokowiec
- Nikolai Grigorev

## 참고자료 (References)
[PDF](https://arxiv.org/pdf/2203.05115v2)
