# -*- coding: utf-8 -*-
"""Volume III, Part Z20 -- The free toolchain, command by command."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, E
from wex import ex, derive

HOUSE = "/home/user/SE/edu/house"


def _c(s):
    return "<pre><code>" + E(s) + "</code></pre>"


def ch_tools():
    s = ['<h1 id="z20">Z20. The Free Toolchain, Command by Command</h1>']

    s.append("""<p>Every number in Parts&nbsp;Z14&ndash;Z19 was produced by tools that
    cost nothing and install from a package manager. A one-person design house can take a
    block from C++ to a placed-and-routed netlist with a timing number without a single
    licence. This part is how, command by command, with the real output each one
    produces.</p>""")

    s.append(tab("The toolchain, as measured in this container",
        ["Tool", "Version here", "Job", "Licence"],
        [["<b>Verilator</b>", "5.020", "Lint, and fast C++-based simulation", "LGPL-3 / Artistic-2"],
         ["<b>Icarus Verilog</b>", "12.0", "Event-driven simulation of the full language",
          "GPL-2"],
         ["<b>Yosys</b>", "0.33", "Synthesis: RTL &rarr; gate netlist", "ISC"],
         ["<b>nextpnr-ice40</b>", "0.6", "Place and route, static timing", "ISC"],
         ["<b>PandA Bambu</b>", "2024.10", "High-level synthesis: C/C++ &rarr; RTL", "GPL-3"],
         ["<b>GCC</b>", "g++ -O2", "Compiles the golden model", "GPL-3"]]))

    s.append("""<p>Two things are missing from that list and it is worth being honest about
    them. There is <b>no free sign-off static timing analyser for ASICs</b> (OpenSTA
    exists but was not available here), and there is <b>no free formal equivalence
    checker</b>. For FPGA work the gap does not bite; for an ASIC tape-out it does, and
    Part&nbsp;Y13 covers what that means commercially.</p>""")

    s.append("<h2>Z20.1 Step one: lint, because it is the cheapest</h2>")
    s.append(_c("""verilator --lint-only -Wall --top-module fir4_hand edu/model/fir4_hand.v"""))

    s.append(tab("What the flags do",
        ["Flag", "Meaning", "Why"],
        [["<code>--lint-only</code>", "Parse and check; do not build a simulator.",
          "Runs in well under a second. This is the whole point."],
         ["<code>-Wall</code>", "Enable all the style and width warnings.",
          "The default set is too quiet. <code>-Wall</code> is what industry actually "
          "turns on."],
         ["<code>--top-module</code>", "Name the top of the hierarchy.",
          "Without it, a file with several modules gives confusing 'no top' errors."]]))

    s.append("""<p>The warnings that matter most, and what each is telling you:</p>""")

    s.append(tab("Verilator warnings you will actually see",
        ["Warning", "Means", "Take it seriously?"],
        [["<code>WIDTHEXPAND</code> / <code>WIDTHTRUNC</code>",
          "An assignment or operation changes bit width implicitly.",
          "<b>Yes, always.</b> This is the class of bug Z16.7 spent five derivation steps "
          "preventing. Every silent truncation lives here."],
         ["<code>UNUSEDSIGNAL</code>", "A signal is declared or driven and never read.",
          "<b>Usually.</b> Either it is dead logic (remove it) or you forgot to connect "
          "something. Suppress deliberately with a comment when a port is genuinely "
          "reserved."],
         ["<code>LATCH</code>", "Combinational block does not assign in all paths.",
          "<b>Yes.</b> Almost never intended. See Z18.5."],
         ["<code>MULTIDRIVEN</code>", "Two blocks drive one signal.",
          "<b>Yes.</b> This is a hard bug: <code>x</code> in simulation, contention in "
          "silicon."],
         ["<code>BLKSEQ</code> / <code>COMBDLY</code>",
          "Blocking assignment in sequential logic, or vice versa.",
          "<b>Yes.</b> The race of Z18.4."],
         ["<code>DECLFILENAME</code>", "Module name does not match file name.",
          "Cosmetic, but fix it &mdash; every build system assumes the convention."],
         ["<code>GENUNNAMED</code>", "Unnamed generate block.",
          "Fix it. Hierarchical names shift when loop bounds change."],
         ["<code>SYNCASYNCNET</code>", "A net is used as both sync and async reset.",
          "Investigate. Usually a real reset-architecture problem."]]))

    s.append(ex("Reading a lint report on generated code",
        given="Running the command above on Bambu's generated <code>fir_top.v</code> "
              "returns 19 warnings: 7 WIDTHEXPAND, 6 UNUSEDSIGNAL, 3 WIDTHTRUNC, "
              "1 UNUSEDPARAM, 1 SYNCASYNCNET, 1 DECLFILENAME.",
        method="Separate warnings that indicate a defect from warnings that indicate a "
               "generator's house style.",
        numbers="Effectively <b>all 19</b> are style, not defects. Generated RTL uses "
                "parameterised width-adapter modules, so WIDTHEXPAND and UNUSEDSIGNAL "
                "appear wherever a generic module is instantiated narrower than its "
                "maximum.",
        trap="The wrong conclusion is &ldquo;lint is useless on generated code.&rdquo; "
             "The right one is that you must <b>lint the generator's output once</b>, "
             "triage it, and then <b>watch for new warning types</b>. A WIDTHTRUNC that "
             "was not there yesterday is a real signal; the same six UNUSEDSIGNAL every "
             "build is noise. Counting warnings by type &mdash; which is what "
             "<code>synth.sh</code> prints &mdash; makes the difference visible.",
        extra="The same reasoning applies to hand-written RTL with a different "
              "conclusion: there, a clean <code>-Wall</code> report is achievable and "
              "should be a release gate. <code>edu/model/fir4_hand.v</code> is clean."))

    s.append("<h2>Z20.2 Step two: simulate</h2>")
    s.append(_c("""# 컴파일 -- 소스 여러 개를 한 실행파일로
iverilog -g2012 -DDUT=fir4_hand -o a.out edu/model/fir_tb.v edu/model/fir4_hand.v

#   -g2012   SystemVerilog-2012 문법을 켠다.  **안 켜면 always_ff 부터 막힌다**
#   -D       매크로 정의.  C 의 -D 와 같다.  여기서는 테스트벤치 하나로
#            손RTL 과 HLS RTL 을 갈아 끼우는 데 쓴다
#   -o       출력 파일
#   -s <톱>  톱 모듈 지정 (여러 개일 때)

# 실행 -- vvp 가 iverilog 의 가상머신이다
vvp a.out

# 결과
#   잰것 400  틀림 0

# 파형을 보고 싶으면 테스트벤치에 이것을 넣는다
#   initial begin $dumpfile("w.vcd"); $dumpvars(0, tb); end
# 그리고 gtkwave 로 연다 (이 컨테이너에는 없다 -- GUI 가 없으므로)"""))

    s.append("""<p>Verilator can also simulate, and it is 10&ndash;100&times; faster than
    Icarus because it compiles to C++ rather than interpreting events. The trade is that
    Verilator's simulation is 2-state and cycle-based: it will not show you
    <code>x</code> propagation, which is exactly the thing you want to see when debugging
    a reset problem. <b>Use Icarus to find the bug and Verilator to run the
    regression.</b></p>""")

    s.append("<h2>Z20.3 Step three: synthesise with Yosys</h2>")
    s.append(_c("""yosys -p "read_verilog -sv edu/model/fir4_hand.v; \\
                hierarchy -check -top fir4_hand; \\
                proc; opt; fsm; opt; memory; opt; techmap; opt; \\
                stat" """))

    s.append(tab("The Yosys script, pass by pass",
        ["Pass", "What it does"],
        [["<code>read_verilog -sv</code>", "Parse. <code>-sv</code> enables "
          "SystemVerilog; without it <code>always_ff</code> is a syntax error."],
         ["<code>hierarchy -check -top M</code>", "Resolve the module tree from "
          "<code>M</code> downward. <code>-check</code> makes a missing module an error "
          "rather than a black box &mdash; <b>without it, a typo in a module name "
          "silently synthesises to nothing.</b>"],
         ["<code>proc</code>", "Convert <code>always</code> blocks into multiplexers and "
          "registers. This is where <code>&lt;=</code> becomes a flip-flop."],
         ["<code>opt</code>", "Constant folding, dead-code removal, simplification. Run "
          "it between every other pass; it is cheap."],
         ["<code>fsm</code>", "Detect state machines and re-encode them."],
         ["<code>memory</code>", "Turn array accesses into RAM primitives."],
         ["<code>techmap</code>", "Map to generic gates (<code>$_AND_</code>, "
          "<code>$_XOR_</code>, &hellip;)."],
         ["<code>stat</code>", "Print the cell count. <b>Do not pass <code>-q</code> to "
          "yosys</b> &mdash; it swallows this output, which was measured here the hard "
          "way."]]))

    s.append("""<p>The real output for the hand-written filter:</p>""")

    s.append(_c("""=== fir4_hand ===

   Number of wires:                268
   Number of wire bits:           1681
   Number of public wires:          14
   Number of public wire bits:      97
   Number of cells:                780
     $_AND_                        340
     $_MUX_                         15
     $_NOT_                         10
     $_OR_                         142
     $_SDFF_PP0_                     9
     $_XOR_                        264"""))

    s.append(derive("Reading that report without guessing",
        [("<code>$_SDFF_PP0_</code> &times; 9 &mdash; nine synchronous flip-flops, "
          "positive edge, positive reset, reset-to-0.",
          "The design has exactly nine state bits: <code>done_port</code> (1) plus "
          "<code>return_port</code> (8). The number matching the count you expected is "
          "the first thing to check &mdash; a surprise here means inferred state you did "
          "not intend."),
         ("<code>$_XOR_</code> &times; 264 dominates the combinational logic.",
          "XOR is the sum output of a full adder (Z17.6). Two 9-bit adds plus a 17-bit "
          "add plus the constant-multiply shift-add network accounts for it."),
         ("<code>$_AND_</code> &times; 340 and <code>$_OR_</code> &times; 142 are the "
          "carry logic.",
          "cout = (a AND b) OR (cin AND (a XOR b)) &mdash; two ANDs and an OR per bit."),
         ("<code>$_MUX_</code> &times; 15 is the saturation.",
          "Two comparisons selecting between three 8-bit values. This is the gate-level "
          "price of saturating rather than wrapping, as Z17.7 predicted."),
         ("But 780 generic cells is <b>not</b> the area of the design.",
          "These are technology-independent gates. The device has 4-input lookup tables "
          "and a dedicated carry chain, so the mapping in the next step collapses this "
          "dramatically &mdash; 780 generic cells became 257 iCE40 cells. <b>Never quote "
          "generic cell counts as area.</b>")]))

    s.append("<h2>Z20.4 Step four: map to a real device</h2>")
    s.append(_c("""yosys -p "read_verilog -sv fir4_hand.v; \\
                synth_ice40 -top fir4_hand -json fir4_hand.json; \\
                stat"

# synth_ice40 은 위의 긴 스크립트를 **대신한다** -- 읽기부터 기술 매핑까지
# 한 명령이다.  다른 판을 쓰면 명령만 바꾼다:
#   synth_ice40     Lattice iCE40
#   synth_ecp5      Lattice ECP5   (더 크다.  nextpnr-ecp5 와 짝)
#   synth_gowin     Gowin
#   synth_xilinx    Xilinx 7-series (nextpnr-xilinx 는 실험적이다)
#   synth_intel     Intel/Altera
#   ABC9 기반 매핑을 쓰려면 `-abc9` 를 붙인다 (보통 더 작고 빠르다)"""))

    s.append(_c("""=== fir4_hand ===
   Number of cells:                257
     SB_CARRY                       48
     SB_DFFSR                        9
     SB_LUT4                       200"""))

    s.append("""<p>Now the numbers mean something physical. <code>SB_LUT4</code> is a
    4-input lookup table, <code>SB_CARRY</code> is one bit of the dedicated carry chain,
    <code>SB_DFFSR</code> is a flip-flop with set/reset. The 48 carry cells are the
    adders using hardware the fabric provides for free &mdash; which is why the generic
    780 collapsed to 257, and why the gate-counting exercise in Z17.6 explains the
    <em>structure</em> but not the <em>number</em>.</p>""")

    s.append("<h2>Z20.5 Step five: place, route, and get a real frequency</h2>")
    s.append(_c("""nextpnr-ice40 --hx8k --package ct256 --json fir4_hand.json \\
              --pcf-allow-unconstrained --placer heap --freq 300 --seed 1"""))

    s.append(tab("The flags that change the answer",
        ["Flag", "Meaning", "Why it matters"],
        [["<code>--hx8k --package ct256</code>", "Device and package.",
          "<b>Pin count is a real constraint.</b> Measured here: up5k/sg48 has 39 I/O "
          "and refused to place a design needing 43, with "
          "<code>Unable to find a placement location</code>. That is not a quality "
          "problem with the design."],
         ["<code>--pcf-allow-unconstrained</code>", "Allow pins with no physical "
          "assignment.",
          "Needed when you are measuring a block rather than building a board."],
         ["<code>--placer heap</code>", "Analytic placer.",
          "Better and more repeatable than the default SA placer."],
         ["<code>--freq 300</code>", "Target frequency in MHz.",
          "<b>Without this the target defaults to 12 MHz</b> and the tool stops "
          "optimising the moment it passes &mdash; the reported Fmax then reflects "
          "routing luck, not the design."],
         ["<code>--seed N</code>", "Placement random seed.",
          "Run three and report the spread. A single seed is a sample of one."]]))

    s.append(_c("""Info:          ICESTORM_LC:   211/ 7680     2%
Info: Max frequency for clock 'clock$SB_IO_IN_$glb_clk': 455.79 MHz (PASS at 12.00 MHz)"""))

    s.append(ex("Why that 455.79 MHz was not usable and 47 MHz was",
        given="Placing the hand-written filter directly gives 455.79 MHz. Wrapping it in "
              "a registered timing shell and re-placing gives 47.4 MHz. Same design.",
        method="Ask which paths the tool is measuring in each case.",
        numbers="Without the shell the design has 9 flops, all at the output. The only "
                "register-to-register paths are trivial, and the real datapath runs from "
                "an <b>input pin</b> to those flops &mdash; unconstrained, therefore "
                "unreported. With the shell, every path starts and ends at a flop, so "
                "the 47.4 MHz is the actual combinational depth of the filter.",
        trap="The 455.79 MHz figure is stable across seeds and looks entirely credible. "
             "A reproducible measurement of the wrong path is the most dangerous kind, "
             "because every instinct says to trust it. What exposed it was a "
             "contradiction, not a tool warning: adding pipeline registers made the "
             "reported frequency <i>fall</i>, and more registers cannot make a design "
             "slower.",
        extra="The general rule: <b>a frequency number is meaningless unless you can say "
              "which two registers the path runs between.</b> Ask that question of every "
              "Fmax anyone quotes you, including your own."))

    s.append("<h2>Z20.6 Step six: HLS, if you are generating the RTL</h2>")
    s.append(_c("""bambu --top-fname=fir_top_tuned \\
      -I/home/user/SE/edu/model \\
      --clock-period=3 \\
      --reset-level=high --reset-type=sync \\
      fir_top_tuned.cpp

#   --top-fname      최상위가 될 C 함수.  **이것이 모듈 이름이 된다**
#   -I               헤더 경로.  g++ 와 **같은 경로**를 줘야 같은 모델이 된다
#   --clock-period   목표 주기 (ns).  스케줄링이 여기에 맞춰진다.
#                    Z15 에서 10·6·3·2·1 로 쓸어 무릎을 찾았다
#   --reset-level    high / low.  **기본이 low 다** -- 집 관례와 다르면 여기서 맞춘다
#   --reset-type     sync / async / no
#   --simulate       내장 테스트벤치로 돌려 본다 (골든이 따로 있으면 안 써도 된다)
#   --device-name    목표 소자.  타이밍 추정에 쓰인다

# 안 되는 것들 -- survey/synth/합성결과.md 의 1변수 대조
#   #pragma HLS ...     rc=11.  Xilinx 방언을 안 받는다
#   hls::stream         rc=1.   FixStructsPassedByValue 에서 크래시
#   깊은 ap_fixed 템플릿  rc=124. 프론트엔드 40분 타임아웃"""))

    s.append("<h2>Z20.7 One command that runs all of it</h2>")
    s.append("""<p><code>edu/house/synth.sh</code> is the whole flow in one script. It is
    written to be read as well as run, and two of its choices came from being wrong
    first.</p>""")

    s.append(_c("""bash edu/house/synth.sh <file.v> <top_module> [--pnr]

# 예
bash edu/house/synth.sh edu/model/fir4_hand.v fir4_hand --pnr

# 출력
#   == 1. verilator lint ==
#      경고+오류 0
#      lint rc=0
#   == 2. yosys 기술독립 합성 ==
#      Number of cells:  780 ...
#   == 3. yosys iCE40 매핑 ==
#      SB_LUT4 200, SB_CARRY 48, SB_DFFSR 9
#   == 4. nextpnr 배치·배선 ==
#      ICESTORM_LC: 211/7680,  Max frequency 47.4 MHz"""))

    s.append(tab("Two things the script does that look fussy and are not",
        ["Choice", "What went wrong without it"],
        [["Tool output goes to a <b>file</b>, then is filtered &mdash; never piped "
          "straight into <code>head</code>.",
          "<code>head</code> closes the pipe, the tool dies of SIGPIPE, and the exit code "
          "comes back <b>141</b>. A lint that passed and a lint that crashed became "
          "indistinguishable. Measured here."],
         ["Cell counts are extracted from inside the <code>stat</code> block, not by "
          "grepping the whole log.",
          "Yosys prints <code>Generating RTLIL representation for module "
          "\\SB_LUT4</code> while loading its cell library. A naive "
          "<code>grep SB_LUT4</code> counts those lines as if they were cells."]]))

    s.append("""<p>Both are the same failure in different clothes: <b>a measurement
    harness that reports a plausible number when it has actually failed.</b> That is the
    defect this whole book is organised against, and it turns out to be just as easy to
    build into a twelve-line shell script as into a verification environment.</p>""")

    s.append("<h2>Z20.8 Installing the lot</h2>")
    s.append(_c("""# Debian / Ubuntu -- 앞의 넷은 패키지가 있다
sudo apt install verilator yosys nextpnr-ice40 iverilog gtkwave

# Bambu 는 패키지가 없다.  소스에서 짓는다 (이 컨테이너에서 한 일이다)
sudo apt install gcc-multilib libc6-dev-i386 gcc-13-plugin-dev \\
                 clang-16 llvm-16-dev libclang-16-dev \\
                 autoconf automake libtool
git clone --recursive https://github.com/ferrandi/PandA-bambu.git
# 막혔던 자리들 (survey/synth/합성결과.md 에 전부 적혀 있다):
#   * --depth 1 로 클론하면 서브모듈이 빠져 Makefile.in 이 없다
#   * ext/Coin-Cbc 와 ext/lpsolve5 는 선택인데도 automake 가 디렉터리 존재를 요구한다
#     -> 빈 디렉터리를 만들면 넘어간다
#   * clang 은 16 이어야 한다.  18 은 너무 새것이라 configure 가 거른다"""))

    s.append("""<p>The install list is short and the whole thing fits on a laptop. That is
    the point of this part: the barrier to running a real IP flow is not money any more.
    What the free tools do not give you is ASIC sign-off timing, formal equivalence, and
    somebody to call &mdash; and those are exactly the things Part&nbsp;Y13 says to budget
    for when a block stops being an exercise and starts being a product.</p>""")

    return "\n".join(s)
