# policy_core — OS-독립 능동탐색 정책 코어 (C)

`recon/sensor_agnostic.py` 의 통합정책(물리 접지 관측모델 + belief + J 최대화 + 센서선택
창발 + RTA)을 **OS/ROS/Linux 없이 bare-metal MCU 에 이식 가능한 순수 C** 로 옮긴 것.

철학: **물리 → 관측모델 → belief → 능동정책 → 안전행동.** 정책 코어는 센서 종류·하드웨어·
OS 를 **모른다** — 추상 인터페이스(`PC_ObsModel` 함수포인터)만 본다. 센서 교체 = 어댑터
교체, 코어 재컴파일 없음.

## 계층

```
  Search Policy π   (policy_core.c)  ── 센서·HW·OS 모름, 결정적, 힙 없음
        │  추상 인터페이스: PC_Belief / PC_Vehicle / PC_ObsModel / PC_Action
  Runtime / Adapter (host_test.c, 또는 MCU 펌웨어)
        │  관측모델(Camera/LiDAR/Thermal…) · belief 갱신 · 센서관리 · 이동 · Safety
  Hardware Interface  (UART/SPI/I2C/CAN · timer · DMA)
        │
     Camera  LiDAR  IMU  …  →  MCU  →  Motor
```

## 핵심 인터페이스 (센서/차량을 코어서 숨김)

```c
PC_Action pc_policy_step(const PC_Belief*, const PC_Vehicle*,
                         const PC_ObsModel* models, uint8_t n,
                         const PC_Env*, const PC_Cfg*);   /* π(s) → a=(m,u,τ) */
PC_Action pc_rta_filter(PC_Action, const PC_Vehicle*, const PC_Safety*, ...);
```

행동 `a = (sensor m, motion u=(v,w), n_look τ)`. 정책은 후보 이동 × 센서 × 관측횟수 중
`J = α·EV − β·T − γ·E` 최대를 고른다. **"밤이면 Thermal" 같은 규칙을 손코딩하지 않는다** —
어느 센서가 이기는지는 어댑터의 `p_useful`(물리) 과 J 에서 창발한다.

## 돌리기 (host)

```sh
make test      # 데스크톱서 코어를 돌려 창발·RTA·belief 회귀를 붙든다
```
host_test 가 붙드는 것: (1) 조명 쓸기서 센서선택 창발(낮→Camera, 밤→Thermal, 손코딩 0),
(2) RTA 가 keep-out 침범 행동을 안전행동으로 대체, (3) 탐지 관측이 belief 엔트로피를 줄임.

## MCU 이식

`policy_core.c` 는 stdio 를 안 쓰고 힙 할당·재귀가 없다 → bare-metal 링크 가능.
```sh
arm-none-eabi-gcc -std=c99 -Os -mcpu=cortex-m4 -c policy_core.c
```
`sqrtf/expf/logf` 는 libm 또는 고정소수 근사로 대체(코어 루프 안엔 sqrtf 하나 — 보통 HW).
`tau` 는 정수 관측횟수라 정수 거듭제곱(곱셈 루프)으로 처리 → `powf` 불필요.
`PC_GRID_W/H` 는 컴파일타임 상수 → belief 는 정적 배열(malloc 없음).

## UGV → UAV 이식

- UGV: `state=(x,y,θ)`, `action=(v,ω,τ)`.
- UAV: 어댑터가 `(v,ω)` 를 `(vx,vy,vz,yaw_rate)` 로 번역. **정책 코어는 불변.**

## 정직한 한계 (과장방지, ctrl/과장방지.md)

- **이 코어는 정책 로직의 이식이지, 실기 검증이 아니다.** host_test 는 양식화된 어댑터로
  창발/RTA 의 *구조*를 붙들 뿐, 실제 야외 성능이 아니다.
- **어댑터의 `p_useful` 곡선은 실측 캘리브레이션이 필요하다.** Camera 조명곡선·LiDAR 반사율/
  입사각·Thermal ΔT — 상수로 두면 "physics-grounded" 는 구호다. Phase 2 의 첫 일이 이 곡선
  실측이어야 한다.
- **관측시간 `n_look` 이 현재 가중치에선 항상 최대(3)로 포화**한다(β 가 작아 관측을 더 하는
  게 늘 이득). τ 가 진짜 트레이드오프가 되려면 β 를 키우거나 시간예산을 넣어야 한다 — 미해결.
- `pc_belief_update` 는 단순 2D 블롭/영역감쇠 모델이다. 실측 센서 잡음모델로 교체 필요.
