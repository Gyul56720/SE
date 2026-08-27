---
title: "The Unreliability of Explanations in Few-shot Prompting for Textual Reasoning"
year: 2022
authors: ['Xi Ye', 'Greg Durrett']
citations: 0
arxiv_id: "2205.03401v2"
doi: ""
tags: [paper-pipeline, 사용자-친화적-퓨샷-설계]
---

# The Unreliability of Explanations in Few-shot Prompting for Textual Reasoning (2022)

> 퓨샷 프롬프팅에서 설명 제공의 성능 향상 한계와 설명의 불완전성을 지적하고, 이를 극복하기 위한 사후 예측 보정 방안을 제시하는 연구

## 개요 (Overview)
본 논문은 텍스트 추론 작업에서 설명(explanation)을 포함한 퓨샷 프롬프팅이 실제 성능 향상에 미치는 영향이 제한적이며, 생성된 설명이 논리적 오류나 허위 사실을 포함할 수 있음을 밝힙니다. 이에 대응하여, 생성된 설명의 신뢰도를 자동으로 평가하는 보정기(calibrator)를 도입하여 모델의 예측 성능을 사후적으로 향상시키는 방법을 제안합니다.

**문제 정의(선행 연구 대비 확장점):** 프롬프트에 설명을 포함하지 않는 표준 퓨샷 학습(standard few-shot learning) 방식을 확장하여 다양한 스타일의 설명을 프롬프트에 추가하는 방식을 평가하고, 자동 추출된 신뢰도 점수를 기반으로 한 사후 보정기(calibrator) 학습 방식을 추가로 도입하였습니다.

## 주요 특징 (Features)
- 4개의 대형 언어 모델(LLMs)
- 3개의 텍스트 추론 데이터셋
- 3개의 실험 설정

## 결과/성과 (Results/Performance)
LLM이 생성한 설명이 실제 모델의 예측 결과로 이어지지 않거나(entail), 입력 텍스트에 사실적으로 부합하지 않을 수 있어 설명의 신뢰성이 보장되지 않습니다.

## 연락처/저자 (Contact/Author)
- Xi Ye
- Greg Durrett

## 참고자료 (References)
[PDF](https://arxiv.org/pdf/2205.03401v2)
