---
title: "DV/DS + AI 취업 및 GIST 대학원 진학 자격증·포트폴리오 로드맵"
tags: [career-plan, DV, AI, GIST, certification]
---

# DV/DS + AI 취업 및 GIST 대학원 진학 로드맵

> 근거: 실제 WebSearch 확인된 자격증/GIST 정보 + 기존 채점된 포트폴리오(rtl-lab/capstone/smart
> antenna/LLM-RTL 리서치). Gemini API가 이 근거만 바탕으로 재배열/우선순위화함(지어낸 내용 없음).

## 전략 요약

본 전은 사용자 고유의 실존 프로젝트(rtl-lab, capstone, smart antenna, LLM-RTL)가 가진 검증 툴체인 및 상용 툴 부족 등의 갭을 전자기사와 UVM/SystemVerilog 트레이닝으로 보완합니다. 또한 SQLD와 어학 스펙을 통해 삼성 DS 계열 DV/DS 취업 기본 요건을 충족합니다. 나아가 GIST 반도체공학과 대학원 진학과 OPEN Lab 지원을 위해 프로젝트를 UVM, SVA, 상용 EDA 툴 연계 단계로 고도화하여 취업과 진학 두 마리 토끼를 모두 잡는 로드맵을 제시합니다.

## 1. 자격증/트레이닝 우선순위

### [1순위] 전자기사 (국가기술자격)
- 왜 필요한가: 다수 출처에서 반도체 설계 직무의 가장 직접적인 국가기술자격으로 확인되며 하드웨어 기초 역량을 증빙합니다.

### [2순위] Siemens Verification Academy (SystemVerilog for Verification / UVM Intermediate) (검증전문트레이닝)
- 왜 필요한가: 인증 보유자가 비보유자 대비 검증직군 연봉 7.5% 높다는 통계가 있으며 rtl-lab과 LLM-RTL 리서치의 UVM 및 검증 툴체인 갭을 직접 해소합니다.

### [3순위] SQLD (SQL개발자) (데이터)
- 왜 필요한가: 데이터 관련 채용공고의 45%가 SQL 역량을 요구하며, 검증 및 불량 데이터 분석 역량을 증빙합니다.

### [4순위] 오픽 또는 토익 (어학)
- 왜 필요한가: 삼성 DS 계열 및 SK하이닉스 공통 기본 스펙으로 미달 시 감점 요인이므로 기본 확보가 필요합니다.

## 2. 포트폴리오 로드맵 (취업 + GIST 대학원 동시 기여)

### UVM 기반 NVDLA CMAC 모듈 검증 고도화
- 발전시키는 기존 프로젝트: rtl-lab
- 목표: 기존의 자체 제작 테스트벤치와 오픈소스 기반 파이프라인을 Siemens Verification Academy에서 학습한 SystemVerilog와 UVM 기반으로 마이그레이션
- 채워지는 역량 갭: UVM 미사용 갭 해소, 공식 커버리지 도구 활용, 검증 방법론 체계화
- 취업(DV/DS+AI) 연결점: 삼성 DS DV 직무 JD에서 요구하는 UVM/SystemVerilog 검증 역량을 직접 증명
- GIST 대학원 연결점: GIST 반도체공학과 대학원 연구실의 첨단 디지털 반도체 설계 및 검증 과제에 즉시 투입 가능한 연구 역량 증빙

### SAR 레이더 실측 데이터 기반 오류 분석 및 불량 데이터 처리 파이프라인
- 발전시키는 기존 프로젝트: capstone
- 목표: capstone 프로젝트의 실측-이론 오차 원인 분석 결과를 바탕으로, 측정 및 불량 데이터 자동 분석 파이프라인 구축
- 채워지는 역량 갭: 데이터 분석 역량, SQL/데이터 처리 툴 활용
- 취업(DV/DS+AI) 연결점: DS 계열 데이터 분석 및 양산 검증 직무에서 요구하는 불량 데이터 분석 경험과 연계
- GIST 대학원 연결점: GIST 첨단패키징 및 신호 처리 관련 연구실에서 요구하는 실측 데이터 해석 능력 입증

### LLM 생성 Verilog RTL 코드 자동 검증 및 SVA 적용 리서치
- 발전시키는 기존 프로젝트: LLM-RTL 리서치
- 목표: LLM-RTL 리서치의 Icarus Verilog 검증 파이프라인에 SVA(Assertion)를 추가하여 formal verification 관점의 코드 품질 자동 평가 체계 구축
- 채워지는 역량 갭: Formal verification, SVA(Assertion) 기반 커버리지 갭 해소
- 취업(DV/DS+AI) 연결점: AI반도체 분야에서 LLM을 활용한 반도체 설계 자동화(EDA) 및 지능형 검증 역량 어필
- GIST 대학원 연결점: GIST 반도체공학과의 AI 반도체 및 설계 자동화 관련 OPEN Lab 지원 시 핵심 연구 실적으로 활용

### 상용 EDA 툴체인 연계 배열안테나 신뢰성 검증
- 발전시키는 기존 프로젝트: smart antenna
- 목표: Dolph-Chebyshev 배열안테나 및 최소자승 고장보상 알고리즘을 Cadence 공식 트레이닝 기반 상용 툴체인 환경으로 확장 구현
- 채워지는 역량 갭: 상용 EDA 툴체인(Cadence/Synopsys) 실습 경험 갭 해소
- 취업(DV/DS+AI) 연결점: 상용 툴 사용 경험을 요구하는 하드웨어 설계 및 검증 직무 JD 충족
- GIST 대학원 연결점: GIST 반도체공학과 하계 인턴십 및 대학원 진학 시 하드웨어 설계 및 시뮬레이션 전문성 입증
