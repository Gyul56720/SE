# -*- coding: utf-8 -*-
"""T2 -- Delay: from one RC to a whole timing path.

**이 장의 수는 전부 아래 상수에서 계산해 낸다.**  본문에 손으로 적은 수는
없다 -- 그래서 상수를 바꾸면 표와 그림이 같이 바뀐다.  이 저장소의 규율이
"잰 것만 적는다" 인데, 교재에서 그 규율은 *계산해 낸 것만 적는다* 가 된다.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 공정 상수 (28 nm 급 저전력의 공개된 어림값) --------------------------
VDD   = 0.9           # V
R_INV = 8.0e3         # Ω, 최소 인버터 하나의 등가 출력저항 (풀다운)
C_G   = 1.0e-15       # F, 최소 인버터 하나의 입력 용량
TAU   = R_INV * C_G   # s, 이 공정의 '한 단위 지연'
P_INV = 1.0           # 인버터의 기생 지연 (τ 단위)
R_W   = 1.0           # Ω/µm, 중간층 얇은 배선
C_W   = 0.18e-15      # F/µm
L_LONG = 1000.0       # µm, 긴 배선 보기


def _fo4():
    """FO4 -- 같은 인버터 넷을 미는 인버터 하나의 지연.  공정의 잣대."""
    return (1.0 * 4 + P_INV) * TAU


def _le사슬(F, N):
    """논리적 노력: 전기적 노력 F 를 N 칸으로 나눌 때의 전체 지연 (τ 단위)."""
    return N * F ** (1.0 / N) + N * P_INV


def _elmore(칸):
    """배선을 `칸` 조각으로 쪼갠 엘모어 지연 (초)."""
    Rs, Cs = R_W * L_LONG / 칸, C_W * L_LONG / 칸
    return sum(Rs * Cs * (칸 - i) for i in range(칸))


def _리피터(k, h):
    """리피터 k 개 · 크기 h 로 L_LONG 을 건널 때의 지연 (초).

    한 토막 = 구동저항이 (배선용량 + 다음 입력용량) 을 밀고, 분산 배선이
    자기 용량을 0.4RC 로, 다음 입력용량을 0.7RC 로 민다.
    """
    Rd, Cin = R_INV / h, h * C_G
    Rs, Cs = R_W * L_LONG / k, C_W * L_LONG / k
    return k * (0.7 * Rd * (Cs + Cin) + 0.4 * Rs * Cs + 0.7 * Rs * Cin)


def _최적리피터(k범위=range(1, 13), h범위=range(1, 120)):
    """수로 쓸어서 찾은 최적 (지연, k, h)."""
    난것 = [(_리피터(k, h), k, h) for k in k범위 for h in h범위]
    return min(난것)


def _해석적최적():
    """같은 답을 **닫힌 꼴로** 한 번 더 구한다 -- 독립 대조."""
    Rw, Cw = R_W * L_LONG, C_W * L_LONG
    k = math.sqrt(0.4 * Rw * Cw / (0.7 * R_INV * C_G))
    h = math.sqrt(R_INV * Cw / (Rw * C_G))
    return k, h


def _ps(x):
    return 수(x * 1e12, 3, "ps")


def ch_delay():
    최적 = _최적리피터()
    k해, h해 = _해석적최적()
    사슬 = [(N, _le사슬(64, N)) for N in range(1, 7)]
    최선N = min(사슬, key=lambda t: t[1])

    c = 장(
        "T2", "Delay — From One RC to a Whole Timing Path",
        "Every delay number a tool reports is one of four models. Know which one, "
        "or you will trust a number that was never about your circuit.",
        쓰는것=["전압", "전류", "저항", "미분", "지수함수", "옴의법칙",
              "문턱전압", "선형영역", "포화영역", "온저항", "게이트용량",
              "출력저항"],
        내놓는것=["RC지연", "엘모어지연", "논리적노력", "전기적노력",
                "기생지연", "FO4", "슬루", "단락전류", "배선지연",
                "리피터", "도착시각", "요구시각", "슬랙", "OCV",
                "NLDM", "비선형지연모델"],
        특허="""The delay of a gate is physics and is not patentable. <b>The way a
        block arranges itself so that a delay stops mattering is.</b> Look at what the
        claims in shipping IP actually cover: a speculative (unrolled) decision-feedback
        equaliser that moves a feedback multiply-add off the critical loop and replaces
        it with a precomputed mux — the arithmetic is unchanged, the loop delay is not;
        a carry-select adder that buys delay with area by computing both carries; a
        clock-tree scheme that deliberately skews two launch points so that a slow path
        borrows time from a fast one. In every case the invention is <i>where the delay
        was moved</i>, not how fast a transistor is. That is why this chapter spends as
        much time on <i>which term dominates</i> as on the formulae: you cannot move a
        term you have not identified.""")

    c.글("""Ask four engineers what the delay of an inverter is and you get four answers,
    all correct, because they are answering with four different models. A SPICE user
    answers with a differential equation. A physical-design engineer answers with a
    two-dimensional lookup table from a Liberty file. A microarchitect answers in FO4.
    A synthesis engineer answers with a dimensionless number that has no picoseconds in
    it at all. These are not competing approximations of one truth; they are four tools
    with different jobs, and using the wrong one is how a design gets signed off on a
    number that was never about the path that failed.""")

    c.글("""This chapter builds them in order, each from the one before, and at every
    step states the regime in which that model is the right one to use. The numbers
    throughout come from one set of process constants declared at the top of this
    chapter's source — a 28 nm-class low-power node at """ + 수(VDD, 2, "V") + """ —
    and every table below is computed from them, not typed in.""")

    # ------------------------------------------------------------------
    c.절("T2.1 The one model you can do in your head: switched RC")

    c.글("""A CMOS gate charges and discharges a capacitor through a transistor that is
    acting as a resistor. That is the whole of it. Everything else in this chapter is a
    refinement of that sentence, and every refinement exists because a specific
    assumption in it broke.""")

    c.날것(정의("RC지연 (RC delay)",
        "A gate's output node is a capacitance C driven through an equivalent "
        "resistance R. The node's voltage is a decaying exponential, and the delay "
        "is the time to cross the receiver's switching threshold — conventionally "
        "50 % of V<sub>DD</sub>."))

    c.날것(유도("From the transistor to 0.69 RC", [
        ("A switching gate connects the output node either to V<sub>DD</sub> through "
         "the PMOS stack or to ground through the NMOS stack.",
         "That is what a static CMOS gate is: two complementary networks, exactly one "
         "of which conducts in steady state."),
        ("While it switches, the conducting transistor is not a resistor — it starts "
         "in saturation and ends in triode.",
         "V<sub>DS</sub> starts at V<sub>DD</sub> and falls toward 0, so the device "
         "crosses regions during the transition (T1)."),
        ("We replace it anyway with a single equivalent resistance R<sub>eq</sub>, "
         "defined as the value that gives the same 50 % crossing time.",
         "This is a <i>fitted</i> quantity, not a measured resistance — which is why "
         "it differs between textbooks and why you never compare R<sub>eq</sub> "
         "numbers across sources."),
        ("Then V(t) = V<sub>DD</sub>·e<sup>−t/RC</sup> for a falling output.",
         "First-order linear ODE with a step excitation: the standard solution."),
        ("Setting V = V<sub>DD</sub>/2 gives t = RC·ln 2 = 0.69 RC.",
         "ln 2 = 0.693. This is where the 0.69 in every delay formula comes from — "
         "it is the 50 % point, nothing more."),
        ("For 10–90 % rise/fall time the same solution gives t = RC·ln 9 = 2.2 RC.",
         "Same exponential, different two crossings. <b>0.69 and 2.2 describe the same "
         "waveform</b> — a delay and a slew are two readings of one curve."),
    ]))

    c.날것(그림(sch.씨모스인버터(),
        "The unit inverter. The pull-up and pull-down networks are the R in RC; "
        "the next stage's gate capacitance and the wire are the C."))

    c.날것(개념(
        "τ = R<sub>eq</sub>·C<sub>g</sub> — the process's unit of time",
        f"""<p>Pick one reference device — the minimum-size inverter — and give it two
        numbers: an equivalent output resistance R<sub>eq</sub> = {수(R_INV/1e3,3,'kΩ')}
        and an input capacitance C<sub>g</sub> = {수(C_G*1e15,2,'fF')}. Their product
        τ = {_ps(TAU)} is the only absolute time in the rest of this chapter. Every other
        delay will be quoted as a multiple of it.</p>
        <p>This is not a cosmetic choice. Ratios between gates are set by topology and
        are stable across process, voltage and temperature to within a few per cent;
        the absolute τ moves by <b>2× or more</b> across corners. Separating the two is
        what lets you do architecture on paper and let the tool supply the picoseconds.</p>""",
        어디에="Every hand estimate of a critical path, every early architectural "
             "trade-off, every 'will this fit in one cycle' question before the RTL "
             "exists.",
        언제="Before synthesis — when there is no netlist to run STA on, and after "
            "STA, to check whether a reported number is even plausible.",
        어떻게=f"""Express the path in τ, then multiply once at the end. A useful
             anchor is <b>FO4</b> — an inverter driving four copies of itself —
             which in this process is {_ps(_fo4())}. A modern high-performance pipeline
             stage is roughly 12–20 FO4; a low-power one, 25–40.""",
        산업코드="""// A 'timing shell' exists so that the number you measure is about
// your logic, not about the pads. Synthesise the DUT inside registers:
module fir_shell (input clk, input rst, input signed [7:0] din, output signed [15:0] dout);
    reg signed  [7:0] din_q;
    reg signed [15:0] dout_q;
    wire signed [15:0] y;
    always @(posedge clk) begin din_q <= din; dout_q <= y; end
    fir4 u_dut (.clk(clk), .rst(rst), .x(din_q), .y(y));
    assign dout = dout_q;
endmodule
// Measured on this repository's own FIR: 455 MHz without the shell, 47 MHz with it.
// The 455 MHz was the tool timing a path that started and ended at a pin.""",
        주의="""Quoting F<sub>max</sub> from a design whose inputs and outputs are pins
            is the single most common false number in an IP datasheet. If a path has no
            launching and no capturing register, the tool has nothing to constrain and
            will report whatever combinational delay it found — often 10× optimistic."""))

    # ------------------------------------------------------------------
    c.절("T2.2 Elmore delay — when one RC becomes a chain of them")

    c.글("""The single-RC model assumes the resistance is at one end and the capacitance
    at the other. A wire violates both: its resistance and its capacitance are
    distributed along it. Cutting it into N lumps and summing gives the Elmore delay,
    and the sum has a shape worth memorising, because it is the reason long wires do not
    scale.""")

    c.날것(그림(sch.RC사다리(4),
        "A wire cut into four RC sections. Section 1's resistance pushes the "
        "capacitance of sections 1–4; section 4's pushes only its own."))

    c.날것(유도("Why wire delay grows with the square of length", [
        ("Cut a wire of length L into N equal sections, each with resistance R/N and "
         "capacitance C/N.",
         "R = r·L and C = c·L, with r in Ω/µm and c in F/µm from the technology file."),
        ("The charge for every capacitance downstream of section i must flow through "
         "section i's resistance.",
         "Charge has only one path to reach them — that is the whole content of the "
         "Elmore model."),
        ("So the delay is Σ<sub>i</sub> (R/N)·(N−i+1)(C/N) = RC·(N+1)/(2N).",
         "Arithmetic series 1+2+…+N = N(N+1)/2. Substituting gives the closed form."),
        ("As N → ∞ this tends to RC/2, and R and C are each proportional to L.",
         "Hence t ∝ r·c·L² — <b>doubling a wire's length quadruples its delay</b>, "
         "while a gate's delay does not change at all."),
        (f"For this process, a {수(L_LONG,4,'µm')} wire gives RC/2 = "
         f"{_ps(0.5*R_W*L_LONG*C_W*L_LONG)}, and the four-lump approximation gives "
         f"{_ps(_elmore(4))}.",
         "The coarse lump <b>over</b>estimates by "
         f"{수(_elmore(4)/(0.5*R_W*L_LONG*C_W*L_LONG),3)}×. Use the closed form for "
         "the distributed case and lumps only when the sections are real (a via, a "
         "branch, a tap)."),
    ]))

    c.날것(표("Lumping a distributed wire: how many sections are enough",
        ["Sections N", "Elmore delay", "Error vs. distributed RC/2"],
        [[str(n), _ps(_elmore(n)),
          수((_elmore(n) / (0.5 * R_W * L_LONG * C_W * L_LONG) - 1) * 100, 3, "%")]
         for n in (1, 2, 4, 8, 16, 32)]))

    c.날것(짚기("""Two facts hide in that table. First, <b>a single lump is 100 % wrong</b>
    — and a single lump is exactly what a naive spreadsheet does. Second, convergence is
    slow: even 8 sections is still 6 % high. This is why extraction tools do not lump
    at all; they solve the distributed network. Your hand estimate should use RC/2 and
    remember that it is a lower bound on what the extractor will report, because the
    extractor also sees coupling capacitance to neighbours."""))

    c.날것(개념(
        "Elmore delay",
        """<p>The first moment of the impulse response of an RC tree: for a node k,
        t<sub>k</sub> = Σ<sub>i</sub> R<sub>ik</sub>·C<sub>i</sub>, where R<sub>ik</sub>
        is the resistance shared by the path to node i and the path to node k. It is
        exact for a single RC, always an <b>upper bound</b> on the 50 % delay for an RC
        tree with a step input, and it ignores inductance entirely.</p>""",
        어디에="Clock-tree synthesis (balancing sinks), buffer and repeater insertion, "
             "and the delay model inside every placer's incremental timing engine — "
             "the placer cannot afford a full extraction per move.",
        언제="Whenever you need a delay that is monotone in the tree's structure and "
            "cheap to update. It is wrong by 10–30 % in absolute terms and right in "
            "its ordering, which is what an optimiser needs.",
        어떻게="Walk the tree from the driver; accumulate the shared resistance for "
             "each sink. Never use it to sign off timing — it is an optimisation "
             "objective, not a signoff model.",
        산업코드="""# Extraction produces this; you read it when a net is suspect.
# SPEF, standard parasitic exchange format, one net:
*D_NET net_dout_3 1.84e-01          $ total capacitance, pF
*CONN
*I u_fir/Z O *L 0 *D INVX4          $ driver
*I u_reg/D I *L 1.02e-03            $ receiver pin cap, pF
*CAP
1 net_dout_3:1 2.31e-02
2 net_dout_3:2 net_clk:7 4.10e-03   $ COUPLING to an aggressor -- not in your hand estimate
*RES
1 net_dout_3:1 net_dout_3:2 1.79e+01 $ ohms""",
        주의="""Elmore is an upper bound <i>for a step input</i>. Real inputs have finite
            slew, and for a fast input into a long wire the true 50 % delay can exceed
            it. The bound you rely on is not the bound you were taught if the slew is
            large — which is the next section."""))

    # ------------------------------------------------------------------
    c.절("T2.3 Logical effort — delay with the picoseconds factored out")

    c.글("""Sizing a chain of gates by RC arithmetic works and is miserable. Logical
    effort removes the process from the problem entirely, leaving a dimensionless
    expression you can optimise in your head, and it answers the two questions that
    actually come up: <i>how many stages</i>, and <i>how much bigger should each one
    be</i>.""")

    c.날것(유도("The normalised delay of one stage", [
        ("Write a gate's delay as d = (R<sub>gate</sub>·C<sub>out</sub>) + "
         "(R<sub>gate</sub>·C<sub>self</sub>).",
         "The output node carries the load <i>and</i> the gate's own drain "
         "capacitance; both are charged through the same resistance."),
        ("Divide through by τ = R<sub>inv</sub>C<sub>g</sub>.",
         "We choose to measure everything relative to the minimum inverter. Nothing "
         "is lost; the units are."),
        ("The first term becomes g·h: <b>logical effort</b> g = how much worse this "
         "topology is than an inverter at driving current, and <b>electrical effort</b> "
         "h = C<sub>out</sub>/C<sub>in</sub>.",
         "g depends only on topology (NAND2 = 4/3, NOR2 = 5/3, inverter = 1); h depends "
         "only on the ratio of load to input, so it is independent of absolute size."),
        ("The second term becomes p, the <b>parasitic delay</b> — the delay of the gate "
         "driving nothing.",
         "It scales with the gate's own diffusion, which grows with its width exactly "
         "as its drive does — so p is size-independent. p<sub>inv</sub> ≈ 1."),
        ("d = g·h + p.",
         "Two multiplications and an addition, and no process constant anywhere."),
        ("For a path of N stages, the total is minimised when every stage carries the "
         "<b>same</b> stage effort f = (G·B·H)<sup>1/N</sup>.",
         "Differentiate the sum with respect to each stage's size and set to zero; the "
         "symmetric solution falls out. G = Πg, H = C<sub>load</sub>/C<sub>in</sub>, "
         "and B accounts for branching off the path."),
    ]))

    c.날것(그림(sch.인버터사슬((1, 4, 16, 64)),
        "Four stages, each 4× the last. Equal stage effort is what makes the total "
        "minimal — not equal sizes, and not one huge final stage."))

    c.날것(예제(
        "Driving a 64× load: how many stages?",
        f"""A 1× inverter must drive a load of 64·C<sub>g</sub> (an on-chip bus with
        several receivers). Logical effort of an inverter chain is G = 1, no branching
        so B = 1, and H = 64, giving path effort F = 64.""",
        """Try each N, computing D = N·F<sup>1/N</sup> + N·p<sub>inv</sub>, and pick
        the smallest. The table below is computed, not recalled.""",
        f"""N = {최선N[0]} stages, with stage effort f = {수(64 ** (1.0/최선N[0]), 3)}
        and total delay {수(최선N[1], 4)}·τ = {_ps(최선N[1] * TAU)}. A single stage would
        take {_ps(_le사슬(64, 1) * TAU)} — <b>{수(_le사슬(64,1)/최선N[1], 3)}× slower</b>.""",
        """Reading the table's minimum as a sharp optimum. N = 3 and N = 4 differ by
        """ + 수((_le사슬(64, 4) / _le사슬(64, 3) - 1) * 100, 2, "%") + """ — inside the
        noise of any real p. Take the <i>cheaper</i> of the two, not the nominally
        faster one; the extra stage costs area, leakage and a slew you must then drive.""",
        덧=표("Stage count versus total delay for F = 64",
              ["Stages N", "Stage effort f", "Delay (τ)", "Delay"],
              [[str(N), 수(64 ** (1.0 / N), 3), 수(D, 4), _ps(D * TAU)]
               for N, D in 사슬])))

    c.날것(표("Logical effort of the cells you will actually instantiate",
        ["Gate", "g", "p (τ)", "Why g is what it is"],
        [["Inverter", "1", "1", "The reference"],
         ["NAND2", "4/3", "2", "Two series NMOS: each must be 2× wider for the same "
          "pull-down current, so the input cap rises to 4/3 per input"],
         ["NAND3", "5/3", "3", "Three in series — g grows linearly with stack depth"],
         ["NOR2", "5/3", "2", "Series PMOS, and PMOS is the weaker device; this is why "
          "<b>NOR is avoided in fast logic</b> and NAND is not"],
         ["NOR3", "7/3", "3", "Same reason, worse"],
         ["XOR2", "4", "4", "Both polarities of both inputs are needed internally"],
         ["MUX2", "2", "4", "Two transmission paths plus select drive"],
         ["Tri-state inverter", "2", "2", "The enable device is in series with the "
          "output — the classic bus driver"]]))

    c.날것(개념(
        "Logical effort, used as a design instrument",
        """<p>d = g·h + p. Total path delay D = Σ(g<sub>i</sub>h<sub>i</sub>) + Σp<sub>i</sub>,
        minimised at equal stage effort f = F<sup>1/N</sup>, with the practical rule that
        <b>f ≈ 4</b> (the true optimum for p<sub>inv</sub> = 1 is 3.6) and an extra stage
        is worth adding only while it removes more than p of delay.</p>""",
        어디에="Deciding how deep a pipeline stage can be before synthesis; choosing "
             "between a NAND-NAND and a NOR-NOR implementation; sizing a clock or "
             "reset distribution by hand; arguing with a synthesis result that looks "
             "wrong.",
        언제="At architecture time, and every time a tool's answer needs a sanity "
            "check. Synthesis does this internally but with a cost function that also "
            "weighs area and power, so its answer will differ — knowing the ideal tells "
            "you whether the difference is a trade or a mistake.",
        어떻게="Count G along the path, compute H from the real load, take F = G·B·H, "
             "then N ≈ log<sub>4</sub>F and f = F<sup>1/N</sup>. Work backwards from "
             "the load to size each stage: C<sub>in,i</sub> = g<sub>i</sub>·C<sub>out,i</sub>/f.",
        산업코드="""# The synthesis constraint that makes the tool solve the same problem.
# Without a real load and a real driver, the tool optimises a fiction.
set_load        0.064            [get_ports dout*]   ;# pF -- from the receiver's .lib
set_driving_cell -lib_cell INVX4 [get_ports din*]    ;# not an ideal source
set_max_transition 0.150 [current_design]            ;# ns -- bounds slew degradation
set_max_fanout    16     [current_design]
# And the one that is almost always missing on a first pass:
set_max_capacitance 0.200 [current_design]""",
        주의="""g is a property of the <i>topology</i>, not of the cell you picked from
            the library. A library's NAND2_X4 and NAND2_X1 have the same g; only C<sub>in</sub>
            differs. Engineers who 'fix timing' by swapping to a bigger cell without
            changing the stage count are changing h for the previous stage — they move
            the problem upstream, and on a long chain it comes back."""))

    # ------------------------------------------------------------------
    c.절("T2.4 Slew, and why a delay has two arguments")

    c.글("""Both models so far take one input: the load. Every real timing tool takes
    two, because the delay of a gate depends on how fast its <i>input</i> moved. A slow
    input keeps both transistors partially on, wastes current through the stack, and
    starts the output late. That is the single largest correction to everything above,
    and it is why a Liberty file holds a table rather than a formula.""")

    c.날것(정의("슬루 (slew / transition time)",
        "The time for a signal to cross between two defined fractions of V<sub>DD</sub>, "
        "conventionally 10 %–90 % or 30 %–70 %. <b>Which pair is a property of the "
        "library, and mixing libraries that use different pairs silently changes every "
        "delay in the design.</b>"))

    c.날것(정의("단락전류 (short-circuit current)",
        "During a transition both the pull-up and pull-down networks conduct "
        "simultaneously, shorting V<sub>DD</sub> to ground through the stack. The charge "
        "lost this way is proportional to the input transition time; at normal slews it "
        "is 5–15 % of switching energy, and at degraded slews it can exceed the useful "
        "switching energy."))

    c.날것(표("The same inverter, four different 'delays' — an NLDM slice",
        ["Input slew (ps)", "Load 4 fF", "Load 16 fF", "Load 64 fF"],
        [[수(s, 3), _ps(TAU * (0.5 + 4 / 1 * 0.25 + 0.20 * s * 1e-12 / TAU)),
          _ps(TAU * (0.5 + 16 / 1 * 0.25 + 0.22 * s * 1e-12 / TAU)),
          _ps(TAU * (0.5 + 64 / 1 * 0.25 + 0.25 * s * 1e-12 / TAU))]
         for s in (20, 60, 120, 240)]))

    c.날것(짚기("""That table is a model, not a measurement — the slew coefficients are
    illustrative. <b>Say so.</b> A real NLDM table is characterised by running SPICE at
    every grid point over the full corner set, typically 7×7 points per arc, per cell,
    per corner. What is real in the table is its shape: delay rises roughly linearly in
    load and roughly linearly in input slew, and <b>the slew term is not small</b> — at
    the light load it is the dominant term."""))

    c.날것(개념(
        "NLDM — the non-linear delay model, and what a tool actually reads",
        """<p>A Liberty (<code>.lib</code>) file gives, for each timing arc of each cell,
        two 2-D tables — one for delay and one for output slew — indexed by input
        transition time and total output capacitance. The tool bilinearly interpolates
        (and, at the edges, <b>extrapolates</b>) to get a number. Everything downstream —
        STA, synthesis cost, placement timing — is built on these tables.</p>
        <p>Its successor, CCS (composite current source), stores a current waveform
        rather than a scalar, which matters when the receiver's input capacitance is
        itself voltage-dependent or when the net's resistance is large enough that the
        driver and the net interact. For an IP deliverable, <b>state which model your
        numbers came from</b>; they are not interchangeable at the 5 % level.</p>""",
        어디에="Every delay number in synthesis, STA, and place-and-route. Also in the "
             "IP datasheet, indirectly: your F<sub>max</sub> is only meaningful with "
             "the library and corner named.",
        언제="You read a .lib directly in exactly two situations: when a path's reported "
            "delay makes no sense and you want to see whether the tool extrapolated off "
            "the table, and when you are asked to support a library you have never seen.",
        어떻게="Find the arc, read index_1 (input slew) and index_2 (load), and check "
             "that your operating point is <i>inside</i> both. Off-table extrapolation "
             "is the standard cause of 'the tool says it passes and silicon says it "
             "does not'.",
        산업코드="""/* Liberty, one arc of one cell -- this is what the tool reads. */
cell (INVX1) {
  area : 1.596 ;
  pin (A) { direction : input ;  capacitance : 1.02 ; }      /* fF */
  pin (Z) {
    direction : output ;
    function : "!A" ;
    max_capacitance : 64.0 ;
    timing () {
      related_pin : "A" ;
      timing_sense : negative_unate ;
      cell_fall (delay_7x7) {
        index_1 ("0.004, 0.012, 0.028, 0.060, 0.124, 0.252, 0.508");  /* input slew, ns */
        index_2 ("0.4, 1.6, 4.0, 8.8, 18.4, 37.6, 76.0");             /* load, fF */
        values ( "0.0091, 0.0142, 0.0241, 0.0431, 0.0812, 0.1574, 0.3098", \\
                 "0.0113, 0.0164, 0.0263, 0.0453, 0.0834, 0.1596, 0.3120", \\
                 /* ... five more rows, one per input slew ... */ );
      }
      fall_transition (delay_7x7) { /* the OUTPUT slew -- this feeds the next stage */ }
    }
  }
}""",
        주의="""Delay and output slew are two <i>separate</i> tables, and the output slew
            is the next stage's input slew. This is how one badly driven net poisons a
            whole path: each stage receives a worse slew, produces a worse slew, and the
            degradation compounds. <b><code>set_max_transition</code> exists to stop that
            compounding</b>, and a design with no max_transition constraint can meet
            setup in the report and fail in silicon."""))

    # ------------------------------------------------------------------
    c.절("T2.5 The wire, and the repeater that saves it")

    c.글("""Gate delay shrinks with each process node. Wire delay does not: r rises as
    wires get thinner, c stays roughly constant per micron, and the die does not shrink
    as fast as the transistors. Beyond a length that has been getting shorter every
    node, a wire dominates the path, and the fix is not a bigger driver — it is to stop
    the wire being long.""")

    c.날것(그림(sch.리피터삽입(),
        "A long wire, and the same wire cut into segments by repeaters. The quadratic "
        "term shrinks by N; the buffer delay grows by N."))

    최적목록 = [(k, min(range(1, 120), key=lambda h: _리피터(k, h))) for k in range(1, 13)]
    c.날것(그림(sch.곡선(
        [("total delay", [(k, _리피터(k, h) * 1e12) for k, h in 최적목록], "#c0392b")],
        가로="repeaters N", 세로="delay (ps)",
        표시=[(최적[1], 최적[0] * 1e12, f"N={최적[1]}")],
        가로눈금=[1, 4, 8, 12]),
        f"""The full sweep for a {수(L_LONG,4,'µm')} wire, each point at its own optimal
        repeater size. <b>The minimum is shallow</b> — N = 3, 4 and 5 are within
        {수((_리피터(5, 38) / 최적[0] - 1) * 100, 2, '%')} of each other — so take the one
        that routes."""))

    c.날것(유도("Where the optimum comes from, and a check on it", [
        ("Cut the wire into k segments, each driven by an inverter of size h.",
         "One repeater per segment; the last one drives the receiver."),
        ("Each segment costs 0.7·(R<sub>inv</sub>/h)(C<sub>w</sub>/k + h·C<sub>g</sub>) "
         "for the driver, 0.4·R<sub>s</sub>C<sub>s</sub> for the distributed wire, and "
         "0.7·R<sub>s</sub>·hC<sub>g</sub> for the far-end load.",
         "The 0.4 and 0.7 are the standard distributed-RC coefficients — 0.4 for a wire "
         "driving its own capacitance, 0.69 for a lumped load."),
        (f"Sweeping k and h numerically gives {_ps(최적[0])} at k = {최적[1]}, "
         f"h = {최적[2]}.",
         "Brute force over the whole grid — no assumption about the shape of the "
         "optimum."),
        (f"The closed forms k = √(0.4R<sub>w</sub>C<sub>w</sub> / 0.7R<sub>inv</sub>C<sub>g</sub>) "
         f"and h = √(R<sub>inv</sub>C<sub>w</sub> / R<sub>w</sub>C<sub>g</sub>) give "
         f"k = {수(k해,3)}, h = {수(h해,3)}.",
         "<b>Independent cross-check.</b> Two routes to the same answer, agreeing to "
         f"{수(abs(h해 - 최적[2]) / 최적[2] * 100, 2, '%')} in size. A single derivation "
         "that no one checked is how the wrong constant survives for years."),
        (f"Without repeaters, the same wire with its own best driver costs "
         f"{_ps(_리피터(1, 최적목록[0][1]))}.",
         f"So repeaters buy {수(_리피터(1, 최적목록[0][1]) / 최적[0], 3)}× here — "
         "<b>and that is the honest headline</b>, not a figure taken from the most "
         "favourable corner of the sweep."),
    ]))

    c.날것(개념(
        "Repeater insertion",
        f"""<p>Break a wire whose delay is quadratic in length into segments short enough
        that the quadratic term is comparable to a buffer delay. The optimum segment
        length is the one where <b>the wire's RC per segment equals the buffer's own
        delay</b>; past that, you are paying buffers to save nothing.</p>
        <p>For this process the crossover is around a wire of
        {수(L_LONG/최적[1], 3, 'µm')} — shorter than that and a repeater costs more than
        it saves.</p>""",
        어디에="Any net that leaves a block: block-to-block datapaths, clock spines, "
             "reset distribution, and the top-level assembly of an SoC where your IP's "
             "ports land.",
        언제="Decided in physical design, but <b>constrained in your deliverable</b>: if "
            "your IP's output has 200 ps of budget and the integrator's wire needs 300, "
            "the block fails through no fault of its RTL.",
        어떻게="Give the integrator a number, not a hope: state output delay, drive "
             "strength, and maximum load in the datasheet, and constrain both ends with "
             "set_output_delay / set_load. Then the repeater problem is theirs and is "
             "solvable.",
        산업코드="""# What the integrator must be told, and what you must constrain.
# In your IP's SDC (shipped with the deliverable):
create_clock -name clk -period 4.000 [get_ports clk]
set_output_delay -max 1.200 -clock clk [get_ports {dout[*] dvalid}]
set_input_delay  -max 1.000 -clock clk [get_ports {din[*] dvalid_i}]
set_load 0.064 [get_ports dout[*]]     ;# what we assumed -- say it in the datasheet
# And in DATASHEET.md, the line that prevents the support call:
#   Output timing assumes <= 64 fF load and <= 150 ps transition at the port.
#   Beyond that, insert a repeater; every 100 fF adds approximately 25 ps.""",
        주의="""Repeaters are inverting. An odd number of them flips the polarity of the
            net, and the fix — using buffers (two inverters) instead — costs more delay
            than the inverter chain. Tools handle this, but <b>hand-placed repeaters in a
            reset or scan-enable path are a classic bring-up bug</b>: the block resets on
            the wrong polarity at one corner only, because that corner is the one where
            the inserted pair was optimised away."""))

    # ------------------------------------------------------------------
    c.절("T2.6 From cells to a path: what STA actually adds up")

    c.글("""Static timing analysis does not simulate. It propagates two numbers through
    the graph — the earliest and latest time a signal can arrive — and compares them
    against what each endpoint requires. Everything above supplies one edge of that
    graph; this section is how the edges become a verdict.""")

    c.날것(유도("Setup and hold, as one inequality each", [
        ("A launching flop puts data out at t<sub>launch</sub> = T<sub>clk,launch</sub> "
         "+ t<sub>cq</sub>.",
         "The clock arrives at the launching flop at its own time — clock delay is not "
         "the same at both ends of a path."),
        ("It arrives at the capturing flop at t<sub>arrival</sub> = t<sub>launch</sub> "
         "+ t<sub>logic</sub>.",
         "t<sub>logic</sub> is everything this chapter has been computing."),
        ("The capture edge occurs at T<sub>clk,capture</sub> + T<sub>period</sub>, and "
         "the data must be stable t<sub>setup</sub> before it.",
         "That stability requirement is a property of the flop, characterised the same "
         "way as any other arc."),
        ("<b>Setup:</b> t<sub>arrival</sub> ≤ T<sub>capture</sub> + T − t<sub>setup</sub> "
         "− t<sub>uncertainty</sub>. Slack is the difference.",
         "Clock uncertainty absorbs jitter and the skew the tool cannot yet know "
         "(pre-CTS). Positive slack passes; negative fails."),
        ("<b>Hold:</b> the <i>fastest</i> path must not arrive before the same capture "
         "edge's hold window: t<sub>arrival,min</sub> ≥ T<sub>capture</sub> + "
         "t<sub>hold</sub>.",
         "<b>Hold has no T in it.</b> Slowing the clock does not fix a hold violation — "
         "this is the single most useful fact in the chapter for a first-time "
         "designer."),
    ]))

    c.날것(표("The four ways a path's numbers get worse than your estimate",
        ["Effect", "What it does", "Typical size", "Where it is set"],
        [["OCV / AOCV / POCV", "Derates cell and net delays differently on the launch "
          "and capture clock paths, because two identical cells on the same die are "
          "not identical", "3–10 % of the clock path", "set_timing_derate"],
         ["Clock uncertainty", "A flat subtraction standing in for jitter and, "
          "pre-CTS, for skew", "50–150 ps", "set_clock_uncertainty"],
         ["CPPR / CRPR", "<b>Gives back</b> the derate double-counted on the shared "
          "part of the launch and capture clock paths", "Recovers 10–50 ps", "on by "
          "default in signoff STA; often off in synthesis"],
         ["SI / crosstalk delay", "An aggressor switching the other way stretches your "
          "transition", "5–15 % on long parallel nets", "SI-aware STA with coupling "
          "from SPEF"]]))

    c.날것(개념(
        "Reading report_timing without being misled",
        """<p>A timing report is a ledger: clock path to the launch flop, cell and net
        delays along the data path, clock path to the capture flop, library setup, and
        the derates. <b>The one line that decides whether the report is meaningful is
        the corner and mode it was run in</b> — a report from the typical corner with
        ideal clocks is not evidence of anything.</p>""",
        어디에="Every timing signoff, every 'why is this failing' investigation, and "
             "every F<sub>max</sub> number you put in a datasheet.",
        언제="Read the whole path when slack is negative; read the <i>startpoint and "
            "endpoint</i> first when it is positive, to check that the tool timed the "
            "path you think it did. False paths and unconstrained endpoints show up "
            "here and nowhere else.",
        어떻게="Check: (1) is the endpoint a register, not a port; (2) is the clock real "
             "(propagated) or ideal; (3) what is the input transition at the worst cell "
             "— if it is at the end of the .lib index range, the number is extrapolated; "
             "(4) how much of the path is net delay. Above ~40 % net delay, the fix is "
             "placement, not logic.",
        산업코드="""# Startpoint: u_fir/acc_reg[7] (rising edge-triggered flip-flop clocked by clk)
# Endpoint:   u_fir/y_reg[15]   (rising edge-triggered flip-flop clocked by clk)
# Corner: ss_0p81v_125c    Check: setup   Path Group: clk
#   Point                                  Incr       Path
#   clock clk (rise edge)                  0.000      0.000
#   clock network delay (propagated)       0.412      0.412     <- real CTS, not ideal
#   u_fir/acc_reg[7]/CK (DFFX1)            0.000      0.412 r
#   u_fir/acc_reg[7]/Q (DFFX1)             0.138      0.550 f
#   u_fir/U231/Z (NAND2X2)                 0.061      0.611 r
#   u_fir/U248/Z (INVX4)                   0.029      0.640 f
#   net (fanout=6, length=214um)           0.087      0.727    <- 12% of the path is WIRE
#   u_fir/y_reg[15]/D (DFFX1)              0.000      0.727 f
#   data arrival time                                 0.727
#   clock clk (rise edge)                  4.000      4.000
#   clock network delay (propagated)       0.438      4.438
#   clock reconvergence pessimism          0.021      4.459    <- CPPR gives this back
#   library setup time                    -0.096      4.363
#   data required time                                4.363
#   slack (MET)                                       3.636""",
        주의="""<code>clock network delay (ideal)</code> in that report instead of
            <code>(propagated)</code> means no clock tree exists yet and the skew is a
            guess. Numbers from an ideal-clock report routinely improve by 200–400 ps at
            signoff — in the wrong direction. <b>Never put an ideal-clock F<sub>max</sub>
            in a datasheet.</b>"""))

    # ------------------------------------------------------------------
    c.절("T2.7 What to do with this on Monday")

    c.날것(쓰는자리([
        ["RC지연 · τ · FO4", "Any block, before RTL exists",
         "Whether the function fits in one cycle at the target frequency"],
        ["엘모어지연", "Clock tree, reset tree, long datapath nets",
         "Where a buffer must go, and which sink is the late one"],
        ["논리적노력", "Critical-path restructuring, pipeline depth",
         "Stage count and the size ratio between stages"],
        ["슬루 · NLDM", "Reading .lib, debugging an implausible delay",
         "Whether the tool interpolated or extrapolated your operating point"],
        ["배선지연 · 리피터", "Block boundaries and top-level assembly",
         "The output-load and transition limits you publish in the datasheet"],
        ["도착시각 · 요구시각 · 슬랙", "Every signoff",
         "Whether the number you are about to sell is real"]]))

    c.날것(사고(f"""This repository measured its own FIR filter at <b>455 MHz</b> and then
    at <b>{수(47.4,3,'MHz')}</b> — a factor of {수(455/47.4,3)} — from the same RTL. The
    difference was a timing shell. Without registers at the boundary, the tool reported
    the delay of a path from a pin to a pin, which is not a path that exists in a chip.
    Every number in this chapter is only as meaningful as the path it was measured on,
    and the cheapest way to be wrong by 10× is to time the wrong path."""))

    c.글("""The next chapter takes the one case this one cannot handle: what happens when
    the setup inequality is violated not by a slow path but because the data was never
    synchronous with the clock at all. The answer is not a longer delay but a
    probability, and it is the only timing quantity in this book that can never be made
    zero.""")

    return c.완성()
