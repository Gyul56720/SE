# 지속적인 차단 우회 전략 및 사전 정의된 스키마(Pre-defined Schema) 리포트

## 1. 차단 지속 시 접속 우회 전략 (Continuous Bypass Strategy)

실시간 웹 검색이 안티봇(Bot Detection) 정책으로 인해 지속적으로 차단될 경우, 무조건 즉시 포기하는 것이 아니라 다음과 같은 체계적인 우회 기법을 순차적으로 적용해야 합니다.

1. **에이전트/프록시 로테이션 (Agent/Header Rotation):**
   * 매 요청마다 `User-Agent`, `Accept-Language`, `Referer` 등 브라우저 지문(Fingerprint)을 다변화하여 단순 IP/User-Agent 기반 차단을 회피합니다.
2. **지수 백오프 (Exponential Backoff):**
   * 연속 차단 발생 시 서버에 가중되는 부하를 줄이고 봇 판정 확률을 낮추기 위해 대기 시간(1초 $\rightarrow$ 2초 $\rightarrow$ 4초 등)을 점진적으로 늘려가며 재시도합니다.
3. **최종 방어선 (Graceful Degradation):**
   * 최대 재시도 횟수(Max Retries)를 초과할 경우, 무리한 크롤링 시도를 멈추고 사전에 검증된 안전한 스키마로 즉시 전환합니다.

---

## 2. 필요한 사전 정보 스키마 (Pre-defined Ground Truth Schema)

실시간 검색이 완전히 차단되었을 때 에이전트가 할루시네이션 없이 정확한 답변을 생성하기 위해 반드시 보유해야 하는 **필수 사전 정보 스키마 구조**는 다음과 같습니다.

```json
{
  "status": "FALLBACK_VIA_PREDEFINED_SCHEMA",
  "schema_version": "1.0.0",
  "entity": "Loopdesk",
  "category": "Agentic AI Video Editing Platform",
  "differentiating_features": [
    "Agentic AI autonomous rough-cut baseline generation",
    "Cloud GPU offloading for low-spec laptops",
    "Short-form sketch clip assembly and BGM beat synchronization"
  ],
  "namespace_resolution": "Explicitly distinguished from Loupedeck (hardware editing console).",
  "anti_hallucination_note": "Persistent bot detection triggered fallback to verified local schema."
}
```

* **핵심 필드 설명:**
  * **entity / category:** 대상 플랫폼의 정확한 명칭과 도메인 정의 (네임스페이스 충돌 방지).
  * **differentiating_features:** 핵심 기능(에이전트 기반 초안 생성, 클라우드 GPU 연동, 숏폼/BGM 싱크) 정의.
  * **namespace_resolution:** 기존 하드웨어(Loupedeck)와의 명확한 개념 분리 기록.
  * **anti_hallucination_note:** 라이브 검색 차단 시 검증된 로컬 스키마를 통해 할루시네이션을 통제했음을 명시하는 메타데이터.
