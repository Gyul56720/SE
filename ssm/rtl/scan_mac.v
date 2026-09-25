// selective-scan 상태갱신 + 출력 (조합, 한 타임스텝, 채널 하나, 상태차원 N).
//
//   h[n] = Abar[n]*hprev[n] + Bbar[n]*x     (N MAC)
//   y    = sum_n C[n]*h[n]                   (N MAC + 가산트리)
//
// 목적(설계.md §2): 이 곱들이 DSP48 로 가는가, N 별 몇 개인가.
// **조합 언롤(상태 병렬)** -- 자원 상한(N 병렬 MAC). 순차판은 곱셈기 하나 재사용(다음 측정).
//
// 고정소수: x,Bbar,C=Q1.15 부호 / Abar=Q0.16 무부호(17b 부호확장) / h,y=Q4.12 부호 포화.
module scan_mac #(parameter N = 16) (
  input  wire signed [15:0]      x,
  input  wire        [16*N-1:0]  Abar,   // 무부호 Q0.16 팩
  input  wire signed [16*N-1:0]  Bbar,   // Q1.15 팩
  input  wire signed [16*N-1:0]  C,      // Q1.15 팩
  input  wire signed [16*N-1:0]  hprev,  // Q4.12 팩
  output wire        [16*N-1:0]  h,      // Q4.12 팩
  output wire signed [15:0]      y
);
  function signed [15:0] sat16(input signed [40:0] v);
    sat16 = (v >  32767) ?  16'sd32767 :
            (v < -32768) ? -16'sd32768 : v[15:0];
  endfunction

  genvar n;
  wire signed [39:0] prod [0:N-1];   // C*h 누산용 부분곱
  generate for (n=0; n<N; n=n+1) begin: g
    wire [15:0]        a_u  = Abar [16*n +: 16];
    wire signed [15:0] bb   = Bbar [16*n +: 16];
    wire signed [15:0] cc   = C    [16*n +: 16];
    wire signed [15:0] hp   = hprev[16*n +: 16];
    // p1 = Abar*hprev : 17b(부호,양수) * 16b = 33b, Q4.28 -> Q4.12 (>>16)
    wire signed [32:0] p1 = $signed({1'b0, a_u}) * hp;
    // p2 = Bbar*x : 16b*16b=32b, Q2.30 -> Q4.12 (>>18)
    wire signed [31:0] p2 = bb * x;
    wire signed [40:0] hn = (p1 >>> 16) + (p2 >>> 18);
    wire signed [15:0] hs = sat16(hn);
    assign h[16*n +: 16] = hs;
    assign prod[n] = cc * hs;          // Q1.15 * Q4.12 = Q5.27
  end endgenerate

  // 출력 리덕션: sum(prod) 를 Q4.12 로 (>>15), 포화
  integer k;
  reg signed [40:0] acc;
  always @* begin
    acc = 0;
    for (k=0; k<N; k=k+1) acc = acc + prod[k];
  end
  assign y = sat16(acc >>> 15);
endmodule
