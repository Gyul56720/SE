// =====================================================================
//  tb_nsw_aim.cpp -- Nowon Silicon Works / Design Verification
//  Owner : Priya Raghavan (Verification Lead)
//
//  AIM2 (KpqC AIMer v2.0) 의 역 Mersenne S-box, GF(2^128).
//
//  **정답을 여기서 짓지 않는다.** KpqC 레퍼런스 C 가 낸 벡터를 읽어 대조한다
//  (aim/dv/gen_vectors_merinv.c 가 gf_exp(x, aim2_sbox_exponents[0]) 를 돌린다).
//  검증이 스스로 정답을 지으면 같은 오해를 두 번 하게 된다.
//
//  내는 것: stdout 에 JSON 한 줄.
// =====================================================================
#include "Vaim_mer_inv.h"
#include "verilated.h"
#if VM_COVERAGE
#include "verilated_cov.h"
#endif

#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

struct U128 { uint32_t w[4]; };                 // verilator 의 128비트 포트 꼴

static bool parse_hex128(const char* s, U128& v) {
    if (strlen(s) != 32) return false;
    for (int i = 0; i < 4; i++) {
        char buf[9];
        memcpy(buf, s + (3 - i) * 8, 8); buf[8] = 0;     // 낮은 워드가 w[0]
        v.w[i] = (uint32_t)strtoul(buf, nullptr, 16);
    }
    return true;
}
static bool eq128(const uint32_t* a, const U128& b) {
    for (int i = 0; i < 4; i++) if (a[i] != b.w[i]) return false;
    return true;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    // 벡터 파일 찾기 -- 흐름은 어느 cwd 에서 부를지 모른다. **못 찾으면 죽는다**(조용히
    // 0 건으로 통과하지 않는다). SE_ROOT 나 AIM_VECTORS 로 못 박을 수 있다.
    std::string vec;
    {
        const char* env = getenv("AIM_VECTORS");
        std::vector<std::string> cand;
        if (env && *env) cand.push_back(env);
        if (const char* root = getenv("SE_ROOT")) {
            cand.push_back(std::string(root) + "/house/dv/vectors_merinv.txt");
            cand.push_back(std::string(root) + "/aim/dv/vectors_merinv.txt");
        }
        cand.push_back("house/dv/vectors_merinv.txt");
        cand.push_back("aim/dv/vectors_merinv.txt");
        cand.push_back("../house/dv/vectors_merinv.txt");
        cand.push_back("../../house/dv/vectors_merinv.txt");
        for (auto& c : cand) { FILE* t = fopen(c.c_str(), "r"); if (t) { fclose(t); vec = c; break; } }
        if (vec.empty()) {
            fprintf(stderr, "tb_nsw_aim: vectors_merinv.txt not found (tried %d paths)\n", (int)cand.size());
            return 2;
        }
    }
    const char* vecpath = vec.c_str();

    Vaim_mer_inv* dut = new Vaim_mer_inv;
    uint64_t clk_edges = 0;
    int txn = 0, pass = 0, fail = 0, timeout = 0;
    int cyc_min = 1 << 30, cyc_max = 0;
    long long cyc_sum = 0;

    auto tick = [&]() { dut->clk = 0; dut->eval(); dut->clk = 1; dut->eval(); clk_edges++; };

    // 비동기 리셋을 **실제로 걸어야** 한다. rst_n 을 0 으로 두기만 하면 엣지가 없다
    // (실측: iverilog 테스트벤치에서 이걸 놓쳐 레지스터가 X 로 남고 시간초과가 났다).
    dut->rst_n = 1; dut->start = 0; dut->clk = 0; dut->eval();
    dut->rst_n = 0; dut->eval(); tick(); tick();
    dut->rst_n = 1; tick();

    FILE* f = fopen(vecpath, "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", vecpath); return 2; }

    char xs[64], ys[64];
    while (fscanf(f, "%63s %63s", xs, ys) == 2) {
        U128 xv, yv;
        if (!parse_hex128(xs, xv) || !parse_hex128(ys, yv)) continue;
        for (int i = 0; i < 4; i++) dut->x[i] = xv.w[i];
        dut->start = 1; tick(); dut->start = 0;
        int c = 0;
        while (!dut->done && c < 400) { tick(); c++; }
        txn++;
        if (c >= 400) { timeout++; }
        else {
            if (c < cyc_min) cyc_min = c;
            if (c > cyc_max) cyc_max = c;
            cyc_sum += c;
            if (eq128(dut->z, yv)) pass++; else fail++;
        }
        tick();
    }
    fclose(f);
    dut->final();

    // **벡터가 0개이면 '틀린 게 없다' 가 아니라 검사를 안 한 것이다.**
    int ok = (txn > 0 && fail == 0 && timeout == 0);
    printf("{");
    printf("\"design\":\"nsw_aim\",");
    printf("\"txn\":%d,\"pass\":%d,\"fail\":%d,\"timeout\":%d,\"proto_err\":0,", txn, pass, fail, timeout);
    printf("\"clk_cycles\":%llu,\"gclk_cycles\":%llu,\"gate_save_pct\":0.0,",
           (unsigned long long)clk_edges, (unsigned long long)clk_edges);
    printf("\"cyc_min\":%d,\"cyc_max\":%d,\"cyc_med\":%d,",
           (txn ? cyc_min : 0), cyc_max, (txn ? (int)(cyc_sum / (txn ? txn : 1)) : 0));
#if VM_COVERAGE
    { const char* cp = getenv("SE_COV_OUT"); if (cp && *cp) VerilatedCov::write(cp); }
#endif
    printf("\"ok\":%d", ok);
    printf("}\n");
    delete dut;
    return ok ? 0 : 1;
}
