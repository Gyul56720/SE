# -*- coding: utf-8 -*-
"""Volume III, Part Z18 -- SystemVerilog for the C++ programmer."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, derive
import sch


def _c(s):
    return "<pre><code>" + E(s) + "</code></pre>"


def ch_sv():
    s = ['<h1 id="z18">Z18. SystemVerilog for the C++ Programmer</h1>']

    s.append("""<p>SystemVerilog looks enough like C to be dangerous. The braces are
    <code>begin</code>/<code>end</code>, the types are unfamiliar, and about a third of
    the constructs mean something that has no software equivalent at all. This part is a
    complete tour, written for somebody who knows C++ and has never seen a hardware
    description language. It covers the synthesisable language in full, then the
    verification subset, and says at every point which of the two you are in.</p>

    <p>The single most important idea, before any syntax: <b>you are not writing
    instructions that execute. You are describing hardware that exists.</b> Every
    <code>always</code> block in a design is a piece of circuitry that is powered on all
    the time, simultaneously with every other block. Sequence exists only inside a single
    block, and even there it is often a fiction the synthesiser unrolls into wires.</p>""")

    s.append("<h2>Z18.1 The thing you asked about: <code>::</code></h2>")
    s.append("""<p><code>::</code> is the scope resolution operator, and it means very
    nearly what it means in C++ &mdash; &ldquo;this name, from inside that
    namespace.&rdquo; SystemVerilog has three scopes that use it.</p>""")

    s.append(tab("The three things that appear to the left of <code>::</code>",
        ["Form", "What the left side is", "C++ analogue"],
        [["<code>my_pkg::WIDTH</code>", "A <b>package</b> &mdash; a named bundle of "
          "types, constants and functions shared across files.",
          "<code>namespace my_pkg { }</code>, and this is the same syntax"],
         ["<code>state_e::IDLE</code>", "An <b>enum type</b>, naming one of its members "
          "explicitly.",
          "<code>enum class state_e { IDLE }</code> &mdash; also the same syntax"],
         ["<code>std::mailbox</code>", "The <b>built-in</b> package, which holds "
          "<code>mailbox</code>, <code>semaphore</code>, <code>process</code>.",
          "<code>std::</code>, and even the same name"],
         ["<code>$unit::foo</code>", "The <b>compilation unit</b> scope &mdash; "
          "everything declared outside any package or module.",
          "The global namespace, <code>::foo</code>"]]))

    s.append(_c("""// ── 패키지: C++ 의 namespace 와 같은 자리다 ───────────────────────
package fir_pkg;
    // parameter = 컴파일 시간 상수.  C++ 의 `constexpr` 에 해당한다.
    parameter int NTAP  = 4;
    parameter int SAMP_W = 8;

    // typedef: C 와 똑같다.  `logic signed [7:0]` 에 이름을 붙인다.
    typedef logic signed [SAMP_W-1:0] samp_t;

    // enum: C++11 의 `enum class` 처럼 타입이 붙는다.
    // 괄호 안 `logic [1:0]` 은 **이 enum 이 하드웨어에서 2비트로 인코딩된다**는
    // 뜻이다.  C++ enum 의 underlying type 과 같은 개념인데, 여기서는
    // 실제 플립플롭 개수를 정한다.
    typedef enum logic [1:0] { IDLE, RUN, DONE } state_e;

    // 함수도 담을 수 있다.  `automatic` 은 아래 Z18.9 에서 설명한다.
    function automatic int unsigned clog2_up(int unsigned v);
        clog2_up = 0;
        while (v > 1) begin v = v >> 1; clog2_up++; end
    endfunction
endpackage

// ── 쓰는 쪽 ────────────────────────────────────────────────────────
module fir_core;
    // (1) 매번 `fir_pkg::` 를 붙여 쓴다 -- C++ 의 `std::vector` 와 같다
    fir_pkg::samp_t  a;
    localparam int N = fir_pkg::NTAP;

    // (2) enum 멤버를 타입 이름으로 한정한다
    fir_pkg::state_e st = fir_pkg::state_e::IDLE;

    // (3) import 로 통째로 끌어온다 -- C++ 의 `using namespace` 다
    import fir_pkg::*;
    samp_t b;              // 이제 접두사 없이 쓴다
endmodule"""))

    s.append("""<p>The difference from C++ that bites: <b>an <code>import</code> inside a
    module is visible only in that module</b>, and a package must be compiled
    <em>before</em> anything that imports it. There is no header-guard mechanism and no
    forward declaration; file order on the compiler command line is part of the build.
    Most projects keep one package per file and list packages first in the file list.</p>""")

    s.append("""<p>One more <code>::</code>-adjacent thing that surprises C++ programmers:
    the dot. <code>dut.internal_reg</code> reaches <em>inside</em> another module instance
    from a testbench, past every encapsulation boundary. This is a <b>hierarchical
    reference</b>, it is legal, it is not synthesisable, and it is how most white-box
    testbenches are written. There is no <code>private</code> in SystemVerilog modules.</p>""")

    s.append("<h2>Z18.2 What a module is, and why it is not a class</h2>")
    s.append(_c("""// 모듈 = 하드웨어 한 덩이.  C++ 의 class 가 아니라 **회로 그 자체**다.
//
// class 와 다른 점:
//   * 생성/소멸이 없다.  전원이 켜져 있는 동안 늘 존재한다
//   * 메서드 호출이 없다.  포트에 신호가 들어오고 나갈 뿐이다
//   * 인스턴스가 **컴파일 시간에 고정**된다.  런타임에 new 할 수 없다
//     (verification 쪽 `class` 는 할 수 있다 -- Z18.11)
module fir4 #(
    // 파라미터 = 인스턴스마다 다르게 줄 수 있는 컴파일 시간 값.
    // C++ 의 **템플릿 인자**에 해당한다: `template<int SAMP_W>`
    parameter int SAMP_W = 8,
    parameter int NTAP   = 4
) (
    // 포트 목록.  방향이 반드시 붙는다.
    //   input   읽기만 한다
    //   output  이 모듈이 구동한다
    //   inout   양방향 (삼상태).  칩 안에서는 거의 안 쓴다
    input  logic                     clk,
    input  logic                     rst,
    input  logic signed [SAMP_W-1:0] x,
    output logic signed [SAMP_W-1:0] y
);
    // ... 내용 ...
endmodule

// 인스턴스화.  `.포트이름(연결할신호)` 를 **이름으로** 잇는다.
// 순서로 잇는 옛 문법(`fir4 u(clk, rst, x, y)`)도 되지만 **쓰지 마라** --
// 포트를 하나 추가하면 그 아래가 전부 조용히 밀린다.
fir4 #(.SAMP_W(8), .NTAP(4)) u_fir (
    .clk (clk_100m),
    .rst (rst_sync),
    .x   (adc_sample),
    .y   (eq_out)
);"""))

    s.append("<h2>Z18.3 Types: the four-state trap</h2>")
    s.append("""<p>C++ has <code>bool</code>. SystemVerilog has a bit that can hold four
    values, and the two extra ones are the most useful debugging tool in the
    language.</p>""")

    s.append(tab("The four values a <code>logic</code> bit can take",
        ["Value", "Means", "Where it comes from", "Why you want it"],
        [["<code>0</code>", "low", "driven low", "&mdash;"],
         ["<code>1</code>", "high", "driven high", "&mdash;"],
         ["<code>x</code>", "unknown", "uninitialised register, two drivers fighting, "
          "reading before reset",
          "<b>It propagates.</b> An <code>x</code> in a sum makes the sum "
          "<code>x</code>, so a missing reset shows up as garbage rather than as a "
          "plausible zero."],
         ["<code>z</code>", "high impedance (not driven)", "a tri-state driver that is "
          "off, an unconnected input",
          "Models buses where several drivers share a wire."]]))

    s.append(tab("The types, and which to use",
        ["Type", "States", "Use it for", "C++ analogue"],
        [["<code>logic</code>", "4", "<b>Almost everything.</b> One bit, or "
          "<code>logic [7:0]</code> for a vector.",
          "Closest to <code>bool</code>/<code>uint8_t</code>, but 4-state"],
         ["<code>wire</code>", "4", "Legacy. A net that must be continuously driven. "
          "<code>logic</code> covers it in SystemVerilog.",
          "&mdash;"],
         ["<code>reg</code>", "4", "Legacy Verilog name for a procedural variable. "
          "<b>It does not mean &lsquo;register&rsquo;</b> &mdash; this misnaming has "
          "confused people for thirty years. Use <code>logic</code>.",
          "&mdash;"],
         ["<code>bit</code>", "2", "Testbench code where you want C semantics and speed.",
          "<code>bool</code>"],
         ["<code>int</code>", "2", "Loop counters, testbench arithmetic. 32-bit signed.",
          "<code>int32_t</code>"],
         ["<code>byte</code>, <code>shortint</code>, <code>longint</code>", "2",
          "8/16/64-bit signed testbench integers.",
          "<code>int8_t</code>, <code>int16_t</code>, <code>int64_t</code>"],
         ["<code>integer</code>", "4", "Legacy 32-bit 4-state.", "&mdash;"],
         ["<code>real</code>", "&mdash;", "Floating point, testbench only.",
          "<code>double</code>"],
         ["<code>string</code>", "&mdash;", "Testbench messages.", "<code>std::string</code>"]]))

    s.append(_c("""// ── 벡터와 부호 ───────────────────────────────────────────────────
logic        [7:0] u;   // 8비트 **부호 없음** (기본값)
logic signed [7:0] a;   // 8비트 부호 있음 -- `signed` 를 빼면 조용히 틀린다

// [7:0] 과 [0:7] 은 다르다.  [7:0] 이 관례다 (왼쪽이 MSB).
// C++ 배열과 달리 **비트 번호를 내가 정한다** -- [15:8] 도 legal 하다.

// 부호를 빠뜨리면 어떻게 되나 -- 실제로 물리는 자리다
logic        [7:0] p = 8'hFF;      // 255 로 읽힌다
logic signed [7:0] q = 8'hFF;      // -1 로 읽힌다
// p > 0  은 참,  q > 0  은 거짓.  **같은 비트, 다른 답.**

// ── 리터럴 ────────────────────────────────────────────────────────
//   <폭>'<진법><값>
8'd10      // 8비트 십진 10
8'hFF      // 8비트 16진
8'b1010_1010   // 밑줄은 자리 구분용.  무시된다 (C++14 의 ' 와 같다)
8'sd10     // 8비트 **부호있는** 십진
'0         // 폭을 문맥에서 가져오는 전부-0.  `'1` 은 전부-1 (0001 아님!)
8'bx       // 전부 unknown -- 리셋 전 상태를 흉내낼 때

// ── 구조체와 배열 ─────────────────────────────────────────────────
typedef struct packed {        // packed = **비트가 연속**이다.  합성된다
    logic        valid;        // [16]
    logic [7:0]  data;         // [15:8]
    logic [7:0]  tag;          // [7:0]
} beat_t;                      // 통째로 17비트 벡터처럼 쓸 수 있다

typedef struct {               // unpacked = 그냥 묶음.  **합성 안 된다**
    int   count;
    string name;
} stat_t;                      // 테스트벤치용

logic [7:0] mem [0:255];       // unpacked 배열 = 메모리.  `[개수]` 가 **뒤**에 온다
logic [3:0][7:0] lanes;        // packed 배열 = 32비트를 4x8 로 본 것
beat_t queue [$];              // 동적 큐 (테스트벤치).  C++ 의 `std::deque`"""))

    s.append(ex("Why <code>signed</code> is the most expensive missing keyword in the language",
        given="The filter adds two 8-bit samples: <code>a0 = x0 + x3</code>, where both "
              "may be negative. Written as <code>logic [7:0] x0</code> without "
              "<code>signed</code>.",
        method="Work out what the comparison and the shift do under unsigned "
               "interpretation.",
        numbers="x0 = &minus;1 is stored as <code>8'hFF</code>. Unsigned, that reads as "
                "<b>255</b>. Adding &minus;1 and &minus;1 should give &minus;2; unsigned "
                "it gives 510, and the right shift that follows brings in zeros from the "
                "top instead of sign bits, so the result is a large positive number "
                "instead of a small negative one.",
        trap="Nothing warns you. The bit patterns are identical &mdash; only the "
             "<i>interpretation</i> differs, and the interpretation lives in a keyword "
             "you forgot to type. The design simulates, synthesises, and is wrong for "
             "exactly the half of the input space where the sample is negative. Random "
             "testing finds it; directed testing with positive-only stimulus does not. "
             "This is why <code>edu/model/fir4_hand.v</code> writes "
             "<code>$signed({x0[7], x0})</code> explicitly rather than relying on "
             "declarations being right.",
        extra="The rule in SystemVerilog: an expression is unsigned if <b>any</b> operand "
              "is unsigned. One unsigned literal in a long signed expression silently "
              "converts the whole thing. When in doubt, wrap in <code>$signed()</code>."))

    s.append("<h2>Z18.4 The two assignments, and when to use which</h2>")
    s.append("""<p>This is the rule that separates working RTL from RTL that simulates and
    then fails in hardware. C++ has one assignment; SystemVerilog has two and they mean
    different things about <em>time</em>.</p>""")

    s.append(tab("Blocking versus non-blocking",
        ["", "<code>=</code> blocking", "<code>&lt;=</code> non-blocking"],
        [["Reads like", "C's <code>=</code>: compute, store, move on.",
          "&ldquo;Sample all right-hand sides now; update all left-hand sides at the end "
          "of the time step.&rdquo;"],
         ["Models", "A wire &mdash; combinational logic.",
          "A flip-flop &mdash; every register in the block updates together on the edge."],
         ["Use in", "<code>always_comb</code>", "<code>always_ff</code>"],
         ["If you get it wrong", "Non-blocking in combinational logic: simulates slowly "
          "and can need extra delta cycles, may mismatch synthesis.",
          "Blocking in sequential logic: <b>creates a race.</b> Simulation result depends "
          "on the order the simulator happens to evaluate blocks in; hardware does "
          "something else."]]))

    s.append(_c("""// ── 왜 순차 논리에 <= 를 쓰는가 ───────────────────────────────────
// 하드웨어에서 이 두 플립플롭은 **동시에** 잡힌다.  a 가 b 로 가고 b 가
// c 로 가는 시프트 레지스터를 생각하면 된다.

always_ff @(posedge clk) begin
    b <= a;      // 이 edge 의 **옛** a 값을 잡는다
    c <= b;      // 이 edge 의 **옛** b 값을 잡는다
end
// 결과: 시프트 레지스터.  a -> b -> c, 한 edge 에 한 칸.  **맞다.**

always_ff @(posedge clk) begin
    b = a;       // b 가 **즉시** a 가 된다
    c = b;       // 그래서 c 도 **같은 edge 에** a 가 되어 버린다
end
// 결과: b 와 c 가 둘 다 a.  시프트 레지스터가 아니라 그냥 팬아웃이다.
// 더 나쁜 것: 다른 always 블록이 b 를 읽고 있으면, 그 블록이 이 블록보다
// 먼저 도느냐 나중에 도느냐에 따라 **옛 b 를 보거나 새 b 를 본다.**
// 시뮬레이터가 순서를 정하고, 그 순서는 명세에 없다 -- 그것이 경주다.

// ── 조합 논리에는 = 를 쓴다 ───────────────────────────────────────
always_comb begin
    sum  = a + b;        // 중간값
    outv = sum + c;      // **방금 계산한** sum 을 쓴다 -- 그래서 blocking
end
// <= 로 쓰면 outv 가 이번이 아니라 **다음** delta 의 sum 을 본다."""))

    s.append("""<p>The rule, stated once and never broken: <b>non-blocking in
    <code>always_ff</code>, blocking in <code>always_comb</code>, never both in one
    block, and never assign the same signal from two blocks.</b> Every lint tool checks
    it. The generated RTL in Part&nbsp;Z15 obeys it because the HLS tool cannot make this
    mistake &mdash; which is one genuine, if unglamorous, advantage of generating RTL.</p>""")

    s.append("<h2>Z18.5 The <code>always</code> blocks</h2>")
    s.append(_c("""// ── SystemVerilog 의 세 가지 (Verilog 의 `always` 를 갈라놓은 것) ──

// 1. 조합 논리.  감도 목록을 **도구가 채운다** -- 빠뜨릴 수가 없다
always_comb begin
    y = a & b;
end
// 옛 Verilog: always @(a or b)  <- b 를 빠뜨리면 래치가 생긴다.
// `always_comb` 는 그 사고를 문법으로 막는다.  **항상 이것을 써라.**

// 2. 순차 논리.  edge 를 적는다
always_ff @(posedge clk) begin           // 동기 리셋
    if (rst) q <= '0;
    else     q <= d;
end

always_ff @(posedge clk or negedge rst_n) begin   // 비동기 리셋
    if (!rst_n) q <= '0;                 // 리셋이 감도 목록에 **있어야** 한다
    else        q <= d;
end

// 3. 래치.  **의도적으로** 래치를 만들 때만.  ASIC 에서는 거의 금지다
always_latch begin
    if (en) q = d;
end

// ── 래치가 사고로 생기는 자리 ─────────────────────────────────────
always_comb begin
    if (sel) y = a;        // sel 이 0 일 때 y 를 안 정했다
end                        // -> y 가 **이전 값을 기억해야** 한다 -> 래치!
// 고치는 법 두 가지:
always_comb begin
    y = '0;                // (a) 먼저 기본값을 준다
    if (sel) y = a;
end
always_comb begin
    if (sel) y = a;        // (b) 모든 갈래를 채운다
    else     y = '0;
end
// `always_comb` 를 쓰면 도구가 "latch inferred" 라고 **경고**해 준다.
// 옛 `always @(*)` 는 조용히 만든다."""))

    s.append("<h2>Z18.6 Operators: what is the same and what is not</h2>")
    s.append(tab("Operators a C++ programmer will misread",
        ["Operator", "Meaning", "The C++ trap"],
        [["<code>&amp;</code> <code>|</code> <code>^</code> <code>~</code>",
          "Bitwise, on vectors.", "Same as C++."],
         ["<code>&amp;&amp;</code> <code>||</code> <code>!</code>",
          "Logical, on truth of the whole value.", "Same as C++."],
         ["<code>&amp;a</code> <code>|a</code> <code>^a</code>",
          "<b>Reduction</b> &mdash; unary. <code>&amp;a</code> is AND of every bit of "
          "<code>a</code>; <code>^a</code> is parity.",
          "<b>No C++ equivalent.</b> <code>^data</code> computing parity in one character "
          "is the single most useful operator in the language."],
         ["<code>==</code> <code>!=</code>", "Equality; result is <code>x</code> if "
          "either operand has an <code>x</code>.",
          "Can return unknown, not just true/false."],
         ["<code>===</code> <code>!==</code>", "Case equality &mdash; compares "
          "<code>x</code> and <code>z</code> literally, always gives 0 or 1.",
          "Use in testbenches to ask &lsquo;is this actually X?&rsquo;. "
          "<b>Not synthesisable.</b>"],
         ["<code>&gt;&gt;</code> <code>&lt;&lt;</code>", "Logical shift &mdash; brings in zeros.",
          "Same as C++ unsigned shift."],
         ["<code>&gt;&gt;&gt;</code>", "<b>Arithmetic</b> right shift &mdash; replicates "
          "the sign bit. Only if the operand is <code>signed</code>.",
          "C++ <code>&gt;&gt;</code> on a signed int does this; SystemVerilog needs the "
          "third angle bracket <b>and</b> a signed operand."],
         ["<code>{a, b}</code>", "Concatenation &mdash; glue bits together.",
          "<b>No C++ equivalent.</b> <code>{x[7], x}</code> is 9-bit sign extension."],
         ["<code>{4{a}}</code>", "Replication &mdash; four copies of <code>a</code>.",
          "<code>{8{x[7]}}</code> is the idiomatic sign-extend."],
         ["<code>a inside {1,2,[5:9]}</code>", "Set membership, ranges allowed.",
          "Like a <code>switch</code> without fallthrough; also used in constraints."],
         ["<code>?:</code>", "Conditional. Synthesises to a multiplexer.",
          "Same as C++, but remember it is <em>hardware</em> &mdash; both sides are "
          "always computed."]]))

    s.append(_c("""// ── 이 저장소의 실제 코드로 본 연산자 ─────────────────────────────

// 부호 확장: 8비트를 9비트로.  {x0[7], x0} 이 최상위 비트를 한 번 더 붙인다
wire signed [8:0] a0 = $signed({x0[7], x0}) + $signed({x3[7], x3});

// 왜 $signed() 로 또 감싸나?
//   {} 연결의 결과는 **언제나 unsigned** 다 -- 안에 뭐가 들었든.
//   이것이 SystemVerilog 에서 가장 흔한 조용한 버그 중 하나다.

// 비트 뽑기와 자르기
acc[16:7]          // 고정 범위
acc[i +: 8]        // i 부터 위로 8비트.  i 가 변수여도 된다
acc[i -: 8]        // i 부터 아래로 8비트
// `acc[i+7 : i]` 는 **불법**이다 (범위 양끝이 다 변수면 안 된다).
// +:/-: 가 그것을 푸는 문법이다.

// 리덕션으로 패리티 한 줄
wire parity = ^data;              // data 의 모든 비트를 XOR

// 전부 0 인지 검사 -- 세 가지가 다 같은 뜻이다
wire empty1 = (count == '0);
wire empty2 = ~|count;            // 리덕션 OR 의 부정
wire empty3 = !count;"""))

    s.append("<h2>Z18.7 Control flow, and what it becomes</h2>")
    s.append(_c("""// if / else -> 멀티플렉서.  **양쪽 다 하드웨어로 존재한다.**
// C++ 처럼 "안 타는 가지는 실행 안 됨" 이 아니다.  둘 다 늘 계산되고
// 마지막에 mux 가 고른다.  그래서 `if (rare) 비싼연산()` 은 하드웨어에서
// 아무것도 아껴 주지 않는다.

// case -> 역시 mux.  수식어가 중요하다
unique case (state)        // 겹치는 가지가 있으면 **시뮬레이션 오류**
    IDLE: ...              // 빠진 가지가 있어도 오류
    RUN:  ...
    DONE: ...
endcase

priority case (sel)        // 위에서부터 우선순위.  겹쳐도 됨
    sel[0]: ...
    sel[1]: ...
endcase

casez (opcode)             // ? 를 don't-care 로 본다
    8'b1010_????: ...      // 상위 4비트만 맞으면 된다
endcase
// `casex` 도 있는데 **쓰지 마라** -- x 를 don't-care 로 취급해서
// 합성 전후가 달라지는 고전적 버그를 낸다.

// for -> **언롤링된다**.  루프가 아니라 하드웨어 복제다
always_comb begin
    acc = '0;
    for (int i = 0; i < NTAP; i++)
        acc = acc + x[i] * H[i];      // 곱셈기 NTAP 개가 **동시에** 생긴다
end
// 경계가 컴파일 시간에 정해져야 한다.  `for (i = 0; i < n; i++)` 에서
// n 이 신호면 합성 안 된다 -- 하드웨어 개수를 못 정하므로.

// generate -> 모듈/블록을 복제한다.  for 와 다르게 **구조**를 만든다
genvar g;
generate
    for (g = 0; g < NTAP; g++) begin : gen_tap   // 라벨을 **반드시** 붙인다
        tap_mul u_mul (.x(x[g]), .h(H[g]), .y(prod[g]));
    end
endgenerate
// 라벨이 없으면 계층 이름이 `genblk1` 이 되고, 나중에 탭을 하나 추가하면
// 이름이 전부 밀려서 파형·제약·커버리지가 통째로 어긋난다.
// verilator -Wall 의 GENUNNAMED 가 이것을 잡는다."""))

    s.append("<h2>Z18.8 Interfaces &mdash; the one big idea with no C++ analogue</h2>")
    s.append("""<p>A bus has a dozen signals and they always travel together. Declaring
    them twelve at a time in every module is where port-list bugs come from. An
    <code>interface</code> bundles them and a <code>modport</code> says which direction
    each end sees.</p>""")

    s.append(_c("""interface axis_if #(parameter int W = 8) (input logic clk);
    logic [W-1:0] tdata;
    logic         tvalid, tready, tlast;

    // modport = 한쪽 끝에서 본 방향.  같은 다발을 양쪽이 반대로 본다
    modport src  (output tdata, tvalid, tlast, input  tready, input clk);
    modport dst  (input  tdata, tvalid, tlast, output tready, input clk);

    // 인터페이스 안에 검사도 넣을 수 있다 -- **한 번 적으면 모든 인스턴스에 걸린다**
    // (아래 assert 문법은 Z18.10)
    property valid_stable;
        @(posedge clk) (tvalid && !tready) |=> $stable(tdata);
    endproperty
    assert property (valid_stable)
        else $error("tvalid 중에 tready 없이 tdata 가 바뀌었다");
endinterface

// 쓰는 쪽: 포트 열두 개가 하나가 된다
module producer (axis_if.src out);
    always_ff @(posedge out.clk) begin
        out.tvalid <= 1'b1;
        out.tdata  <= next_byte;
    end
endmodule

module top;
    logic clk;
    axis_if #(.W(8)) bus (.clk(clk));
    producer u_p (.out(bus));
    consumer u_c (.in (bus));
endmodule"""))

    s.append("""<p>The property embedded in the interface is the point. AXI-Stream
    requires that once <code>tvalid</code> is asserted, the data may not change until
    <code>tready</code> is seen. Written inside the interface, that rule is checked at
    <em>every</em> instance of the bus in the whole design, automatically. Written in each
    testbench, it is checked wherever somebody remembered.</p>""")

    s.append("<h2>Z18.9 Functions and tasks</h2>")
    s.append(tab("<code>function</code> versus <code>task</code>",
        ["", "<code>function</code>", "<code>task</code>"],
        [["Can consume time", "No &mdash; no <code>@</code>, no <code>#</code>, no "
          "<code>wait</code>", "Yes"],
         ["Returns a value", "Yes", "No (use <code>output</code> arguments)"],
         ["Synthesisable", "Yes, if it has no time control", "No"],
         ["C++ analogue", "A <code>constexpr</code>-ish pure function",
          "A coroutine &mdash; it can block and resume"]]))

    s.append(_c("""// `automatic` 이 왜 필요한가 -- C++ 프로그래머가 가장 놀라는 자리
//
// Verilog 의 기본은 `static` 이다.  함수의 지역 변수가 **하나만 존재하고
// 모든 호출이 그것을 공유한다.**  C 의 함수 안 `static int` 가 기본값인 셈이다.
// 동시에 두 번 불리면 서로의 변수를 덮어쓴다.

function automatic int unsigned clog2_up(int unsigned v);
    int unsigned r = 0;             // automatic 이라 호출마다 새로 생긴다
    while (v > 1) begin v >>= 1; r++; end
    return r;
endfunction
// **테스트벤치 함수에는 늘 `automatic` 을 붙여라.**  안 붙이면 여러
// 스레드에서 부를 때 조용히 틀린 값이 나온다.
// (SystemVerilog 의 `module` 안 기본은 static, `program`/`class` 안은 automatic)

// task: 시간을 쓴다
task automatic send_byte(input logic [7:0] b);
    @(negedge clk);
    tdata  <= b;
    tvalid <= 1'b1;
    @(posedge clk);
    while (!tready) @(posedge clk);   // **기다린다** -- function 은 못 하는 일
    tvalid <= 1'b0;
endtask"""))

    s.append("<h2>Z18.10 The verification half of the language</h2>")
    s.append("""<p>Everything above describes hardware. The rest of SystemVerilog is a
    testbench language, and it is much closer to C++ &mdash; classes, inheritance,
    randomisation, dynamic allocation. <b>None of it synthesises</b>, and keeping the two
    halves separate in your head is most of learning the language.</p>""")

    s.append(_c("""// ── 어서션: 무엇이 참이어야 하는가를 적는다 ───────────────────────
// 즉시 어서션 -- 절차 코드 안에서
always_ff @(posedge clk)
    if (!rst) assert (!(full && empty))
        else $error("FIFO 가 full 이면서 empty 다");

// 동시 어서션 -- 시간에 걸친 성질.  이것이 진짜 물건이다
property req_gets_ack;
    @(posedge clk) disable iff (rst)
        req |-> ##[1:8] ack;      // req 가 뜨면 1~8 사이클 안에 ack 가 온다
endproperty
assert property (req_gets_ack);
cover  property (req_gets_ack);   // **정말 일어났는지**도 센다

//   |->  같은 사이클부터 (overlapping)
//   |=>  다음 사이클부터 (non-overlapping)
//   ##n  n 사이클 뒤
//   $rose $fell $stable $past   edge 와 과거 값

// ── 커버리지: 무엇을 **봤는지** 센다 ──────────────────────────────
covergroup cg_sample @(posedge clk);
    cp_val: coverpoint x {
        bins neg_sat  = {-128};        // 포화 경계를 실제로 밟았나
        bins neg      = {[-127:-1]};
        bins zero     = {0};
        bins pos      = {[1:126]};
        bins pos_sat  = {127};
    }
    cp_pair: cross cp_val, cp_state;   // 조합까지 봤나
endgroup
// 어서션이 "틀린 것이 없었나" 라면 커버리지는 "볼 것을 다 봤나" 다.
// 이 책의 변이 점수(Part Z1)는 세 번째 질문에 답한다:
// **"검사가 정말 무는가"**.  셋이 서로를 대신하지 못한다.

// ── 무작위화 ──────────────────────────────────────────────────────
class packet;
    rand bit [7:0] payload [];        // 동적 배열
    rand int       len;
    constraint c_len { len inside {[1:64]};
                       payload.size() == len; }
    // 경계를 **일부러 자주** 뽑는다 -- 무작위만으로는 len==1 이 거의 안 나온다
    constraint c_edge { len dist {1 := 20, [2:8] := 40, [9:64] := 40}; }
endclass

packet p = new();
if (!p.randomize()) $fatal(1, "제약을 못 풀었다");"""))

    s.append("<h2>Z18.11 Classes: where SystemVerilog really is C++</h2>")
    s.append(_c("""// 검증 쪽 class 는 C++ class 와 거의 같다.  다른 점만 적는다.
class base_driver;
    // 모든 객체가 **참조**다.  C++ 의 `T*` 나 `shared_ptr` 에 해당하고,
    // 값 복사(`=`)는 포인터 복사다.  깊은 복사는 직접 적어야 한다.
    protected virtual axis_if vif;    // `virtual interface` = 인터페이스 핸들

    function new(virtual axis_if vif);   // 생성자 이름이 **언제나 `new`** 다
        this.vif = vif;
    endfunction

    // `virtual` 은 C++ 과 같은 뜻 (동적 디스패치).
    // 다만 **기본이 non-virtual** 이라 붙여야 한다.
    virtual task run();
        $display("base");
    endtask
endclass

class fir_driver extends base_driver;      // `:` 이 아니라 `extends`
    function new(virtual axis_if vif);
        super.new(vif);                    // C++ 의 base(vif) 초기화
    endfunction
    virtual task run();
        super.run();
        // ...
    endtask
endclass

// 없는 것들 (C++ 에서 오면 찾게 된다):
//   * 다중 상속 없음.  인터페이스 클래스로 흉내낸다
//   * 연산자 오버로딩 없음
//   * 소멸자 없음 -- 가비지 컬렉션이다
//   * const 멤버 함수 없음
//   * 템플릿은 있다: `class stack #(type T = int);`  (parameterized class)"""))

    s.append("<h2>Z18.12 What is and is not synthesisable</h2>")
    s.append(tab("The dividing line",
        ["Synthesisable", "Not synthesisable"],
        [["<code>always_comb</code>, <code>always_ff</code>, <code>assign</code>",
          "<code>initial</code> (except FPGA memory init), <code>final</code>"],
         ["<code>if</code>, <code>case</code>, <code>for</code> with constant bounds",
          "<code>while</code>/<code>forever</code> with data-dependent exit"],
         ["<code>logic</code>, <code>struct packed</code>, packed arrays, "
          "<code>enum</code>",
          "<code>class</code>, <code>string</code>, <code>real</code>, queues "
          "(<code>[$]</code>), associative arrays, dynamic arrays"],
         ["<code>function</code> without time control", "<code>task</code>, "
          "<code>fork</code>/<code>join</code>, <code>@</code>, <code>#delay</code>"],
         ["<code>parameter</code>, <code>localparam</code>, <code>generate</code>",
          "<code>$display</code>, <code>$fopen</code>, <code>randomize()</code>, "
          "assertions (they are <i>checked</i>, not built)"],
         ["<code>interface</code>, <code>modport</code>",
          "<code>virtual interface</code>, hierarchical references "
          "(<code>dut.internal</code>)"],
         ["<code>$signed</code>, <code>$unsigned</code>, <code>$clog2</code>, "
          "<code>$bits</code>",
          "<code>$random</code>, <code>$time</code>, <code>$past</code>"]]))

    s.append("""<p>The practical test, and the one this repository uses: if
    <code>yosys</code> reads it and <code>verilator --lint-only -Wall</code> is quiet, it
    is synthesisable. Both are free, both run in seconds, and
    <code>edu/house/synth.sh</code> runs them in that order for exactly this reason
    &mdash; Part&nbsp;Z20 walks that script line by line.</p>""")

    s.append("<h2>Z18.13 The house style, in ten rules</h2>")
    s.append(tab("Rules worth enforcing with a linter, and why each exists",
        ["Rule", "The failure it prevents"],
        [["<code>always_ff</code>/<code>always_comb</code>, never bare <code>always</code>",
          "Accidental latches and missing sensitivity items."],
         ["<code>&lt;=</code> in <code>always_ff</code>, <code>=</code> in "
          "<code>always_comb</code>, never mixed",
          "Simulation/synthesis mismatch and evaluation-order races."],
         ["One signal is driven by exactly one block",
          "Multiple drivers &mdash; produces <code>x</code> in simulation and a short in "
          "silicon."],
         ["Always declare <code>signed</code> when the value is signed, and wrap "
          "concatenations in <code>$signed()</code>",
          "The half-the-input-space bug of Z18.3."],
         ["Name every <code>generate</code> block", "Hierarchical names shifting when a "
          "loop bound changes."],
         ["Connect ports by name, never by position",
          "Silent mis-connection when a port is inserted."],
         ["One module per file, file named after the module",
          "Verilator's DECLFILENAME; also how every build tool finds things."],
         ["No <code>casex</code>; use <code>casez</code> or explicit comparison",
          "<code>x</code> treated as don't-care, differing pre- and post-synthesis."],
         ["Reset every flop that needs a known initial value, and say which ones do not",
          "Simulation starting in <code>x</code> and hardware starting in whatever."],
         ["No magic numbers for widths &mdash; use <code>parameter</code> and "
          "<code>$clog2</code>",
          "The width change that gets made in four of five places."]]))

    s.append("""<p>Nine of those ten are checked automatically by
    <code>verilator --lint-only -Wall</code>. Running it costs under a second and it is
    the highest-yield thing in the entire flow &mdash; which is why it is step one of
    <code>synth.sh</code> and not an afterthought.</p>""")

    return "\n".join(s)
