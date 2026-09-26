/* policy_core.c -- OS-독립 능동탐색 정책 코어 구현. 힙/재귀 없음, 결정적.
 * recon/sensor_agnostic.py 의 통합정책(J 최대화 + 센서선택 창발 + RTA)을 C 로 이식. */
#include "policy_core.h"
#include <math.h>   /* sqrtf 만 -- 나머지 초월함수는 관측모델 adapter 쪽 */

static float cell_dist(float ax, float ay, float bx, float by) {
    float dx = ax - bx, dy = ay - by;
    return sqrtf(dx * dx + dy * dy);
}

static float clampf(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

void pc_default_moves(float dx[PC_MAX_MOVES], float dy[PC_MAX_MOVES], uint8_t *n) {
    static const float MX[PC_MAX_MOVES] = { 4,-4, 0, 0, 3,-3, 3,-3, 5, 0, 0, 0};
    static const float MY[PC_MAX_MOVES] = { 0, 0, 4,-4, 3, 3,-3,-3, 0, 5, 0, 0};
    uint8_t i;
    for (i = 0; i < 11; ++i) { dx[i] = MX[i]; dy[i] = MY[i]; }
    *n = 11;  /* 마지막 (0,0) 제자리 포함 */
}

/* 한 후보(위치 c, 센서 m, 관측횟수 nlook)의 기대 탐지가치 EV.
 * EV = sum_x b(x) * [1-(1-p1)^nlook] / precision   ( >r_max 는 0 ) */
static float expected_value(const PC_Belief *b, float cx, float cy,
                            const PC_ObsModel *m, uint8_t nlook,
                            const PC_Env *env, const PC_Cfg *cfg) {
    float ev = 0.0f;
    int gx, gy, k;
    for (gy = 0; gy < PC_GRID_H; ++gy) {
        for (gx = 0; gx < PC_GRID_W; ++gx) {
            int idx = gy * PC_GRID_W + gx;
            float bx = b->p[idx];
            if (bx <= 0.0f) continue;
            float rc = cell_dist((float)gx, (float)gy, cx, cy);
            if (rc > cfg->r_max_cells) continue;
            float r_m = rc * cfg->cell_m;
            float ang = 0.0f; /* UGV 단순화: 등방 관측(각도 무관). 어댑터가 원하면 씀 */
            float p1 = m->p_useful(m->cfg, r_m, ang, env);
            /* tau=nlook 회 관측의 누적 탐지: 1-(1-p1)^nlook, 정수 거듭제곱(powf 불필요) */
            float miss = 1.0f;
            for (k = 0; k < (int)nlook; ++k) miss *= (1.0f - p1);
            float pT = 1.0f - miss;
            float sig = m->precision(m->cfg, r_m);
            if (sig < 1e-3f) sig = 1e-3f;
            ev += bx * pT / sig;
        }
    }
    return ev;
}

/* belief-적응 비용 스케일 계산(greedy·lookahead 공용). */
static void adaptive_cost(const PC_Belief *b, const PC_Cfg *cfg, float *beta_eff, float *gamma_eff) {
    *beta_eff = cfg->beta; *gamma_eff = cfg->gamma;
    if (cfg->cost_uncert_pow > 0) {
        float logN = logf((float)PC_GRID_N);
        float Hn = (logN > 0.0f) ? (pc_belief_entropy(b) / logN) : 0.0f;
        Hn = clampf(Hn, 0.0f, 1.0f);
        float scale = 1.0f; uint8_t j;
        for (j = 0; j < cfg->cost_uncert_pow; ++j) scale *= (1.0f - Hn);
        *beta_eff = cfg->beta * scale; *gamma_eff = cfg->gamma * scale;
    }
}

/* 한 스텝 greedy 평가: 최적 행동을 *out 에 채우고 그 최댓값 J 를 반환.
 * pc_policy_step 과 lookahead 의 value-to-go 가 공유한다(거동 동일). */
static float greedy_eval(const PC_Belief *b, const PC_Vehicle *veh,
                         const PC_ObsModel *models, uint8_t n_models,
                         const PC_Env *env, const PC_Cfg *cfg, PC_Action *out) {
    float dx[PC_MAX_MOVES], dy[PC_MAX_MOVES];
    uint8_t nmv, i, si, nl;
    float bestJ = -1e30f;
    PC_Action best;
    pc_default_moves(dx, dy, &nmv);
    best.sensor = 0; best.v = 0; best.w = 0; best.n_look = 1;
    best.tgt_x = veh->x; best.tgt_y = veh->y; best.rta_tripped = 0;
    float beta_eff, gamma_eff; adaptive_cost(b, cfg, &beta_eff, &gamma_eff);

    for (i = 0; i < nmv; ++i) {
        float cx = veh->x + dx[i], cy = veh->y + dy[i];
        cx = clampf(cx, 0, PC_GRID_W - 1);
        cy = clampf(cy, 0, PC_GRID_H - 1);
        float move_m = cell_dist(cx, cy, veh->x, veh->y) * cfg->cell_m;
        float t_move = (cfg->v_nom > 1e-6f) ? (move_m / cfg->v_nom) : 0.0f;
        for (si = 0; si < n_models; ++si) {
            for (nl = 1; nl <= cfg->n_look_max; ++nl) {
                float ev = expected_value(b, cx, cy, &models[si], nl, env, cfg);
                float t_search = t_move + (float)nl * cfg->t_obs;
                float J = cfg->alpha * ev - beta_eff * t_search - gamma_eff * move_m;
                if (J > bestJ) {
                    bestJ = J;
                    best.sensor = si; best.n_look = nl;
                    best.tgt_x = cx; best.tgt_y = cy;
                    float d = cell_dist(cx, cy, veh->x, veh->y);
                    if (d > 1e-3f) { best.v = cfg->v_nom; best.w = 0.0f; }
                    else           { best.v = 0.0f;       best.w = 0.0f; }
                }
            }
        }
    }
    *out = best;
    return bestJ;
}

PC_Action pc_policy_step(const PC_Belief *b, const PC_Vehicle *veh,
                         const PC_ObsModel *models, uint8_t n_models,
                         const PC_Env *env, const PC_Cfg *cfg) {
    PC_Action a; greedy_eval(b, veh, models, n_models, env, cfg, &a);
    a.rta_tripped = 0;
    return a;
}

/* 2-스텝 lookahead(첫 이동에 대해). 각 첫 이동 후보마다 (센서·τ 는 greedy) J1 을 구하고,
 * 그 셀에서 '기대 미탐지' belief 갱신 후 남은 greedy value-to-go(J2)를 더해 최적 첫 이동 선택.
 * 탐색에서 계획이 가장 이득인 건 '어디로 갈지'라 이동에만 lookahead 를 건다.
 * MCU 주의: 힙 없음(스택 belief 복사 1개)·재귀 없음이나 greedy 의 ~후보수배 무겁다 -- 실험
 * 변형이며 배포 코어(pc_policy_step)는 greedy 유지. disc: 미래 할인(0..1). */
PC_Action pc_policy_step_la2(const PC_Belief *b, const PC_Vehicle *veh,
                             const PC_ObsModel *models, uint8_t n_models,
                             const PC_Env *env, const PC_Cfg *cfg, float disc) {
    float dx[PC_MAX_MOVES], dy[PC_MAX_MOVES];
    uint8_t nmv, i, si, nl;
    pc_default_moves(dx, dy, &nmv);
    float beta_eff, gamma_eff; adaptive_cost(b, cfg, &beta_eff, &gamma_eff);
    float bestTotal = -1e30f;
    PC_Action best;
    best.sensor = 0; best.v = 0; best.w = 0; best.n_look = 1;
    best.tgt_x = veh->x; best.tgt_y = veh->y; best.rta_tripped = 0;
    PC_Belief b1;   /* 스택 복사(재사용), 힙 없음 */

    for (i = 0; i < nmv; ++i) {
        float cx = clampf(veh->x + dx[i], 0, PC_GRID_W - 1);
        float cy = clampf(veh->y + dy[i], 0, PC_GRID_H - 1);
        float move_m = cell_dist(cx, cy, veh->x, veh->y) * cfg->cell_m;
        float t_move = (cfg->v_nom > 1e-6f) ? (move_m / cfg->v_nom) : 0.0f;
        /* 이 셀서의 restricted greedy: 최적 (sensor,τ) 와 J1 */
        float bestJ1 = -1e30f; uint8_t bs = 0, bnl = 1;
        for (si = 0; si < n_models; ++si) {
            for (nl = 1; nl <= cfg->n_look_max; ++nl) {
                float ev = expected_value(b, cx, cy, &models[si], nl, env, cfg);
                float J1 = cfg->alpha * ev - beta_eff * (t_move + (float)nl * cfg->t_obs) - gamma_eff * move_m;
                if (J1 > bestJ1) { bestJ1 = J1; bs = si; bnl = nl; }
            }
        }
        /* value-to-go: (cx,cy,bs) 에서 기대 미탐지 갱신 후 greedy 값 */
        b1 = *b;
        PC_Vehicle v1; v1.x = cx; v1.y = cy; v1.theta = 0.0f; v1.batt = veh->batt;
        pc_belief_update(&b1, &v1, &models[bs], env, cfg, 0, 0.0f, 0.0f);
        PC_Action ja; float J2 = greedy_eval(&b1, &v1, models, n_models, env, cfg, &ja);
        float total = bestJ1 + disc * J2;
        if (total > bestTotal) {
            bestTotal = total;
            best.sensor = bs; best.n_look = bnl; best.tgt_x = cx; best.tgt_y = cy;
            float d = cell_dist(cx, cy, veh->x, veh->y);
            if (d > 1e-3f) { best.v = cfg->v_nom; best.w = 0.0f; }
            else           { best.v = 0.0f;       best.w = 0.0f; }
        }
    }
    best.rta_tripped = 0;
    return best;
}

PC_Action pc_rta_filter(PC_Action a, const PC_Vehicle *veh, const PC_Safety *saf,
                        const float dx[], const float dy[], uint8_t n_moves) {
    if (!saf || !saf->active) return a;
    float d = cell_dist(a.tgt_x, a.tgt_y, saf->thr_x, saf->thr_y);
    if (d >= saf->keepout_cells) return a;             /* 안전 -> 통과 */
    /* 침범: keep-out 밖 후보 중 현재 위치서 가장 가까운 것으로 대체(센서/관측 유지) */
    float bestd = 1e30f; float bx = veh->x, by = veh->y; uint8_t i, found = 0;
    for (i = 0; i < n_moves; ++i) {
        float cx = veh->x + dx[i], cy = veh->y + dy[i];
        cx = clampf(cx, 0, PC_GRID_W - 1);
        cy = clampf(cy, 0, PC_GRID_H - 1);
        if (cell_dist(cx, cy, saf->thr_x, saf->thr_y) < saf->keepout_cells) continue;
        float mv = cell_dist(cx, cy, veh->x, veh->y);
        if (mv < bestd) { bestd = mv; bx = cx; by = cy; found = 1; }
    }
    a.tgt_x = bx; a.tgt_y = by; a.rta_tripped = 1;
    if (!found) { a.v = 0; a.w = 0; }                  /* 안전 후보 없으면 정지 */
    return a;
}

void pc_belief_update(PC_Belief *b, const PC_Vehicle *at, const PC_ObsModel *m,
                      const PC_Env *env, const PC_Cfg *cfg,
                      int detect, float meas_x, float meas_y) {
    int gx, gy; float sum = 0.0f;
    float sig = m->precision(m->cfg, 0.0f); if (sig < 0.6f) sig = 0.6f;  /* 격자 바닥[셀] */
    for (gy = 0; gy < PC_GRID_H; ++gy) {
        for (gx = 0; gx < PC_GRID_W; ++gx) {
            int idx = gy * PC_GRID_W + gx;
            float rc = cell_dist((float)gx, (float)gy, at->x, at->y);
            float L;
            if (detect) {
                float d2 = ((float)gx - meas_x) * ((float)gx - meas_x) +
                           ((float)gy - meas_y) * ((float)gy - meas_y);
                L = expf(-d2 / (2.0f * sig * sig)) + 0.02f;          /* 탐지: 측정 근처 블롭 */
            } else {
                float p1 = 0.0f;
                if (rc <= cfg->r_max_cells) p1 = m->p_useful(m->cfg, rc * cfg->cell_m, 0.0f, env);
                L = 1.0f - 0.85f * p1;                               /* 미탐지: 본 곳 감쇠 */
            }
            b->p[idx] *= L; sum += b->p[idx];
        }
    }
    if (sum > 0.0f) { int i; for (i = 0; i < PC_GRID_N; ++i) b->p[i] /= sum; }
}

float pc_belief_entropy(const PC_Belief *b) {
    float H = 0.0f; int i;
    for (i = 0; i < PC_GRID_N; ++i) { float p = b->p[i]; if (p > 1e-12f) H -= p * logf(p); }
    return H;
}

void pc_belief_argmax(const PC_Belief *b, float *out_x, float *out_y, float *out_p) {
    int i, best = 0; float bp = -1.0f;
    for (i = 0; i < PC_GRID_N; ++i) if (b->p[i] > bp) { bp = b->p[i]; best = i; }
    *out_x = (float)(best % PC_GRID_W); *out_y = (float)(best / PC_GRID_W); *out_p = bp;
}
