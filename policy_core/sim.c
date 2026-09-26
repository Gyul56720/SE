/* sim.c -- Phase-1 측정: 능동탐색 정책 6종을 같은 시뮬레이터로 돌려
 *   P_detect(성공률) · T_search(초) · C_motion(거리[m]) · 센서전환 · RTA개입 을 잰다.
 *
 * 과장방지(ctrl/과장방지.md):
 *  - 모든 정책이 같은 관측모델(어댑터)을 통해 관측한다. proposed 의 이점은 '결정'뿐
 *    (어느 센서 m · 어디 u · 얼마나 τ). 관측 물리를 proposed 에게만 유리하게 주지 않는다.
 *  - 단일 조건이 아니라 조건 분포에서 잰다: day-clear / night / day-degraded-cam.
 *    고정센서는 절반에서 죽고, hand-rule 은 "낮->카메라" 가정이 깨지는 degraded 에서
 *    진다. proposed 는 창발로 적응한다. 기여는 '최고 센서'가 아니라 '조건 강건성'.
 *  - 성공률(예산 내 국소화)이 헤드라인. 시간/거리는 성공 에피소드 한정임을 명시한다.
 *  - 시뮬레이터에서 모델=진실(공정한 공통지반). 실기에선 모델≠진실이고 어댑터 곡선은
 *    실측 캘리브가 필요하다(README 한계). false alarm(pfa)은 v1 에서 0 -- 아래 명시.
 */
#include "policy_core.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

/* ── 결정적 RNG (xorshift32) : 재현 가능 ── */
static uint32_t RNG = 0;
static void  seed(uint32_t s) { RNG = s ? s : 1u; }
static uint32_t xr(void) { RNG ^= RNG << 13; RNG ^= RNG >> 17; RNG ^= RNG << 5; return RNG; }
static float urand(void) { return (float)(xr() >> 8) * (1.0f / 16777216.0f); } /* [0,1) */
static float nrand(void) { /* 표준정규(Box-Muller) */
    float u1 = urand() + 1e-7f, u2 = urand();
    return sqrtf(-2.0f * logf(u1)) * cosf(6.2831853f * u2);
}

/* ── 관측모델 어댑터: 유일한 센서-특정 조각. env->extra0 = 카메라 건강도[0..1]
 *    (렌즈오염/역광 등 물리적 열화). LiDAR/Thermal 은 조명·건강도 무관(능동/열). ── */
static float cam_p(const void *c, float r, float a, const PC_Env *e) {
    (void)c; (void)a; return 0.92f * expf(-(r/25.f)*(r/25.f)) * e->illum * e->extra0;
}
static float cam_s(const void *c, float r) { (void)c; return 0.30f + 0.010f * r; }
static float lid_p(const void *c, float r, float a, const PC_Env *e) {
    (void)c; (void)a; (void)e; return 0.80f * expf(-(r/18.f)*(r/18.f));
}
static float lid_s(const void *c, float r) { (void)c; return 0.50f + 0.020f * r; }
static float thr_p(const void *c, float r, float a, const PC_Env *e) {
    (void)c; (void)a; (void)e; return 0.85f * expf(-(r/22.f)*(r/22.f));
}
static float thr_s(const void *c, float r) { (void)c; return 0.40f + 0.015f * r; }

enum { CAM = 0, LID = 1, THR = 2, NSENS = 3 };
enum { P_PROP = 0, P_INFO, P_FCAM, P_FLID, P_HAND, P_RAND, NPOL };
static const char *POLNAME[NPOL] = {
    "Proposed", "Info/EV-only", "Fixed-Camera", "Fixed-LiDAR", "Hand-rule", "Random"
};

/* 정책 한 스텝. 반환 a.sensor 는 항상 '전역 센서 id'(CAM/LID/THR)로 맞춘다.
 * models[i].id == i 로 정렬되어 full/info 는 그대로, fixed/hand 는 사후 remap. */
static PC_Action step_policy(int pol, const PC_Belief *b, const PC_Vehicle *veh,
                             const PC_ObsModel M[NSENS], const PC_Env *env,
                             const PC_Cfg *cfg,
                             const float dx[], const float dy[], uint8_t nmv) {
    PC_Action a;
    switch (pol) {
    case P_PROP:  /* 제안: 전체 J, 센서·τ 창발 */
        a = pc_policy_step(b, veh, M, NSENS, env, cfg);
        break;
    case P_INFO: { /* Info/EV-only: 비용항 끄기(β=γ=0) -> 탐욕적 정보/탐지값만. */
        PC_Cfg c0 = *cfg; c0.beta = 0.f; c0.gamma = 0.f;
        a = pc_policy_step(b, veh, M, NSENS, env, &c0);
        break; }
    case P_FCAM:  /* 고정 카메라: 카메라 한 대로 할 수 있는 최선(이동·τ 는 최적) */
        a = pc_policy_step(b, veh, &M[CAM], 1, env, cfg); a.sensor = CAM; break;
    case P_FLID:  /* 고정 라이다 */
        a = pc_policy_step(b, veh, &M[LID], 1, env, cfg); a.sensor = LID; break;
    case P_HAND: { /* 손코딩 규칙: 밝으면 카메라, 어두우면 열화상 (건강도는 모른다) */
        int idx = (env->illum > 0.5f) ? CAM : THR;
        a = pc_policy_step(b, veh, &M[idx], 1, env, cfg); a.sensor = (uint8_t)idx; break; }
    default: {    /* Random: 무작위 이동·센서·관측횟수 */
        uint8_t mi = (uint8_t)(xr() % nmv);
        float cx = veh->x + dx[mi], cy = veh->y + dy[mi];
        cx = (cx < 0) ? 0 : (cx > PC_GRID_W - 1 ? PC_GRID_W - 1 : cx);
        cy = (cy < 0) ? 0 : (cy > PC_GRID_H - 1 ? PC_GRID_H - 1 : cy);
        a.sensor = (uint8_t)(xr() % NSENS);
        a.n_look = (uint8_t)(1 + xr() % cfg->n_look_max);
        a.tgt_x = cx; a.tgt_y = cy; a.rta_tripped = 0;
        a.v = cfg->v_nom; a.w = 0.f; break; }
    }
    return a;
}

typedef struct { int success; float t_search, dist_m; int switches, rta; } Metrics;

/* 에피소드 하나. 표적은 시작 관측반경 밖 무작위 셀(탐색이 필요하도록).
 * ep_seed 로 시드해 표적/시작을 정책과 무관하게 만든다 -> 모든 정책이 같은 시나리오를
 * 본다(짝짓기 비교, 공정). 표적을 먼저 뽑고 나서 정책/관측 난수가 흐른다. */
static Metrics run_episode(int pol, PC_Env env, const PC_Cfg *cfg,
                           const PC_Safety *saf, const PC_ObsModel M[NSENS],
                           uint32_t ep_seed) {
    Metrics m = {0, 0.f, 0.f, 0, 0};
    seed(ep_seed);
    float dx[PC_MAX_MOVES], dy[PC_MAX_MOVES]; uint8_t nmv; pc_default_moves(dx, dy, &nmv);
    PC_Vehicle veh = { 2.f, 2.f, 0.f, 1.f };
    /* 자연어-유도 prior: 언어가 "표적이 대략 이 구역" 이라고 준다. 이 세션은 그 구역을
     * 넓은 blob 으로 모델한다(균일 아님 -- 균일은 '언어 없음'이라 문제에 안 맞다).
     * 표적은 그 prior 에서 뽑아 prior 를 정직하게 보정한다(broad, 과확신 아님). */
    const float S_PRIOR = 5.0f;   /* 언어 prior 폭[셀] (넓음 -> 국소화는 여전히 능동탐색 필요) */
    const float S_TGT   = 3.0f;   /* 표적이 prior 중심서 흩어진 폭[셀] (prior 보다 좁음) */
    float pcx = 4.f + (float)(xr() % (PC_GRID_W - 8));   /* prior 중심(경계 여유) */
    float pcy = 4.f + (float)(xr() % (PC_GRID_H - 8));
    float tx, ty;
    do {
        tx = pcx + nrand() * S_TGT; ty = pcy + nrand() * S_TGT;
        tx = (tx < 0) ? 0 : (tx > PC_GRID_W - 1 ? PC_GRID_W - 1 : tx);
        ty = (ty < 0) ? 0 : (ty > PC_GRID_H - 1 ? PC_GRID_H - 1 : ty);
    } while (sqrtf((tx-veh.x)*(tx-veh.x)+(ty-veh.y)*(ty-veh.y)) <= cfg->r_max_cells
             || sqrtf((tx-saf->thr_x)*(tx-saf->thr_x)+(ty-saf->thr_y)*(ty-saf->thr_y)) < saf->keepout_cells);
    PC_Belief b; {   /* prior blob = 언어 유도 사전분포 */
        int gx, gy; float sum = 0.f;
        for (gy = 0; gy < PC_GRID_H; ++gy) for (gx = 0; gx < PC_GRID_W; ++gx) {
            float d2 = (gx-pcx)*(gx-pcx) + (gy-pcy)*(gy-pcy);
            float v = expf(-d2 / (2.f*S_PRIOR*S_PRIOR)) + 0.01f;   /* +floor: 언어 밖도 0 아님 */
            b.p[gy*PC_GRID_W + gx] = v; sum += v;
        }
        { int i; for (i = 0; i < PC_GRID_N; ++i) b.p[i] /= sum; }
    }
    int prev_sensor = -1;
    const int MAXSTEP = 25;   /* 커버리지 예산: 24x24 격자를 footprint(r=9)로 덮는 데 충분 */
    int s;
    for (s = 0; s < MAXSTEP; ++s) {
        PC_Action a = step_policy(pol, &b, &veh, M, &env, cfg, dx, dy, nmv);
        a = pc_rta_filter(a, &veh, saf, dx, dy, nmv);
        if (a.rta_tripped) m.rta++;
        /* 이동 */
        float d = sqrtf((a.tgt_x-veh.x)*(a.tgt_x-veh.x)+(a.tgt_y-veh.y)*(a.tgt_y-veh.y)) * cfg->cell_m;
        m.dist_m += d; m.t_search += d / cfg->v_nom;
        veh.x = a.tgt_x; veh.y = a.tgt_y;
        /* 센서 전환 */
        int cur = a.sensor;
        if (prev_sensor >= 0 && cur != prev_sensor) m.switches++;
        prev_sensor = cur;
        /* τ 회 관측: 진실 표적이 footprint 안이면 p_useful 로 탐지 샘플 */
        float r_true = sqrtf((veh.x-tx)*(veh.x-tx)+(veh.y-ty)*(veh.y-ty)) * cfg->cell_m;
        int detected = 0; int k;
        for (k = 0; k < (int)a.n_look; ++k) {
            m.t_search += cfg->t_obs;
            if (r_true <= cfg->r_max_cells * cfg->cell_m) {
                float p = M[cur].p_useful(M[cur].cfg, r_true, 0.f, &env);
                if (urand() < p) { detected = 1; break; }
            }
        }
        if (detected) {
            float sig = M[cur].precision(M[cur].cfg, r_true) / cfg->cell_m;   /* [셀] */
            float mx = tx + nrand() * sig, my = ty + nrand() * sig;
            pc_belief_update(&b, &veh, &M[cur], &env, cfg, 1, mx, my);
            float ax, ay, ap; pc_belief_argmax(&b, &ax, &ay, &ap);
            if (sqrtf((ax-tx)*(ax-tx)+(ay-ty)*(ay-ty)) <= 2.0f) { m.success = 1; break; }
        } else {
            pc_belief_update(&b, &veh, &M[cur], &env, cfg, 0, 0.f, 0.f);   /* 미탐지: footprint 감쇠 */
        }
    }
    return m;
}

int main(int argc, char **argv) {
    PC_ObsModel M[NSENS];
    M[CAM].p_useful = cam_p; M[CAM].precision = cam_s; M[CAM].cfg = 0; M[CAM].id = CAM;
    M[LID].p_useful = lid_p; M[LID].precision = lid_s; M[LID].cfg = 0; M[LID].id = LID;
    M[THR].p_useful = thr_p; M[THR].precision = thr_s; M[THR].cfg = 0; M[THR].id = THR;

    /* 탐색 영역 기본값: β(초당가치) 작음 = 표적 발견가치 >> 시간가치(탐색 임무 본성).
     * β 를 키우면(시간 급박) cold-start 탐색이 근시안적으로 얼어 성공률이 떨어진다 --
     * 이건 버그가 아니라 시간-급박 영역의 올바른 거동. 전체 β-sweep 은 RESULTS.md.
     * (argv 로 β,γ 덮어써 스윕 가능: ./sim 0.002 0.0004) */
    PC_Cfg cfg; cfg.alpha = 1.f; cfg.beta = 0.002f; cfg.gamma = 0.0004f;
    cfg.cell_m = 5.f; cfg.r_max_cells = 9.f; cfg.v_nom = 1.f; cfg.t_obs = 0.5f; cfg.n_look_max = 6;
    if (argc >= 3) { cfg.beta = (float)atof(argv[1]); cfg.gamma = (float)atof(argv[2]); }
    printf("(cfg: alpha=%.3f beta=%.4f gamma=%.5f  [탐색영역])\n", cfg.alpha, cfg.beta, cfg.gamma);
    PC_Safety saf = { 12.f, 12.f, 3.f, 1 };   /* 중앙 근처 위협 keep-out (모든 정책 동일) */

    struct { const char *name; float illum, cam_health; } COND[3] = {
        { "day-clear",     1.00f, 1.0f },
        { "night",         0.05f, 1.0f },
        { "day-degraded",  1.00f, 0.2f },   /* 낮이지만 카메라 열화 -> hand-rule 가정 깨짐 */
    };
    const int NEP = 200;   /* 조건당 에피소드 */

    /* 조건별 표 + 전체 평균 */
    printf("=== Phase-1 baseline 측정: 6 정책 x 3 조건 x %d 에피소드 ===\n", NEP);
    printf("(성공률=예산 내 국소화; T/거리=성공 에피소드 한정 평균; 전환/RTA=전 에피소드 평균)\n\n");

    double succ_all[NPOL] = {0}, t_all[NPOL] = {0}, d_all[NPOL] = {0};
    int    tn_all[NPOL] = {0};
    double sw_all[NPOL] = {0}, rta_all[NPOL] = {0};

    int c, p, e;
    for (c = 0; c < 3; ++c) {
        printf("[%s]  illum=%.2f cam_health=%.1f\n", COND[c].name, COND[c].illum, COND[c].cam_health);
        printf("  %-13s  succ%%   T[s]|succ  dist[m]|succ  switch  RTA\n", "policy");
        for (p = 0; p < NPOL; ++p) {
            int succ = 0, tn = 0, sw = 0, rta = 0; double tsum = 0, dsum = 0;
            for (e = 0; e < NEP; ++e) {
                /* ep_seed 는 (조건,에피소드)로만 정해짐 -> 모든 정책이 같은 표적/시작을 본다 */
                uint32_t ep_seed = 0xC0FFEEu + (uint32_t)(c * 100000 + e);
                PC_Env env = { 0.f, COND[c].illum, COND[c].cam_health, 0.f };
                Metrics m = run_episode(p, env, &cfg, &saf, M, ep_seed);
                succ += m.success; sw += m.switches; rta += m.rta;
                if (m.success) { tn++; tsum += m.t_search; dsum += m.dist_m; }
            }
            double sr = 100.0 * succ / NEP;
            double mt = tn ? tsum / tn : 0.0, md = tn ? dsum / tn : 0.0;
            printf("  %-13s  %5.1f   %8.1f  %10.1f   %5.2f  %4.2f\n",
                   POLNAME[p], sr, mt, md, (double)sw / NEP, (double)rta / NEP);
            succ_all[p] += succ; if (tn) { t_all[p] += tsum; d_all[p] += dsum; tn_all[p] += tn; }
            sw_all[p] += sw; rta_all[p] += rta;
        }
        printf("\n");
    }

    printf("[전체 평균 (3 조건 혼합, 조건 강건성)]\n");
    printf("  %-13s  succ%%   T[s]|succ  dist[m]|succ  switch  RTA\n", "policy");
    for (p = 0; p < NPOL; ++p) {
        double sr = 100.0 * succ_all[p] / (3.0 * NEP);
        double mt = tn_all[p] ? t_all[p] / tn_all[p] : 0.0;
        double md = tn_all[p] ? d_all[p] / tn_all[p] : 0.0;
        printf("  %-13s  %5.1f   %8.1f  %10.1f   %5.2f  %4.2f\n",
               POLNAME[p], sr, mt, md, sw_all[p] / (3.0 * NEP), rta_all[p] / (3.0 * NEP));
    }
    return 0;
}
