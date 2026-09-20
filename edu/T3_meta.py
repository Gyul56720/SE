# -*- coding: utf-8 -*-
"""T3 -- Metastability and clock-domain crossing.

이 장의 수는 전부 아래 상수에서 계산해 낸다.  **손으로 적은 수는 없다.**
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 상수 (28 nm 급 표준 셀 플롭의 공개된 어림값) -------------------------
TAU  = 25e-12          # s, 결정 시간상수 -- 준안정이 풀리는 속도
T0   = 1e-10           # s, 준안정 창의 유효 너비
오버헤드 = 150e-12      # s, t_cq + t_setup + 사이 논리 (한 단에서 잃는 시간)
해 = 3.15576e7          # s/년


def _mtbf(tr, fc, fd, n=1):
    """동기화기 n 단, 단마다 해결시간 tr 초를 줄 때의 평균 고장 간격(초)."""
    return math.exp(n * tr / TAU) / (T0 * fc * fd)


def _년(s):
    return s / 해


def _tr(f, 오버=오버헤드):
    return 1.0 / f - 오버


def ch_meta():
    c = 장(
        "T3", "Metastability — the One Failure You Cannot Design Away",
        "Every other timing quantity can be made to pass. This one can only be made "
        "improbable, and you must say how improbable.",
        쓰는것=["전압", "전류", "미분", "지수함수", "로그", "확률", "평균",
              "트랜스컨덕턴스", "출력저항", "게이트용량", "RC지연",
              "도착시각", "요구시각", "슬랙", "FO4"],
        내놓는것=["준안정", "결정시간상수", "해결시간", "준안정창", "MTBF",
                "동기화기깊이", "다중비트문제", "재수렴", "그레이코드",
                "핸드셰이크", "비동기FIFO", "리셋동기화기", "리커버리",
                "리무벌", "CDC검증", "준정적신호"],
        특허="""Metastability itself is physics, and the two-flop synchroniser is older
        than anyone reading this. <b>What is still being claimed is the arrangement
        around it</b>: a pointer encoding that keeps a multi-bit crossing safe with one
        synchroniser instead of N (gray codes and their successors); a
        latency-versus-MTBF scheme that switches synchroniser depth by operating mode;
        a data-path crossing that avoids synchronising the data at all by synchronising
        only a qualifier and holding the data <i>stable</i> across the boundary. Every
        one of these is an argument about <i>what must cross</i>, not about the flop.
        Read this chapter asking: which of my signals actually has to cross, and what
        would let the rest stay on one side?""")

    c.글("""A setup violation is a scheduling problem: the data was late, and if you slow
    the clock or shorten the logic, it is fixed. Metastability is not that. When a
    flip-flop samples an input that is changing at the moment of the clock edge, the
    output can sit between the two legal levels for an unbounded time. No amount of
    slowing down removes it — the sampling instant and the data transition are
    uncorrelated, so the bad coincidence will happen again. <b>The only question is how
    often, and whether you have budgeted for it.</b>""")

    c.글("""This chapter answers that question with a number, then spends the rest of its
    length on the more common failure: engineers who compute the number correctly, put in
    a two-flop synchroniser, and still ship a chip that hangs — because the thing that
    crossed the boundary was not one bit.""")

    # ------------------------------------------------------------------
    c.절("T3.1 Why a decision can take unbounded time")

    c.날것(유도("From the cross-coupled pair to an exponential", [
        ("A flip-flop's storage element is two inverters in a loop: the output of each "
         "drives the input of the other.",
         "That loop is what holds state with no clock — it is the only structure in "
         "digital design that has memory without a capacitor being explicitly named."),
        ("The loop has three equilibria: a solid 0, a solid 1, and a point in the "
         "middle where both inverters sit at their own switching threshold.",
         "Plot V<sub>out1</sub> vs V<sub>in1</sub> and the mirrored curve for the "
         "second inverter; they cross three times. The middle crossing is the "
         "metastable point."),
        ("The middle equilibrium is <b>unstable</b>: the loop gain there is A² > 1, so "
         "any deviation grows.",
         "Each inverter has small-signal gain A = −g<sub>m</sub>(r<sub>o,n</sub> ∥ "
         "r<sub>o,p</sub>) at its threshold, and T1 gave both terms."),
        ("Linearise around it: C·dv/dt = (A − 1)·v/R, so v(t) = v<sub>0</sub>·e<sup>t/τ</sup> "
         "with τ = RC/(A − 1).",
         "This is where <b>τ, the decision time constant, comes from</b>. It is a "
         "circuit property — roughly the loop's RC divided by its excess gain — and it "
         "is <i>not</i> a specification you can choose."),
        ("To resolve to a valid level the loop must grow the deviation from "
         "v<sub>0</sub> to about V<sub>DD</sub>/2, which takes "
         "t = τ·ln(V<sub>DD</sub>/2v<sub>0</sub>).",
         "The time is <b>logarithmic in how close the sample landed to the centre</b> — "
         "and v<sub>0</sub> can be arbitrarily small, so t is unbounded. There is no "
         "worst case to design for, only a distribution."),
        ("The probability that a sample lands within a window that needs more than "
         "t<sub>r</sub> to resolve falls as e<sup>−t<sub>r</sub>/τ</sup>.",
         "Uniform arrival within the clock period, and v<sub>0</sub> proportional to how "
         "close the edge was, give the exponential directly."),
    ]))

    c.날것(그림(sch.씨모스인버터(),
        "One of the two inverters in the loop. At the metastable point it sits at its "
        "own switching threshold with both devices in saturation — the highest-gain, "
        "highest-current, least-stable operating point it has."))

    c.날것(짚기("""Two consequences fall out of that derivation and both matter in
    practice. <b>First, τ is a small-signal quantity</b>, so it degrades exactly where
    gain degrades: slow corner, low voltage, high temperature. <b>Second, the metastable
    point is where the flop burns the most current</b> — both devices are on. A design
    that goes metastable often does not just fail logically; it draws current it was not
    budgeted for."""))

    # ------------------------------------------------------------------
    c.절("T3.2 MTBF, and what every symbol in it actually is")

    c.날것(정의("MTBF (mean time between failures)",
        "The average time between two events in which a synchroniser fails to resolve "
        "within the time allowed. <b>It is a rate, not a guarantee</b> — a 1000-year "
        "MTBF does not mean the first failure is in year 1000; it means the failures "
        "are Poisson with that mean."))

    c.날것(개념(
        "The MTBF expression",
        f"""<p>MTBF = e<sup>t<sub>r</sub>/τ</sup> / (T<sub>0</sub>·f<sub>c</sub>·f<sub>d</sub>)</p>
        <p><b>t<sub>r</sub></b> — resolution time: the time the synchroniser flop is
        given to settle before anything reads it. In a single-stage crossing that is
        T<sub>clk</sub> minus the flop's own t<sub>cq</sub>, minus the setup of whatever
        reads it, minus any logic in between. <b>τ</b> — decision time constant, from
        T3.1, here {수(TAU*1e12,3,'ps')}. <b>T<sub>0</sub></b> — the effective width of
        the aperture in which a sample can go metastable, here {수(T0*1e12,3,'ps')};
        both are measured per cell per corner, not derived. <b>f<sub>c</sub></b> —
        the sampling (destination) clock frequency. <b>f<sub>d</sub></b> — the rate at
        which the asynchronous input changes.</p>
        <p>Only t<sub>r</sub> is in the exponent, and that is the whole engineering
        content of this formula: <b>everything you can do is linear, and the thing you
        cannot control is exponential.</b> Doubling f<sub>d</sub> halves MTBF. Adding
        one synchroniser stage <i>multiplies the exponent</i>.</p>""",
        어디에="Every asynchronous boundary in the design: an external interrupt, a "
             "reset release, a pushbutton, a FIFO pointer crossing between clock "
             "domains, a PHY's recovered-clock domain meeting the core's.",
        언제="At architecture time you pick the depth; at signoff you state the number. "
            "<b>An IP datasheet that claims 'CDC safe' without an MTBF and the "
            "conditions it was computed at has claimed nothing.</b>",
        어떻게="Get τ and T<sub>0</sub> from the library's synchroniser cell "
             "characterisation (they are published per corner). Compute t<sub>r</sub> "
             "from the real path, not the ideal clock period. Then state MTBF at the "
             "<b>slow corner</b>, because τ is worst there.",
        산업코드="""// The synchroniser, written so the tools recognise it.
// The attribute is not decoration: it tells the tool to keep the two flops
// adjacent and out of retiming, and it tells CDC checkers this is intentional.
(* ASYNC_REG = "TRUE" *) reg [1:0] sync_q;          // Xilinx; Intel: altera_attribute
always_ff @(posedge clk_dst or negedge rst_n) begin
    if (!rst_n) sync_q <= 2'b00;
    else        sync_q <= {sync_q[0], async_in};    // 2-stage
end
wire safe_in = sync_q[1];

// And the constraint, without which STA tries to time an impossible path:
// set_max_delay -datapath_only 2.0 -from [get_pins u_src/*/Q] -to [get_pins u_sync/sync_q_reg[0]/D]
// NOT set_false_path -- a false path lets the tool put unbounded wire delay there,
// and then the first stage's own setup window is no longer what you assumed.""",
        주의="""Using <code>set_false_path</code> on a crossing is the single most common
            CDC constraint error. It silences the timing report, but it also removes any
            bound on the wire delay into the synchroniser — so the source can change
            arbitrarily close to the destination edge <i>and</i> the skew between the two
            bits of a bus becomes unbounded. Use <code>set_max_delay -datapath_only</code>."""))

    표들 = []
    for f in (5e8, 1e9, 2e9):
        tr = _tr(f)
        줄 = [수(f/1e9, 2, "GHz"), 수(tr*1e12, 3, "ps")]
        for n in (1, 2, 3):
            y = _년(_mtbf(tr, f, f/10, n))
            줄.append(수(y, 3, "년") if y < 1e6 else f"{y:.2g} 년")
        표들.append(줄)
    c.날것(표("MTBF against clock frequency and synchroniser depth "
             f"(τ = {수(TAU*1e12,3,'ps')}, T₀ = {수(T0*1e12,3,'ps')}, "
             f"f_d = f_c/10, overhead {수(오버헤드*1e12,3,'ps')})",
             ["f_clk", "t_r per stage", "1 stage", "2 stages", "3 stages"], 표들))

    c.날것(예제(
        "Why two stages is the default, and where it stops being enough",
        f"""A 1 GHz destination clock, an input that changes at 100 MHz, and
        {수(오버헤드*1e12,3,'ps')} of overhead per stage, so t<sub>r</sub> =
        {수(_tr(1e9)*1e12,3,'ps')}.""",
        """Put the numbers into the expression once per depth. The exponent scales with
        the number of stages because each stage gets its own full t<sub>r</sub>.""",
        f"""One stage: {수(_년(_mtbf(_tr(1e9),1e9,1e8,1)),3)} 년 — <b>a failure every
        couple of years, per crossing.</b> Two stages:
        {_년(_mtbf(_tr(1e9),1e9,1e8,2)):.2g} 년. Three stages:
        {_년(_mtbf(_tr(1e9),1e9,1e8,3)):.2g} 년.""",
        f"""Reading the two-stage number as a property of the design rather than of the
        corner. Recompute it with τ merely 2× worse — a plausible slow-corner,
        low-voltage degradation — and the same two-stage crossing gives
        <b>{_년(math.exp(2*_tr(1e9)/(2*TAU))/(T0*1e9*1e8)):.3g} 년.</b> The exponent
        collapsed. <b>MTBF is exponentially sensitive to the one parameter you do not
        control</b>, which is why the number must be quoted at the slow corner and why
        the third stage exists.""",
        덧=표("The same two-stage crossing at 1 GHz, as τ degrades",
             ["τ", "MTBF"],
             [[수(k, 2) + "×", f"{_년(math.exp(2*_tr(1e9)/(k*TAU))/(T0*1e9*1e8)):.3g} 년"]
              for k in (1.0, 1.25, 1.5, 2.0)])))

    c.날것(짚기(f"""At 2 GHz the table says something worth pausing on: a
    <b>single</b>-stage crossing has an MTBF of
    {_mtbf(_tr(2e9),2e9,2e8,1):.3g} seconds. Not years — seconds. To reach 100 years
    with one stage at that frequency you would need t<sub>r</sub> =
    {수(TAU*math.log(100*해*T0*2e9*2e8)*1e12, 4, 'ps')}, which is longer than the
    clock period itself ({수(500,3,'ps')}). <b>The requirement is not achievable in one
    cycle at all</b> — this is the regime where depth stops being a safety margin and
    becomes the only way the circuit works."""))

    # ------------------------------------------------------------------
    c.절("T3.3 A synchroniser is not a CDC solution")

    c.글("""Everything so far concerns one bit. The failures that actually reach silicon
    almost never come from a wrong MTBF; they come from designers who synchronised each
    bit of a bus correctly and still lost.""")

    c.날것(그림(sch.다중비트깨짐(),
        "Two bits crossing through their own synchronisers. Each bit is individually "
        "safe. The pair is not: one resolves this cycle, the other next cycle, and the "
        "receiver sees a value that was never sent."))

    c.날것(개념(
        "The multi-bit problem, and the three ways out",
        """<p>Independent synchronisers make independent decisions. If two bits change
        in the same source cycle, each may resolve on either side of the boundary, so
        the destination can observe an intermediate value — <b>a code that the source
        never drove</b>. A binary counter crossing 0111 → 1000 can be seen as 1111 or
        0000 or anything between. No MTBF calculation detects this: every flop behaved
        correctly.</p>""",
        어디에="Any bus, counter, pointer, status word or configuration field that "
             "crosses a clock boundary. In practice: FIFO pointers, interrupt status "
             "registers, and 'mode' fields written by a slow configuration domain and "
             "read by a fast datapath.",
        언제="The moment more than one bit crosses. The three-bit case is not safer "
            "than the thirty-two-bit case — it is the <i>simultaneity</i> that matters, "
            "not the width.",
        어떻게="""Pick one: <b>(1) Gray code</b> — only one bit changes per increment,
             so an intermediate sample is either the old or the new value, both valid.
             Works for counters and pointers, not for arbitrary data. <b>(2) Handshake</b>
             — hold the data stable and cross a single request bit; the receiver
             acknowledges. Costs round-trip latency, works for anything.
             <b>(3) Asynchronous FIFO</b> — a dual-port memory with gray-coded pointers;
             this is (1) and (2) combined and is what you ship for streaming data.""",
        산업코드="""// Gray-coded pointer crossing -- the standard async FIFO core.
// The pointer is converted to gray BEFORE crossing and back AFTER.
function automatic [PW:0] bin2gray(input [PW:0] b); return b ^ (b >> 1); endfunction

always_ff @(posedge wclk or negedge wrst_n)
    if (!wrst_n) {wbin, wgray} <= '0;
    else         {wbin, wgray} <= {wbin_next, bin2gray(wbin_next)};

// crossing: gray value only, two stages, one synchroniser per bit is now SAFE
// because at most one bit differs between consecutive gray values.
(* ASYNC_REG = "TRUE" *) reg [PW:0] wq1_rgray, wq2_rgray;
always_ff @(posedge wclk or negedge wrst_n)
    if (!wrst_n) {wq2_rgray, wq1_rgray} <= '0;
    else         {wq2_rgray, wq1_rgray} <= {wq1_rgray, rgray};

// FULL is computed from the SYNCHRONISED read pointer, so it is CONSERVATIVE:
// it can be asserted when the FIFO has already been drained, never the reverse.
assign wfull = (wgray_next == {~wq2_rgray[PW:PW-1], wq2_rgray[PW-2:0]});""",
        주의="""Gray code protects the <i>pointer</i>, not the <i>data</i>. The data path
            in an async FIFO is a dual-port RAM, and it is safe only because the read
            address is never allowed to reach a location the write side has not finished
            writing — that is what the conservative full/empty comparison buys. Copying
            the gray-code trick onto a data bus does nothing: consecutive data words
            differ in many bits."""))

    c.날것(사고("""A crossing can also fail with <b>zero</b> metastability events. If a
    source pulse is shorter than one destination clock period, the destination may never
    sample it — the synchroniser resolves cleanly to the old value, every time. This is
    not a probabilistic failure; it is a guaranteed one, and it is invisible to MTBF
    analysis. The rule that prevents it: <b>a signal crossing into a slower domain must
    be held for at least one and a half destination periods</b>, or converted to a
    level-toggle with a handshake back."""))

    c.날것(표("What each crossing style costs and what it protects",
        ["Style", "Latency (dst cycles)", "Throughput", "Protects", "Fails when"],
        [["2-flop synchroniser", "2", "1 bit / cycle", "One bit, level-stable",
          "More than one bit changes together; pulses shorter than 1.5 cycles"],
         ["Pulse synchroniser (toggle)", "2–3", "1 event / 3 cycles",
          "Single events across any ratio", "Events arrive faster than the round trip"],
         ["Gray pointer", "2", "1 increment / cycle", "Monotone counters and pointers",
          "Used on arbitrary data"],
         ["Req/ack handshake", "4–6 round trip", "1 word / round trip",
          "Arbitrary data of any width", "Latency budget cannot absorb the round trip"],
         ["Async FIFO", "2–3 + fill", "1 word / cycle sustained",
          "Streaming data, rate mismatch", "Depth is too small for the burst pattern"],
         ["Quasi-static (config field)", "0", "written once",
          "Fields that change only while the consumer is idle or in reset",
          "Someone writes it while the datapath is running"]]))

    c.날것(정의("준정적신호 (quasi-static signal)",
        "A crossing signal that is <b>guaranteed by protocol</b> to change only while "
        "the destination is not using it — typically a configuration field written "
        "before the block is enabled. It needs no synchroniser, but it does need "
        "<b>a written rule in the datasheet</b> and a CDC waiver that says so. An "
        "undocumented quasi-static assumption is how an IP works in the lab and fails "
        "in the customer's system."))

    # ------------------------------------------------------------------
    c.절("T3.4 Reset: the crossing everyone forgets")

    c.글("""Reset is asynchronous by nature — it must work before any clock is running —
    and synchronous by necessity, because releasing it at the wrong instant violates the
    flop's recovery time and puts the state machine in a metastable state on its first
    cycle. The resolution is the same for every design and is worth memorising as a
    single sentence: <b>assert asynchronously, release synchronously.</b>""")

    c.날것(그림(sch.리셋동기화기(),
        "The reset synchroniser. The asynchronous assertion path has no clock in it; "
        "the release path runs through two flops clocked by the destination domain."))

    c.날것(개념(
        "리커버리 · 리무벌 (recovery and removal)",
        """<p>Recovery time is the setup constraint on reset <b>de-assertion</b>: reset
        must be released at least t<sub>recovery</sub> before the active clock edge.
        Removal time is the corresponding hold constraint. They are characterised like
        any other timing arc and appear in the .lib — which means STA checks them
        <b>only if the reset is a timed, synchronous signal at that flop</b>.</p>
        <p>An asynchronous reset that is released without a synchroniser has no such
        relation to the clock, so STA reports nothing, and the failure appears as a
        state machine that occasionally starts in an illegal state after power-up —
        typically at one corner, on some boards, after some power ramps.</p>""",
        어디에="Every clock domain. A design with three clocks needs three reset "
             "synchronisers, each clocked by its own domain and all fed by the same "
             "asynchronous source.",
        언제="Always. The cost is two flops per domain; the failure it prevents is the "
            "hardest class of bug to reproduce.",
        어떻게="Assert straight through (no clock), release through two flops. Then "
             "constrain it: the release is now a synchronous signal and STA will check "
             "recovery/removal on every flop it reaches.",
        산업코드="""// Reset synchroniser -- one per clock domain.
module reset_sync (input clk, input arst_n, output rst_n);
    (* ASYNC_REG = "TRUE" *) reg [1:0] q;
    always_ff @(posedge clk or negedge arst_n)
        if (!arst_n) q <= 2'b00;          // ASSERT: asynchronous, no clock needed
        else         q <= {q[0], 1'b1};   // RELEASE: two clocked stages
    assign rst_n = q[1];
endmodule

// SDC: the asynchronous assertion is not a timed path; the release is.
set_false_path -from [get_ports arst_n] -to [get_pins u_rsync/q_reg[0]/CLR]
// and every flop fed by rst_n gets a normal recovery/removal check -- verify with:
//   report_timing -delay_type max -check_type recovery -from [get_pins u_rsync/q_reg[1]/Q]""",
        주의="""Resetting the synchroniser's own flops with the <i>synchronised</i> reset
            is a loop with no way out: the block never leaves reset if the release edge
            is missed. The synchroniser must take the <b>raw asynchronous</b> reset on
            its clear pin. This is also why the two flops in a reset synchroniser reset
            to 0 and shift in 1, rather than the other way round."""))

    # ------------------------------------------------------------------
    c.절("T3.5 What STA cannot check, and what a CDC tool does instead")

    c.날것(표("Two tools, two questions",
        ["Question", "STA", "CDC analysis"],
        [["Does this path meet setup at the given clock relation?", "yes", "no"],
         ["Is there a clock relation at all?", "assumes one", "<b>this is its job</b>"],
         ["Does every crossing have a synchroniser?", "no", "yes (structural)"],
         ["Do multiple bits cross together?", "no",
          "yes — reconvergence and bus-coherency checks"],
         ["Is the source stable long enough?", "no",
          "yes — protocol checks, usually as generated assertions in simulation"],
         ["Is this crossing intentionally unsynchronised?", "no",
          "only if you <b>waive it</b>, by name, with a reason"]]))

    c.날것(짚기("""The waiver file is the part of CDC signoff that decides whether the
    analysis meant anything. A tool run with two hundred waivers and a green summary is
    not evidence; it is two hundred assertions by an engineer. <b>An IP deliverable
    should ship its CDC waivers as a readable document</b>, one line of justification
    each, because the integrator inherits every one of them and cannot re-derive them
    from the netlist."""))

    c.날것(개념(
        "Proving a crossing in simulation as well as structurally",
        """<p>Structural CDC analysis proves a synchroniser <i>exists</i>. It cannot
        prove the source obeys the protocol the synchroniser assumes — that the data is
        stable while the request is high, that pulses are long enough, that a
        quasi-static field is not written while the datapath runs. Those are <b>temporal
        properties</b>, and they are checked by assertions, either hand-written or
        generated by the CDC tool.</p>
        <p>The strongest available check adds metastability <i>injection</i>: the
        simulator randomly delays the synchroniser output by one cycle, so that a design
        which only works when the crossing resolves immediately fails in regression
        rather than in silicon.</p>""",
        어디에="Block-level verification of anything with more than one clock, and "
             "every IP you intend to sell into someone else's clocking scheme.",
        언제="Run structural CDC at every RTL freeze; run injection in the nightly "
            "regression. The two find different bugs and neither subsumes the other.",
        어떻게="Bind the assertions to the crossing module, run the regression with "
             "injection on, and record the result in the deliverable's verification "
             "section with the number of crossings and the number of waivers.",
        산업코드="""// The protocol the handshake crossing assumes, stated as a checkable property.
property data_stable_while_req;
    @(posedge clk_src) disable iff (!rst_n)
        req |-> ##0 $stable(data) throughout (req [*1:$] ##1 ack_sync);
endproperty
assert property (data_stable_while_req)
    else $error("CDC: data changed while req was asserted -- the receiver may latch a mix");

// Metastability injection (simulation only): the synchroniser may take one extra cycle.
`ifdef CDC_INJECT
    always_ff @(posedge clk_dst)
        if ($urandom_range(0,99) < 5) sync_q[1] <= sync_q[1];   // hold: resolve later
`endif""",
        주의="""Assertions written in the destination domain about source-domain signals
            are themselves a clock-domain crossing and can report failures that are
            artefacts of the testbench. Sample source signals in the source domain
            (<code>@(posedge clk_src)</code>) and cross only the boolean result."""))

    # ------------------------------------------------------------------
    c.절("T3.6 What to do with this on Monday")

    c.날것(쓰는자리([
        ["MTBF · 결정시간상수", "Every asynchronous boundary",
         "Synchroniser depth, and the number you write in the datasheet"],
        ["동기화기깊이", "Architecture, per crossing",
         "Two by default; three above ~1 GHz or when τ is poorly characterised"],
        ["다중비트문제 · 그레이코드", "FIFO pointers, counters, status words",
         "Whether the crossing needs an encoding, a handshake, or a FIFO"],
        ["핸드셰이크 · 비동기FIFO", "Streaming data between domains",
         "Latency and depth, and therefore area"],
        ["리셋동기화기 · 리커버리", "Every clock domain",
         "Whether the block starts in a legal state at every corner"],
        ["CDC검증 · 준정적신호", "Signoff and the deliverable",
         "The waiver list the integrator inherits"]]))

    c.글("""Two numbers end this chapter, and they are the ones to carry: at 1 GHz a
    single-stage crossing fails about once every """ +
        수(_년(_mtbf(_tr(1e9), 1e9, 1e8, 1)), 2) + """ years, and the same crossing with
    τ twice as large fails about once every """ +
        f"{_년(math.exp(2*_tr(1e9)/(2*TAU))/(T0*1e9*1e8)):.2g}" + """ years even with two
    stages. The first number is why synchronisers exist; the second is why the answer is
    always quoted with its corner.""")

    c.글("""The next chapter takes the quantity this one kept assuming — that a sample is
    either right or wrong — and replaces it with a distribution. Noise sets the floor
    under every analog measurement in a mixed-signal IP, and unlike metastability it can
    be traded directly against power and area.""")

    return c.완성()
