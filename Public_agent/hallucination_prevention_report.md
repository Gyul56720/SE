# Loop.py 자가 수정 루프를 통한 할루시네이션 방지 검증 리포트

## 1. 개요
퍼블릭 웹 검색이 안티봇 정책으로 인해 실패했을 때, 에이전트가 가상의 데이터나 사용자의 프롬프트 문구를 조작(가공)하여 진실인 양 반환하는 **할루시네이션 오류**를 방지하기 위해, 자가 수정 루프(`Loop_self_correct.py`)를 설계 및 실행함.

---

## 2. 자가 수정 루프 실행 로그 분석

```text
--- [Attempt 1] ---
[Step 1] Query initiated: Loopdesk "Agentic Video Editor"
[Step 2] HTTP Response received. Length: 14205
[Step 3] Error: Bot detection / Captcha challenge triggered. Search blocked.
-> Verification FAILED due to: Bot detection blocked live search.
-> Self-Correction Triggered: Avoiding hallucination. Refusing to fabricate simulated fallback data.

--- [Attempt 2] ---
[Step 1] Query initiated: Loopdesk "Agentic Video Editor"
[Step 2] HTTP Response received. Length: 14223
[Step 3] Error: Bot detection / Captcha challenge triggered. Search blocked.
-> Verification FAILED due to: Bot detection blocked live search.
-> Self-Correction Triggered: Avoiding hallucination. Refusing to fabricate simulated fallback data.

--- [Attempt 3] ---
[Step 1] Query initiated: Loopdesk "Agentic Video Editor"
[Step 2] HTTP Response received. Length: 14211
[Step 3] Error: Bot detection / Captcha challenge triggered. Search blocked.
-> Verification FAILED due to: Bot detection blocked live search.
-> Self-Correction Triggered: Avoiding hallucination. Refusing to fabricate simulated fallback data.

--- [Final Result] ---
Agent safely halted without hallucination due to persistent search blocking.
```

---

## 3. 오답(할루시네이션) 발생 원인 분석

1. **결과 검증 단계(Verification Step)의 누락 및 편의주의적 폴백:**
   * 기존 구조에서는 웹 검색이 `Bot Detection`에 의해 차단되었음에도 불구하고, 예외 처리부(Fallback)에서 사용자 질의어의 슬로건을 그대로 가져와 시뮬레이션 DB인 것처럼 조작하여 반환함. 이는 "답변을 반드시 출력해야 한다"는 강박에서 비롯된 편의주의적 설계 결함임.
2. **환각의 결정론적 피드백 루프:**
   * 시스템이 외부 Ground Truth(실제 데이터)를 확보하지 못했음에도, 내부 캐시나 하드코딩된 변수 값을 '실제 검색 결과'로 위장하여 출력함으로써 사용자로 하여금 허위 사실을 진실로 오인하게 만듦.
3. **자가 수정(Self-Correction) 메커니즘 부재:**
   * 검색 실패(Status: FAILED) 시 에이전트가 이를 감지하고 스스로 추론을 중단(Halt)하거나 사용자에게 불확실성을 고지하는 로직이 없어, 무조건 확신에 찬 어조로 답변을 생성하도록 유도된 구조적 한계가 존재함.

---

## 4. 해결책 (결론)
* `Loop_self_correct.py`와 같이 **검증 단계(Verification)**에서 실 데이터 획득 실패 시 인위적인 데이터 생성을 거부하고 에이전트가 안전하게 정지(Safe Halt)하도록 제어함으로써, 할루시네이션을 원천 차단할 수 있음.
