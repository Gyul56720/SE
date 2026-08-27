---
title: "Language Models (Mostly) Know What They Know"
year: 2022
authors: ['Saurav Kadavath', 'Tom Conerly', 'Amanda Askell', 'Tom Henighan', 'Dawn Drain']
citations: 170
arxiv_id: ""
doi: "10.48550/arxiv.2207.05221"
tags: [paper-pipeline, rlhf-기반-품질-향상]
---

# Language Models (Mostly) Know What They Know (2022)

> 언어 모델이 자신의 답변의 타당성과 지식 보유 여부를 스스로 평가하고 예측할 수 있음을 보여준 연구

## 개요 (Overview)
대형 언어 모델이 스스로 생성한 답변의 타당성을 평가하는 능력(P(True))과 질문에 대해 답을 알고 있는지 예측하는 능력(P(IK))을 갖추고 있음을 규명하였습니다. 모델 크기가 커질수록 이러한 자가 평가 및 보정(calibration) 성능이 향상되며, 다중 샘플을 고려할 때 평가 능력이 더욱 강화됩니다.

**문제 정의(선행 연구 대비 확장점):** 객관식 및 단순 진위 여부(True/False) 질문에 국한되었던 기존 모델 보정(calibration) 연구를 확장하여, 열린 질문(open-ended tasks)에서 모델이 스스로 생성한 답변의 정답 확률인 P(True)를 평가하고 구체적인 답변 후보 없이 질문 자체만으로 지식 유무 확률인 P(IK)를 예측하도록 개선함.

## 주요 특징 (Features)
- (없음)

## 결과/성과 (Results/Performance)
새로운 성격의 작업(new tasks)에 직면했을 때, 질문에 대해 답을 알고 있는지 여부를 나타내는 P(IK)의 보정(calibration) 성능이 저하되는 한계가 있습니다.

## 연락처/저자 (Contact/Author)
- Saurav Kadavath
- Tom Conerly
- Amanda Askell
- Tom Henighan
- Dawn Drain

## 참고자료 (References)
[PDF](https://arxiv.org/pdf/2207.05221)
