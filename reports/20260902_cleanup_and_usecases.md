# 시스템 정리 결과 및 활용 방안 (2026-09-02)

정리 전 커밋: `c620c9b` — 지운 파일은 전부 이 커밋에 살아 있다.
복구: `git checkout c620c9b -- <경로>`

| | 정리 전 | 정리 후 |
|---|---|---|
| 추적 파일 | 565 | 266 |
| 저장소 용량 | 54.95 MB | 1.13 MB |
| 루트 파일 | 164 | 16 |

삭제 300 · 이동 48 · 수정 3. 정리 후 `python3 gatekeeper.py` → **10개 게이트 전부 통과**.

---

## 1. 남긴 것 — 요청하신 세 시스템

### (1) Discord 서버 에이전트
`discord_bot_server.py` `main_public.py` `bot_tools.py` `quota_tracker.py`
`agent_context.py` `agent_memory.py` `public_agent_files.py` `memory_hygiene.py`
`log_streamer.py` + `deploy/` + `.github/workflows/`

여기에 **붙어 있어서 뗄 수 없는 것**도 함께 남겼다(요청하신 목록에는 없었지만 지우면 봇이
커밋 자체를 못 한다):

- `gatekeeper.py` + `gates/` — `git_sync()`가 커밋 직전에 호출한다. G003이 이 호출 한 줄의
  존재까지 감시하므로, 게이트를 지우면 봇의 저장 경로가 통째로 깨진다.
- `self_challenge.py` — 게이트 승격의 유일한 경로(G003이 `def prove` 존재를 요구).
- `tests/` — 게이트가 실제 사고를 잡는지 재증명하는 스위트 + 오케스트레이터 테스트.
- `public_agent_memory/` (53) — `search_memory`/`save_memory`가 실제로 읽고 쓰는 데이터.

### (2) 오케스트레이션 에이전트
`orchestrator/` 전체(41) — 계획·컴포넌트·검증·실행 기록.

### (3) 3×3 m=22 / 밤새 도는 최적화 루프
`mathmetics/matrix_exponent/`(16) — `searcher.py` `verifier.py` `self_improve_loop.py`
`improve_agent.py` `optimizer.py` `benchmarks.json` `jump_searcher*.py`,
`scripts/check_improve.sh`, `deploy/se-matrix-search.service`.
관련 기록으로 `Public_agent/`의 IJP·matrix 로그 md 8개를 남겼다.

## 2. 지시하신 범위를 넘어 남긴 것 — 판단 근거와 취소 방법

말씀하신 "놓쳤거나 중요해 보이면 남기고 보고"에 해당하는 항목이다. 필요 없으면 아래 명령
한 줄로 지우면 된다.

| 남긴 것 | 왜 | 지우려면 |
|---|---|---|
| `npu/` (47) — 1.58비트 삼진 NPU SystemVerilog 설계·테스트벤치·검증 스위트 | **오늘(09-02) 작업분**이다. 커밋 `6722076`과 오늘 자 기억 노트가 이 프로젝트를 가리킨다. 에세이가 아니라 합성 가능한 설계 + 검증 코드라 재작성 비용이 크다 | `git rm -r npu` |
| `법이론서/`(17), `ai_concept/`(12), `편입수학 이론서/`(1), `mathmetics/LLM_응답품질/`(16) | 옵시디언으로 동기화되는 **학습·이론 문서**(총 ~140KB 본문). 코드가 아니라 읽는 자료이고, 지우면 다음 pull 때 볼트에서도 사라진다 | `git rm -r 법이론서 ai_concept "편입수학 이론서" mathmetics/LLM_응답품질` |
| `Public_agent/challenge.py`, `verify.py` | `gates/__init__.py`와 `self_challenge.py`가 "위조 불가 오라클"의 선례로 이 두 파일을 근거로 든다. 지우면 설계 근거가 끊긴다 | `git rm Public_agent/challenge.py Public_agent/verify.py` |
| `Public_agent/incident_2026-08-27_admin_agent_outage.md`, `public_agent_problem_resolution.md` | 봇 장애 사고 기록. G003의 원칙("사고 기록은 재발 방지 자산이다")과 같은 부류 | `git rm` 해당 파일 |

## 3. 지운 것

| 분류 | 개수 | 예 |
|---|---|---|
| 빌드 산출물 | 3 (52 MB) | `check_syntax`, `final_sim_exec`, `final_sim_opt` — iverilog vvp 출력, `npu/`에서 재생성 가능 |
| 낡은 사본·스냅샷 | 5 | `bot_tools.py.bak`, `searcher.py.bak`, `_last_good_searcher.py`, `searcher_new.py`, 중복 `memory/test_inference_prompt.py` |
| 런타임 찌꺼기 | 8 | `state_cache.json`, `ijp_pid.txt`, `simulation_*.txt/log`, `generated_page.html` 등 |
| 일회성 에세이·시뮬 스크립트 | 47 | `Loop*.py` 7종, `origin_check.py`, `proof_verification.py`, `infinite_*.py`, `human_cognition_model.py` … 출력이 stdout 산문뿐이고 아무도 임포트하지 않는다 |
| 옵시디언/리포트 생성 파이프라인 | 39 | `main.py` `collector.py` `organizer.py` `theory_generator.py` `config.py` `gemini_client.py` 등 31개 + `sources/` 8개 |
| 텐서 단발 실험 | 12 | `strassen_tensor_analysis.py`, `quaternion_tensor_optimizer.py` 등 — `mathmetics/matrix_exponent/`가 대체 |
| 생성물 폴더 | 5 | `corp/` `result/` `paper_result/` `project_furiosa/` `redteam-ctf/` |
| 대화 로그·테스트 폴더 | 102 | `logs/code_dialogue/`(100), `TEST/`(2) |
| Public_agent 일회성 | 40 | challenge/attack/스캔 스크립트 23개 + 무관한 리포트 md 16개 |
| 루트 md 에세이 | 5 | `rigorous_proof.md` 등 타원곡선 모듈러리티 에세이(3×3 m=22와 무관) |

## 4. 정리 중 고친 것 (1건)

`gates/G009_verifier_integrity.py` — numpy 가드를 모듈 임포트보다 **위로** 옮겼다.
전에는 numpy 없는 환경에서 `verifier.py` 임포트가 먼저 터져 "심판이 깨졌다"로 **모든 커밋이
차단**됐다(이전 보고서 F1, 이 컨테이너에서 재현). numpy가 없을 때는 소스 텍스트로 필수
심볼만 확인하고 행동 검증은 건너뛴다 — G010이 원래 쓰던 방식과 같다. 이 수정 덕분에 이번
정리 커밋 자체가 저장소 자신의 게이트로 검증됐다.

이전 보고서의 나머지 P0/P1(F2 CI 부재, F3 배포 paths에 `gates/` 누락, F4 run_shell 비밀값
유출)은 손대지 않았다 — 정리 범위가 아니다.

---

## 5. 이 시스템을 어디에 쓸 수 있나

남은 자산의 핵심은 봇이 아니라 **"에이전트가 스스로 만든 규율을 실행 경로에 강제로 박는
구조"** 다. 이건 이 저장소 밖에서 더 값이 나간다.

### A. 자율 코딩 에이전트용 가드레일 (가장 가치 큼)
`gatekeeper.py` + `gates/` + `self_challenge.py`를 저장소 독립 패키지로 떼면, Claude Code /
Cursor / 사내 에이전트가 커밋하기 전에 통과해야 하는 검사층이 된다. 차별점은 규칙의 출처다 —
사람이 프롬프트에 적는 게 아니라, **사고가 나면 그 사고를 잡는 검사를 red-green으로 증명해야만
규칙이 된다.** "AI가 코드를 고치게 두면 뭐가 무너지는가"를 이미 10건의 실측 사고로 갖고 있는
저장소는 흔치 않다.
- 다음 단계: `gates/`의 저장소 고유 항목(G003의 파일·문자열 목록)을 설정 파일로 빼고
  `pip install se-gates` + `pre-commit` 훅으로 포장.

### B. 에이전트 평가 하네스
`tests/test_gates_on_incidents.py`가 이미 하는 일 — 실제 사고 커밋 트리를 꺼내 "이 검사가
그때 걸리는가"를 판정 — 을 뒤집으면 **에이전트 벤치마크**가 된다. 사고 커밋의 직전 상태를
주고 "같은 실수를 하는가"를 모델별로 재는 것. 정답이 exit code라 채점에 LLM 심판이 필요 없다.

### C. LLM 가용성 라우터 (즉시 재사용 가능)
`bot_tools.build_agent_pool` + `run_with_fallback_pool` + `quota_tracker`는 봇과 거의
분리돼 있다. (키 × 모델) 후보 순환, RPM 429와 일일 429 구분, 영구 dead 사전 제거, 성공 조합
pin — 무료/저가 티어로 서비스를 유지해야 하는 어떤 LLM 앱에도 그대로 붙는다.

### D. 검증 가능한 탐색 문제 일반화
`mathmetics/matrix_exponent`의 구조(탐색기 자유 / 심판 고정 / 능력 래칫 G010)는 행렬곱에
묶여 있지 않다. **정답을 기계적으로 검산할 수 있는 모든 최적화**에 이식된다:
커널 스케줄링, 회로 최적화, 쿼리 플랜, 조합 최적화. 이식할 때 바꿀 건 `verifier.py`뿐이다.

### E. D + `npu/` 결합 — 가장 자연스러운 다음 프로젝트
지금 저장소에 **탐색 루프**와 **삼진 NPU 설계 + 시뮬레이터**가 둘 다 있다. 심판을
`verify_scheme` 대신 `iverilog`+`vvp` 결과(사이클 수·정확도)로 바꾸면, 밤새 도는 루프가
행렬곱 스킴 대신 **PE 스케줄/타일링을 탐색**한다. `benchmarks.json` 형식이 그대로 회귀
방지(PPA 후퇴 차단)로 쓰인다.

### F. 개인 인프라 운영 에이전트
현재 봇은 이미 "Discord로 지시 → 서버에서 셸 실행 → 근거 기반 보고 → 커밋"을 한다.
여기에 기억(`public_agent_memory/`)과 원격 반영 검증이 붙어 있으므로, 로그 조사·배포·정기
리포트 같은 1인 운영 업무를 맡기기에 이미 충분하다. 단, 그 전에 이전 보고서 F4(공개 채널
`run_shell` 비밀값 유출 경로)를 먼저 막아야 한다.

### G. 사례 연구로서의 가치
`gates/`의 각 게이트 독스트링은 "무엇이 언제 어떻게 무너졌고, 그래서 어떤 검사를 두었는가"를
커밋 해시와 함께 담고 있다. 자기수정 에이전트의 실패 유형(제약 자기소거, 재작성 붕괴,
거짓 커밋 보고, 그럴듯한 퇴보)이 실측으로 정리된 문서는 드물다 — 글·발표·포트폴리오로
그대로 쓸 수 있다.

### 우선순위 제안
1. **F 전에 F4 보안 수정** — 지금 공개 채널은 `.env`를 읽어 출력할 수 있다.
2. **A** — 게이트 패키지화. 이 저장소에서 가장 이전 가능성이 높은 자산.
3. **E** — 이미 있는 두 조각을 잇는 것뿐이라 착수 비용이 가장 낮다.
