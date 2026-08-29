# orchestrator — 문제 분해·실행·검증 파이프라인

문제를 하위 알고리즘 DAG 로 쪼개(플래너), 위상정렬로 실행하며 노드별 신뢰 verifier 로
검증(오케스트레이터)한다. 모든 LLM 호출은 Gemini 쿼터/모델 자동전환을 견딘다(llm_pool).

## 계층 (아래가 신뢰 기반, 위가 불안정한 LLM)

- `planner.py` — 문제 → DAG(plan.json + components/*.py) 생성. LLM(가장 불안정).
- `orchestrator.py` — DAG 실행·검증·복원. 노드별 verifier 통과한 것만 채택.
- `plan_schema.py` — DAG 데이터 모델(노드=goal·deps·component·verifier·status).
- `llm_pool.py` — 모든 LLM 호출의 (키×모델) 폴백. quota_tracker 재사용
  (429 소진→다음, 404/403→영구 제외, 503→재시도, 성공→pin).
- `solve.py` — 문제 하나로 플래너+오케스트레이터를 한 번에 돌리는 진입점.

## 사용 (VM)

```bash
cd ~/SE
git pull origin main
# 문제 하나 풀기 (GEMINI_API_KEY 필요)
python3 orchestrator/solve.py "N=91에서 x^2 ≡ 16 (mod N)의 모든 해를 구하라"
# 도중에 죽었으면 같은 런을 이어서 (복원)
python3 orchestrator/solve.py --resume orchestrator/runs/<디렉토리>
```

산출물은 `orchestrator/runs/<타임스탬프>/` 에 plan.json + components/*.py + results/*.json
으로 남아 git 으로 복원 가능하다.

## 원칙

제안이 아니라 검증된 채택. 플래너가 엉뚱한 DAG 를 내도 노드 verifier 가 통과 안 시키면
그 결과는 채택되지 않는다. 실행 중 죽어도 plan.json 상태에서 재개한다.
"""
