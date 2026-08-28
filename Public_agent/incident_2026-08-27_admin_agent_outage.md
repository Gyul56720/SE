# 2026-08-27 admin agent 다운 & API 쿼터 소진 디버깅 정리

## 증상
- public 채널 agent가 Gemini 무료 티어 쿼터(하루 500회, 프로젝트 단위) 초과로 429 반복
- 사용자가 admin 채널에 상태 점검/수정을 요청하는 도중 `se-discord-bot.service`가 내려감
- 이후 admin의 fallback 키까지 429가 나서 "다른 키인데 왜 같이 소진되냐"는 의문 발생

## 원인 (확인된 것 위주)
1. **admin/public 서비스 다운**: admin agent가 `.env` 수정 지시를 받고 `run_shell`로 값을 바꾼 뒤
   스스로 `systemctl restart se-discord-bot`을 실행 → 자기 자신이 속한 프로세스가 재시작되며
   응답을 못 보내고 끊김. `.env` 값 자체는 손상되지 않았음(나중에 curl로 두 키 다 정상 확인).
2. **fallback 키까지 소진**: VM에 로컬로 이미 적용돼 있던 `main_public.py` 패치가
   모듈 임포트 시점(=서비스 시작/재시작마다)에 `candidate_llm.invoke("ping")`으로 실제 API를
   호출하는 구조였음 → 트러블슈팅 중 반복된 재시작 자체가 두 키의 쿼터를 갉아먹음.
3. **재시작이 반복된 진짜 이유**: `.github/workflows/deploy-oracle.yml`이 `discord_bot_server.py`
   등 특정 파일이 바뀐 push마다 자동으로 `git pull` + `systemctl restart`를 실행함. admin/public
   agent가 self-modification 권한으로 이 파일들을 고쳐서 자동 push하면 그때마다 재배포가 걸림.
   이건 의도된 기능(코드 고치면 자동 반영)이라 없애지 않고, 대신 self-correction 루프가 이
   재시작에 안 죽게 만드는 쪽으로 대응함.

## 반영한 수정 (commit 순서대로)
- `discord_bot_server.py`: `GEMINI_API_KEY_FALLBACK`이 비어있어도 admin 채널이 `KeyError`로
  죽지 않고 `GEMINI_API_KEY`로 대체하도록 변경.
- `main_public.py`: public agent도 429를 만나면 `GEMINI_API_KEY_FALLBACK`으로 자동 재시도.
  단, 시작 시 ping 테스트 없이 **실제 요청이 실패했을 때만** 전환(재시작마다 쿼터 안 태움).
  두 에이전트가 같은 `MemorySaver`를 공유해서 전환돼도 대화 맥락 유지.
- `Public_agent/Loop.py` (`AutoRegressivePatcher`):
  - `max_iters` 기본값 50 → 100
  - `checkpoint_path`: 매 iteration마다 진행 상태(JSON, 원자적 교체)를 저장하고, 재시작 후
    중단된 지점부터 재개. 성공하면 삭제(=재개용이라 다 쓰면 필요 없음).
  - `history_log_path`: 체크포인트와 별개로, 성공/실패 불문 모든 diff+이유를 append-only
    JSONL로 영구 보존 (나중에 다른 LLM 호출이 참고할 수 있게).
- `Public_agent/run_detached.py` (신규): `systemd-run --scope` + `setsid nohup`으로 스크립트를
  봇 서비스 cgroup 밖에서 백그라운드 실행 + `ps`로 생존 확인까지 코드로 고정. 재배포로 봇이
  재시작돼도 루프가 안 죽게 하는 걸, 매번 LLM이 셸 명령을 조합하지 않고 한 줄 호출로 되게 함.

## 남은 이슈 / 확인 필요
- VM 로컬 `main`과 origin이 여러 번 갈라졌었음(로컬 자동커밋 vs 이 세션의 push) — 한 번
  merge conflict(`main_public.py`)로 정리했음. 앞으로 VM에서 직접 커밋하는 습관이 남아있으면
  또 갈라질 수 있으니 주의.
- 두 API 키가 같은 Google 계정 소속인지 서로 다른 계정인지 확인함(→ 다른 계정 확인됨).
  같은 계정/프로젝트였다면 fallback을 나눠도 쿼터가 공유돼 의미가 없었을 것.
- `run_shell`은 실행한 명령 자체를 로그에 안 남긴다(stdout/stderr만 반환) — 이번처럼 agent가
  정확히 뭘 실행했는지 사후 추적이 안 되는 문제가 있음. 필요하면 개선 검토.
