// selective-scan 순차판 -- 곱셈기 하나를 재사용. 자원 하한(DSP 상수), 지연 큼.
// scan_mac(언롤)와 같은 결과를 내되 시간으로 편다. Pareto 의 반대 끝.
//
// 한 타임스텝에 3N 곱을 곱셈기 하나로: 상태갱신 2N(Abar*hprev, Bbar*x) + 출력 N(C*h).
// FSM: start 로 시작, done 으로 끝. h 는 내부 레지스터 배열. 입력은 그동안 안정.
// 고정소수는 scan_mac 과 동일 (비트로 같게).
module scan_seq #(parameter N = 16) (
  input  wire                   clk, rst_n, start,
  input  wire signed [15:0]     x,
  input  wire        [16*N-1:0] Abar, Bbar, C, hprev,
  output reg         [16*N-1:0] h,
  output reg  signed [15:0]     y,
  output reg                    done
);
  function signed [15:0] sat16(input signed [40:0] v);
    sat16 = (v> 32767)? 16'sd32767 : (v< -32768)? -16'sd32768 : v[15:0];
  endfunction

  // 공유 곱셈기 (18x18 부호). p = a*b.
  reg signed [17:0] ma, mb;
  wire signed [35:0] mp = ma * mb;

  localparam S_IDLE=0, S_UP=1, S_OUT=2, S_DONE=3;
  reg [1:0] st;
  integer idx;
  reg signed [40:0] acc;
  reg signed [40:0] p1;         // Abar*hprev >>16 를 담아 두 곱을 한 곱셈기로

  // 현재 인덱스의 슬라이스
  wire [15:0]        a_u = Abar [16*idx +:16];
  wire signed [15:0] bb  = Bbar [16*idx +:16];
  wire signed [15:0] cc  = C    [16*idx +:16];
  wire signed [15:0] hp  = hprev[16*idx +:16];
  reg phase;                    // S_UP 안에서 0:Abar*hprev, 1:Bbar*x
  wire signed [15:0] h_now = sat16(p1 + (mp >>> 18));   // phase1 에서 확정되는 h[idx]

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin st<=S_IDLE; done<=0; y<=0; idx<=0; acc<=0; phase<=0; h<=0; end
    else case (st)
      // 부호확장은 반드시 18b 로. 17b 만 하면 음수 피연산자가 양수로 뒤집힌다(실측 버그).
      S_IDLE: begin done<=0;
        if (start) begin idx<=0; phase<=0; acc<=0; st<=S_UP;
          ma <= {2'b00, Abar[15:0]};                 // Abar 무부호 양수
          mb <= {{2{hprev[15]}}, hprev[15:0]}; end
      end
      S_UP: begin
        if (phase==0) begin
          p1 <= mp >>> 16;                           // Abar*hprev -> Q4.12
          ma <= {{2{bb[15]}}, bb};  mb <= {{2{x[15]}}, x};   // 다음 곱: Bbar*x
          phase <= 1;
        end else begin
          h[16*idx +:16] <= h_now;                   // p1 + Bbar*x>>18
          phase <= 0;
          if (idx==N-1) begin
            idx<=0; st<=S_OUT;                        // 첫 출력곱: C[0]*h[0]
            ma <= {{2{C[15]}}, C[15:0]}; mb <= {{2{h[15]}}, h[15:0]};
          end else begin
            idx<=idx+1;
            ma <= {2'b00, Abar[16*(idx+1) +:16]};
            mb <= {{2{hprev[16*(idx+1)+15]}}, hprev[16*(idx+1) +:16]};
          end
        end
      end
      S_OUT: begin
        acc <= acc + mp;                             // 전정밀 누산(골든과 동일; 시프트는 끝에서 한 번)
        if (idx==N-1) begin st<=S_DONE; end
        else begin idx<=idx+1;
          ma <= {{2{C[16*(idx+1)+15]}}, C[16*(idx+1) +:16]};
          mb <= {{2{h[16*(idx+1)+15]}}, h[16*(idx+1) +:16]};
        end
      end
      S_DONE: begin y <= sat16(acc >>> 15); done<=1; st<=S_IDLE; end
    endcase
  end
endmodule
