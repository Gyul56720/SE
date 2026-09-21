// =====================================================================
//  tb_nsw_fir.cpp -- Nowon Silicon Works / Design Verification
//  Owner : Priya Raghavan (Verification Lead)
//
//  UVM 을 못 쓴다(이 기계에 VCS/Questa 가 없다). 그래서 **UVM 의 구조를 그대로
//  C++ 로 옮겼다** -- sequence / driver / monitor / reference model / scoreboard /
//  coverage 가 따로 있고, monitor 는 driver 의 의도를 모르고 핀만 본다.
//
//  왜 verilator 인가: 초당 수십만 주기가 나온다. "수천, 수만 번" 은 말이 아니라
//  수여야 하고, 그 수를 낼 수 있는 유일한 엔진이 여기 있는 것이 이것뿐이다.
//
//  내는 것: stdout 에 JSON 한 줄. 파이썬이 그것을 읽어 그림을 그린다.
// =====================================================================
#include "Vnsw_fir.h"
#include "verilated.h"
#if VM_TRACE
#include "verilated_vcd_c.h"
#endif

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <string>
#include <map>
#include <set>
#include <algorithm>

// ---------------------------------------------------------------- 파라미터
static const int TAPS   = 8;
static const int ACCW   = 40;
static const int STAGES = 3;

static int64_t SAT_HI =  ((int64_t)1 << (ACCW - 1)) - 1;
static int64_t SAT_LO = -((int64_t)1 << (ACCW - 1));

// ---------------------------------------------------------------- 난수 (재현 가능)
struct Rng {
    uint64_t s;
    explicit Rng(uint64_t seed) : s(seed ? seed : 0x9E3779B97F4A7C15ull) {}
    uint64_t next() { s ^= s << 13; s ^= s >> 7; s ^= s << 17; return s; }
    uint32_t u32() { return (uint32_t)(next() >> 32); }
    int      range(int lo, int hi) { return lo + (int)(u32() % (uint32_t)(hi - lo + 1)); }
    bool     chance(int pct) { return (int)(u32() % 100) < pct; }
    int16_t  s16(int mag) {                       // 제약: |x| <= mag
        int v = (int)(u32() % (uint32_t)(2 * mag + 1)) - mag;
        return (int16_t)v;
    }
};

// ---------------------------------------------------------------- 거래
struct Txn {
    int              id;
    int              len;
    std::vector<int16_t> coef;
    std::vector<int16_t> data;
    int              gap_pct;      // 입력 밸리드가 비는 비율 (백프레셔 흉내)
    int64_t          golden;       // 참조 모델 결과
    int64_t          got;          // DUT 결과
    int              done_cnt;     // 프로토콜: 거래당 정확히 1 이어야 한다
    int              cycles;
    bool             ok;
};

// ---------------------------------------------------------------- 참조 모델
//  RTL 과 **따로** 적는다. 같은 식을 두 번 적는 것이 아니라, 스펙을 보고 적는다.
//  포화는 RTL 과 같은 규칙(감싸지 않고 끝값에 붙인다).
static int64_t golden_model(const std::vector<int16_t>& data,
                            const std::vector<int16_t>& coef, int len) {
    int64_t acc = 0;
    for (int i = 0; i < len; i++) {
        int64_t p = (int64_t)data[i] * (int64_t)coef[i % TAPS];
        int64_t n = acc + p;
        if (n > SAT_HI) n = SAT_HI;
        if (n < SAT_LO) n = SAT_LO;
        acc = n;
    }
    return acc;
}

// ---------------------------------------------------------------- 커버리지
struct Coverage {
    // 커버포인트: len 구간 · 계수 부호 · 데이터 크기 · 백프레셔 · FSM 상태 · 포화 여부
    std::set<int> cp_len, cp_sign, cp_mag, cp_bp, cp_state, cp_sat;
    std::set<std::pair<int,int>> cross_len_bp;      // len x 백프레셔
    std::set<std::pair<int,int>> cross_mag_sat;     // 데이터 크기 x 포화

    static int bin_len(int v) { return v < 8 ? 0 : v < 32 ? 1 : v < 128 ? 2 : v < 512 ? 3 : 4; }
    static int bin_bp(int v)  { return v == 0 ? 0 : v < 20 ? 1 : v < 50 ? 2 : 3; }
    static int bin_mag(int v) { return v < 64 ? 0 : v < 1024 ? 1 : v < 16384 ? 2 : 3; }

    void sample(const Txn& t, bool saturated, int mag) {
        int bl = bin_len(t.len), bb = bin_bp(t.gap_pct), bm = bin_mag(mag);
        cp_len.insert(bl); cp_bp.insert(bb); cp_mag.insert(bm);
        cp_sat.insert(saturated ? 1 : 0);
        int neg = 0, pos = 0;
        for (int i = 0; i < TAPS; i++) { if (t.coef[i] < 0) neg = 1; if (t.coef[i] > 0) pos = 1; }
        cp_sign.insert(neg * 2 + pos);
        cross_len_bp.insert({bl, bb});
        cross_mag_sat.insert({bm, saturated ? 1 : 0});
    }
    void state(int oh) { cp_state.insert(oh); }

    double pct() const {
        // 닿을 수 있는 칸: len 5 · bp 4 · mag 4 · sat 2 · sign 4(00 은 계수가 전부 0 일 때) ·
        // state 5 · cross(5x4=20) · cross(4x2=8)
        int hit = (int)(cp_len.size() + cp_bp.size() + cp_mag.size() + cp_sat.size() +
                        cp_sign.size() + cp_state.size() + cross_len_bp.size() + cross_mag_sat.size());
        int all = 5 + 4 + 4 + 2 + 4 + 5 + 20 + 8;
        return 100.0 * hit / all;
    }
};

// ---------------------------------------------------------------- 주 하네스
struct Harness {
    Vnsw_fir* dut;
    Rng rng;
    vluint64_t t = 0;
    // 토글 세기 -- 클럭 게이팅이 실제로 무엇을 아꼈는지
    uint64_t clk_edges = 0, gclk_edges = 0;
    int last_gclk = 0;
    // CDC: cfg 도메인은 다른 주기로 돈다
    int cfg_period, cfg_phase = 0;
    // 관측기(monitor)가 본 것
    std::vector<int> state_seq;
    Coverage cov;
#if VM_TRACE
    VerilatedVcdC* tfp = nullptr;
#endif
    // 파형 그림용 작은 흔적 (앞 N 주기)
    std::vector<std::string> trace_clk, trace_gclk, trace_vld, trace_done;
    std::vector<int> trace_state;
    int trace_n;

    Harness(uint64_t seed, int cfgp, int tracen)
        : dut(new Vnsw_fir), rng(seed), cfg_period(cfgp), trace_n(tracen) {}
    ~Harness() {
#if VM_TRACE
        if (tfp) { tfp->close(); delete tfp; }
#endif
        delete dut;
    }

    void tick_cfg() {
        cfg_phase++;
        if (cfg_phase >= cfg_period) {
            cfg_phase = 0;
            dut->cfg_clk = !dut->cfg_clk;
        }
    }

    // 한 주기: clk 를 한 번 토글. cfg_clk 은 제 주기로 따로 토글한다(비동기).
    void cyc() {
        dut->clk = 0; tick_cfg(); dut->eval();
#if VM_TRACE
        if (tfp) tfp->dump(t);
#endif
        t++;
        dut->clk = 1; tick_cfg(); dut->eval();
        clk_edges++;
        // ICG 에 실제로 들어가는 en 을 DUT 이 관측 포트로 낸다 -- 추측하지 않는다.
        int dp_en = dut->gate_en_o;
        if (dp_en) gclk_edges++;
        state_seq.push_back(dut->state_o);
        cov.state(dut->state_o);
        if ((int)trace_state.size() < trace_n) {
            trace_clk.push_back("1"); trace_gclk.push_back(dp_en ? "1" : "0");
            trace_vld.push_back(dut->in_vld ? "1" : "0");
            trace_done.push_back(dut->done ? "1" : "0");
            trace_state.push_back(dut->state_o);
        }
#if VM_TRACE
        if (tfp) tfp->dump(t);
#endif
        t++;
    }

    void reset() {
        dut->clk = 0; dut->cfg_clk = 0;
        dut->rst_n = 0; dut->cfg_rst_n = 0; dut->cfg_soft_rst = 0;
        dut->scan_en = 0; dut->start = 0; dut->ack = 0;
        dut->in_vld = 0; dut->in_data = 0; dut->cfg_we = 0; dut->cfg_coef = 0;
        dut->len = 0;
        for (int i = 0; i < 12; i++) cyc();
        dut->rst_n = 1; dut->cfg_rst_n = 1;
        for (int i = 0; i < 4; i++) cyc();
    }

    // ---- driver: 설정 도메인으로 계수를 밀어 넣는다 (CDC 를 진짜로 건넌다) ----
    void push_coefs(const std::vector<int16_t>& coef, int& cyc_used, int cap) {
        size_t k = 0;
        int guard = 0;
        while (k < coef.size() && guard < cap) {
            // cfg_clk 상승 직전에만 값을 세운다 -- 느린 도메인의 드라이버
            if (!dut->cfg_full) {
                dut->cfg_we = 1;
                dut->cfg_coef = (uint16_t)coef[k];
                // cfg_clk 이 한 번 오를 때까지 돌린다
                int before = dut->cfg_clk;
                int spin = 0;
                while (spin < 64 && !(before == 0 && dut->cfg_clk == 1)) {
                    before = dut->cfg_clk; cyc(); cyc_used++; spin++; guard++;
                }
                dut->cfg_we = 0;
                k++;
            } else {
                dut->cfg_we = 0; cyc(); cyc_used++; guard++;
            }
        }
        dut->cfg_we = 0;
    }

    // ---- 한 거래를 끝까지 돌린다 ----
    bool run_txn(Txn& tx, int cap) {
        int used = 0;
        tx.done_cnt = 0;

        push_coefs(tx.coef, used, cap / 2);

        dut->len = tx.len;
        dut->start = 1; cyc(); used++;
        dut->start = 0;

        size_t si = 0;
        int guard = 0;
        int prev_done = 0;
        while (guard < cap) {
            int st = dut->state_o;
            // LOAD: FIFO 가 알아서 빠진다. RUN: 샘플을 던진다(백프레셔 포함).
            if (st & 0x4) {
                if (si < tx.data.size() && !rng.chance(tx.gap_pct)) {
                    dut->in_vld = 1; dut->in_data = (uint16_t)tx.data[si]; si++;
                } else {
                    dut->in_vld = 0;
                }
            } else {
                dut->in_vld = 0;
            }
            cyc(); used++; guard++;
            if (dut->done && !prev_done) tx.done_cnt++;
            prev_done = dut->done;
            if (dut->done) break;
        }
        dut->in_vld = 0;
        if (!dut->done) { tx.cycles = used; return false; }

        // ---- monitor: 핀에서만 읽는다 ----
        tx.got = (int64_t)dut->out_acc;
        if (tx.got & ((int64_t)1 << (ACCW - 1)))
            tx.got -= ((int64_t)1 << ACCW);          // 부호 확장
        tx.cycles = used;

        dut->ack = 1; cyc(); dut->ack = 0;
        for (int i = 0; i < 3; i++) cyc();
        return true;
    }
};

// ---------------------------------------------------------------- main
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    uint64_t seed = 1;
    int txn_n = 200, cap = 40000, cfg_period = 3, trace_n = 0, directed_n = 0;
    int max_len = 256, err_show = 6;
    const char* vcd = nullptr;
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        auto val = [&](int d) { return (i + 1 < argc) ? atoi(argv[++i]) : d; };
        if      (a == "--seed")  seed = (uint64_t)val(1);
        else if (a == "--txn")   txn_n = val(200);
        else if (a == "--cap")   cap = val(40000);
        else if (a == "--cfg")   cfg_period = val(3);
        else if (a == "--trace") trace_n = val(0);
        else if (a == "--maxlen")max_len = val(256);
        else if (a == "--dir")   directed_n = val(0);
        else if (a == "--vcd")   vcd = (i + 1 < argc) ? argv[++i] : nullptr;
    }

    Harness H(seed, cfg_period, trace_n);
#if VM_TRACE
    if (vcd) {
        Verilated::traceEverOn(true);
        H.tfp = new VerilatedVcdC;
        H.dut->trace(H.tfp, 99);
        H.tfp->open(vcd);
    }
#else
    (void)vcd;
#endif
    H.reset();

    int pass = 0, fail = 0, timeout = 0, proto = 0;
    std::vector<std::string> errs;
    std::vector<int> cycles_hist;
    int64_t worst_diff = 0;
    int sat_cnt = 0;

    // 랜덤 구간 뒤에 **지시 시험(directed)** 구간이 붙는다.
    //   왜: 포화 칸은 제약 랜덤으로 영영 안 닿는다. |a|,|x| 를 아무리 키워도 부호가
    //   섞이면 누산이 랜덤 워크가 되어 sqrt(len) 로만 자란다 -- 실측: maxlen 4000,
    //   |x|<=32767 에서도 포화 0건. 부호를 같게 **고정**해야 닿는다. 그것이 지시 시험이다.
    int total_n = txn_n + directed_n;
    for (int i = 0; i < total_n; i++) {
        Txn tx;
        tx.id = i;
        bool directed = (i >= txn_n);
        // ---- sequence: 제약 랜덤 (+ 지시) ----
        int shape = directed ? (10 + (i - txn_n) % 2) : H.rng.range(0, 9);
        if      (shape == 0) tx.len = H.rng.range(1, 4);            // 아주 짧은 것
        else if (shape == 1) tx.len = TAPS;                         // 정확히 한 바퀴
        else if (shape == 2) tx.len = max_len;                      // 최장
        else if (shape >= 10) tx.len = max_len;                     // 지시: 최장
        else                 tx.len = H.rng.range(1, max_len);
        int mag = (shape == 3 || shape >= 10) ? 32767
                                              : (H.rng.chance(25) ? 32767 : H.rng.range(1, 4096));
        tx.gap_pct = (shape >= 10) ? 0 : (H.rng.chance(30) ? 0 : H.rng.range(1, 70));
        tx.coef.resize(TAPS);
        tx.data.resize(tx.len);
        if (shape >= 10) {
            // 지시 시험: 모든 곱이 같은 부호가 되게 고정한다 -> 누산이 선형으로 자라 포화에 닿는다
            int16_t dv = (shape == 10) ? (int16_t)32767 : (int16_t)-32768;
            for (int k = 0; k < TAPS; k++) tx.coef[k] = (int16_t)32767;
            for (int k = 0; k < tx.len; k++) tx.data[k] = dv;
        } else {
            for (int k = 0; k < TAPS; k++)
                tx.coef[k] = (shape == 4) ? (int16_t)(k % 2 ? -32768 : 32767) : H.rng.s16(mag);
            for (int k = 0; k < tx.len; k++)
                tx.data[k] = (shape == 4) ? (int16_t)32767 : H.rng.s16(mag);
        }

        tx.golden = golden_model(tx.data, tx.coef, tx.len);
        bool saturated = (tx.golden == SAT_HI || tx.golden == SAT_LO);
        if (saturated) sat_cnt++;

        bool ok = H.run_txn(tx, cap);
        H.cov.sample(tx, saturated, mag);
        cycles_hist.push_back(tx.cycles);

        if (!ok) {
            timeout++;
            if ((int)errs.size() < err_show)
                errs.push_back("txn " + std::to_string(i) + ": TIMEOUT len=" + std::to_string(tx.len));
            // 회복: 하드 리셋
            H.dut->rst_n = 0; for (int z = 0; z < 6; z++) H.cyc(); H.dut->rst_n = 1;
            for (int z = 0; z < 4; z++) H.cyc();
            continue;
        }
        // ---- scoreboard ----
        bool datum_ok = (tx.got == tx.golden);
        bool proto_ok = (tx.done_cnt == 1);       // 거래당 done 은 정확히 하나
        if (!proto_ok) proto++;
        if (datum_ok && proto_ok) pass++;
        else {
            fail++;
            int64_t d = tx.got - tx.golden;
            if (d < 0) d = -d;
            if (d > worst_diff) worst_diff = d;
            if ((int)errs.size() < err_show) {
                char buf[256];
                snprintf(buf, sizeof buf,
                         "txn %d: len=%d gap=%d%% got=%lld exp=%lld done_cnt=%d",
                         i, tx.len, tx.gap_pct, (long long)tx.got, (long long)tx.golden, tx.done_cnt);
                errs.push_back(buf);
            }
        }
    }

    // ---- 보고 (JSON 한 줄) ----
    double gate_save = H.clk_edges ? 100.0 * (1.0 - (double)H.gclk_edges / (double)H.clk_edges) : 0.0;
    std::sort(cycles_hist.begin(), cycles_hist.end());
    int cyc_med = cycles_hist.empty() ? 0 : cycles_hist[cycles_hist.size() / 2];
    int cyc_max = cycles_hist.empty() ? 0 : cycles_hist.back();

    printf("{");
    printf("\"seed\":%llu,", (unsigned long long)seed);
    printf("\"directed\":%d,", directed_n);
    printf("\"txn\":%d,\"pass\":%d,\"fail\":%d,\"timeout\":%d,\"proto_err\":%d,", total_n, pass, fail, timeout, proto);
    printf("\"sat_txn\":%d,\"worst_diff\":%lld,", sat_cnt, (long long)worst_diff);
    printf("\"clk_cycles\":%llu,\"gclk_cycles\":%llu,\"gate_save_pct\":%.4f,",
           (unsigned long long)H.clk_edges, (unsigned long long)H.gclk_edges, gate_save);
    printf("\"cov_pct\":%.4f,", H.cov.pct());
    printf("\"cov_len\":%d,\"cov_bp\":%d,\"cov_mag\":%d,\"cov_sat\":%d,\"cov_sign\":%d,\"cov_state\":%d,",
           (int)H.cov.cp_len.size(), (int)H.cov.cp_bp.size(), (int)H.cov.cp_mag.size(),
           (int)H.cov.cp_sat.size(), (int)H.cov.cp_sign.size(), (int)H.cov.cp_state.size());
    printf("\"cross_len_bp\":%d,\"cross_mag_sat\":%d,",
           (int)H.cov.cross_len_bp.size(), (int)H.cov.cross_mag_sat.size());
    printf("\"cyc_med\":%d,\"cyc_max\":%d,", cyc_med, cyc_max);
    printf("\"cross_len_bp_pairs\":[");
    { bool f = true; for (auto& p : H.cov.cross_len_bp) { if (!f) printf(","); printf("[%d,%d]", p.first, p.second); f = false; } }
    printf("],");
    printf("\"cyc_hist\":[");
    { for (size_t i = 0; i < cycles_hist.size(); i++) { if (i) printf(","); printf("%d", cycles_hist[i]); } }
    printf("],");
    printf("\"trace_state\":[");
    { for (size_t i = 0; i < H.trace_state.size(); i++) { if (i) printf(","); printf("%d", H.trace_state[i]); } }
    printf("],");
    printf("\"trace_gclk\":\"");
    { for (auto& s : H.trace_gclk) printf("%s", s.c_str()); }
    printf("\",");
    printf("\"trace_vld\":\"");
    { for (auto& s : H.trace_vld) printf("%s", s.c_str()); }
    printf("\",");
    printf("\"trace_done\":\"");
    { for (auto& s : H.trace_done) printf("%s", s.c_str()); }
    printf("\",");
    printf("\"errors\":[");
    { for (size_t i = 0; i < errs.size(); i++) { if (i) printf(","); printf("\"%s\"", errs[i].c_str()); } }
    printf("]}");
    printf("\n");
    return (fail || timeout) ? 1 : 0;
}
