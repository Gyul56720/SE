# 선행조사 — 무인체계 편대제어 · 공진SSM · MPC 스택

요청: 무인체계(드론) 제어를 (1) 단일기 공진/SSM 제어, (2) 편대 집단모드·통신지연·
다운워시 커플링 불안정, (3) 전술비행 3층 스택(계획→MPC→편대수행)으로 코드화.

## 무엇을 짓기 전인가

`ctrl/model/swarm.py`(편대 집단모드·다운워시 커플링 불안정 임계)와
`ctrl/model/tactical.py`(위협회피 계획 → MPC 중심궤적 → 편대 수행) — 그리고 이를
붙드는 테스트.

## 정직한 성격 — 이것은 **재현/교육 시연이지 신규 연구가 아니다**

여기서 재는 모든 것(공진모드=내부모델, 편대 복소 집단모드, 통신지연 여유,
다운워시 양방향 커플링의 음강성 발산, 분산 고정모드, MPC 회피, 편대 footprint
마진)은 **이미 확립된 제어이론**이다. 우리 기여는 새 이론이 아니라, 이것들을 한
저장소 안에서 **실제로 재서 잇는 시연**이다. 아래 표의 "우리가 다른 점" 칸은 전부
"재현"이며, 신규성을 주장하지 않는다(과장방지).

## 찾아본 질의

- `internal model principle disturbance rejection resonant controller`
- `consensus formation control graph Laplacian eigenvalue oscillation`
- `vehicle platoon string stability`
- `decentralized fixed modes Wang Davison stabilizability`
- `multirotor downwash aerodynamic interaction formation instability`
- `model predictive control obstacle avoidance trajectory generation UAV`
- `selective state space model Mamba control policy`

## 가장 가까운 선행연구

| 무엇 | arXiv/DOI/출처 | 연도 | 우리가 다른 점 |
|---|---|---|---|
| 내부모델원리 (정현 외란은 그 주파수 극이 있어야 제거) | Francis & Wonham, *Automatica* doi:10.1016/0005-1098(76)90006-6 | 1976 | **재현** — 공진 SSM이 PI를 이기는 이유로 인용만 |
| 비례공진(PR) 제어 | Teodorescu et al., *IET Power Electronics* doi:10.1049/iet-pel:20050008 | 2006 | **재현** — 정현 외란에서 PI 대비 시연 |
| 합의 기반 편대/그래프 라플라시안 | Olfati-Saber & Murray, *IEEE TAC* doi:10.1109/TAC.2004.834113 | 2004 | **재현** — 집단모드=라플라시안 고유값 시연 |
| 편대제어 그래프 이론 | Fax & Murray, *IEEE TAC* doi:10.1109/TAC.2004.834433 | 2004 | **재현** |
| 차량군 스트링 안정성 | Seiler, Pant, Hedrick, *IEEE TAC* doi:10.1109/TAC.2004.834531 | 2004 | **재현** — 외란이 편대를 따라 전파 |
| 분산 고정모드(분산제어로 못 옮기는 극) | Wang & Davison, *IEEE TAC* doi:10.1109/TAC.1973.1100263 | 1973 | **재현** — "이웃정보 없으면 커플링 불안정 못 잡음"의 근거 |
| 다중로터 다운워시 상호작용 | Michael et al. GRASP; Shi et al. "Neural-Swarm" arXiv:2003.02992 | 2020 | **재현/단순화** — 후류 커플링 모델은 교육용 단순화, 실측 α 아님 |
| MPC 장애물 회피 궤적 | Kamel et al., *Robotics* MPC survey doi:10.1007/978-3-319-91590-6_3 | 2017 | **재현** — 조밀 선형 MPC로 회피궤적 |
| Selective SSM (Mamba) | Gu & Dao, arXiv:2312.00752 | 2023 | **재현** — 제어정책 형태로 축소 사용 |

> 이 표의 모든 행이 "재현"이다. **새로움을 주장하지 않는다.** 목적은 포트폴리오용
> 정직한 시연: 알려진 이론을 실제로 측정해 하나의 무인체계 제어 서사로 잇는 것.

## 아직 못 본 곳

- 상용/방산 무인체계 편대 자율비행 스택(구체 알고리즘은 비공개일 수 있음)
- 최근 3년 로보틱스 학회(ICRA·IROS·RSS·CoRL)의 학습형 편대제어 최신본
- 다중로터 근접장 CFD 문헌(다운워시 양방향성 α의 실제 물리 범위)
- 특허(편대 footprint 기반 회피 계획이 특허일 수 있음)

## 아직 못 지운 가능성

- 다운워시 양방향 결합계수 α의 **물리적 실제 범위를 측정으로 확인하지 않았다** —
  코드의 불안정 임계 α*≈0.225는 단순화 모델 안의 값이지, 실제 드론이 그 α에
  도달한다는 주장이 아니다. CFD/실험이 필요하다.
- 학습형(Mamba/ES) 편대제어의 최신 결과가 우리 "이웃정보가 관건" 결론을 이미
  더 정교하게 보였을 수 있다(Neural-Swarm 계열).
- MPC 회피의 최적성/안전성 보장(제어 불변집합·CBF)은 다루지 않았다.
