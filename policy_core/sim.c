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
#include <string.h>

/* ── 결정적 RNG (xorshift32) : 재현 가능 ── */
static uint32_t RNG = 0;
static void  seed(uint32_t s) { RNG = s ? s : 1u; }
static uint32_t xr(void) { RNG ^= RNG << 13; RNG ^= RNG >> 17; RNG ^= RNG << 5; return RNG; }
static float urand(void) { return (float)(xr() >> 8) * (1.0f / 16777216.0f); } /* [0,1) */
static float nrand(void) { /* 표준정규(Box-Muller) */
    float u1 = urand() + 1e-7f, u2 = urand();
    return sqrtf(-2.0f * logf(u1)) * cosf(6.2831853f * u2);
}
static float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

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
enum { P_PROP = 0, P_INFO, P_FCAM, P_FLID, P_HAND, P_RAND, NPOL, P_LA2 = NPOL };
static const char *POLNAME[NPOL + 1] = {
    "Proposed", "Info/EV-only", "Fixed-Camera", "Fixed-LiDAR", "Hand-rule", "Random", "Lookahead-2"
};
static float g_disc = 0.9f;   /* lookahead 미래 할인 */

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
    case P_LA2:   /* Lookahead-2: 같은 전체 J·센서 3종, 첫 이동에 2-스텝 lookahead */
        a = pc_policy_step_la2(b, veh, M, NSENS, env, cfg, g_disc); break;
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

typedef struct { int success; float t_search, dist_m; int switches, rta, steps; } Metrics;

/* 트레이스(그림용): 켜지면 한 에피소드의 belief 그리드·궤적을 stdout 에 덤프한다.
 * 측정 경로엔 영향 없음(NULL 이면 아무것도 안 함). 그림은 실 C 코어 출력에서 나온다. */
static FILE *g_trace = NULL;
static int g_maxstep = 25;   /* 탐색 예산(스텝). argv 로 조일 수 있다(한계④ 검증). */
static float g_pfa = 0.0f;   /* 오경보 확률(관측당). 0 이면 기존과 동일.
   ⚠ 한계③-a: 이 순진한 모델로는 '오경보 강건성'을 못 잰다. detect 업데이트가 belief 를
   단일 탐지에 붕괴시켜, 스퓨리어스 탐지가 근시안 greedy 에 '무작위 재시작' 탐색 부스트로
   작용해 성공률이 *올라간다*(pfa=0.1 서 83.5->89.2, 균일격자 클러터로도 재현 -> 표적상관 아님).
   제대로 재려면 순차 확인(단일 탐지에 붕괴 안 하는 우도)이 필요. pfa 는 인프라일 뿐 아직
   유효한 강건성 손잡이가 아니다. RESULTS.md [한계③] 참고. */
static int g_dynamic = 0;    /* 1 이면 에피소드 내 illum 스케줄(낮->터널->밤)(한계③-b). */

/* 동적 조건 스케줄: 에피소드 진행(스텝)에 따라 낮->터널(암흑)->밤. 정책이 센서를
 * 에피소드 *안에서* 전환하는지 보려는 것 -- 정적 조건(switch~0)과 대비. */
static void dyn_env(int s, int maxstep, PC_Env *e) {
    float f = (maxstep > 0) ? (float)s / (float)maxstep : 0.0f;   /* 0..1 */
    if (f < 0.34f)      { e->illum = 1.00f; }   /* 낮: 카메라 유효 */
    else if (f < 0.67f) { e->illum = 0.00f; }   /* 터널: 암흑, 카메라 실명 */
    else                { e->illum = 0.05f; }   /* 밤: 잔광 */
    e->extra0 = 1.0f; e->extra1 = 0.0f;         /* 카메라 건강도 1(열화 아님) */
}
static void dump_grid(const char *tag, const PC_Belief *b) {
    int i; fprintf(g_trace, "GRID %s", tag);
    for (i = 0; i < PC_GRID_N; ++i) fprintf(g_trace, " %.6f", b->p[i]);
    fprintf(g_trace, "\n");
}

/* 에피소드 하나. 표적은 시작 관측반경 밖 무작위 셀(탐색이 필요하도록).
 * ep_seed 로 시드해 표적/시작을 정책과 무관하게 만든다 -> 모든 정책이 같은 시나리오를
 * 본다(짝짓기 비교, 공정). 표적을 먼저 뽑고 나서 정책/관측 난수가 흐른다. */
static Metrics run_episode(int pol, PC_Env env, const PC_Cfg *cfg,
                           const PC_Safety *saf, const PC_ObsModel M[NSENS],
                           uint32_t ep_seed) {
    Metrics m = {0, 0.f, 0.f, 0, 0, 0};
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
    if (g_trace) {
        fprintf(g_trace, "META tx %.3f ty %.3f vx %.3f vy %.3f pcx %.3f pcy %.3f "
                "kox %.2f koy %.2f kor %.2f rmax %.2f cellm %.2f\n",
                tx, ty, veh.x, veh.y, pcx, pcy, saf->thr_x, saf->thr_y,
                saf->keepout_cells, cfg->r_max_cells, cfg->cell_m);
        dump_grid("prior", &b);
    }
    int prev_sensor = -1;
    const int MAXSTEP = g_maxstep;   /* 탐색 예산(스텝). 기본 25 = 넉넉. argv 로 조인다(한계④) */
    int s;
    for (s = 0; s < MAXSTEP; ++s) {
        /* 이 스텝의 환경: 동적이면 스케줄(낮->터널->밤), 아니면 정적. 정책·관측 모두 이걸 본다 */
        PC_Env env_s = env;
        if (g_dynamic) dyn_env(s, MAXSTEP, &env_s);
        PC_Action a = step_policy(pol, &b, &veh, M, &env_s, cfg, dx, dy, nmv);
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
        /* τ 회 관측: 진짜 탐지(표적 footprint 안 + p_useful) 우선. 없으면 오경보(pfa)로
         * footprint 내 무작위 클러터 셀에 오탐이 날 수 있다. pfa=0 이면 기존과 동일. */
        float r_true = sqrtf((veh.x-tx)*(veh.x-tx)+(veh.y-ty)*(veh.y-ty)) * cfg->cell_m;
        int true_det = 0, false_det = 0; float fmx = 0.f, fmy = 0.f; int k;
        for (k = 0; k < (int)a.n_look; ++k) {
            m.t_search += cfg->t_obs;
            if (r_true <= cfg->r_max_cells * cfg->cell_m &&
                urand() < M[cur].p_useful(M[cur].cfg, r_true, 0.f, &env_s)) {
                true_det = 1; break;                       /* 진짜 탐지 -> 이 스텝 종료 */
            }
            if (g_pfa > 0.f && urand() < g_pfa) {          /* 오경보: footprint 내 클러터 */
                float ang = urand() * 6.2831853f, rr = urand() * cfg->r_max_cells;
                fmx = clampf(veh.x + rr * cosf(ang), 0.f, PC_GRID_W - 1);
                fmy = clampf(veh.y + rr * sinf(ang), 0.f, PC_GRID_H - 1);
                false_det = 1;                             /* 마지막 오경보 위치 기억, 계속 관측 */
            }
        }
        if (true_det) {
            float sig = M[cur].precision(M[cur].cfg, r_true) / cfg->cell_m;   /* [셀] */
            float mx = tx + nrand() * sig, my = ty + nrand() * sig;
            pc_belief_update(&b, &veh, &M[cur], &env_s, cfg, 1, mx, my);
            float ax, ay, ap; pc_belief_argmax(&b, &ax, &ay, &ap);
            if (g_trace) { fprintf(g_trace, "TRAJ %d %.3f %.3f %d %d %d\n", s, veh.x, veh.y, cur, a.n_look, 1); }
            if (sqrtf((ax-tx)*(ax-tx)+(ay-ty)*(ay-ty)) <= 2.0f) {   /* 진짜 표적 국소화 = 성공 */
                m.success = 1; m.steps = s + 1;
                if (g_trace) { fprintf(g_trace, "STEPS %d\n", s + 1); dump_grid("final", &b); }
                break;
            }
        } else if (false_det) {
            /* 오경보를 탐지로 믿고 belief 가 엉뚱한 데로 쏠림(성공 아님). 이후 미탐지로 복구 */
            pc_belief_update(&b, &veh, &M[cur], &env_s, cfg, 1, fmx, fmy);
            if (g_trace) { fprintf(g_trace, "TRAJ %d %.3f %.3f %d %d 2\n", s, veh.x, veh.y, cur, a.n_look); }
        } else {
            pc_belief_update(&b, &veh, &M[cur], &env_s, cfg, 0, 0.f, 0.f);   /* 미탐지: footprint 감쇠 */
            if (g_trace) { fprintf(g_trace, "TRAJ %d %.3f %.3f %d %d 0\n", s, veh.x, veh.y, cur, a.n_look); }
        }
        if (g_trace && s == 4) dump_grid("mid", &b);   /* 탐색 중간 스냅샷 */
    }
    if (!m.success) m.steps = MAXSTEP;
    return m;
}

int main(int argc, char **argv) {
    PC_ObsModel M[NSENS];
    M[CAM].p_useful = cam_p; M[CAM].precision = cam_s; M[CAM].cfg = 0; M[CAM].id = CAM;
    M[LID].p_useful = lid_p; M[LID].precision = lid_s; M[LID].cfg = 0; M[LID].id = LID;
    M[THR].p_useful = thr_p; M[THR].precision = thr_s; M[THR].cfg = 0; M[THR].id = THR;

    /* NOW-3: belief-적응 비용으로 cold-start freeze 를 고친다. base β=0.05 는 NOW-2 에서
     * 근시안 정책을 얼려 0% 였던 바로 그 값이다. cost_uncert_pow=2 면 확산 belief 서 비용이
     * 낮아져 자유 탐색하고, 집중되면 비용이 살아나 절제된 확인을 한다.
     * (argv 스윕: ./sim <beta> <gamma> [pow].  pow=0 이면 적응 끔 = NOW-2 의 얼었던 거동) */
    PC_Cfg cfg; cfg.alpha = 1.f; cfg.beta = 0.05f; cfg.gamma = 0.01f;
    cfg.cell_m = 5.f; cfg.r_max_cells = 9.f; cfg.v_nom = 1.f; cfg.t_obs = 0.5f; cfg.n_look_max = 6;
    cfg.cost_uncert_pow = 2;
    PC_Safety saf = { 12.f, 12.f, 3.f, 1 };   /* 중앙 근처 위협 keep-out (모든 정책 동일) */

    /* --trace: 한 에피소드(Proposed, day-clear)의 belief·궤적을 덤프(그림용). 성공하는
     * seed 를 골라 검색이 끝까지 진행된 사례를 보인다. 측정 경로와 무관, 실 C 코어 출력. */
    if (argc >= 2 && strcmp(argv[1], "--trace") == 0) {
        PC_Env day = { 0.f, 1.f, 1.f, 0.f };
        uint32_t sd, chosen = 0;
        for (sd = 1; sd <= 400 && !chosen; ++sd) {   /* 검색이 충분히 진행된 성공 사례(6~16 스텝) */
            Metrics mm = run_episode(P_PROP, day, &cfg, &saf, M, 0xC0FFEEu + sd);
            if (mm.success && mm.steps >= 6 && mm.steps <= 16) chosen = 0xC0FFEEu + sd;
        }
        if (!chosen) chosen = 0xC0FFEEu + 1;
        g_trace = stdout;
        run_episode(P_PROP, day, &cfg, &saf, M, chosen);
        return 0;
    }

    /* --lookahead: Greedy(Proposed) vs Lookahead-2 를 예산별로 집중 비교(한계②).
     * 근시안 1-스텝이 정말 손해인지 -- 특히 타이트 예산에서 -- 재는 것. */
    if (argc >= 2 && strcmp(argv[1], "--lookahead") == 0) {
        struct { const char *n; float il, h; } CC[3] = {
            {"day",1.0f,1.0f}, {"night",0.05f,1.0f}, {"deg",1.0f,0.2f} };
        int budgets[3] = {25, 10, 6};
        int pols[2] = {P_PROP, P_LA2};
        const int NEP_LA = 150;
        printf("=== 한계②: Greedy(Proposed) vs Lookahead-2 (disc=%.2f, %d ep x 3 조건) ===\n", g_disc, NEP_LA);
        printf("  budget  policy         succ%%   steps|succ\n");
        int bi, pi, c2, e2;
        for (bi = 0; bi < 3; ++bi) {
            g_maxstep = budgets[bi];
            for (pi = 0; pi < 2; ++pi) {
                int succ = 0, tn = 0; double stp = 0;
                for (c2 = 0; c2 < 3; ++c2) {
                    for (e2 = 0; e2 < NEP_LA; ++e2) {
                        PC_Env env = { 0.f, CC[c2].il, CC[c2].h, 0.f };
                        Metrics mm = run_episode(pols[pi], env, &cfg, &saf, M, 0xBEEF00u + c2*100000 + e2);
                        succ += mm.success; if (mm.success) { tn++; stp += mm.steps; }
                    }
                }
                printf("  %4d    %-12s  %5.1f   %6.2f\n", budgets[bi], POLNAME[pols[pi]],
                       100.0 * succ / (3.0 * NEP_LA), tn ? stp / tn : 0.0);
            }
        }
        return 0;
    }

    /* --dynamic [pfa]: 에피소드 내 조건변화(낮->터널->밤). 위치인자 대신 이 플래그. */
    if (argc >= 2 && strcmp(argv[1], "--dynamic") == 0) {
        g_dynamic = 1;
        if (argc >= 3) g_pfa = (float)atof(argv[2]);
    } else {
        if (argc >= 3) { cfg.beta = (float)atof(argv[1]); cfg.gamma = (float)atof(argv[2]); }
        if (argc >= 4) { cfg.cost_uncert_pow = (uint8_t)atoi(argv[3]); }
        if (argc >= 5) { g_maxstep = atoi(argv[4]); }               /* 탐색 예산(스텝) */
        if (argc >= 6) { cfg.n_look_max = (uint8_t)atoi(argv[5]); } /* 스텝당 관측 예산 */
        if (argc >= 7) { g_pfa = (float)atof(argv[6]); }            /* 오경보 확률(관측당) */
    }
    printf("(cfg: alpha=%.3f beta=%.4f gamma=%.5f pow=%u maxstep=%d n_look_max=%u pfa=%.3f dynamic=%d)\n",
           cfg.alpha, cfg.beta, cfg.gamma, cfg.cost_uncert_pow, g_maxstep, cfg.n_look_max, g_pfa, g_dynamic);

    typedef struct { const char *name; float illum, cam_health; } Cond;
    Cond COND_S[3] = {
        { "day-clear",     1.00f, 1.0f },
        { "night",         0.05f, 1.0f },
        { "day-degraded",  1.00f, 0.2f },   /* 낮이지만 카메라 열화 -> hand-rule 가정 깨짐 */
    };
    Cond COND_D[1] = {
        { "dynamic(day->tunnel->night)", 1.00f, 1.0f },   /* illum 은 dyn_env 가 스텝별로 덮음 */
    };
    int NCOND = g_dynamic ? 1 : 3;
    #define COND(i) (g_dynamic ? COND_D[i] : COND_S[i])
    const int NEP = 200;   /* 조건당 에피소드 */

    printf("=== 측정: 6 정책 x %d 조건 x %d 에피소드%s ===\n",
           NCOND, NEP, g_dynamic ? " [동적 조건]" : "");
    printf("(성공률=예산 내 국소화; T/거리=성공 한정; 전환/RTA=전 에피소드 평균)\n\n");

    double succ_all[NPOL] = {0}, t_all[NPOL] = {0}, d_all[NPOL] = {0};
    int    tn_all[NPOL] = {0};
    double sw_all[NPOL] = {0}, rta_all[NPOL] = {0};

    int c, p, e;
    for (c = 0; c < NCOND; ++c) {
        printf("[%s]  illum=%.2f cam_health=%.1f\n", COND(c).name, COND(c).illum, COND(c).cam_health);
        printf("  %-13s  succ%%   T[s]|succ  dist[m]|succ  switch  RTA\n", "policy");
        for (p = 0; p < NPOL; ++p) {
            int succ = 0, tn = 0, sw = 0, rta = 0; double tsum = 0, dsum = 0;
            for (e = 0; e < NEP; ++e) {
                /* ep_seed 는 (조건,에피소드)로만 정해짐 -> 모든 정책이 같은 표적/시작을 본다 */
                uint32_t ep_seed = 0xC0FFEEu + (uint32_t)(c * 100000 + e);
                PC_Env env = { 0.f, COND(c).illum, COND(c).cam_health, 0.f };
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
        double sr = 100.0 * succ_all[p] / ((double)NCOND * NEP);
        double mt = tn_all[p] ? t_all[p] / tn_all[p] : 0.0;
        double md = tn_all[p] ? d_all[p] / tn_all[p] : 0.0;
        printf("  %-13s  %5.1f   %8.1f  %10.1f   %5.2f  %4.2f\n",
               POLNAME[p], sr, mt, md, sw_all[p] / ((double)NCOND * NEP), rta_all[p] / ((double)NCOND * NEP));
    }
    return 0;
}
