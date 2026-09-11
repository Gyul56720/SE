---
topic: '2-D Controller Structure (Entropy & Badness)'
saved_at: 2026-09-11T15:07:40.814222+00:00
author_discord_id: 732577811172163605
source: discord-public-channel-agent
---

# 2-D Controller Structure (Entropy & Badness)

제안된 2-D controller 구조:
1. Entropy ($H_t$) -> Continue/Halt 판단 (Adaptive Threshold $T_t = T_0 + \alpha B_t$)
2. Badness ($B_t$) -> Stay/Change direction 판단 ($B_t > B_{\text{critical}}$ 시 latent direction 전환)
- 매트릭스:
  - Entropy 낮음 & Badness 낮음: 즉시 종료
  - Entropy 낮음 & Badness 높음: 방향만 변경
  - Entropy 높음 & Badness 낮음: 같은 방향으로 추가 탐색
  - Entropy 높음 & Badness 높음: 방향 변경 + 추가 계산
- 차별점: Structural Bias(Badness)
