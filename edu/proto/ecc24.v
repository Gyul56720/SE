// ecc24.v -- 24비트 헤더 + 6비트 ECC, SEC-DED.  CSI-2/DSI 헤더 모양.
//
// ── 회로 구조 ─────────────────────────────────────────────────────────
//
//   data[23:0] ──┬─> P0 = ^(data & MASK0)  ──┐
//                ├─> P1 = ^(data & MASK1)  ──┤
//                ├─> P2 = ^(data & MASK2)  ──┼─> ecc_calc[4:0]
//                ├─> P3 = ^(data & MASK3)  ──┤
//                └─> P4 = ^(data & MASK4)  ──┘
//                          │
//                          └─> ecc_calc[5] = ^data ^ ^ecc_calc[4:0]
//
// 전부 **XOR 나무**다.  곱셈기도 덧셈기도 없다.  그래서 ECC 는 면적이
// 작고 빠르다 -- 13~14 입력 XOR 다섯 개가 전부다.  FPGA 에서 4입력 LUT
// 하나가 4입력 XOR 이므로, 14입력 XOR 는 LUT 다섯 개짜리 나무가 된다.
//
// ── 복호 ─────────────────────────────────────────────────────────────
//   신드롬 = 다시 계산한 P0..P4  XOR  받은 P0..P4
//   전체패리티 = 받은 30비트 전체의 XOR   <- **다시 부호화해서 비교하지 않는다**
//
//   신드롬 0, 전체패리티 0  ->  성함
//   신드롬 0, 전체패리티 1  ->  ECC 의 여섯째 비트가 깨짐.  데이터는 성함
//   신드롬 != 0, 전체패리티 1 -> 단일 오류.  신드롬이 가리키는 비트를 뒤집는다
//   신드롬 != 0, 전체패리티 0 -> 이중 오류.  **고치지 않고 알린다**
//
// 마지막 줄이 중요하다.  이중 오류를 고치려 들면 **성한 것을 더 망가뜨린다**.
// SEC-DED 의 D 는 "고칠 수 있다" 가 아니라 "고치지 말라고 알린다" 는 뜻이다.
module ecc24 (
    input  [23:0] data_in,
    input  [5:0]  ecc_in,
    output [5:0]  ecc_out,      // 부호화 결과 (송신 쪽이 쓴다)
    output [23:0] data_fixed,   // 고친 데이터 (수신 쪽이 쓴다)
    output        err_single,   // 한 비트 틀렸고 고쳤다
    output        err_double    // 둘 이상 틀렸다.  고치지 못했다
);
    // 패리티 마스크.  C++ 모델(`ecc24.h`)의 ECC_MASK 와 같은 값이다.
    // **손으로 다시 적었다** -- 생성하지 않았다.  그래야 골든 비교가
    // 양쪽을 다 검사한다.
    localparam [23:0] M0 = 24'hAAAD5B;
    localparam [23:0] M1 = 24'h33366D;
    localparam [23:0] M2 = 24'hC3C78E;
    localparam [23:0] M3 = 24'hFC07F0;
    localparam [23:0] M4 = 24'hFFF800;

    // `^(vector)` 는 리덕션 XOR -- 모든 비트를 XOR 한다.  이 한 글자가
    // 14입력 XOR 나무 하나다.  C++ 에는 이런 연산자가 없다 (Z18.6 참고).
    wire [4:0] p;
    assign p[0] = ^(data_in & M0);
    assign p[1] = ^(data_in & M1);
    assign p[2] = ^(data_in & M2);
    assign p[3] = ^(data_in & M3);
    assign p[4] = ^(data_in & M4);
    wire p5 = (^data_in) ^ (^p);

    assign ecc_out = {p5, p};

    // ── 복호 ─────────────────────────────────────────────────────────
    wire [4:0] syn  = p ^ ecc_in[4:0];
    // 전체패리티는 받은 것에서 바로 센다.  다시 부호화해 비교하면
    // 신드롬 자신의 패리티가 섞여 **단일오류 절반을 이중으로 오인한다**
    // (C++ 쪽에서 실측으로 물린 자리다).
    wire opar = (^data_in) ^ (^ecc_in);

    // 신드롬 -> 비트 자리.  각 데이터 비트의 신드롬은 그 비트가 어느
    // 마스크에 들어 있는가로 정해진다.  전부 상수라 합성기가 푼다.
    wire [23:0] fix;
    genvar g;
    generate
        for (g = 0; g < 24; g = g + 1) begin : gen_fix
            wire [4:0] s_g = { M4[g], M3[g], M2[g], M1[g], M0[g] };
            assign fix[g] = (syn == s_g) & opar & (syn != 5'd0);
        end
    endgenerate

    assign data_fixed = data_in ^ fix;
    // 홀수 개가 틀렸다 = 단일 오류로 다룬다.  신드롬이 0 이든 아니든
    // opar 하나로 정해지므로 그냥 opar 다.  (처음에는
    // `(syn != 0) ? opar : opar` 라고 썼는데, 두 갈래가 같은 삼항은
    // **읽는 사람에게 버그로 보인다** -- 같으면 갈래를 쓰지 않는다.)
    assign err_single = opar;
    assign err_double = (syn != 5'd0) & ~opar;
endmodule
