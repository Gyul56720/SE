# orchestrator — 문제 분해·실행·검증 파이프라인

문제를 하위 알고리즘 DAG 로 쪼개(플래너), 위상정렬로 실행하며 노드별 신뢰 verifier 로
검증(오케스트레이터)하고, 실패하면 그 사유를 플래너에 되먹여 다시 시도한다(drive 루프).
모든 LLM 호출은 Gemini 쿼터/모델 자동전환을 견딘다(llm_pool).

## 계층 (아래가 신뢰 기반, 위가 불안정한 LLM)

- `planner.py` — 문제 → DAG(plan.json + components/*.py) 생성. 실패 시 노드 수리
  (`repair_node`) / 계획 재수립(`replan`). LLM(가장 불안정).
- `orchestrator.py` — DAG 실행·검증·복원. 노드별 verifier 통과한 것만 채택.
- `plan_schema.py` — DAG 데이터 모델(노드=goal·deps·component·verifier·status).
- `llm_pool.py` — 모든 LLM 호출의 (키×모델) 폴백. quota_tracker 재사용
  (429 소진→다음, 404/403→영구 제외, 503→재시도, 성공→pin).
- `solve.py` — 진입점. `drive()` 가 실행→검증→수리→재실행 루프를 목표 달성까지 돈다.

## 사용 (VM)

```bash
cd ~/SE
git pull origin main
# 문제 하나 풀기 (GEMINI_API_KEY 필요)
python3 orchestrator/solve.py "N=91에서 x^2 ≡ 16 (mod N)의 모든 해를 구하라"
# 도중에 죽었으면 같은 런을 이어서 (복원 + 남은 실패 노드 수리)
python3 orchestrator/solve.py --resume orchestrator/runs/<디렉토리>
# 루프 한도 조절 (기본: 라운드 3, 노드당 수리 2, 재계획 1)
python3 orchestrator/solve.py --resume <런> --max-repair-rounds 5 --max-node-repairs 3

# 되먹임 루프 자체의 회귀 테스트 (LLM 없이 실측 런으로 red-green)
python3 tests/test_planner_repair.py
```

산출물은 `orchestrator/runs/<타임스탬프>/` 에 plan.json + components/*.py + results/*.json
으로 남아 git 으로 복원 가능하다.

## 사용 (Discord admin 채널)

`../orchestrator_tool.py` 가 이 파이프라인을 봇 도구로 노출한다. `orchestrator_solve` 가 런을
백그라운드(setsid)로 띄우고 런 이름/로그 경로를 즉시 돌려주며, 진행은 `orchestrator_status`,
이어서 돌리기는 `orchestrator_resume`, 중지는 `orchestrator_stop` 이다. 런 이름 인자는
`runs/` 바로 아래로만 해석되고(G014 가 카나리로 감시), 도구 출력은 비밀값이 마스킹된다.
공개 채널에는 붙이지 않는다 -- 자식 환경에 키가 없어 계획 단계에서 실패한다.

## 되먹임 루프 (목적지향의 조건)

계획→실행→검증까지만 이어지면 개루프다. 실측: `runs/20260829-224043` 은 최종 노드가
`solve: 7`(JSON 왕복으로 dict 키 7 이 "7" 이 된 KeyError) 로 죽었는데, 실패 사유가 attempts 에
쌓이기만 하고 아무도 읽지 않아 재개해도 같은 코드를 다시 돌렸고 같은 예외가 두 번 쌓인 채
영구히 미완으로 남았다. `solve.drive()` 가 그 간선을 잇는다 -- 싼 단계부터:

1. **재실행** — verified 노드는 건너뛴다(오케스트레이터).
2. **노드 수리** — 실패 노드의 `solve` 만 실패 사유 + 선행 노드의 *실제* 결과값을 보고 다시
   쓴다(`planner.repair_node`). 노드당 `--max-node-repairs` 회까지.
3. **계획 재수립** — 수리로 안 되면 DAG 자체가 틀린 것이므로 통째로 다시 세운다
   (`planner.replan`). 이전 plan/components/results 는 `attempts/attemptN/` 으로 보존한다.
4. **포기** — 그래도 미완이면 사실대로 `status="incomplete"` + `reason` 을 반환한다.

안전 규칙 두 개:
- **verifier 는 절대 다시 쓰지 않는다.** 실패를 채점표를 고쳐 없애면 검증 채택 원칙이 무너진다.
  수리는 `component` 파일만 덮어쓰고 verifier 는 읽기 전용으로 프롬프트에 넣는다.
- **깨진 수리안은 채택하지 않는다.** 문법 오류·`def solve` 부재·빈 응답이면 파일을 덮어쓰지
  않는다(그나마 돌던 코드를 지우면 재개 기반이 무너진다).

## 원칙

제안이 아니라 검증된 채택. 플래너가 엉뚱한 DAG 를 내도 노드 verifier 가 통과 안 시키면
그 결과는 채택되지 않는다. 실행 중 죽어도 plan.json 상태에서 재개한다. 수리 횟수도 plan.json
에 남으므로, 재개해도 같은 수리를 무한 반복하지 않고 이어서 센다.
