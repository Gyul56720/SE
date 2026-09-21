# -*- coding: utf-8 -*-
"""이 교안이 감당해야 하는 **채용공고 세 장**.

사용자가 준 것이 세 개다.

  AIE  Agent Infrastructure Engineer  (에이전트 시스템 프레임워크 코어)
  NAV  NAVER  AI 에이전트 엔지니어 (경력)     -- jobkorea 49693418
  KAK  카카오 AI Research Engineer / Agentic Search LLM -- jobkorea 49870287

**왜 코드로 적는가.** "이 책을 읽으면 이 일을 할 수 있다" 는 말은 검사할 수
없으면 광고다. 여기에 요구를 한 줄씩 열쇠로 적어 두면, 각 장이 `직무([...])` 로
자기가 감당하는 줄을 선언하고, `tests/test_agentbook.py` 가

    **감당하는 장이 하나도 없는 요구가 있으면 빨간불**

을 낸다. 공고 문구는 사용자가 보낸 화면 그대로 옮겼다(요약하지 않았다).
"""

_공고 = {
    "AIE": "Agent Infrastructure Engineer",
    "NAV": "NAVER AI 에이전트 엔지니어(경력)",
    "KAK": "카카오 AI Research Engineer — Agentic Search LLM",
}

요구 = {
    # ---- Agent Infrastructure Engineer -------------------------------
    "AIE.코어":    ("AIE", "Agent System Framework 의 코어 인프라 설계"),
    "AIE.런타임":  ("AIE", "에이전트 런타임 — 오케스트레이션 · 컨텍스트 관리 · 도구 실행 · 메모리 추상"),
    "AIE.시제품":  ("AIE", "새 능력을 빠르게 시제품으로 만들고 운영 시스템으로 키운다"),
    "AIE.인터페이스": ("AIE", "개발자용 인터페이스 — CLI · SDK 같은 개발자 도구"),
    "AIE.도구사용": ("AIE", "도구 사용 · 계획 · 추론을 하는 LLM 응용"),

    # ---- NAVER --------------------------------------------------------
    "NAV.계획":    ("NAV", "LLM 기반 planning · tool-calling · multi-step reasoning 구조 설계 및 구현"),
    "NAV.메모리":  ("NAV", "agent memory module (short-term · long-term · retrieval-augmented) 설계 및 최적화"),
    "NAV.상태":    ("NAV", "agent workflow orchestration 및 상태 관리 구조 설계"),
    "NAV.RAG":     ("NAV", "RAG 파이프라인 및 문헌 검색 시스템 구축 (벡터DB · 임베딩 모델 포함)"),
    "NAV.지표":    ("NAV", "해결 대상을 정량 지표로 정의하고 평가 파이프라인 자동화 "
                         "(task-success rate · tool-call accuracy · hallucination rate)"),
    "NAV.벤치":    ("NAV", "벤치마크 데이터셋 설계·수집·정제 및 human-in-the-loop 레이블링"),
    "NAV.논문":    ("NAV", "최신 AI agent/LLM 논문 재현 및 내재화 — 차용을 넘어 이론적 기반과 failure case 분석"),
    "NAV.최적화":  ("NAV", "latency · cost · reliability 관점에서 agent pipeline 최적화"),
    "NAV.실패":    ("NAV", "운영 중 발생한 failure case 분석 및 fallback 전략 설계"),
    "NAV.감사":    ("NAV", "안정성 · 재현성 · 감사 가능성(auditability) 확보"),
    "NAV.규제":    ("NAV", "규제(식약처 가이드라인 · HIPAA · 개인정보보호법) 요건을 고려한 안전한 에이전트 설계"),
    "NAV.코딩에이전트": ("NAV", "coding agent(Codex · Claude Code) 및 loop engineering 을 활용한 생산성"),
    "NAV.프레임워크": ("NAV", "LangChain · LangGraph · AutoGen 등 에이전트 프레임워크 1종 이상 실무 적용"),
    "NAV.파이토치": ("NAV", "Python 기반 딥러닝 프레임워크(PyTorch 등)"),
    "NAV.깃":      ("NAV", "Git 기반 코드 협업 · PR 리뷰 · CI/CD 기본 이해"),
    "NAV.분해":    ("NAV", "추상적 비즈니스 문제를 기술 요구사항으로 분해·구조화하는 시스템적 사고"),
    "NAV.관측":    ("NAV", "observability 도구를 활용한 에이전트 디버깅 (LangSmith · Langfuse · W&B)"),
    "NAV.멀티":    ("NAV", "multi-agent system 설계"),
    "NAV.정렬":    ("NAV", "RL/RLHF/GRPO/On-Policy Distillation 등 파인튜닝·alignment 기법, 경량화"),
    "NAV.안전":    ("NAV", "model safety · alignment, 에이전트 safety · hallucination 완화 · 신뢰성"),
    "NAV.서빙":    ("NAV", "Kubernetes · Docker 기반 ML 서빙 환경 운영, production-grade 운영"),
    "NAV.그래프RAG": ("NAV", "GraphRAG · memory-augmented generation"),
    "NAV.오픈소스": ("NAV", "오픈소스 에이전트 프로젝트 기여"),

    # ---- 카카오 -------------------------------------------------------
    "KAK.검색에이전트": ("KAK", "검색 과정에서 스스로 계획하고 탐색하며 도구를 활용하는 Agentic Search LLM 연구"),
    "KAK.정책최적화": ("KAK", "GRPO 등 Policy Optimization 기반 LLM 학습 및 성능 최적화"),
    "KAK.환경":    ("KAK", "실제 검색 인덱스·API 와 상호작용하는 환경에서의 Agent 학습"),
    "KAK.PPO":     ("KAK", "PPO · GRPO 등 Policy Optimization 방법을 활용한 LLM 강화학습"),
    "KAK.분석":    ("KAK", "LLM 학습 결과를 분석하고 실험을 통해 성능을 개선"),
    "KAK.동적환경": ("KAK", "실제 환경과 상호작용하는 Dynamic Environment 기반 강화학습"),
    "KAK.브라우징": ("KAK", "검색 · 브라우징 · Tool Use Agent 연구"),
    "KAK.벤치마크": ("KAK", "BrowseComp 등 Search LLM Benchmark 를 활용한 모델 평가 및 개선"),
    "KAK.장기":    ("KAK", "Agent 의 Planning · Tool Calling · Long-Horizon Reasoning"),
    "KAK.분산학습": ("KAK", "대규모 LLM 학습 또는 분산 학습 파이프라인 구축"),
    "KAK.기본":    ("KAK", "머신러닝 기본 개념과 모델의 학습 원리를 설명할 수 있을 것"),
    "KAK.선택이유": ("KAK", "Loss · Optimization · Sampling · Evaluation Metric 의 **선택 이유**를 설명할 수 있을 것"),
    "KAK.가설":    ("KAK", "학습이 안 될 때 가설을 세우고 재현 가능한 실험으로 원인을 좁혀나감"),
    "KAK.오프라인": ("KAK", "오프라인 지표와 실제 서비스 품질의 차이를 이해하고 "
                          "학습→추론→평가→배포까지 고려해 문제를 푼다"),
}


def 글(열쇠):
    return 요구[열쇠][1]


def 어디(열쇠):
    return _공고[요구[열쇠][0]] + " ·"


def 공고이름(약자):
    return _공고[약자]


def 전부():
    return sorted(요구)
