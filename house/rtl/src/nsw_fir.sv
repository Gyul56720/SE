// =====================================================================
//  nsw_fir.sv -- Nowon Silicon Works, FIR/MAC accelerator IP
//  Owner : Ethan Ross (Front-End Design)
//
//  무엇을 보이려고 지었나 (다섯 가지를 한 파일에서 다 보이게 한다):
//    1. FSM 제어 흐름        -- nsw_ctrl : IDLE/LOAD/RUN/FLUSH/DONE, one-hot
//    2. 파이프라인            -- nsw_mac  : MUL -> ADD -> SAT, STAGES 로 깊이 조절
//    3. 파라미터 재사용성      -- TAPS/DW/CW/ACCW/STAGES 만 바꾸면 다른 IP 가 된다
//    4. 클럭 게이팅 전력 최적화 -- nsw_icg : latch+AND, 데이터패스 전체를 en 으로 잠근다
//    5. CDC                  -- nsw_sync2 / nsw_afifo : cfg_clk -> clk 두 도메인
//
//  클럭/리셋 구조:
//    clk      : 데이터패스. 비동기 assert / 동기 de-assert 리셋 (rst_n)
//    cfg_clk  : 설정 버스. 느리고 비동기. cfg_rst_n 은 제 도메인에서 동기화된다
//    모든 도메인 건넘은 nsw_sync2(제어) 또는 nsw_afifo(데이터)만 쓴다. 맨선 없음.
// =====================================================================

/* verilator lint_off DECLFILENAME */

// ---------------------------------------------------------------------
// 통합 클럭 게이팅 셀 (ICG). latch 가 빠지면 en 이 clk 高 구간에 바뀌며 글리치가
// 난다 -- 플롭이 볼 만큼 길고 최소 펄스폭을 어길 만큼 짧은 반쪽 펄스. latch 는
// clk 가 낮을 때만 투명하므로 en 은 낮은 상에서만 바뀐다.
// ---------------------------------------------------------------------
module nsw_icg (
    input  wire clk,
    input  wire en,
    input  wire test_en,     // 스캔 시프트 중에는 클럭을 무조건 통과시킨다 (DFT)
    output wire gclk
);
    reg en_lat;
    /* verilator lint_off LATCH */
    always @(*) if (!clk) en_lat = en | test_en;   // clk 낮을 때만 투명 (의도한 래치)
    /* verilator lint_on LATCH */
    assign gclk = clk & en_lat;
endmodule

// ---------------------------------------------------------------------
// 2단(파라미터) 동기화기. 단일 비트 제어 신호 전용.
// STAGES 를 늘리면 MTBF 가 지수로 는다 (DV 가 수로 확인한다).
// ---------------------------------------------------------------------
module nsw_sync2 #(
    parameter integer STAGES = 2,
    parameter         INIT   = 1'b0
) (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);
    reg [STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sync_q <= {STAGES{INIT}};
        else        sync_q <= {sync_q[STAGES-2:0], d};
    assign q = sync_q[STAGES-1];
endmodule

// ---------------------------------------------------------------------
// 그레이 코드 비동기 FIFO. 데이터 버스를 도메인 사이로 나른다.
// 포인터를 그레이로 건네는 까닭: 이진 카운터는 여러 비트가 한꺼번에 바뀌어
// 표본 순간에 어떤 조합으로도 잡힐 수 있다. 그레이는 한 비트만 바뀐다.
// ---------------------------------------------------------------------
module nsw_afifo #(
    parameter integer DW    = 16,
    parameter integer ADDRW = 3            // 깊이 = 2**ADDRW
) (
    input  wire            wclk,
    input  wire            wrst_n,
    input  wire            wpush,
    input  wire [DW-1:0]   wdata,
    output wire            wfull,
    input  wire            rclk,
    input  wire            rrst_n,
    input  wire            rpop,
    output wire [DW-1:0]   rdata,
    output wire            rempty
);
    localparam integer DEPTH = (1 << ADDRW);

    reg [DW-1:0] mem [0:DEPTH-1];

    reg  [ADDRW:0] wbin, wgray, rbin, rgray;
    reg            wfull_r, rempty_r;

    // **full/empty 는 등록한다.** 조합으로 두면 wfull -> wbin_nxt -> wgray_nxt -> wfull
    // 이라는 조합 고리가 생긴다 (verilator UNOPTFLAT 이 실제로 잡아냈다).
    wire           wen       = wpush & ~wfull_r;
    wire           ren       = rpop  & ~rempty_r;
    wire [ADDRW:0] wbin_nxt  = wbin + {{ADDRW{1'b0}}, wen};
    wire [ADDRW:0] wgray_nxt = (wbin_nxt >> 1) ^ wbin_nxt;
    wire [ADDRW:0] rbin_nxt  = rbin + {{ADDRW{1'b0}}, ren};
    wire [ADDRW:0] rgray_nxt = (rbin_nxt >> 1) ^ rbin_nxt;

    // 건너온 포인터 -- 그레이로 건네고 2단 동기화한다
    reg [ADDRW:0] wq1_rgray, wq2_rgray, rq1_wgray, rq2_wgray;

    wire full_nxt  = (wgray_nxt == {~wq2_rgray[ADDRW:ADDRW-1], wq2_rgray[ADDRW-2:0]});
    wire empty_nxt = (rgray_nxt == rq2_wgray);

    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wbin <= '0; wgray <= '0; wfull_r <= 1'b0; end
        else         begin wbin <= wbin_nxt; wgray <= wgray_nxt; wfull_r <= full_nxt; end

    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wq1_rgray <= '0; wq2_rgray <= '0; end
        else         begin wq1_rgray <= rgray; wq2_rgray <= wq1_rgray; end

    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rbin <= '0; rgray <= '0; rempty_r <= 1'b1; end
        else         begin rbin <= rbin_nxt; rgray <= rgray_nxt; rempty_r <= empty_nxt; end

    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rq1_wgray <= '0; rq2_wgray <= '0; end
        else         begin rq1_wgray <= wgray; rq2_wgray <= rq1_wgray; end

    always @(posedge wclk)
        if (wen) mem[wbin[ADDRW-1:0]] <= wdata;

    assign rdata  = mem[rbin[ADDRW-1:0]];
    assign wfull  = wfull_r;
    assign rempty = rempty_r;
endmodule

// ---------------------------------------------------------------------
// 파이프라인 MAC. STAGES = 1|2|3 으로 깊이를 고른다.
//   1 : MUL+ADD 한 주기 (느린 클럭, 작은 면적)
//   2 : MUL | ADD
//   3 : MUL | ADD | SAT   (기본 -- 가장 짧은 임계경로)
// 파이프라인의 값은 지연(latency)이고 사는 것은 주파수다. DV 가 둘 다 잰다.
// ---------------------------------------------------------------------
module nsw_mac #(
    parameter integer DW     = 16,
    parameter integer CW     = 16,
    parameter integer ACCW   = 40,
    parameter integer STAGES = 3
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 en,          // 파이프라인을 한 칸 민다 (RUN + FLUSH)
    input  wire                 push,        // 새 곱을 s1 에 넣는다 (RUN 에서만)
    input  wire                 clr,         // 누산기 비우기
    input  wire signed [DW-1:0] din,
    input  wire signed [CW-1:0] coef,
    output wire signed [ACCW-1:0] acc_o,
    output wire                 vld_o
);
    localparam integer PW = DW + CW;

    reg signed [PW-1:0]   p_s1;
    reg                   v_s1;
    reg signed [ACCW-1:0] a_s2;
    reg                   v_s2;
    reg signed [ACCW-1:0] a_s3;
    reg                   v_s3;

    wire signed [PW-1:0]   prod = din * coef;
    wire signed [ACCW-1:0] ext  = $signed({{(ACCW-PW){p_s1[PW-1]}}, p_s1});
    wire signed [ACCW:0]   raw  = $signed({a_s2[ACCW-1], a_s2}) + $signed({ext[ACCW-1], ext});

    // 포화 -- 넘침을 감싸지 않고 끝값에 붙인다. 오디오/영상 필터의 표준 거동이다.
    // 감싸면 큰 입력에서 부호가 뒤집혀 필터가 발진한 것처럼 보인다.
    localparam signed [ACCW-1:0] SAT_HI = {1'b0, {(ACCW-1){1'b1}}};
    localparam signed [ACCW-1:0] SAT_LO = {1'b1, {(ACCW-1){1'b0}}};
    wire ovf = (raw[ACCW] != raw[ACCW-1]);
    wire signed [ACCW-1:0] sum = ovf ? (raw[ACCW] ? SAT_LO : SAT_HI) : raw[ACCW-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p_s1 <= '0; v_s1 <= 1'b0;
            a_s2 <= '0; v_s2 <= 1'b0;
            a_s3 <= '0; v_s3 <= 1'b0;
        end else begin
            if (clr) begin
                p_s1 <= '0; v_s1 <= 1'b0;
                a_s2 <= '0; v_s2 <= 1'b0;
                a_s3 <= '0; v_s3 <= 1'b0;
            end else if (en) begin
                // **FLUSH 에서 push=0 이면 0 을 민다.** 안 그러면 남은 세 주기 동안
                // din 에 걸린 값이 계속 곱해져 누산기가 더럽혀진다 -- 파이프라인
                // 설계에서 가장 흔한 자리다.
                p_s1 <= push ? prod : '0;
                v_s1 <= push;
                a_s2 <= sum;       v_s2 <= v_s1;
                a_s3 <= a_s2;      v_s3 <= v_s2;
            end
        end
    end

    assign acc_o = (STAGES >= 3) ? a_s3 : a_s2;
    assign vld_o = (STAGES >= 3) ? v_s3 : v_s2;
endmodule

// ---------------------------------------------------------------------
// 제어 FSM. one-hot 인코딩 -- 상태 디코드가 한 비트이므로 임계경로가 짧고,
// 불법 상태(여러 비트 1 또는 0)가 DFT/어서션으로 보인다.
//
//   IDLE  --start--> LOAD  --cnt==TAPS-1--> RUN --cnt==LEN-1--> FLUSH --> DONE --ack--> IDLE
//                      ^                     |
//                      +-------- reload -----+
// ---------------------------------------------------------------------
module nsw_ctrl #(
    parameter integer TAPS   = 8,
    parameter integer CNTW   = 12,
    parameter integer STAGES = 3,
    // 0 = 상태 기반 게이팅 (LOAD|RUN|FLUSH 내내 클럭을 준다)
    // 1 = 박자 기반 게이팅 (유효한 샘플이 있는 주기에만 준다)
    // 둘의 차이는 **재서** 고른다 -- house/rtl 보고서의 A/B 그림이 그것이다.
    parameter integer GATE_POLICY = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            start,
    input  wire [CNTW-1:0] len,
    input  wire            ack,
    input  wire            in_vld,
    output wire            dp_en,        // 데이터패스 클럭 게이팅 인에이블
    output wire            acc_clr,
    output wire            coef_we,
    output wire            busy,
    output wire            done,
    output wire [CNTW-1:0] cnt_o,
    output wire [4:0]      state_o
);
    localparam [4:0] S_IDLE  = 5'b00001,
                     S_LOAD  = 5'b00010,
                     S_RUN   = 5'b00100,
                     S_FLUSH = 5'b01000,
                     S_DONE  = 5'b10000;

    reg [4:0]      st, st_n;
    reg [CNTW-1:0] cnt, cnt_n;

    always @(*) begin
        st_n  = st;
        cnt_n = cnt;
        case (st)
            S_IDLE : if (start) begin st_n = S_LOAD;  cnt_n = {CNTW{1'b0}}; end
            S_LOAD : if (in_vld) begin
                         if (cnt == TAPS[CNTW-1:0] - 1) begin st_n = S_RUN; cnt_n = {CNTW{1'b0}}; end
                         else cnt_n = cnt + 1'b1;
                     end
            S_RUN  : if (in_vld) begin
                         if (cnt >= len - 1) begin st_n = S_FLUSH; cnt_n = {CNTW{1'b0}}; end
                         else cnt_n = cnt + 1'b1;
                     end
            S_FLUSH: if (cnt == STAGES[CNTW-1:0] - 1) begin st_n = S_DONE; cnt_n = {CNTW{1'b0}}; end
                     else cnt_n = cnt + 1'b1;
            S_DONE : if (ack) begin st_n = S_IDLE; cnt_n = {CNTW{1'b0}}; end
            default: st_n = S_IDLE;                 // 불법 상태에서 빠져나온다
        endcase
    end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin st <= S_IDLE; cnt <= {CNTW{1'b0}}; end
        else        begin st <= st_n;   cnt <= cnt_n;        end

    // **클럭 게이팅의 인에이블이 여기서 나온다.** IDLE/DONE 에서 데이터패스 클럭이
    // 통째로 멈춘다 -- 전체 주기의 대부분이다(DV 가 토글로 잰다).
    wire st_active = (st == S_LOAD) | (st == S_RUN) | (st == S_FLUSH);
    assign dp_en   = (GATE_POLICY == 0) ? st_active
                                        : ((st == S_FLUSH) | (st_active & in_vld));
    assign acc_clr = (st == S_IDLE) | ((st == S_LOAD) & (cnt == {CNTW{1'b0}}));
    assign coef_we = (st == S_LOAD) & in_vld;
    assign busy    = ~(st[0] | st[4]);
    assign done    = st[4];
    assign cnt_o   = cnt;
    assign state_o = st;
endmodule

// ---------------------------------------------------------------------
// 최상위. cfg_clk 도메인에서 계수를 받아 afifo 로 건네고, clk 도메인에서
// FSM + 게이팅된 MAC 을 돌린다.
// ---------------------------------------------------------------------
module nsw_fir #(
    parameter integer TAPS   = 8,
    parameter integer DW     = 16,
    parameter integer CW     = 16,
    parameter integer ACCW   = 40,
    parameter integer STAGES = 3,
    parameter integer CNTW   = 12,
    parameter integer CDC_STAGES = 2,
    parameter integer GATE_POLICY = 1
) (
    // --- 데이터패스 도메인 ---
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   scan_en,      // DFT: 시프트 중 ICG 를 연다
    input  wire                   start,
    input  wire [CNTW-1:0]        len,
    input  wire                   ack,
    input  wire                   in_vld,
    input  wire signed [DW-1:0]   in_data,
    output wire                   busy,
    output wire                   done,
    output wire signed [ACCW-1:0] out_acc,
    output wire                   out_vld,
    output wire [4:0]             state_o,
    output wire                   gate_en_o,    // 관측용: ICG 에 실제로 들어가는 en
    // --- 설정 도메인 (비동기) ---
    input  wire                   cfg_clk,
    input  wire                   cfg_rst_n,
    input  wire                   cfg_we,
    input  wire signed [CW-1:0]   cfg_coef,
    output wire                   cfg_full,
    input  wire                   cfg_soft_rst  // 비동기 펄스 -> 동기화해서 쓴다
);
    // ---- CDC 1: 계수 버스 (async FIFO) ----
    wire                 coef_empty;
    wire signed [CW-1:0] coef_q;
    wire                 coef_pop;

    nsw_afifo #(.DW(CW), .ADDRW(3)) u_coef_fifo (
        .wclk(cfg_clk), .wrst_n(cfg_rst_n), .wpush(cfg_we), .wdata(cfg_coef), .wfull(cfg_full),
        .rclk(clk),     .rrst_n(rst_n),     .rpop(coef_pop), .rdata(coef_q),  .rempty(coef_empty)
    );

    // ---- CDC 2: 소프트 리셋 제어 비트 (2FF 동기화기) ----
    wire soft_rst_sync;
    nsw_sync2 #(.STAGES(CDC_STAGES)) u_srst_sync (
        .clk(clk), .rst_n(rst_n), .d(cfg_soft_rst), .q(soft_rst_sync)
    );

    wire rst_n_i = rst_n & ~soft_rst_sync;

    // ---- 제어 ----
    wire            dp_en, acc_clr, coef_we_i;
    /* verilator lint_off UNUSEDSIGNAL */
    wire [CNTW-1:0] cnt;
    /* verilator lint_on UNUSEDSIGNAL */
    wire            load_vld = ~coef_empty;
    wire            run_vld  = in_vld;
    wire            fsm_vld;

    nsw_ctrl #(.TAPS(TAPS), .CNTW(CNTW), .STAGES(STAGES), .GATE_POLICY(GATE_POLICY)) u_ctrl (
        .clk(clk), .rst_n(rst_n_i), .start(start), .len(len), .ack(ack),
        .in_vld(fsm_vld), .dp_en(dp_en), .acc_clr(acc_clr), .coef_we(coef_we_i),
        .busy(busy), .done(done), .cnt_o(cnt), .state_o(state_o)
    );

    assign fsm_vld  = state_o[1] ? load_vld : run_vld;   // LOAD 는 FIFO, RUN 은 입력
    assign coef_pop = coef_we_i;

    // ---- 계수 메모리 ----
    reg signed [CW-1:0] coef_mem [0:TAPS-1];
    always @(posedge clk)
        if (coef_we_i) coef_mem[cnt[$clog2(TAPS)-1:0]] <= coef_q;

    reg [$clog2(TAPS)-1:0] tap_ptr;
    wire run_beat = state_o[2] & run_vld;          // RUN 상태의 유효 샘플
    always @(posedge clk or negedge rst_n_i)
        if (!rst_n_i)      tap_ptr <= '0;
        else if (acc_clr)  tap_ptr <= '0;
        else if (run_beat) tap_ptr <= (tap_ptr == TAPS[$clog2(TAPS)-1:0] - 1) ? '0 : tap_ptr + 1'b1;

    wire signed [CW-1:0] coef_sel = coef_mem[tap_ptr];

    // ---- 클럭 게이팅 ----
    wire gclk;
    nsw_icg u_icg (.clk(clk), .en(dp_en), .test_en(scan_en), .gclk(gclk));
    assign gate_en_o = dp_en;

    // ---- 데이터패스 ----
    nsw_mac #(.DW(DW), .CW(CW), .ACCW(ACCW), .STAGES(STAGES)) u_mac (
        .clk(gclk), .rst_n(rst_n_i), .en(run_beat | state_o[3]), .push(run_beat), .clr(acc_clr),
        .din(in_data), .coef(coef_sel), .acc_o(out_acc), .vld_o(out_vld)
    );
endmodule

/* verilator lint_on DECLFILENAME */
