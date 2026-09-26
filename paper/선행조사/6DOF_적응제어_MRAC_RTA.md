# 선행조사 — 6-DOF 내부루프 하이브리드 (LQR-PI + MRAC + 학습SSM + RTA)

요청: 사용자의 연구(LQR-PI 명목 + MRAC 적응 비행가능 UAV 아키텍처)를, 6-DOF
내부루프(롤·피치·요 자세 + 고도) MIMO 로 확장하고 그 위에 학습 SSM 성능층과
RTA 안전층을 얹은 하이브리드로 코드화.

## 무엇을 짓기 전인가

`ctrl/model/hybrid6dof.py`(4축 MIMO: 명목 모델매칭 + 축별 MRAC 적응 + 공진극 SSM
피드포워드 + RTA 게이트)와 이를 붙드는 `tests/test_hybrid6dof.py`.

## 정직한 성격 — 이것은 **재현/시연이지 신규 제어이론이 아니다**

MRAC(기준모델 적응·Lyapunov 적응법칙·투영), RTA/Simplex(검증 백업 + 안전 감시자),
학습 피드포워드 증강 — 모두 **이미 확립된 방법**이다. 우리 기여는 새 이론이 아니라:
(1) 세 층의 **역할을 갈라** 한 저장소에서 실제로 재고, (2) **어느 층이 값을 내는지
정직하게 측정**한 것이다. 아래 표의 "우리가 다른 점"은 이 측정과 AI-HW 공동설계
각도이지, 새 제어이론 주장이 아니다(과장방지).

## 측정된 정직한 결과 (실측 2026-09-26, `ctrl/model/hybrid6dof.py`)

4축 ±0.3rad 공격 기동, 불확실 = 제어효과손실 + CG바이어스 + 정합파라미터 +
축간 자이로 커플링 + 공진외란. 자세추종 RMS:

| 제어기 | 자세RMS | 판정 |
|---|---|---|
| 명목·무불확실 | 0.0148 | 기준(안정) |
| ① 명목+불확실 | 0.0433 | 불확실이 2.9배 악화 |
| ② +MRAC | **0.0221** | 명목 대비 **2배↓** — 확실히 작동 |
| ③ +학습SSM(하이브리드) | 0.0210 | MRAC 대비 **+5%뿐 — 거의 잉여** |

RTA(반감쇠 명령 주입): 끄면 최대자세 **1.446**(안전집합 0.7 이탈), 켜면 **0.445**
(유지) — 안전층 확실히 작동.

**정직한 세 판정:**
1. **MRAC 는 6-DOF 에서 작동한다(2배).** 단, 적응률 γ 가 관건이었다 — 작은-오차
   영역(잘 감쇠·모드 지령)에서 γ=8 은 24초 안에 수렴 못 했다(|Θ|이 0.6 에 멈춤).
   γ=200 에서 정합 불확실을 이론대로 잡는다. 이건 튜닝이지 rigging 이 아니다(성분별
   γ 쓸기로 확인 — 정합-only 에서 γ↑ 시 RMS 단조 감소, |Θ| 단조 증가).
2. **RTA 는 작동한다** — 학습항이 오작동해도 안전집합을 지킨다.
3. **학습 SSM(Mamba)은 이 시나리오에서 +5% 로 거의 잉여다.** 강한 MRAC 가 정합분을
   먹어 잔차(커플링·공진)가 얇다. 1-DOF 의 +10%보다도 작다. **정확도 근거로는 남기지
   않고**, FPGA 엣지추론 매핑(scan_mac·복소극 SSM)이라는 **하드웨어 근거로만** 남긴다.

## 찾아본 질의

- `model reference adaptive control MRAC multirotor UAV attitude 6-DOF control effectiveness loss`
- `run-time assurance simplex architecture safety filter learned controller flight UAV`
- `state space model SSM Mamba learned feedforward augment adaptive control resonant disturbance`
- `feedback linearization MRAC multirotor fuel payload uncertainty` (KAIST Bang 그룹 추적)
- `deep model reference adaptive control neural network augmentation`

## 가장 가까운 선행연구

| 무엇 | arXiv/DOI/출처 | 연도 | 확인수준 | 우리가 다른 점 |
|---|---|---|---|---|
| **FBL-MRAC 멀티로터, 연료·페이로드(=질량·CG) 불확실** | Lee, Kim, Jang, Lee, **Bang**(KAIST), *Proc. IMechE Part G* doi:10.1177/09544100241295840 | 2025 | 목록 | **가장 가까움.** 우리 CG바이어스 시나리오와 직결. 우리는 여기에 RTA 안전층 + 어느 층이 값 내는지 측정을 더함 |
| Deep MRAC (DNN 이 MRAC 증강) | Joshi & Chowdhary, arXiv:1909.08602 | 2019 | 초록 | **재현/대조** — DNN 대신 해석가능 복소극 SSM. 우리는 학습층이 잉여임을 측정으로 보임 |
| 분산 직접 MRAC 쿼드로터 자세(축별) | Zhao et al., ResearchGate 320677430 | 2017 | 목록 | **재현** — 축별 MRAC 배치 동일 |
| MRAC 결함허용(추력·로터 효과손실) | (academia.edu 50380026) MRAFTC quadrotor | — | 조각 | **재현** — 제어효과 손실 Λ 시나리오 근거 |
| RTA 안전필터 서베이 | Hobbs et al., arXiv:2110.03506 | 2021 | 초록 | **재현** — MRAC 명목을 검증 백업으로 사용 |
| Black-Box Simplex RTA | Mehmood et al., arXiv:2102.12981 | 2021 | 목록 | **재현** — 감시자+백업 구조 |
| 학습 sUAS 분리정책 런타임 안전필터 | (arXiv:2607.10014) | 2026 | 조각 | **참고** — 관측필터 vs 행동필터 비교(우리는 행동/노력 게이트) |
| Selective SSM (Mamba) | Gu & Dao, arXiv:2312.00752 | 2023 | 목록 | **재현** — 공진극 SSM 을 제어 피드포워드로 축소 |
| 내부모델원리(공진극 = 정현외란 제거) | Francis & Wonham, *Automatica* doi:10.1016/0005-1098(76)90006-6 | 1976 | 목록 | **재현** — 공진 SSM 근거로 인용 |

> 표의 확인수준은 정직하게 적었다(대부분 **목록/초록/조각** — 전문 정독 아님). Lee et
> al.(2025, KAIST Bang) 은 초록·저자·기관까지만 확인했고 전문은 못 읽었다. 인용을
> 논문 표면에 쓸 때는 `[출처:조각]` 등으로 그 수준을 표시한다(G022).

## 아직 못 본 곳

- Lee et al.(2025, KAIST Bang) **전문** — 그들이 CG 불확실에 쓴 적응법칙·기준모델의
  구체 형태(우리 것과 얼마나 겹치는지 전문 없이는 못 가른다).
- 최근 3년 GNC/ACC/CDC 의 학습증강 적응비행제어 최신본(우리 "학습층 잉여" 결론을
  더 정교히 보였을 수 있음).
- Neural-Fly(Caltech, O'Connell et al. *Science Robotics* 2022) 계열 — 학습 잔차가
  실제로 크게 이기는 반례일 수 있다. 우리 결론은 "이 시나리오에선" 잉여라는 것.
- 상용/방산 비행제어 스택의 적응·안전 아키텍처(비공개).

## 아직 못 지운 가능성

- **학습 SSM 이 다른(더 비정합·비선형) 불확실에선 크게 이길 수 있다.** 우리 +5%
  결론은 "정합 불확실이 지배하고 MRAC 를 제대로 튜닝한" 이 시나리오 한정이다.
  Neural-Fly 류(풍동 실측 공력 잔차)에선 학습층이 지배할 수 있다 — 반증 안 됨.
- γ=200 고이득 MRAC 의 **실기 견실성**(측정잡음·시간지연·미모델 동역학 하에서)은
  이 결정론 시뮬로는 확인 못 했다. 실기에선 σ-수정·투영·정규화 적응이 필요할 수 있다.
- 축간 커플링·공진의 크기(KAP·AD)가 **실측 물리값이 아니다** — 단순화 모델 파라미터다.
  사용자 캡스톤 기체의 sysID 로 교체해야 "네 UAV 검증"이 된다.
- RTA 안전집합·게이트 임계(0.7·노력 5)는 시연용이고, 실제 CBF/제어불변집합 기반
  인증 백업으로 대체해야 형식 보장이 된다.
