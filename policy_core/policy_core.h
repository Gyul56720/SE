/* policy_core.h -- OS-독립 능동탐색 정책 코어 (bare-metal MCU 이식 가능).
 *
 * 철학(paper/선행조사/센서불가지_능동탐색.md, recon/sensor_agnostic.py 의 C 이식):
 *   물리 -> 관측모델 -> belief -> 능동정책 -> 안전행동.
 *   정책 코어는 센서 종류/하드웨어/OS 를 모른다. 추상 인터페이스(PC_ObsModel 함수포인터)
 *   만 본다. 센서 교체 = adapter 교체, 코어 재컴파일 없음.
 *
 * MCU 안전성: 힙 할당 없음(정적 배열), 재귀 없음, 경계 있는 루프, 결정적.
 *   초월함수(expf/sqrtf)는 관측모델 adapter 쪽에 두고 코어는 산술만 쓴다(sqrtf 하나 예외 --
 *   보통 HW 명령). tau 는 정수 '관측 횟수'라 정수 거듭제곱(곱셈 루프)으로 처리 -> powf 불필요.
 *
 * 이식 목표: 같은 policy_core 가 데스크톱 host 테스트 -> bare-metal UGV MCU -> (RTOS) -> UAV
 *   로 재컴파일만으로 옮겨진다. state/action 은 UGV(x,y,theta / v,w) 기준이나 UAV 확장 시
 *   코어 불변(어댑터가 (vx,vy,vz,yaw_rate) 로 번역).
 */
#ifndef POLICY_CORE_H
#define POLICY_CORE_H

#include <stdint.h>

#ifndef PC_GRID_W
#define PC_GRID_W 24
#endif
#ifndef PC_GRID_H
#define PC_GRID_H 24
#endif
#define PC_GRID_N   (PC_GRID_W * PC_GRID_H)
#define PC_MAX_MOVES 12

/* 환경 조건: 관측모델 adapter 만 해석. 코어는 의미를 모르고 실어 나른다. */
typedef struct { float weather; float illum; float extra0; float extra1; } PC_Env;

/* modality-independent belief: 지상 위치 사후분포(정규화 확률, 센서-무관 월드좌표). */
typedef struct { float p[PC_GRID_N]; } PC_Belief;

/* 차량 상태 (UGV: x,y,theta[셀,rad]). UAV 확장은 어댑터 몫 -- 코어 불변. */
typedef struct { float x, y, theta; float batt; } PC_Vehicle;

/* 추상 관측모델 = 유일한 센서-특정 조각. 코어는 함수포인터만 본다(센서 종류 모름). */
typedef struct {
    /* 표적이 있을 때 range_m·angle·env 에서 유용 관측 확률 (한 번 관측) */
    float (*p_useful)(const void *cfg, float range_m, float angle_rad, const PC_Env *e);
    /* 국소화 정밀도[m] (작을수록 날카로움). 탐지 1건의 정보가치 ~ 1/precision */
    float (*precision)(const void *cfg, float range_m);
    const void *cfg;   /* adapter 사설 파라미터 */
    uint8_t id;        /* 센서 식별값(코어는 값만 나름, 의미 모름) */
} PC_ObsModel;

/* 행동 a_t = (m_t 센서, u_t 이동, tau_t 관측시간). */
typedef struct {
    uint8_t sensor;      /* m_t: 고른 관측모델 인덱스 */
    float   v, w;        /* u_t: (전진속도, 각속도) -- 목표셀로 가는 명령 */
    uint8_t n_look;      /* tau_t: 관측 횟수(정수, MCU 친화) */
    float   tgt_x, tgt_y;/* 다음 관측 위치[셀] */
    uint8_t rta_tripped; /* RTA 가 안전행동으로 대체했나 */
} PC_Action;

/* 목적 J 가중치 + 물리 스케일 + 후보 탐색 파라미터.
 * J = alpha*P_detect - beta*T_search - gamma*E_motion.
 *   T_search[s] = t_move + tau*t_obs  (실제 경과시간 -- nl 이 아니라 초).
 *     t_move = 이동거리[m] / v_nom[m/s],  tau*t_obs = 관측시간[s].
 *   beta = '초당 탐지가치'(임무 긴급도). 크면 -> 덜 보고 이동(급함), 작으면 -> 더 봄.
 *   gamma = 이동 에너지/마모(거리[m] 당). 시간(beta)과 별개의 물리량이라 둘 다 남긴다.
 * tau(관측횟수)가 진짜 트레이드오프가 되는 이유: EV(tau)는 diminishing(1-(1-p1)^tau,
 *   오목)인데 시간비용은 tau 에 선형 -> 한계정보가 시간비용(beta*t_obs) 밑으로 내려가는
 *   지점에서 멈춘다(최적 포식/MVT). 근거리·고p1 장면은 빨리 포화 -> tau* 작고, 원거리·
 *   열화 장면은 정보가 덜 차 tau* 크다. 손코딩 없이 장면·긴급도에서 창발. */
typedef struct {
    float alpha, beta, gamma;  /* J 가중치 (beta = 초당 가치) */
    float cell_m;              /* 셀 한 칸[m] */
    float r_max_cells;         /* 관측 반경[셀] */
    float v_nom;               /* 이동속도[m/s] -- t_move = 거리/v_nom */
    float t_obs;               /* 관측 한 번의 시간[s] -- 관측시간 = tau*t_obs */
    uint8_t n_look_max;        /* 시도할 최대 관측횟수(1..n) */
    /* belief-적응 비용(cold-start freeze 방지): 비용을 belief 불확실도로 스케일한다.
     *   beta_eff = beta*(1-H_norm)^p,  gamma_eff = gamma*(1-H_norm)^p,
     *   H_norm = H(belief)/log(N) in [0,1].  불확실(확산)하면 비용↓ -> 자유 탐색,
     *   확신(집중)하면 비용↑ -> 절제된 확인. 근시안 정책이 두 국면을 다 서게 한다.
     *   p(정수 거듭제곱, powf 불필요): 0 = 적응 끔(항상 full 비용, 하위호환), 1 선형, 2+ 급. */
    uint8_t cost_uncert_pow;
} PC_Cfg;

/* 안전집합: 위협 keep-out (RTA). */
typedef struct { float thr_x, thr_y, keepout_cells; uint8_t active; } PC_Safety;

/* 후보 이동(셀 오프셋 목록). */
void pc_default_moves(float dx[PC_MAX_MOVES], float dy[PC_MAX_MOVES], uint8_t *n);

/* pi(s) -> a. 후보 이동 x 센서 x 관측횟수 중 J 최대. 힙/재귀 없음, 결정적. */
PC_Action pc_policy_step(const PC_Belief *b, const PC_Vehicle *veh,
                         const PC_ObsModel *models, uint8_t n_models,
                         const PC_Env *env, const PC_Cfg *cfg);

/* a_safe = RTA(a). keep-out 침범이면 가장 가까운 안전 후보로 대체(센서/관측시간 유지). */
PC_Action pc_rta_filter(PC_Action a, const PC_Vehicle *veh, const PC_Safety *saf,
                        const float dx[], const float dy[], uint8_t n_moves);

/* 관측 -> 베이즈 belief 갱신. detect/meas 는 상위(HW/시뮬)가 관측모델로 판정해 넣는다. */
void pc_belief_update(PC_Belief *b, const PC_Vehicle *at, const PC_ObsModel *m,
                      const PC_Env *env, const PC_Cfg *cfg,
                      int detect, float meas_x, float meas_y);

/* belief 섀넌 엔트로피(정보이득 측정용). */
float pc_belief_entropy(const PC_Belief *b);

/* belief 최대확률 셀과 그 확률. */
void pc_belief_argmax(const PC_Belief *b, float *out_x, float *out_y, float *out_p);

#endif /* POLICY_CORE_H */
