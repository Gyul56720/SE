// FFT-256, radix-2 DIT, **스트리밍 아님 -- 자원을 재는 것이 목적**이라 가장 단순한 꼴.
//
// 왜 이 꼴인가: AIM 을 죽인 것이 "자원부터 안 쟀다" 였다. 그래서 여기서는 완성도가
// 아니라 **중급 FPGA 에 들어가는 규모인지** 를 먼저 본다. 조합 나비 하나 + 레지스터.
//
// Q1.15 고정소수. 트위들은 ROM. 이 판은 나비 한 개를 재사용하는 반복 구조가 아니라
// **한 단(stage)을 펼친 조합 버전**이라 크다 -- 상한을 잡기 위한 것이다.
// 실제 IP 는 Xilinx FFT(파이프라인/버스트)를 쓰지만 그건 라이선스 IP 라 여기 없다.
module fft256_bfly (
  input  wire signed [15:0] ar, ai,   // 입력 A
  input  wire signed [15:0] br, bi,   // 입력 B
  input  wire signed [15:0] wr, wi,   // 트위들 W
  output wire signed [15:0] xr, xi,   // A + W*B
  output wire signed [15:0] yr, yi    // A - W*B
);
  // W*B (복소곱): (wr+jwi)(br+jbi) = (wr*br - wi*bi) + j(wr*bi + wi*br)
  wire signed [31:0] pr = wr*br - wi*bi;
  wire signed [31:0] pi = wr*bi + wi*br;
  wire signed [15:0] tr = pr >>> 15;   // Q1.15 정규화
  wire signed [15:0] ti = pi >>> 15;
  assign xr = ar + tr;  assign xi = ai + ti;
  assign yr = ar - tr;  assign yi = ai - ti;
endmodule
