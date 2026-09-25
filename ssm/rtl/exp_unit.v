// 이산화 감쇠게이트 exp 근사 -- 직접 LUT.
//
// Abar = exp(-m), m = -z = -(delta*A) >= 0. 입력 m 은 Q3.13 무부호 16b [0,8).
// 출력 Abar 는 Q0.16 무부호 16b (0,1]. 1.0 은 0xffff 로 포화.
//
// 근사: m 의 상위 IDXBITS 비트로 K=2^IDXBITS 엔트리 LUT 을 친다. **곱셈 없음** ->
// exp 가 DSP 가 아니라 로직/ROM 으로 가는지 재는 것이 목적(설계.md §2).
// 조합 유닛(자원 상한). 실제 파이프라인은 한 단 레지스터만 더 붙이면 된다.
module exp_unit #(
  parameter IDXBITS = 6,                       // K = 2^IDXBITS 엔트리
  parameter MBITS   = 16,
  parameter ABITS   = 16,
  parameter LUTFILE = "ssm/dv/exp_lut_64.memh"
)(
  input  wire [MBITS-1:0] m,                   // Q3.13 무부호, = -z
  output wire [ABITS-1:0] abar                 // Q0.16 무부호
);
  localparam K = (1 << IDXBITS);
  reg [ABITS-1:0] tab [0:K-1];
  initial $readmemh(LUTFILE, tab);
  wire [IDXBITS-1:0] idx = m[MBITS-1 -: IDXBITS];   // 상위 IDXBITS 비트
  assign abar = tab[idx];
endmodule
