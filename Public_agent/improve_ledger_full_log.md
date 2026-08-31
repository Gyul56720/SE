# Improve Ledger Full Log

```json
{
  "version": 3,
  "best_by_target": {
    "3,22": 0.00010727281865109621
  },
  "best_seen_by_target": {
    "3,22": 8.597496031710997e-05
  },
  "attempts": [
    {
      "ts": 1788099970.9251697,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "gate_rejected",
      "detail": "[게이트 차단] 커밋하지 않았다. 아래를 고친 뒤 다시 시도하라.\n\nG010 -- 이미 도달 가능한 기준을 후퇴시키지 않는가 (능력 래칫)\n  - 기준 'matmul_b3_m23_laderman' (b=3, m=23) 을 넉넉한 예산(seeds=8, iters=1500)으로도 재현하지 못했다 (최소 잔차 7.43e-02)."
    },
    {
      "ts": 1788100149.2749858,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "gate_rejected",
      "detail": "[게이트 차단] 커밋하지 않았다. 아래를 고친 뒤 다시 시도하라.\n\nG010 -- 이미 도달 가능한 기준을 후퇴시키지 않는가 (능력 래칫)\n  - 기준 'matmul_b3_m23_laderman' (b=3, m=23) 을 재현하지 못했다."
    },
    {
      "ts": 1788111507.440471,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.0007955721055192399,
      "best_prev": 0.0004001588668050879
    },
    {
      "ts": 1788112627.5901742,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.0005695609597360284,
      "best_prev": 0.0004001588668050879
    },
    {
      "ts": 1788114223.4095504,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "applied",
      "bench_residual": 0.0002763060727274864,
      "solved": false,
      "pushed": true
    },
    {
      "ts": 1788118700.5142903,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.0002876616547707177,
      "best_prev": 0.0002763060727274864
    },
    {
      "ts": 1788120400.4005005,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.00036901423879770375,
      "best_prev": 0.0002763060727274864
    },
    {
      "ts": 1788122742.423245,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "applied",
      "bench_residual": 0.00016123699936939712,
      "solved": false,
      "pushed": true
    },
    {
      "ts": 1788124987.2282426,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.00023617160058332786,
      "best_prev": 0.00016123699936939712
    },
    {
      "ts": 1788127411.0726178,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.00017994725454893278,
      "best_prev": 0.00016123699936939712
    },
    {
      "ts": 1788132063.4294186,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "applied",
      "bench_residual": 0.00010727281865109621,
      "solved": false,
      "pushed": true
    },
    {
      "ts": 1788135125.1678905,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.00015152184485220615,
      "best_prev": 0.00010727281865109621
    },
    {
      "ts": 1788141582.8371515,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.00014972618170370992,
      "best_prev": 0.00010727281865109621
    },
    {
      "ts": 1788144444.1474988,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.0001589928517841272,
      "best_prev": 0.00010727281865109621
    },
    {
      "ts": 1788147763.3232977,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.00012953748760127803,
      "best_prev": 0.00010727281865109621
    },
    {
      "ts": 1788150767.0621514,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "gate_rejected",
      "detail": "G010 -- 래칫 검증 실패"
    },
    {
      "ts": 1788154275.2450783,
      "backend": "llm_proposer",
      "target": "3,22",
      "result": "no_improvement",
      "bench_residual": 0.00013948656875656447,
      "best_prev": 0.00010727281865109621
    }
  ],
  "checks": 40,
  "last_check": {
    "ts": 1788153641.8936415,
    "target": "3,22",
    "stagnant": true,
    "reason": "정체",
    "observed": 0.00012559558523640138,
    "best_seen_prev": 8.597496031710997e-05,
    "threshold": 7.737746428539897e-05
  }
}
```
