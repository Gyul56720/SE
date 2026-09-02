# 에이전트 분석 및 평가 (2026-09-02)

대상: 이 저장소가 운영하는 자기수정 에이전트 시스템
(`discord_bot_server.py` / `main_public.py` / `bot_tools.py` + 강제 게이트 `gates/` +
증명 승격 `self_challenge.py` + 기억 `agent_memory.py` / `memory_hygiene.py`).

방법: 코드 정독 + 실제 실행. 주장이 아니라 실행 결과만 근거로 적는다. 이 저장소 자신의
규율("검증했다면 검산했음을 보여라")을 이 보고서에도 적용했다. 실행 환경은 이 세션의
컨테이너이며 `numpy`/`pytest` 미설치, 저장소는 shallow clone(62 커밋)이다 — 이 사실
자체가 아래 F1·F8의 근거가 된다.

---

## 1. 구조 요약

| 층 | 구성 | 역할 |
|---|---|---|
| 입구 | `discord_bot_server.on_message` | admin 채널(화이트리스트) / public 채널(무제한) 라우팅 |
| 두뇌 | LangGraph ReAct + Gemini, `build_agent_pool` | (키 × 모델) 후보 풀, 실패 시 순차 폴백 |
| 손 | `run_shell`, `search_memory`, `save_memory`, `write_public_answer` | 셸 전권 + 기억 + 산출물 |
| 가용성 | `quota_tracker` | 일일 소진/RPM 쿨다운/영구 dead/성공 후보 pin |
| 안전장치 | `gatekeeper.run_gates` (G001~G010) | 커밋 직전 강제 차단 (fail-closed) |
| 규율 승격 | `self_challenge.py prove` | RED/GREEN 실행 증명을 통과한 진단만 `gates/`로 |
| 사후 확인 | `_verify_pushed`, `_integrity_note` | "저장했다" 주장 vs 원격 실제 상태 대조 |
| 기억 | `public_agent_memory/` 53개 노트 + `memory_hygiene.py` | 노트 축적 + 모순 노트 정리 |

## 2. 강점 (실제로 드문 설계)

1. **산문이 아니라 실행 경로 위의 강제.** `gates/__init__.py`가 명시한 진단이 정확하다 —
   "20:35에 임포트 검사 필요를 저장하고 20:37에 임포트 불가 코드를 push했다". 해법이
   프롬프트 추가가 아니라 `git_sync()` 커밋 직전 게이트라는 점이 핵심이다. 에이전트가
   노트를 읽든 말든 막힌다.
2. **게이트 승격의 위조 불가 오라클.** `self_challenge.prove`는 사고 커밋 트리를 꺼내
   RED(고치기 전 실패) → GREEN(고친 뒤 통과) 두 실행을 요구한다. 모델의 자기 확신이
   개입할 여지가 없다. 자가수정 시스템에서 "진단이 옳다"를 exit code로 환산한 것은
   이 저장소의 가장 강한 자산이다.
3. **보고 무결성 자동 대조.** `_claims_persistence` + `_remote_status_note`가 "커밋했다"는
   답변에 대해 실제 원격 상태를 붙인다. 환각 보고를 프롬프트가 아니라 코드로 막는다.
4. **가용성 공학이 실측 기반.** 키 라벨 해시(접두사 충돌), RPM 429와 일일 429 구분,
   permanent dead 사전 제거, 성공 후보 pin — 모두 겪은 사고에서 역산된 것이며 주석에
   근거 날짜가 남아 있다.
5. **경로 강제.** `agent_memory._resolve_inside_memory`, `public_agent_files`가 쓰기
   경로를 코드로 제한하고, 커밋 대상도 해당 경로로 좁힌다.

## 3. 결함 (실측 근거 순)

### F1 [높음] G009가 numpy 없는 환경에서 모든 커밋을 차단한다 — 재현됨
`python3 gatekeeper.py` 실행 결과(이 컨테이너):

```
[게이트 차단] 커밋하지 않았다.
G009 -- 자가 수정 심판(verifier)이 약화되지 않았는가
  - mathmetics/matrix_exponent/verifier.py 를 임포트할 수 없다 -- 심판이 깨졌다: No module named 'numpy'
```

G009 자신의 독스트링은 "numpy가 없어 행동 검증을 못 하는 환경에서는 정적 검사(1,2)만
수행한다"고 적었지만, 코드는 정적 검사보다 **먼저** `_load(path)`로 모듈을 실행한다.
`verifier.py`는 최상위에서 `import numpy as np`를 한다. 따라서 numpy 없는 환경에서는
"심판이 깨졌다"는 (사실과 다른) 위반으로 게이트 전체가 차단되고, 에이전트는 아무것도
커밋할 수 없다. G010은 같은 상황을 올바르게 처리한다(`import numpy` 실패 시 조용히 skip).
즉 같은 저장소 안에 정답 패턴이 이미 있다.

- 영향: 배포 VM에서 numpy가 빠지거나 깨지는 순간, 봇의 저장 경로 전체가 정지한다.
  실패 메시지가 "의존성 없음"이 아니라 "심판이 깨졌다"여서 오진을 유도한다.
- 최소 수정: `check()` 맨 앞에서 `import numpy` 실패 시 정적 검사만 수행하도록
  numpy 가드를 `_load` 호출보다 위로 옮긴다(G010과 동일 형태).

### F2 [높음] 게이트가 커밋 경로 중 한 곳에만 있다 — CI 없음
`gatekeeper.run_gates`를 부르는 곳은 `discord_bot_server._git_sync_locked` 하나뿐이다.
`.github/workflows/`에는 게이트도 `tests/`도 돌리는 잡이 없다(`deploy-oracle.yml`은 배포만,
`se-agent.yml`은 수동 폴백). 따라서 VM 밖의 모든 push — 개발 세션, 웹 UI, 다른 머신 —
는 게이트를 통과하지 않는다. "커밋 경로 위에 놓았다"는 설계 의도가 경로 하나에만
적용돼 있다.
- 최소 수정: push/PR에서 `python3 gatekeeper.py`와 `tests/test_gates_on_incidents.py`를
  돌리는 워크플로 1개 추가(`fetch-depth: 0` 필수, F8 참조).

### F3 [높음] 새 게이트가 서버에 도달하지 않는다
`deploy-oracle.yml`의 `paths:` 목록에 `gates/**`, `gatekeeper.py`, `self_challenge.py`,
`memory_hygiene.py`, `public_agent_files.py`가 없다. 게이트만 추가/수정하는 커밋은 배포를
트리거하지 않으므로, `self_challenge`로 승격한 게이트가 VM의 `git_sync`에 반영되기까지
무관한 다른 파일이 바뀌는 다음 배포를 기다려야 한다.
이것은 같은 파일이 주석으로 두 번이나 기록한 실패 유형("코드가 좋아져도 서버에 도달하지
못하는 경로", searcher.py·bot_tools.py 사례)의 **세 번째 재발**이다. 강제 장치 자신이
그 경로에서 빠져 있다는 점에서 앞의 둘보다 나쁘다.
- 최소 수정: `paths:`에 위 4~5개 항목 추가.

### F4 [높음/보안] public 채널의 경로 제한은 명목상이다
`write_public_answer`는 `Public_agent/` 밖으로 못 나가고 push도 안 한다 — 그러나 같은
에이전트가 `run_shell`(무제한 `bash -lc`, cwd=REPO_DIR)을 함께 가진다. 즉 화이트리스트
없는 채널의 누구나 `cat .env`, 임의 경로 쓰기, `git push`를 시킬 수 있다. G004는
**커밋되는 파일**의 자격증명만 보므로 stdout으로 Discord에 흘러나가는 유출은 못 막는다.
run_shell 부여 자체는 사용자가 명시적으로 감수한 위험이지만, "경로가 강제된다"는 문서상
안전감과 실제 권한 사이의 간극은 별개의 문제다.
- 최소 수정(권한 축소 없이 가능): `run_shell` 반환값에 대해 환경변수 비밀값 스크럽
  필터를 적용(로드된 `GEMINI_API_KEY`/`DISCORD_BOT_TOKEN` 등의 리터럴을 `***`로 치환).
  도구를 없애지 않으면서 유출 경로만 좁힌다.
- **2026-09-02 조치 완료.** `secret_filter.py` 신설: (1) 공개 채널의 `run_shell` 자식
  프로세스 환경에서 비밀 변수를 제거하고, (2) 모든 채널의 도구 출력과 `save_memory`/
  `write_public_answer` 내용에서 알려진 비밀값을 base64/hex 표현까지 함께 마스킹한다.
  `run_shell` 권한 자체는 그대로다. 이 규율은 산문이 아니라 게이트 **G011**로 승격됐고
  (red-green 증명: RED=`c3b3b88`, GREEN=현재), 가짜 비밀값을 넣어 실제로 마스킹되는지
  행동 검증까지 한다. 남는 한계: 셸을 가진 상대가 값을 쪼개거나 다른 인코딩으로 내보내는
  우회는 못 막는다 -- 그건 프로세스 격리(별도 사용자/컨테이너)의 몫이다.

### F5 [중간] 게스트 차단 기본값이 자기 독스트링과 모순
`agent_context.py`는 "기본값으로 기존 ID를 남겨서 환경변수를 안 채워도 보안 정책이 조용히
풀리지 않게 하되"라고 적어놓고 `_DEFAULT_BLOCKED = ""`이다. `GUEST_BLOCKED_USER_IDS`가
비어 있으면 차단 목록은 공집합 — 정확히 "조용히 풀리는" 상태다. 주석을 사실에 맞추거나
기본값을 되살리거나 둘 중 하나여야 한다.

### F6 [중간] admin 경로에서 호출자 맥락이 설정되지 않는다
`current_author.set(...)`는 `main_public.run_public_agent`에만 있다. `run_admin_agent`에는
없으므로 admin 턴에서 `is_blocked()`는 항상 `"unknown"`을 보고(화이트리스트가 있어 실효
피해는 없다), `save_memory`가 남기는 작성자는 항상 `unknown`이 된다 — 추적/되돌리기를
위해 작성자를 남긴다는 `agent_memory` 설계 목적이 admin 쪽에서는 성립하지 않는다.
부수 위험: contextvar를 executor 스레드에서 set하므로, LangChain이 도구를 별도
스레드풀에서 실행하는 경로가 있으면 public 쪽 차단도 무력화될 수 있다(확인 필요 —
현재는 가설이며 실측하지 않았다).

### F7 [중간] `git add -A` + 단일 커밋 메시지 = 이력이 증거로 못 쓰인다
`_git_sync_locked`는 워킹트리 전체를 담고 메시지는 항상 "SE-agent: Discord 요청 처리 결과
자동 반영"이다(최근 15커밋 중 11개가 동일 문자열). 요청과 무관한 산출물이 함께 실려도
구분이 안 되고, ADMIN 프롬프트의 "함께 커밋된 파일이 있으면 요청과 무관해도 보고하라"는
규율을 사람이 사후 검증할 방법이 이력에 남지 않는다. G005는 **삭제량**만 보므로 무분별한
추가는 게이트에 걸리지 않는다(루트 `.py` 118개가 그 결과다).

### F8 [중간] 게이트 회귀 스위트가 shallow clone에서 traceback으로 죽는다 — 재현됨
`python3 tests/test_gates_on_incidents.py` 실행:
`subprocess.CalledProcessError: Command '['git','archive','1a82685']' returned non-zero exit
status 128` — 사고 커밋이 이 clone에 없기 때문이다(`git rev-parse --is-shallow-repository`
= true). "게이트가 실효를 매번 다시 증명한다"는 이 파일의 목적이 clone 형태에 따라 조용히
사라지고, 실패도 skip이 아니라 스택트레이스다. CI를 붙일 때(F2) `fetch-depth: 0`이
필수이며, 커밋이 없으면 명시적 SKIP으로 보고해야 한다.

### F9 [낮음] G010이 커밋마다 CP-ALS를 최대 12 × 2000 iter 돌린다
능력 래칫은 옳은 개념이지만 비용이 커밋 경로에 얹혀 있다. `git_sync`는 답변 전송 **후**
실행되므로 사용자 응답 지연은 아니지만, GIT_LOCK을 잡은 채 수 초~수십 초가 흐르면 동시
요청의 저장이 직렬로 밀린다. 벤치마크 재현은 커밋 게이트가 아니라 배포/야간 잡으로
옮기고, 커밋 시에는 결과 캐시를 확인하는 편이 구조적으로 맞다.

### F10 [낮음] 저장소 위생
루트에 `.py` 118개, 추적되는 ELF 바이너리 3개(`check_syntax`, `final_sim_exec`,
`final_sim_opt`, 각 16~18MB). 실험 산출물과 봇을 이루는 소스가 같은 평면에 섞여 있어
G003/G005가 "핵심 파일"을 손으로 열거해야 하는 원인이 된다.

### F11 [낮음] "쓸수록 아는 게 늘어난다"는 아직 약한 주장
`search_memory`는 불용어 제거 후 토큰 겹침 점수 상위 5개를 돌려주는 방식이고, 모델이
호출해야만 동작한다(자동 주입 아님). 노트 53개 규모에서는 동작하지만 정밀도 근거가 없고,
`memory_hygiene`이 지적한 "노트는 느는데 행동은 안 변한다"의 정량 지표(호출률, 적중률)가
수집되지 않는다.

## 4. 평가

| 항목 | 등급 | 근거 |
|---|---|---|
| 자기수정 안전장치 설계 | A− | 강제 게이트 + red-green 승격 + 원격 대조. 개념적으로 동급 사례가 드물다 |
| 안전장치의 실제 적용 범위 | C | F2(CI 없음), F3(게이트가 서버에 도달 안 함), F1(게이트가 스스로 전체 차단) |
| 가용성/장애 대응 | A− | 키×모델 폴백, RPM/일일 429 구분, dead 사전 제거, pin — 전부 실측 기반 |
| 보안 | C− | 무제한 채널 × 무제한 셸. 유출 경로에 필터 없음(F4), 차단 기본값 공집합(F5) |
| 관측 가능성/증거성 | B− | 원격 대조는 훌륭. 반면 커밋 이력이 균질해 사후 감사 불가(F7) |
| 기억 시스템 | B− | 경로/개수 강제와 위생 절차는 좋음. 검색 품질·효과 측정 없음(F11) |
| 저장소 위생 | D | 루트 118 py, 52MB 바이너리 추적, 실험물과 소스 혼재(F10) |

한 줄 요약: **규율 설계는 이 저장소의 강점이고, 그 규율이 실제로 닿는 범위가 약점이다.**
게이트는 잘 만들었는데 (a) 게이트가 서버에 배포되지 않고 (b) VM 밖 push에는 적용되지 않고
(c) 의존성 하나가 빠지면 스스로 전부를 막는다. 세 결함 모두 이 저장소가 이미 이름 붙인
실패 유형("코드가 서버에 도달하지 못하는 경로", "fail-closed의 오작동")에 속한다.

## 5. 권고 (비용 대비 효과 순)

- **P0 / 수분**: F1 — G009의 numpy 가드를 `_load` 위로 이동(G010과 동일 형태).
- **P0 / 수분**: F3 — `deploy-oracle.yml`의 `paths:`에 `gates/**`, `gatekeeper.py`,
  `self_challenge.py`, `memory_hygiene.py`, `public_agent_files.py` 추가.
- **P1 / 30분**: F2+F8 — push/PR에서 `gatekeeper.py`와 사고 회귀 스위트를 돌리는 워크플로
  (`fetch-depth: 0`), 사고 커밋 부재 시 SKIP 처리.
- **P1 / 30분**: F4 — `run_shell` 반환값 비밀값 스크럽(권한은 그대로 두고 유출 경로만 차단).
- **P2**: F5(기본값/주석 일치), F6(admin에서 `current_author.set`), F7(커밋 메시지에 요청
  요약 + 변경 파일 수 포함), F9(래칫을 야간 잡으로), F10/F11.

이 보고서 자체에 대한 주의: 이것도 산문이다. 이 저장소의 규율대로라면 F1·F3처럼 검사로
환산 가능한 항목은 노트가 아니라 게이트/워크플로로 옮겨야 실효가 있다.
