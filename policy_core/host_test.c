/* host_test.c -- 데스크톱에서 policy_core 를 돌려 창발·RTA·belief 갱신을 증명.
 * "C 코어가 Python 시뮬(recon/sensor_agnostic.py)과 같은 행동을 낸다"를 붙든다.
 * UGV 현실 센서 3종 어댑터(Camera·LiDAR·Thermal)와 조명 노브(낮->밤)로 센서선택이
 * 손코딩 없이 창발하는지 본다. 정책 코어는 이 어댑터들이 무엇인지 모른다. */
#include "policy_core.h"
#include <math.h>
#include <stdio.h>

/* ── 관측모델 어댑터: 유일한 센서-특정 조각. 코어는 함수포인터만 본다 ── */
/* Camera: 고해상, 조명 의존(밤에 죽음). */
static float cam_p(const void *c, float r, float a, const PC_Env *e) {
    (void)c; (void)a; return 0.92f * expf(-(r / 25.f) * (r / 25.f)) * e->illum;
}
static float cam_s(const void *c, float r) { (void)c; return 0.30f + 0.010f * r; }
/* LiDAR: 조명 무관(능동), 중간 해상, 거리 제한. */
static float lid_p(const void *c, float r, float a, const PC_Env *e) {
    (void)c; (void)a; (void)e; return 0.80f * expf(-(r / 18.f) * (r / 18.f));
}
static float lid_s(const void *c, float r) { (void)c; return 0.50f + 0.020f * r; }
/* Thermal: 조명 무관(주야), 중고해상. */
static float thr_p(const void *c, float r, float a, const PC_Env *e) {
    (void)c; (void)a; (void)e; return 0.85f * expf(-(r / 22.f) * (r / 22.f));
}
static float thr_s(const void *c, float r) { (void)c; return 0.40f + 0.015f * r; }

static int inside_keepout(float x, float y, float tx, float ty, float ko) {
    float dx = x - tx, dy = y - ty; return (dx * dx + dy * dy) < ko * ko;
}
static PC_Cfg mkcfg(void) {
    PC_Cfg c; c.alpha = 1.f; c.beta = 0.02f; c.gamma = 0.01f;
    c.cell_m = 5.f; c.r_max_cells = 9.f; c.v_nom = 1.f; c.n_look_max = 3;
    return c;
}
static void belief_bump(PC_Belief *b, float cx, float cy, float s) {
    int gx, gy; float sum = 0.f;
    for (gy = 0; gy < PC_GRID_H; ++gy) for (gx = 0; gx < PC_GRID_W; ++gx) {
        float d2 = (gx - cx) * (gx - cx) + (gy - cy) * (gy - cy);
        float v = expf(-d2 / (2.f * s * s)) + 0.02f;
        b->p[gy * PC_GRID_W + gx] = v; sum += v;
    }
    { int i; for (i = 0; i < PC_GRID_N; ++i) b->p[i] /= sum; }
}

int main(void) {
    PC_ObsModel M[3];
    M[0].p_useful = cam_p; M[0].precision = cam_s; M[0].cfg = 0; M[0].id = 0; /* Camera */
    M[1].p_useful = lid_p; M[1].precision = lid_s; M[1].cfg = 0; M[1].id = 1; /* LiDAR  */
    M[2].p_useful = thr_p; M[2].precision = thr_s; M[2].cfg = 0; M[2].id = 2; /* Thermal*/
    const char *NAME[3] = { "Camera", "LiDAR", "Thermal" };
    PC_Cfg cfg = mkcfg();
    PC_Vehicle veh = { 5.f, 5.f, 0.f, 1.f };
    PC_Belief b; belief_bump(&b, 9.f, 9.f, 1.2f);   /* 표적 질량 근처(관측반경 안) */
    int fails = 0;

    /* 1. 창발: 조명 쓸기서 정책이 고르는 센서 (손코딩 규칙 없음) */
    printf("[emergence] illum 1.0(day)->0.0(night) 에서 pi(s) 가 고르는 센서:\n");
    int day_sensor = -1, night_sensor = -1;
    for (int i = 0; i <= 10; ++i) {
        float illum = 1.0f - 0.1f * i;
        PC_Env env = { 0.f, illum, 0.f, 0.f };
        PC_Action a = pc_policy_step(&b, &veh, M, 3, &env, &cfg);
        printf("   illum=%.1f -> %s (n_look=%u)\n", illum, NAME[a.sensor], a.n_look);
        if (i == 0)  day_sensor = a.sensor;
        if (i == 10) night_sensor = a.sensor;
    }
    if (day_sensor != 0) { printf("FAIL: day 에 Camera 안 고름\n"); fails++; }
    if (night_sensor == 0) { printf("FAIL: night 에 Camera 고름(죽었는데)\n"); fails++; }
    if (night_sensor != 2) { printf("FAIL: night 에 Thermal 안 고름(=%d)\n", night_sensor); fails++; }
    printf("  => day=%s, night=%s  (창발: 조명서 센서선택이 손코딩 없이 뒤바뀜)\n",
           NAME[day_sensor], NAME[night_sensor]);

    /* 2. RTA: 위협 keep-out 이 표적 방향에 있으면 안전행동으로 대체 */
    float dx[PC_MAX_MOVES], dy[PC_MAX_MOVES]; uint8_t nmv; pc_default_moves(dx, dy, &nmv);
    PC_Env night = { 0.f, 0.f, 0.f, 0.f };
    PC_Action a = pc_policy_step(&b, &veh, M, 3, &night, &cfg);
    PC_Safety saf = { a.tgt_x, a.tgt_y, 3.f, 1 };   /* 정책이 가려던 바로 그 셀을 keep-out 로 */
    PC_Action as = pc_rta_filter(a, &veh, &saf, dx, dy, nmv);
    if (!as.rta_tripped) { printf("FAIL: RTA 가 keep-out 침범을 안 막음\n"); fails++; }
    if (inside_keepout(as.tgt_x, as.tgt_y, saf.thr_x, saf.thr_y, saf.keepout_cells)) {
        printf("FAIL: RTA 대체 후에도 keep-out 안\n"); fails++;
    }
    printf("[RTA] keep-out 침범 -> 대체 %s (tgt (%.0f,%.0f)->(%.0f,%.0f))\n",
           as.rta_tripped ? "발동" : "미발동", a.tgt_x, a.tgt_y, as.tgt_x, as.tgt_y);

    /* 3. belief 갱신: 탐지 시 엔트로피 감소(정보이득) */
    float H0 = pc_belief_entropy(&b);
    PC_Belief b2 = b;
    pc_belief_update(&b2, &veh, &M[2], &night, &cfg, 1, 9.f, 9.f);
    float H1 = pc_belief_entropy(&b2);
    if (!(H1 < H0)) { printf("FAIL: 탐지 후 엔트로피 안 줄음 %.3f->%.3f\n", H0, H1); fails++; }
    printf("[belief] 탐지 관측 -> 엔트로피 %.3f -> %.3f (정보이득)\n", H0, H1);

    printf(fails ? "\npolicy_core host_test: %d FAIL\n" : "\npolicy_core host_test: ALL PASS\n", fails);
    return fails ? 1 : 0;
}
