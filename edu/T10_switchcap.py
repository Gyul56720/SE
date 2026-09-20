# -*- coding: utf-8 -*-
"""T10 -- Switched capacitors: trading bandwidth for accuracy, on purpose."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

k볼츠만 = 1.380649e-23
T상온 = 300.0


def _Req(C, fs):
    return 1.0 / (fs * C)


def _정착타우(N):
    """N 비트로 정착하는 데 필요한 시상수 개수."""
    return math.log(2 ** N)


def _최소이득(N, beta=1.0):
    """정적 이득 오차가 ½ LSB 를 안 넘게 하는 개루프 이득."""
    return 2 ** (N + 1) / beta


def _ktc(C):
    return math.sqrt(k볼츠만 * T상온 / C)


def ch_switchcap():
    c = 장(
        "T10", "Switched Capacitors — Accuracy Bought with Time",
        "A resistor whose value is a capacitor ratio and a clock. That one substitution "
        "is why precision analog survived the move to digital processes.",
        쓰는것=["전압", "전류", "전하", "저항", "주파수", "적분", "로그",
              "kTC잡음", "차지인젝션", "부트스트랩스위치", "표본화정리",
              "RC지연", "논리적노력", "정합", "INL", "DNL"],
        내놓는것=["등가저항", "두상클럭", "겹침없음", "바닥판표본화",
                "SC적분기", "되먹임계수", "정착시간", "유한이득오차",
                "상관이중표본화", "자동영점", "전하보존", "기생무감"],
        특허="""The switched-capacitor field is old and its basic circuits are long out
        of patent, but two families keep producing claims: <b>error-cancellation
        schemes</b> (correlated double sampling, auto-zeroing, chopper-stabilised
        amplifiers, and every variant that measures an error in one phase and subtracts
        it in the next) and <b>amplifier substitutes</b> — ring amplifiers, dynamic
        amplifiers, comparator-based switched capacitor circuits — whose whole point is
        that a modern process cannot build the high-gain op-amp the textbook assumes.
        Both families answer the same question: <i>what do you do when the op-amp is not
        good enough?</i>""")

    c.글("""A precision analog circuit needs an accurate coefficient, and in an
    integrated process there is exactly one accurate thing: the <b>ratio</b> of two
    identically drawn structures. Absolute resistance varies ±20 % over process;
    absolute capacitance likewise; but the ratio of two capacitors drawn side by side
    matches to a fraction of a per cent. Switched-capacitor technique is the discipline
    of expressing everything you need in terms of that ratio — and paying for it with
    sampling, and therefore with time.""")

    # ------------------------------------------------------------------
    c.절("T10.1 A resistor made of a capacitor and a clock")

    c.날것(유도("From charge transfer to an equivalent resistance", [
        ("Charge a capacitor C to V₁, then dump it onto a node at V₂. The charge moved "
         "is ΔQ = C(V₁ − V₂).",
         "This is the whole circuit: two switches and one capacitor, driven by "
         "non-overlapping clocks."),
        ("Repeat at f<sub>s</sub>. The average current is I = f<sub>s</sub>·C·(V₁ − V₂).",
         "Charge per cycle times cycles per second."),
        ("That is Ohm's law with R<sub>eq</sub> = 1/(f<sub>s</sub>C).",
         f"For C = {수(1,2,'pF')} and f<sub>s</sub> = {수(10,2,'MHz')}, "
         f"R<sub>eq</sub> = {수(_Req(1e-12,10e6)/1e3,4,'kΩ')} — a resistor that would "
         "be enormous in silicon, built from a capacitor that is not."),
        ("A time constant made this way is R<sub>eq</sub>C₂ = C₂/(f<sub>s</sub>C₁) — "
         "a <b>capacitor ratio divided by a clock frequency</b>.",
         "Absolute values cancel. The accuracy of the circuit is now the accuracy of a "
         "ratio (fractions of a per cent) and of a crystal (parts per million), instead "
         "of the accuracy of an absolute RC (tens of per cent)."),
    ]))

    c.날것(표("Equivalent resistance of a switched capacitor",
        ["C", "f_s", "R_eq", "Note"],
        [[수(1,2,"pF"), 수(10,2,"MHz"), 수(_Req(1e-12,10e6)/1e3,4,"kΩ"),
          "A poly resistor this size is hundreds of µm²"],
         [수(1,2,"pF"), 수(100,3,"MHz"), 수(_Req(1e-12,100e6)/1e3,4,"kΩ"), ""],
         [수(0.5,2,"pF"), 수(500,3,"MHz"), 수(_Req(0.5e-12,500e6)/1e3,4,"kΩ"),
          "At this rate the settling requirement below is the binding constraint"]]))

    c.날것(개념(
        "두 상 겹침 없는 클럭 (two-phase non-overlapping clocks)",
        """<p>The two switches must <b>never be on together</b>: if they are, the source
        and the destination are shorted and the transferred charge is wrong by an amount
        that depends on the overlap — which varies with process and temperature. The
        clocks are therefore generated with a deliberate dead time, typically from a
        cross-coupled NAND pair whose delay chains set the gap.</p>
        <p><b>Bottom-plate sampling</b> is the refinement that matters: open the switch
        connected to the <i>fixed</i> plate slightly first. That switch sees a constant
        voltage, so the charge it injects is constant and becomes an offset rather than
        signal-dependent distortion (T5's charge-injection problem, solved by
        sequencing instead of by circuitry).</p>""",
        어디에="Every switched-capacitor circuit: SC filters, SAR and pipeline ADC "
             "stages, sample-and-holds, reference buffers.",
        언제="Always. The dead time is not an optimisation — a design with overlapping "
            "phases fails at some corner, and it fails as a slow accuracy drift rather "
            "than as an obvious break.",
        어떻게="Generate the phases from one clock in a single cell, simulate the "
             "overlap at the fast corner (where it is smallest), and route the two "
             "phases together so they share delay variation.",
        산업코드="""// Two-phase non-overlapping clock. The feedback is what guarantees
// the gap: neither output can rise until the other has fallen.
module clk_2ph (input clk, output logic p1, p1d, p2, p2d);
    wire n1 = ~(clk    & p2);          // cross-coupled NAND pair
    wire n2 = ~((~clk) & p1);
    assign p1 = delay_chain(n1);       // the chain sets the dead time
    assign p2 = delay_chain(n2);
    assign p1d = delay_small(p1);      // 'delayed' phases for BOTTOM-PLATE sampling:
    assign p2d = delay_small(p2);      // the fixed-plate switch opens FIRST
endmodule
// Verify at the FAST corner -- that is where the dead time is smallest and
// where overlap, if it exists at all, appears.""",
        주의="""Simulating the phase generator alone proves nothing: the overlap that
            matters is at the <b>switches</b>, after routing, with their real loads. A
            layout that routes one phase across the chip and the other locally has
            already broken the guarantee that the schematic provides."""))

    # ------------------------------------------------------------------
    c.절("T10.2 What the amplifier must do in half a clock period")

    c.날것(유도("Two requirements on one op-amp, and why they fight", [
        ("In the transfer phase the amplifier must settle the output to within ½ LSB.",
         "Anything less and the charge did not fully move — an error that is "
         "<i>gain-like</i> and therefore shows up as INL, not as noise."),
        ("Settling is exponential, so reaching N-bit accuracy takes ln(2<sup>N</sup>) "
         "time constants.",
         f"{수(_정착타우(12),3)} time constants for 12 bits, "
         f"{수(_정착타우(16),3)} for 16 — <b>the requirement grows only logarithmically "
         "with resolution</b>, which is the good news."),
        ("The available time is half a clock period, so the closed-loop bandwidth must "
         "be at least ln(2<sup>N</sup>)/(π·T<sub>s</sub>) — and the open-loop unity-gain "
         "frequency is that divided by the feedback factor β.",
         "β is the fraction of the output fed back, typically 1/2 to 1/4 in a "
         "gain stage; a small β multiplies the requirement."),
        ("Separately, <b>static</b> accuracy needs loop gain: the residual error is "
         "1/(Aβ), so A must exceed 2<sup>N+1</sup>/β.",
         f"{수(20*math.log10(_최소이득(12)),3,'dB')} for 12 bits at β = 1, "
         f"{수(20*math.log10(_최소이득(16)),3,'dB')} for 16 — <b>and this grows "
         "exponentially with resolution</b>. This is the bad news, and it is why "
         "high-resolution SC design is hard in a process with low intrinsic gain."),
        ("Bandwidth wants a short channel and lots of current; gain wants a long "
         "channel and cascodes, which cost headroom.",
         "The two requirements pull in opposite directions in every process node, and "
         "the gap has widened with scaling — which is why calibration and "
         "error-cancellation now appear in designs that would once have used a better "
         "amplifier."),
    ]))

    c.날것(표("What the amplifier must deliver, per resolution",
        ["Bits", "Time constants to settle", "Minimum DC gain (β = 1)",
         "Minimum DC gain (β = ¼)"],
        [[str(N), 수(_정착타우(N), 3),
          수(20*math.log10(_최소이득(N)), 4, "dB"),
          수(20*math.log10(_최소이득(N, 0.25)), 4, "dB")]
         for N in (10, 12, 14, 16)]))

    c.날것(짚기(f"""Compare the two columns' growth. Going from 10 to 16 bits multiplies
    the settling requirement by {수(_정착타우(16)/_정착타우(10),3)} and the gain
    requirement by {수(_최소이득(16)/_최소이득(10),4)}. <b>Speed scales gently with
    resolution; static accuracy does not.</b> That asymmetry is the reason the
    high-resolution end of the market moved to architectures that <i>measure</i> the
    amplifier's shortfall and correct it digitally, rather than architectures that
    demand a better amplifier."""))

    c.날것(개념(
        "상관 이중 표본화 (correlated double sampling)",
        """<p>Sample the amplifier's error — its offset and its low-frequency (flicker)
        noise — in one phase, then subtract that sample during the signal phase. Because
        the error is correlated between the two closely spaced samples, the subtraction
        removes most of it.</p>
        <p>What it costs: the uncorrelated (thermal) noise of the two samples adds in
        power, so <b>broadband noise gets worse by √2</b> while offset and flicker get
        much better. It also folds noise from above the sampling rate into the band
        (T5), so the amplifier's bandwidth must be limited deliberately.</p>""",
        어디에="Precision SC gain stages, image-sensor readout (where it is universal), "
             "any circuit whose input is near DC and whose amplifier has a flicker "
             "problem (T4).",
        언제="When offset and 1/f dominate — which is to say, when the signal band "
            "reaches below the flicker corner.",
        어떻게="Add one phase and one capacitor. Then check the noise budget again: the "
             "√2 penalty on thermal noise may cancel the benefit if the design was "
             "already thermal-limited.",
        산업코드="""* The measurement that shows whether CDS helped -- run BOTH.
.noise v(out) VIN dec 20 1 100MEG      $ with CDS disabled
* ... then with CDS enabled, and compare the INTEGRATED noise over the signal band.
* Reporting only the 1/f improvement while the broadband floor rose by 3 dB is
* the kind of half-truth that gets found in the customer's lab.""",
        주의="""CDS removes what is <b>correlated between the two samples</b>. Noise at
            frequencies comparable to the sampling rate is not correlated and is not
            removed — it is aliased in. A design that samples the error long before it
            uses it has all of the cost and little of the benefit."""))

    # ------------------------------------------------------------------
    c.절("T10.3 Noise: you pay kT/C more than once")

    c.날것(표("kT/C in a two-phase circuit",
        ["C", "kT/C (one sample)", "Two phases (√2)", "Bits at 1 V FS"],
        [[수(Cv*1e12, 3, "pF"), 수(_ktc(Cv)*1e6, 3, "µV"),
          수(_ktc(Cv)*math.sqrt(2)*1e6, 3, "µV"),
          수((20*math.log10((1/(2*math.sqrt(2)))/(_ktc(Cv)*math.sqrt(2)))-1.76)/6.02, 3)]
         for Cv in (0.5e-12, 1e-12, 4e-12)]))

    c.날것(짚기("""A switched-capacitor stage samples at least twice per cycle — once on
    the input capacitor and once on the feedback capacitor — so the noise power adds.
    The <b>√2 is the minimum</b>; a pipeline stage with several capacitors and a
    reference path can easily reach 2×. Taking the single-sample kT/C from T4 and
    sizing to it is a factor-of-two error in noise power, which is half a bit — and
    half a bit is exactly the kind of shortfall that gets discovered after tape-out."""))

    # ------------------------------------------------------------------
    c.절("T10.4 What to do with this on Monday")

    c.날것(쓰는자리([
        ["등가저항", "Filter and bias design in a digital process",
         "Whether a resistor is needed at all"],
        ["두상클럭 · 바닥판표본화", "Every SC circuit, at schematic time",
         "Whether charge injection is an offset or a distortion"],
        ["정착시간 · 유한이득오차", "Op-amp specification",
         "Bandwidth and DC gain — and whether the process can supply the gain"],
        ["상관이중표본화 · 자동영점", "Near-DC precision paths",
         "Whether the flicker problem is solved in the circuit or in the architecture"],
        ["kTC잡음", "Capacitor sizing",
         "The factor of √2 that is missing from the textbook formula"]]))

    c.글(f"""The numbers to carry: reaching 16 bits needs
    {수(_정착타우(16),3)} settling time constants — only
    {수(_정착타우(16)/_정착타우(12),3)}× more than 12 bits — but
    {수(20*math.log10(_최소이득(16)),4,'dB')} of DC gain against
    {수(20*math.log10(_최소이득(12)),4,'dB')}, which is
    {수(_최소이득(16)/_최소이득(12),3)}× more. <b>Resolution is cheap in time and
    expensive in gain</b>, and every modern architecture in this space is an answer to
    that one sentence.""")

    c.글("""The next chapter takes the quantity all of these circuits assume they have —
    a stable bias current that does not move with supply or temperature — and shows what
    it costs to make one.""")

    return c.완성()
