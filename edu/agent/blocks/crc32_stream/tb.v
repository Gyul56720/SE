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
