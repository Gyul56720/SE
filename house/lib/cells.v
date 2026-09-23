// -*- coding: utf-8 -*-
//
// **게이트 레벨 시뮬용 셀 모델.**  `lab/lib/se10.lib` + `house/lib/mk.py` 의 LATX1.
//
// 합성이 낸 넷리스트는 이 셀들을 부른다. 그것을 돌려 보려면 셀의 **동작**이
// 있어야 하는데 이 저장소에는 Liberty(타이밍/면적)만 있고 Verilog 모델이
// 없었다. 그래서 관문 4e(게이트 레벨 시뮬)가 아예 설 수 없었다.
//
// ## 지어내지 않았다 -- Liberty 의 `function` 을 그대로 옮겼다
//
// 셀마다 아래 주석에 원문을 붙여 둔다. 모델과 Liberty 가 갈라지면 합성이
// 가정한 것과 시뮬이 보는 것이 달라지고, 그러면 **게이트 레벨 시뮬이
// 거짓말을 한다** -- RTL 과 달라도 셀 모델 탓인지 합성 탓인지 못 가린다.
// `tests/test_게이트시뮬.py` 가 이 파일과 se10.lib 의 function 을 맞춰 본다.
//
// **타이밍이 없다.** 지연 0 의 기능 모델이다. SDF 역주석은 이 길로는 못 한다 --
// 쓰는 시뮬레이터에 타이밍이 없기 때문이다. 그 한계는 관문 글에 그대로 적는다.
//
// (`// verilator` 로 시작하는 주석 줄을 쓰지 마라 -- 그것은 lint 지시어로 읽혀
//  "Unknown verilator comment" 로 죽는다. 실측 2026-09-23.)

`timescale 1ns/1ps

module INVX1  (input A, output Y);            assign Y = !A;          endmodule  // "!A"
module INVX4  (input A, output Y);            assign Y = !A;          endmodule  // "!A"
module BUFX2  (input A, output Y);            assign Y = A;           endmodule  // "A"
module NAND2X1(input A, input B, output Y);   assign Y = !(A & B);    endmodule  // "!(A&B)"
module NOR2X1 (input A, input B, output Y);   assign Y = !(A | B);    endmodule  // "!(A|B)"
module AND2X1 (input A, input B, output Y);   assign Y =  (A & B);    endmodule  // "(A&B)"
module OR2X1  (input A, input B, output Y);   assign Y =  (A | B);    endmodule  // "(A|B)"
module XOR2X1 (input A, input B, output Y);   assign Y =  (A ^ B);    endmodule  // "(A^B)"
module XNOR2X1(input A, input B, output Y);   assign Y = !(A ^ B);    endmodule  // "!(A^B)"

// "(A&!S)|(B&S)" -- S 가 0 이면 A, 1 이면 B 다. **이 방향을 뒤집으면 회로가
// 통째로 틀리는데 게이트 시뮬은 조용히 돈다.** 그래서 원문을 옆에 붙인다.
module MUX2X1 (input A, input B, input S, output Y); assign Y = (A & !S) | (B & S); endmodule

module AOI21X1(input A1, input A2, input B, output Y); assign Y = !((A1 & A2) | B); endmodule  // "!((A1&A2)|B)"
module OAI21X1(input A1, input A2, input B, output Y); assign Y = !((A1 | A2) & B); endmodule  // "!((A1|A2)&B)"

// ff(IQ,IQN) clocked_on:"CK" next_state:"D"
module DFFX1 (input CK, input D, output reg Q, output QN);
  always @(posedge CK) Q <= D;
  assign QN = !Q;
endmodule

// ff(IQ,IQN) clocked_on:"CK" next_state:"D" clear:"!RN"   -- 비동기 클리어
module DFFRX1 (input CK, input RN, input D, output reg Q, output QN);
  always @(posedge CK or negedge RN) if (!RN) Q <= 1'b0; else Q <= D;
  assign QN = !Q;
endmodule

// latch(IQ,IQN) enable:"G" data_in:"D"  -- G 가 높을 때 투명
module LATX1 (input G, input D, output reg Q, output QN);
  always @(*) if (G) Q = D;
  assign QN = !Q;
endmodule
