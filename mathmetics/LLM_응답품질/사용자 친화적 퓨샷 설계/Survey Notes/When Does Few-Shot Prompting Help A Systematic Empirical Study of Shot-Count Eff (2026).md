---
title: "When Does Few-Shot Prompting Help? A Systematic Empirical Study of Shot-Count Effects Across Model Scale, Architecture, and Output Parsing Robustness"
year: 2026
authors: ['Ayush Dwivedi', 'Ashvi Soni']
citations: 0
arxiv_id: "2607.22969v1"
doi: ""
tags: [paper-pipeline, 사용자-친화적-퓨샷-설계]
---

# When Does Few-Shot Prompting Help? A Systematic Empirical Study of Shot-Count Effects Across Model Scale, Architecture, and Output Parsing Robustness (2026)

> LLM 샷 수(shot count)에 따른 성능 변화는 단조적이지도 예측 가능하지도 않다는 사실을 보여주는 체계적 실증 연구

## 개요 (Overview)
이 논문은 모델의 크기, 아키텍처, 출력 파싱에 따른 샷 수(shot-count)와 분류 성능 간의 상호작용을 체계적으로 분석했습니다. 연구 결과 샷 수 증가에 따른 성능 변화는 단조롭지도 보편적이지도 않으며 모델별로 4가지의 독특한 거동 패턴을 보임을 확인했고, 출력 파싱 오류 수정을 통해 평가 오차를 대폭 줄이는 방법론적 기여를 제시했습니다.

**문제 정의(선행 연구 대비 확장점):** 샷 수의 증가가 항상 일관된 성능 향상을 불러온다는 기존의 일반적인 통념 및 단순 평가 방식에서 벗어나, 파서 오류 보정(parser correction) 단계를 체계적 실험 설계에 도입하여 실제 모델의 내재적 능력을 더욱 정밀하게 측정하도록 고도화했습니다.

## 주요 특징 (Features)
- 5개의 대형 언어 모델(LLMs)
- 6개의 샷 수 설정(k in {0, 1, 2, 3, 5, 8})
- AG News 벤치마크 데이터 수 n=200
- Llama 3.3 70B의 파싱 교정 시 성능 개선도 최대 206%
- Llama 3.1 8B의 1-shot 복구 효과 크기 d=10.98

## 결과/성과 (Results/Performance)
분석이 AG News 4클래스 분류 벤치마크(n=200)라는 단일 데이터셋 및 상대적으로 소규모인 샘플 크기에 한정되어 있어, 다양한 테스크나 광범위한 도메인에서의 보편적 일반화 가능성을 완전히 검증하지는 못했습니다.

## 연락처/저자 (Contact/Author)
- Ayush Dwivedi
- Ashvi Soni

## 참고자료 (References)
[PDF](https://arxiv.org/pdf/2607.22969v1)
