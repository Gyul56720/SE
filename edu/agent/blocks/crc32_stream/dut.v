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

   function [31:0] crc_step;
      input [31:0] c;
      input        b;
      begin
         if (c[0] ^ b) crc_step = (c >> 1) ^ 32'hEDB88320;
         else          crc_step = (c >> 1);
      end
   endfunction

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

// 테스트벤치: 자극 파일을 읽어 **무작위 back-pressure 를 걸면서** 넣고,
// 나온 패킷 CRC 만 out.txt 에 적는다.  비교는 트랜잭션 수준이므로 타이밍이
// 달라도 값이 같으면 통과한다 -- 실제 DV 가 하는 방식이다.
//
// **구동은 negedge, 표본은 posedge.**  처음에는 둘 다 posedge 에서 했는데
// `while (!s_ready)` 가 클럭 경계 뒤에 ready 를 읽어 **바이트 하나를 흘렸다**
// (실측: 출력 59 개, 기대 58 개).  핸드셰이크 테스트벤치의 고전적 경주다.
module tb;
   reg         clk = 0, rst_n = 0;
   reg   [7:0] s_data;
   reg         s_valid, s_last;
   wire        s_ready;
   wire [31:0] m_crc;
   wire        m_valid;
   reg         m_ready;

   integer fi, fo, fc, r;
   integer seed;
   integer cyc = 0;
   reg [7:0]  d;
   reg        last;
   reg [31:0] lfsr;

   crc32_stream dut(.clk(clk), .rst_n(rst_n), .s_data(s_data), .s_valid(s_valid),
                    .s_last(s_last), .s_ready(s_ready), .m_crc(m_crc),
                    .m_valid(m_valid), .m_ready(m_ready));

   always #5 clk = ~clk;
   always @(posedge clk) if (rst_n) cyc = cyc + 1;

   task roll;
      begin
         lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
      end
   endtask

   // 한 바이트를 핸드셰이크로 넣는다.
   task send;
      input [7:0] dd;
      input       ll;
      begin
         // 무작위로 공백을 넣는다 (입력이 늘 준비돼 있지 않게)
         while (lfsr[2:0] == 3'b000) begin
            @(negedge clk); s_valid = 0; m_ready = lfsr[8]; roll;
            @(posedge clk);
         end
         @(negedge clk);
         s_data = dd; s_last = ll; s_valid = 1; m_ready = lfsr[8]; roll;
         @(posedge clk);
         while (!s_ready) begin
            @(negedge clk); m_ready = lfsr[8]; roll;
            @(posedge clk);
         end
         @(negedge clk);
         s_valid = 0;
      end
   endtask

   initial begin
      fi = $fopen("stim.txt", "r");
      fo = $fopen("out.txt", "w");
      if (fi == 0) begin $display("stim.txt 없음"); $finish; end
      r = $fscanf(fi, "%d\n", seed);
      lfsr = (seed == 0) ? 32'h1 : seed;
      s_valid = 0; s_last = 0; s_data = 0; m_ready = 1;
      repeat (4) @(posedge clk);
      @(negedge clk); rst_n = 1;
      @(posedge clk);

      while (!$feof(fi)) begin
         r = $fscanf(fi, "%h %b\n", d, last);
         if (r == 2)
           send(d, last);
      end
      @(negedge clk); s_valid = 0; m_ready = 1;
      repeat (40) @(posedge clk);
      fc = $fopen("cycles.txt", "w");
      $fwrite(fc, "%0d\n", cyc);
      $fclose(fc);
      $fclose(fi); $fclose(fo);
      $finish;
   end

   // 출력 트랜잭션만 기록한다 (경계 직전 값을 본다)
   always @(posedge clk)
     if (rst_n && m_valid && m_ready)
       $fwrite(fo, "%h\n", m_crc);
endmodule
