# -*- coding: utf-8 -*-
"""생성된 레지스터 파일 + APB 테스트벤치를 만든다.

DUT 는 `edu/house/regmap.py` 가 **생성한** RTL 이다.  골든모델은 같은 맵의
접근 규칙을 파이썬으로 따로 쓴 것이다.  즉 이 블록은 **생성기를 검사한다**.
"""
import os, sys
여기 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(여기, "..", "..", "..", "house"))
sys.path.insert(0, "/home/user/SE/edu/house")
import regmap

TB = r'''
// APB 테스트벤치.  자극 파일의 각 줄은 한 번의 APB 접근이다:
//     <쓰기?1/0> <주소hex> <쓸값hex> <하드웨어이벤트hex>
// 매 접근의 읽기 데이터를 out.txt 에 적는다 (쓰기도 뒤이어 읽어서 낸다).
//
// **하드웨어 쪽 입력을 구동한다.**  처음에는 hw_set_* 를 전부 0 으로 묶었는데,
// 변이 점수가 58 % 로 떨어지며 이유를 짚었다: `|` 를 `^` 로 바꾼 변이가
// 안 잡혔다 -- 0 과 OR 하나 XOR 하나 같기 때문이다.  **W1C 와 RC 경로가
// 한 번도 안 돌고 있었다.**  자극이 안 건드리는 자리는 검사되지 않는다.
module tb;
   reg         clk = 0, rst_n = 0;
   reg  [31:0] paddr, pwdata;
   reg         psel, penable, pwrite;
   wire [31:0] prdata;
   wire        pready;

   integer fi, fo, r;
   reg        wr;
   reg [31:0] adr, dat, hwev;
   reg  [2:0] hw_irq;      // IRQ_STATUS 의 W1C 비트 셋을 세우는 하드웨어 사건
   reg [31:0] hw_errc;     // ERR_COUNT 의 RC 필드에 더해지는 값

   // 하드웨어 쪽 입력은 0 으로 묶는다 -- 이 검사는 버스 의미를 본다
   crcip_regs dut(.clk(clk), .rst_n(rst_n), .paddr(paddr), .psel(psel),
                  .penable(penable), .pwrite(pwrite), .pwdata(pwdata),
                  .prdata(prdata), .pready(pready),
                  HWPORTS);

   always #5 clk = ~clk;

   // 하드웨어 사건을 **한 사이클** 넣는다.  실제 블록에서 오류 펄스가 그렇다.
   task hw_pulse;
      input [31:0] ev;
      begin
         @(negedge clk);
         hw_irq  = ev[2:0];
         hw_errc = {29'd0, ev[5:3]};
         @(posedge clk);
         @(negedge clk);
         hw_irq  = 3'd0;
         hw_errc = 32'd0;
      end
   endtask

   task apb_write;
      input [31:0] a; input [31:0] d;
      begin
         @(negedge clk); paddr = a; pwdata = d; pwrite = 1; psel = 1; penable = 0;
         @(negedge clk); penable = 1;
         @(posedge clk);
         @(negedge clk); psel = 0; penable = 0; pwrite = 0;
      end
   endtask

   task apb_read;
      input [31:0] a; output [31:0] d;
      begin
         @(negedge clk); paddr = a; pwrite = 0; psel = 1; penable = 0;
         @(negedge clk); penable = 1;
         @(posedge clk); d = prdata;
         @(negedge clk); psel = 0; penable = 0;
      end
   endtask

   reg [31:0] got;
   initial begin
      fi = $fopen("stim.txt", "r");
      fo = $fopen("out.txt", "w");
      if (fi == 0) begin $display("stim.txt 없음"); $finish; end
      psel = 0; penable = 0; pwrite = 0; paddr = 0; pwdata = 0;
      hw_irq = 0; hw_errc = 0;
      repeat (4) @(posedge clk);
      @(negedge clk); rst_n = 1;
      repeat (2) @(posedge clk);

      while (!$feof(fi)) begin
         r = $fscanf(fi, "%b %h %h %h\n", wr, adr, dat, hwev);
         if (r == 4) begin
            if (hwev != 32'd0) hw_pulse(hwev);
            if (wr) apb_write(adr, dat);
            apb_read(adr, got);
            $fwrite(fo, "%h\n", got);
         end
      end
      $fclose(fi); $fclose(fo);
      $finish;
   end
endmodule
'''


def 만들기(낼자리):
    m = regmap.예제
    v = regmap.rtl(m)
    # 하드웨어 쪽 포트를 0 으로 묶는다
    hw = []
    for r in m.레지스터들:
        for f in r.필드들:
            n = f"{r.이름.lower()}_{f.이름.lower()}"
            if f.접근 == "RO":
                if f.하드웨어:
                    hw.append(f".hw_{n}({f.폭}'d0)")
            elif f.접근 in ("W1C", "W1S", "RC"):
                if not f.하드웨어:
                    # 하드웨어가 안 세우는 필드는 hw_set 포트가 없다
                    hw.append(f".{n}()")
                    continue
                if r.이름 == "IRQ_STATUS":
                    비트 = {"ERR_CRC": 0, "ERR_LEN": 1, "OVERFLOW": 2}[f.이름]
                    hw.append(f".hw_set_{n}(hw_irq[{비트}])")
                elif r.이름 == "ERR_COUNT":
                    hw.append(f".hw_set_{n}(hw_errc)")
                else:
                    hw.append(f".hw_set_{n}({f.폭}'d0)")
                hw.append(f".{n}()")
            else:
                hw.append(f".{n}()")
    tb = TB.replace("HWPORTS", ",\n                  ".join(hw))
    # **한 파일에 한 모듈** -- lint(DECLFILENAME) 과 합성이 DUT 만 보게 한다.
    dutp = os.path.join(낼자리, "crcip_regs.v")
    tbp = os.path.join(낼자리, "tb.v")
    with open(dutp, "w", encoding="utf-8") as f:
        f.write(v.rstrip() + "\n")          # 파일 끝 개행 (verilator EOFNEWLINE)
    with open(tbp, "w", encoding="utf-8") as f:
        f.write(tb)
    return dutp, tbp
