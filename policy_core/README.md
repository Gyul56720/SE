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
`J = α·EV − β·T_search − γ·E` 최대를 고른다. **"밤이면 Thermal" 같은 규칙을 손코딩하지
않는다** — 어느 센서가 이기는지는 어댑터의 `p_useful`(물리) 과 J 에서 창발한다.

`T_search = t_move + τ·t_obs` (실제 경과시간[s]; `t_move = 이동거리/v_nom`). `β`는 **초당
탐지가치(임무 긴급도)**다. 그래서 **관측시간 τ 도 손코딩 없이 창발한다**: `EV(τ)=1−(1−p1)^τ`
는 오목(수확체감), 시간비용은 τ 에 선형 → 한계정보가 시간비용 밑으로 내려가는 데서 멈춘다
(최적 포식/MVT). 긴급하면(β↑) 덜 보고 이동, 근거리·고 p1 장면은 정보가 빨리 차 τ* 가 작다.
host_test 의 `[tau-sweep]`(β 6→1 로 τ* 갈림)·`[scene-sweep]`(근접 4 < 원거리 6)이 붙든다.

**belief-적응 비용(`cost_uncert_pow=p`)**: `β_eff=β·(1−H_norm)^p` (`H_norm=H(belief)/log(N)`).
확산 belief(불확실)면 비용↓ → 자유 탐색, 집중되면 비용↑ → 절제. 근시안 정책의 cold-start
freeze(확산 prior 서 이동비용이 EV 이득보다 커 제자리에 얼던 것)를 고친다. `p=0` 이면 끔.
host_test `[freeze-fix]`·`sim` β/pow 스윕(RESULTS.md)이 붙든다. 정수 거듭제곱이라 powf 불필요.

## 돌리기 (host)

```sh
make test        # 코어 회귀: 센서선택 창발·τ 트레이드오프·RTA·belief 를 붙든다
make baselines   # Phase-1 측정: 6 정책 x 3 조건 성공률·시간·거리·전환·RTA 표 (-> RESULTS.md)
```
host_test 가 붙드는 것: (1) 조명 쓸기서 센서선택 창발(낮→Camera, 밤→Thermal, 손코딩 0),
(2) RTA 가 keep-out 침범 행동을 안전행동으로 대체, (3) 탐지 관측이 belief 엔트로피를 줄임.

추가 모드: `./sim --lookahead`(greedy vs 2-스텝 lookahead), `./sim --dynamic [pfa]`(에피소드 내
조건변화), `./sim --trace`(belief·궤적 덤프). 결과 해석은 `RESULTS.md`.
현장 캘리브(하드웨어) 준비: `CALIBRATION.md` — sim 의 model=truth 를 실측 곡선으로 바꾸는 절차.
응용 정의: `PROJECT_SAR.md` — 재난 수색구조(SAR) 능동수색 로버로 논문·캘리브·측정을 하나로 묶은 상위 정의서.

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
- ~~관측시간 `n_look` 이 항상 최대로 포화~~ **[해결]** `T_search` 를 실제 시간
  `t_move+τ·t_obs` 로 바꾸고 `β` 를 초당 가치로 재해석해 τ 가 긴급도·장면에서 갈리게 했다
  (host_test `[tau-sweep]`/`[scene-sweep]`). 다만 **`β`(초당 탐지가치=임무 긴급도)의 절대값은
  임무가 정하는 자유 파라미터**다 — 논문은 단일 β 결과가 아니라 β-쓸기 전체를 보고한다(과장방지).
  또 여기서 τ 는 *한 스텝의 탐욕적* 최적이지 유한지평 예산의 전역 최적이 아니다(그건 Phase-1 에피소드에서 잰다).
- `pc_belief_update` 는 단순 2D 블롭/영역감쇠 모델이다. 실측 센서 잡음모델로 교체 필요.
