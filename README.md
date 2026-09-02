# SE — 자기수정 에이전트 저장소

Discord로 지시를 받아 스스로 코드를 고치고, 고친 결과를 강제 게이트로 검사한 뒤에만
커밋하는 에이전트 시스템. 2026-09-02 정리로 살아있는 세 시스템만 남겼다.

## 1. Discord 에이전트 (봇 본체)

Oracle VM에서 systemd로 상시 구동. admin 채널(화이트리스트)과 public 채널(무제한) 둘 다
Gemini + LangGraph ReAct 에이전트가 처리하고, 둘 다 `run_shell`로 저장소를 직접 고칠 수 있다.

| 파일 | 역할 |
|---|---|
| `discord_bot_server.py` | 이벤트 라우팅, admin 에이전트, `git_sync`(게이트 → 커밋 → push → 원격 반영 확인) |
| `main_public.py` | 공개 채널 에이전트 정의 |
| `bot_tools.py` | 공유 도구(`run_shell`/`search_memory`/`save_memory`/`write_public_answer`) + (키×모델) 폴백 풀 |
| `orchestrator_tool.py` | admin 채널 도구가 orchestrator 런을 백그라운드로 띄우고/보고/재개/중지 |
| `quota_tracker.py` | 일일 소진·RPM 쿨다운·영구 dead·성공 후보 pin |
| `agent_context.py` | 요청 단위 호출자 맥락과 게스트 차단 |
| `agent_memory.py` | `public_agent_memory/` 장기 기억(쓰기 경로 강제 + 커밋) |
| `public_agent_files.py` | 공개 채널 산출물을 `Public_agent/` 안으로만 |
| `memory_hygiene.py` | 코드/게이트와 모순되는 기억 노트 정리 |
| `log_streamer.py` | 로그 스트리밍 서비스 |

**안전장치(커밋 경로 위에 강제):**

- `gatekeeper.py` + `gates/` — 커밋 직전 게이트 9개(G003·G004·G005·G008·G009·G011~G014)를
  돌리고 하나라도 걸리면 커밋하지 않는다. 산문 규칙은 읽히지 않으면 아무것도 막지 못하므로,
  규칙을 실행 경로에 올린 것이 요점이다. 전체 ~0.6초.
- `scripts/capability_ratchet.py` — 능력 래칫(옛 G010). CP-ALS를 실제로 돌리는 무거운
  검사라 커밋 경로에서 빼서 `scripts/check_improve.sh`(점검 시점)로 옮겼다.
- `self_challenge.py` — 진단을 검사 코드로 써서 RED(사고 커밋에서 실패) / GREEN(현재 통과)
  두 실행을 통과해야만 `gates/`로 승격한다. 증명되지 않은 진단은 게이트가 되지 못한다.
- `tests/test_gates_on_incidents.py` — 실제 사고 커밋 트리에서 게이트가 정말 걸리는지 재증명.
  (전체 이력이 필요하다. shallow clone에서는 돌지 않는다.)

게이트는 두 곳에서 강제된다: VM의 `git_sync()`(봇이 스스로 커밋할 때)와
`.github/workflows/gates.yml`(누가 어디서 push하든). 후자는 전체 이력을 받아
사고 회귀 증명까지 돌리고, 의존성이 실제로 깔렸는지 먼저 확인한다 -- 설치가 반쯤
실패해 게이트가 조용히 SKIP 되면서 CI만 초록으로 뜨는 것을 막는다.

```bash
python3 gatekeeper.py                 # 게이트 전체 실행 (통과 0 / 위반 1)
python3 gatekeeper.py --list          # 등록된 게이트와 그 사고 이력
python3 self_challenge.py prove --candidate <검사.py> --broken-commit <사고커밋>
python3 memory_hygiene.py             # dry-run, --apply 로 실제 정리
```

## 2. 오케스트레이션 에이전트 — `orchestrator/`

문제를 계획(plan.json) → 컴포넌트 코드 + 검증 코드로 쪼개서 실행하고, 실패하면 계획을
고쳐 다시 시도한다. 실행 기록은 `orchestrator/runs/<이름>/`에 남는다.
자세한 내용은 `orchestrator/README.md`.

**Discord(admin 채널)에서 부를 수 있다** — `orchestrator_tool.py`가 다리다. 런은 수 분
걸리므로 백그라운드(`setsid`)로 띄우고 런 이름/로그 경로를 즉시 돌려준다:

| 도구 | 하는 일 |
|---|---|
| `orchestrator_solve(problem)` | 새 런을 띄운다. 살아 있는지 확인한 뒤에만 "시작했다"고 답한다 |
| `orchestrator_status(run)` | 노드별 검증 상태·마지막 실패 사유·최종 결과·로그 끝부분 |
| `orchestrator_resume(run)` | 죽었거나 미완인 런을 이어서(검증된 노드는 건너뛴다) |
| `orchestrator_stop(run)` | 프로세스 그룹째 중지. 산출물은 남으므로 재개 가능 |

런 이름 인자는 `orchestrator/runs/` 바로 아래로만 해석된다(G014가 탈출 카나리로 감시).
자식은 새 세션에 들어가지만 systemd cgroup은 벗어나지 못한다 -- 재배포로 봇이 재시작되면
돌던 런도 죽는다. 그때는 `orchestrator_resume`으로 이어서 돌린다.

## 3. 행렬곱 자가개선 루프 — `mathmetics/matrix_exponent/`

`se-matrix-search.service`로 밤새 돌리는 무한 개선 루프. 3×3 행렬곱 스킴을 CP-ALS로 탐색하고
(`searcher.py`), 심판(`verifier.py`)이 정확 검산으로만 통과시킨다.

- `self_improve_loop.py` / `improve_agent.py` — 탐색 전략 자체를 고쳐가는 루프
- `benchmarks.json` — 이미 도달한 기준. G010(능력 래칫)이 이 기준의 후퇴를 막는다
- `jump_searcher*.py`, `run_jump_project.py` — IJP(도약 탐색) 계열 실험
- 심판 무결성은 G009, 검증 함수의 공허한 통과는 G008이 막는다
- `scripts/check_improve.sh` — 서버에 배포된 코드와 루프 상태 점검

## 그 밖에 남긴 것

| 경로 | 왜 남겼나 |
|---|---|
| `npu/` | 1.58비트 삼진 NPU(SystemVerilog) 설계·검증 스위트. 2026-09-02 작업분 |
| `public_agent_memory/` | 봇이 실제로 읽고 쓰는 장기 기억 |
| `Public_agent/` | 공개 채널 산출물 폴더 + m=22/IJP 기록, 봇 사고 기록 |
| `ai_concept/`, `법이론서/`, `편입수학 이론서/`, `mathmetics/LLM_응답품질/` | 옵시디언으로 동기화되는 학습·이론 문서 |
| `reports/` | 시스템 분석·정리 보고서 |
| `deploy/`, `.github/workflows/` | systemd 유닛과 배포 워크플로 |

## 배포

`main`에 push하면 `.github/workflows/deploy-oracle.yml`이 Oracle VM에 SSH로 들어가
`git reset --hard origin/main` 후 서비스를 재시작한다. 서비스는 `deploy/*.service` 세 개
(`se-discord-bot`, `se-log-streamer`, `se-matrix-search`).

## 설정

`.env.example`을 `.env`로 복사해 채운다. `.env`는 절대 커밋하지 않는다(G004가 자격증명
커밋·로그 출력을 막는다). 의존성은 `requirements.txt`.
