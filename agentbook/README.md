# Agent Infrastructure Engineering — 교안

`edu/` 의 IP 교안과 **같은 규격**이다: 이론을 처음 원리부터 적고, **수는 전부
빌드할 때 계산한다**(인용하지 않는다). 그리고 이 저장소에서 **실제로 난 사고**를
사고 상자로 넣는다 -- 그것이 이 교안이 교과서가 아니라 현장 기록인 까닭이다.

## 이 교안이 겨누는 직무

    JD        Job Description (직무기술서)
    직무명    Agent Infrastructure Engineer
              (= Agent Platform Engineer / Agent Framework Engineer)
              한국어: 에이전트 플랫폼(인프라) 엔지니어

JD 의 책임 네 줄이 이 교안의 뼈대다:

    Design and build core infrastructure for the Agent System Framework   -> 2부·5부
    orchestration, context management, tool execution, memory abstraction -> 2부 (A4~A9)
    rapidly prototype ... and scale them into production systems          -> 5부 (A18~A20)
    developer-facing interfaces such as CLI tools and SDKs                -> 4부 (A15~A17)

## 짓기

    python3 agentbook/build.py            # Agent_Theory_KR.pdf
    python3 agentbook/build.py --영어     # Agent_Theory_EN.pdf
