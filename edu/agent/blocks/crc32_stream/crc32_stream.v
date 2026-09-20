// 스트리밍 CRC-32 (IEEE 802.3 FCS) -- AXI-Stream 꼴 핸드셰이크.
//
// 판매 가능한 블록이 갖춰야 하는 것을 일부러 다 넣었다:
//   * valid/ready 핸드셰이크, **ready 가 valid 를 조합으로 안 본다**
//   * tlast 로 패킷 경계, 패킷마다 CRC 를 낸다
//   * 동기 리셋 해제, 리셋 중 출력 무효
//   * 바이트당 한 사이클 (8비트 병렬 갱신)
//
// 골든모델은 파이썬 zlib 이다 -- **독립 참조**(Y11 장).
module crc32_stream (input  wire        clk,
                     input  wire        rst_n,
                     input  wire  [7:0] s_data,
                     input  wire        s_valid,
                     input  wire        s_last,
                     output wire        s_ready,
                     output reg  [31:0] m_crc,
                     output reg         m_valid,
                     input  wire        m_ready);

   /* verilator lint_off BLKSEQ */
   // 면제 사유: 함수의 지역 변수는 blocking 대입이라야 한다.
   // 함수는 조합 계산이고, 그 안의 t 는 레지스터가 아니다.
   // 여기서 '<=' 를 쓰면 루프가 의도대로 안 돈다.
   function [31:0] crc_step;
      input [31:0] c;
      input        b;
      begin
         if (c[0] ^ b) crc_step = (c >> 1) ^ 32'hEDB88320;
         else          crc_step = (c >> 1);
      end
   endfunction
   /* verilator lint_on BLKSEQ */

   /* verilator lint_off BLKSEQ */
   // 면제 사유: 함수의 지역 변수는 blocking 대입이라야 한다.
   // 함수는 조합 계산이고, 그 안의 t 는 레지스터가 아니다.
   // 여기서 '<=' 를 쓰면 루프가 의도대로 안 돈다.
   function [31:0] crc_byte;
      input [31:0] c;
      input  [7:0] d;
      reg   [31:0] t;
      integer i;
      begin
         t = c;
         for (i = 0; i < 8; i = i + 1)
           t = crc_step(t, d[i]);
         crc_byte = t;
      end
   endfunction
   /* verilator lint_on BLKSEQ */

   reg [31:0] acc;

   // 출력이 아직 안 빠졌으면 입력을 안 받는다.  ready 는 m_valid 와 m_ready 만
   // 보고, s_valid 는 **안 본다** -- 조합 고리를 만들지 않기 위해서다(X37 장).
   assign s_ready = ~(m_valid & ~m_ready);

   always @(posedge clk) begin
      if (!rst_n) begin
         acc     <= 32'hFFFFFFFF;
         m_crc   <= 32'd0;
         m_valid <= 1'b0;
      end else begin
         if (m_valid & m_ready)
           m_valid <= 1'b0;
         if (s_valid & s_ready) begin
            if (s_last) begin
               m_crc   <= crc_byte(acc, s_data) ^ 32'hFFFFFFFF;
               m_valid <= 1'b1;
               acc     <= 32'hFFFFFFFF;
            end else begin
               acc <= crc_byte(acc, s_data);
            end
         end
      end
   end
endmodule
