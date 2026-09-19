# -*- coding: utf-8 -*-
"""Volume I, Part B -- Devices, CMOS circuits, timing, power."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line, poly


def _f_inv():
    b = []
    b += [line(120, 25, 120, 55), txt(124, 22, "VDD", 9)]
    b.append(box(95, 55, 52, 34, "PMOS", None, 8))
    b.append(box(95, 111, 52, 34, "NMOS", None, 8))
    b += [line(120, 89, 120, 111), line(120, 145, 120, 175), txt(124, 190, "GND", 9)]
    b += [line(120, 100, 190, 100), arr(190, 100, 215, 100), txt(196, 92, "OUT", 9)]
    b += [arr(35, 100, 95, 100), txt(37, 92, "IN", 9), line(75, 72, 75, 128), line(75,100,95,100)]
    b += [line(215, 100, 215, 130), box(196, 130, 40, 22, "C_L", None, 8)]
    b.append(txt(300, 60, "t_pd ≈ 0.69 R_on C_L", 10))
    b.append(txt(300, 82, "R_on ∝ 1/(W/L) ⇒ bigger device, faster, more input cap", 9))
    b.append(txt(300, 104, "FO4 = delay driving four identical inverters", 9))
    b.append(txt(300, 126, "— the technology-independent speed unit", 9,
                 "start", 'font-style="italic"'))
    return svg(620, 200, "".join(b))


def _f_setup():
    b = []
    b.append(box(30, 55, 74, 40, "FF1", None, 9))
    b.append(box(200, 50, 120, 50, "combinational", None, 9))
    b.append(box(400, 55, 74, 40, "FF2", None, 9))
    b += [arr(104, 75, 200, 75), arr(320, 75, 400, 75)]
    b += [line(67, 120, 67, 140), line(437, 120, 437, 140), line(67, 140, 437, 140)]
    b += [line(252, 140, 252, 160), box(212, 160, 80, 24, "clock", None, 9)]
    b.append(txt(252, 30, "T_clk ≥ t_cq + t_logic + t_setup + t_skew", 11, "middle"))
    b.append(txt(252, 212, "Hold:  t_cq + t_logic,min ≥ t_hold + t_skew", 10, "middle"))
    b.append(txt(252, 234, "Setup fails ⇒ slow the clock. Hold fails ⇒ the chip is dead.",
                 9, "middle", 'font-style="italic"'))
    return svg(500, 246, "".join(b))


def ch_mos():
    s = ['<h1 id="b1">B1. The MOSFET &mdash; What a Digital Designer Must Know</h1>']
    s.append("""<p>A digital IP engineer does not size transistors, but every timing
    number, every power figure and several verification hazards trace back to device
    behaviour. This chapter keeps only what changes decisions.</p>""")

    s.append("<h2>B1.1 Regions of operation</h2>")
    s.append(tab("MOSFET regions",
        ["Region", "Condition", "Current", "Where it matters"],
        [["Cut-off", "<i>V<sub>GS</sub></i> &lt; <i>V<sub>TH</sub></i>",
          "<i>I</i><sub>sub</sub> &prop; e<sup>(V<sub>GS</sub>&minus;V<sub>TH</sub>)/nV<sub>T</sub></sup>",
          "<b>Subthreshold leakage</b> &mdash; the dominant static power term below 65 nm"],
         ["Triode / linear", "<i>V<sub>DS</sub></i> &lt; <i>V<sub>GS</sub></i>&minus;<i>V<sub>TH</sub></i>",
          "&mu;C<sub>ox</sub>(W/L)[(V<sub>GS</sub>&minus;V<sub>TH</sub>)V<sub>DS</sub> &minus; V<sub>DS</sub><sup>2</sup>/2]",
          "Switch resistance <i>R</i><sub>on</sub>; pass gates; the ON device of an inverter at end of transition"],
         ["Saturation", "<i>V<sub>DS</sub></i> &gt; <i>V<sub>GS</sub></i>&minus;<i>V<sub>TH</sub></i>",
          "&frac12;&mu;C<sub>ox</sub>(W/L)(V<sub>GS</sub>&minus;V<sub>TH</sub>)<sup>2</sup>(1+&lambda;V<sub>DS</sub>)",
          "Analogue gain stages; the beginning of a digital transition"],
         ["Velocity saturation", "Short channel, high field",
          "&prop; (V<sub>GS</sub>&minus;V<sub>TH</sub>)<sup>1</sup> &mdash; <b>linear, not square</b>",
          "<b>Modern nodes live here.</b> Textbook square-law intuition overestimates drive"]]))
    s.append("""<div class="ms">The last row is the single most important correction for
    anyone who learned the square law. In a short-channel device carriers reach their
    saturation velocity, so drive current becomes roughly proportional to overdrive
    rather than its square. Two practical consequences: <b>(i)</b> increasing supply
    voltage buys less speed than square-law intuition suggests, while dynamic power still
    rises as <i>V</i><sup>2</sup>, so voltage scaling is a poor speed lever; <b>(ii)</b>
    stacking devices (as in a NAND with many inputs) costs more than the naive series-resistance
    estimate, which is why wide fan-in gates are avoided and logic is restructured into
    trees. When a synthesis tool reports that a 4-input gate is slower than two 2-input
    gates in series, this is why.</div>""")

    s.append("<h2>B1.2 Threshold voltage and its enemies</h2>")
    s.append(tab("V<sub>TH</sub> modulation effects",
        ["Effect", "Mechanism", "Design consequence"],
        [["Body effect", "Source&ndash;bulk bias raises <i>V<sub>TH</sub></i>",
          "Stacked devices are slower than expected"],
         ["DIBL", "Drain field lowers the barrier",
          "<i>V<sub>TH</sub></i> falls with <i>V<sub>DS</sub></i> &rarr; more leakage"],
         ["Random dopant fluctuation", "Discrete dopant atoms",
          "&sigma;<sub>VTH</sub> &prop; 1/&radic;(<i>WL</i>) &mdash; <b>small devices mismatch more</b>"],
         ["Temperature", "&minus;1 to &minus;2 mV/K",
          "Hot chip is <i>faster</i> at low <i>V<sub>DD</sub></i> (temperature inversion)"],
         ["NBTI / PBTI ageing", "Trap generation under stress",
          "<b>|<i>V<sub>TH</sub></i>| drifts over years</b> &mdash; timing must include an ageing margin"],
         ["Multi-<i>V<sub>TH</sub></i> offering", "Process option",
          "LVT for critical paths, HVT elsewhere: the primary leakage-vs-speed lever"]]))
    s.append("""<div class="ms"><b>Temperature inversion is a verification trap.</b> At
    high supply voltage a chip is slowest when hot, so signing off at the high-temperature
    corner is conservative. At low supply voltage &mdash; which is where modern low-power
    modes operate &mdash; the <i>V<sub>TH</sub></i> reduction outweighs mobility
    degradation and the chip is slowest when <b>cold</b>. Teams that carried forward a
    "hot is worst case" habit have taped out parts that fail at &minus;40&nbsp;&deg;C.
    The corner list is not a formality; it is a statement about which physics dominates
    in the operating region you are selling into.</div>""")

    s.append("<h2>B1.3 Scaling and what it stopped giving</h2>")
    s.append(tab("Dennard scaling and its breakdown",
        ["Quantity", "Ideal scaling (factor <i>s</i>&gt;1)", "What actually happened"],
        [["Dimensions", "1/<i>s</i>", "Continued (with FinFET, GAA)"],
         ["Supply <i>V<sub>DD</sub></i>", "1/<i>s</i>",
          "<b>Stalled near 0.7&ndash;0.9 V</b> &mdash; <i>V<sub>TH</sub></i> cannot follow without leakage explosion"],
         ["Delay", "1/<i>s</i>", "Slower than ideal; interconnect does not scale"],
         ["Power density", "constant", "<b>Rose</b> &rarr; dark silicon, thermal limits"],
         ["Leakage", "negligible", "<b>Comparable to dynamic</b> below 65 nm"],
         ["Interconnect RC", "&mdash;", "<b>Worsens</b>: resistance rises as cross-section shrinks"]]))
    s.append("""<div class="ms">The end of Dennard scaling is the reason the industry
    turned to <b>specialised accelerators</b>, and therefore the reason the IP business
    grew. When a single general-purpose core could no longer be made faster within a
    power budget, the way to get performance became putting the right fixed-function
    block next to the processor. <b>Every FEC, crypto, codec and NPU IP sold today exists
    because of this graph.</b> Understanding it lets a design house argue its value
    proposition in the customer's own terms: not "our block is fast", but "your
    general-purpose alternative costs <i>x</i> times the energy per operation".</div>""")
    return "\n".join(s)


def ch_cmos():
    s = ['<h1 id="b2">B2. CMOS Logic, Delay and Power</h1>']
    s.append(fig(_f_inv(), "The inverter, and the delay model every timing number "
                           "ultimately rests on."))
    s.append("<h2>B2.1 Delay models</h2>")
    s.append(tab("Delay models by fidelity",
        ["Model", "Form", "Use"],
        [["RC (Elmore)", "<i>t<sub>pd</sub></i> = 0.69<i>R</i><sub>on</sub><i>C<sub>L</sub></i>",
          "Hand estimates, intuition"],
         ["<b>Logical effort</b>", "<i>d</i> = <i>gh</i> + <i>p</i>",
          "<b>Optimal gate sizing and stage count</b> without simulation"],
         ["NLDM (lookup)", "table over input slew &times; output load",
          "Standard-cell STA"],
         ["CCS / ECSM", "current-source model", "Advanced nodes, accurate slew propagation"],
         ["SPICE", "device equations", "Characterisation, critical custom paths"]]))
    s.append("""<div class="ms"><b>Logical effort is the one hand method worth
    memorising.</b> With <i>g</i> the logical effort of a gate (1 for an inverter, 4/3 for
    NAND2, 5/3 for NOR2), <i>h</i> the electrical effort (fanout), and <i>p</i> parasitic
    delay, the path delay is minimised when <b>every stage carries equal effort</b>
    <i>f</i> = (<i>GH</i>)<sup>1/<i>N</i></sup>, and the optimal per-stage effort is
    &asymp;&nbsp;3.6&nbsp;(&asymp;4 in practice, whence "fanout-of-4"). This yields the
    optimal number of stages <i>N</i> &asymp; log<sub>4</sub>(<i>GH</i>) directly.
    In an IP context it answers questions such as "how many buffer stages should the
    clock tree have?" or "is this 12-input decoder better as one stage or three?" before
    a single tool is run &mdash; which matters because those questions arise during
    architecture, when no netlist exists.</div>""")
    s.append("""<div class="ms"><b>FO4 as a unit.</b> Quoting delay in FO4 units makes a
    design comparable across processes: a 30-FO4 pipeline stage is 30 FO4 whether the
    node is 130 nm or 5 nm. A measured data point for calibration: in the open
    SkyWater 130 nm PDK, an inverter chain with <i>W<sub>p</sub></i>=2.0&nbsp;&mu;m,
    <i>W<sub>n</sub></i>=1.0&nbsp;&mu;m, <i>L</i>=0.15&nbsp;&mu;m and
    <i>C<sub>L</sub></i>=6&nbsp;fF gives <b>FO4 &asymp; 48 ps</b> (ngspice; stage delays
    47.5 and 44.5 ps, rise time 67.9 ps). That implies a practical ceiling near
    <b>1 GHz</b> for a ~20-FO4 pipeline stage in that process &mdash; which is the
    quantitative reason a 56 GBd analogue decision loop is impossible there, and why an
    open-PDK project must choose a digital, sub-rate architecture.</div>""")

    s.append("<h2>B2.2 Power</h2>")
    s.append("""<div class="math">P = &alpha;C V<sub>DD</sub><sup>2</sup> f
    &nbsp;+&nbsp; I<sub>SC</sub>V<sub>DD</sub> &nbsp;+&nbsp; I<sub>leak</sub>V<sub>DD</sub></div>""")
    s.append(tab("Power components and levers",
        ["Component", "Driver", "Lever", "Cost of the lever"],
        [["Dynamic (switching)", "&alpha;<i>CV</i><sup>2</sup><i>f</i>",
          "Clock gating; reduce &alpha; by data gating; lower <i>V<sub>DD</sub></i>",
          "Gating adds skew and verification states"],
         ["Short-circuit", "Both devices on during transition",
          "Sharp input slews", "Bigger drivers &rarr; more <i>C</i>"],
         ["Subthreshold leakage", "e<sup>&minus;V<sub>TH</sub>/nV<sub>T</sub></sup>",
          "HVT cells, power gating, body bias", "Slower; wake-up latency; state retention"],
         ["Gate leakage", "Tunnelling through oxide",
          "High-&kappa; dielectric", "Process choice, not design"],
         ["Glitch power", "Unbalanced arrival times",
          "<b>Balance logic depth</b>; pipeline", "Area, latency"]]))
    s.append("""<div class="ms"><b>Glitch power is an IP-level design decision that
    rarely appears in textbooks.</b> In an unbalanced arithmetic tree, a node can toggle
    several times before settling, and each toggle costs full switching energy. Ripple-carry
    adders and unbalanced multiplier trees are notorious. Balancing the tree &mdash; or
    inserting a pipeline register that stops glitch propagation &mdash; can reduce
    datapath power by tens of percent at no functional cost. Because glitching is
    invisible in RTL simulation (it appears only in gate-level simulation with timing),
    it is systematically underestimated during architecture. <b>A design house that
    reports power measured from a back-annotated gate-level run, with the customer's own
    data pattern, differentiates itself from one that reports a synthesis estimate.</b></div>""")

    s.append("<h2>B2.3 Logic families</h2>")
    s.append(tab("Logic styles",
        ["Style", "Principle", "Advantage", "Why it is rarely used in IP"],
        [["<b>Static CMOS</b>", "Complementary pull-up/down",
          "Robust, no clock, easy to verify", "&mdash; the default"],
         ["Transmission gate", "Pass logic", "Fewer devices for MUX/XOR",
          "Threshold loss, charge sharing"],
         ["Domino / dynamic", "Precharge then evaluate",
          "Fast, small", "<b>Noise-sensitive, needs custom timing</b>; not synthesisable"],
         ["Pass-transistor (CPL)", "&mdash;", "Compact XOR",
          "Level restoration needed"],
         ["Current-mode (CML/ECL)", "Differential current steering",
          "<b>Very high speed, constant current</b>", "Static power; used only in SerDes front ends"],
         ["Adiabatic", "Slow charge recovery", "Low energy", "Needs special clocks; niche"]]))
    s.append("""<div class="ms">A synthesisable IP is static CMOS by definition &mdash;
    everything else requires custom timing verification that a customer cannot repeat in
    their own flow. <b>This is a commercial constraint, not a technical preference.</b>
    The exception is the SerDes front end, where CML is unavoidable above a few GHz;
    that is precisely the part that is sold as a hard macro rather than RTL, and it is
    why the PMA/PCS boundary in a PHY falls where it does.</div>""")
    return "\n".join(s)


def ch_timing():
    s = ['<h1 id="b3">B3. Timing, Clocking and Static Timing Analysis</h1>']
    s.append(fig(_f_setup(), "The two timing constraints. Setup limits frequency; "
                             "hold limits correctness at any frequency."))
    s.append("<h2>B3.1 The two inequalities</h2>")
    s.append("""<div class="math">T<sub>clk</sub> &ge; t<sub>cq</sub> + t<sub>logic,max</sub>
    + t<sub>setup</sub> + t<sub>skew</sub> + t<sub>jitter</sub></div>
    <div class="math">t<sub>cq,min</sub> + t<sub>logic,min</sub> &ge; t<sub>hold</sub>
    + t<sub>skew</sub></div>""")
    s.append("""<div class="warn"><b>The asymmetry between the two is the single most
    important operational fact in digital timing.</b> A setup violation is fixed by
    lowering the clock frequency, so a chip that fails setup still works, just slower. A
    hold violation has no frequency term: the chip is <b>broken at every frequency</b>
    and the only remedy is a mask change. Consequently hold is fixed exhaustively before
    tape-out, by buffer insertion, while setup is traded against performance targets.
    In IP delivery this means the constraint file (SDC) you ship must make the customer's
    hold analysis possible &mdash; omitting clock definitions or false-path declarations
    can cause a customer to close hold on a path that does not exist, or worse, to miss
    one that does.</div>""")

    s.append("<h2>B3.2 Clock distribution</h2>")
    s.append(tab("Clock network structures",
        ["Structure", "Skew", "Power", "Use"],
        [["H-tree", "Low by symmetry", "High", "Regular arrays, large blocks"],
         ["Buffered tree (CTS)", "Tool-balanced", "Moderate", "<b>Standard ASIC flow</b>"],
         ["Mesh / grid", "Very low", "<b>Very high</b>", "High-performance CPUs"],
         ["Spine + local trees", "Moderate", "Moderate", "Common compromise"],
         ["<b>Useful skew</b>", "Deliberately non-zero", "&mdash;",
          "Borrow time from a fast stage to a slow one"]]))
    s.append("""<div class="ms"><b>Useful skew (clock borrowing)</b> is worth knowing
    because it turns a timing failure into a scheduling problem. If stage&nbsp;A has
    slack and stage&nbsp;B does not, delaying B's launch clock moves margin from A to B.
    The tool does this automatically, but the consequence for an IP vendor is subtle:
    <b>a block whose internal paths are already borrowing has little tolerance for the
    customer's clock tree</b>. Reporting timing with an assumed skew budget, and stating
    that budget explicitly in the datasheet, prevents the integration failure where the
    block meets timing in the vendor's flow and misses it in the customer's.</div>""")

    s.append("<h2>B3.3 What STA cannot see</h2>")
    s.append(tab("Limits of static timing analysis",
        ["Issue", "Why STA misses it", "What catches it"],
        [["False paths", "STA is structural, not functional",
          "Designer-declared exceptions &mdash; <b>and a wrong declaration hides a real path</b>"],
         ["Multicycle paths", "Same", "Declaration plus functional verification"],
         ["Asynchronous crossings", "No single clock relation",
          "<b>CDC static analysis</b>, not STA"],
         ["Metastability", "Probabilistic, not deterministic",
          "MTBF calculation; synchroniser depth"],
         ["Glitches", "STA reports arrival, not toggle count", "Gate-level power simulation"],
         ["Crosstalk-induced delay", "Depends on aggressor timing",
          "SI-aware STA (signal-integrity mode)"],
         ["IR drop", "Voltage assumed constant", "Power/IR co-analysis"],
         ["On-chip variation", "Single delay per cell",
          "OCV / AOCV / POCV derating"]]))
    s.append("""<div class="ms"><b>Exception declarations are the most dangerous artefact
    in a timing constraint file.</b> Each <code>set_false_path</code> removes a path from
    analysis; if the declaration is wrong, that path is simply never checked and the
    failure appears only in silicon. A mature IP deliverable therefore ships its SDC with
    a written justification for every exception, and ideally with an assertion or formal
    property that proves the path is genuinely unexercisable. <b>This is a place where a
    modelling engineer contributes directly: the argument that a path cannot be
    sensitised is a functional argument, and the person who wrote the reference model is
    usually the one who can make it.</b></div>""")

    s.append("<h2>B3.4 Metastability quantified</h2>")
    s.append("""<div class="math">MTBF = e<sup>t<sub>r</sub>/&tau;</sup> /
    (T<sub>0</sub> f<sub>clk</sub> f<sub>data</sub>)</div>""")
    s.append("""<div class="ms">The exponential in <i>t<sub>r</sub></i> (resolution time
    allowed) is why adding one synchroniser stage improves MTBF by orders of magnitude
    rather than by a factor of two. With typical 28 nm flip-flop parameters
    (&tau;&nbsp;&asymp;&nbsp;20&nbsp;ps), one extra stage at 1&nbsp;GHz multiplies MTBF
    by e<sup>1000/20</sup>&nbsp;=&nbsp;e<sup>50</sup> &mdash; an astronomically large
    factor. The corollary is that <b>two stages is almost always enough and three is
    almost always superstition</b>, except at very high clock rates where
    <i>t<sub>r</sub></i> per stage is small. Being able to compute this rather than
    follow a rule is what lets an IP vendor justify a latency budget to a customer who
    wants the crossing to be faster.</div>""")
    return "\n".join(s)


def ch_interconnect():
    s = ['<h1 id="b4">B4. Interconnect, Transmission Lines and Signal Integrity</h1>']
    s.append("""<p>Below roughly 250 nm, wires stopped being ideal connections and became
    circuit elements. Above a few GHz they stop being lumped elements and become
    transmission lines. Both transitions change what a designer must do.</p>""")

    s.append("<h2>B4.1 On-chip interconnect as distributed RC</h2>")
    s.append("""<div class="math">t<sub>delay</sub> &asymp; 0.38 R<sub>w</sub>C<sub>w</sub>L<sup>2</sup>
    &nbsp;&nbsp;(distributed RC line of length L)</div>""")
    s.append(tab("Interconnect scaling and its remedies",
        ["Problem", "Cause", "Remedy", "Cost"],
        [["Delay grows as <i>L</i><sup>2</sup>", "Distributed RC",
          "<b>Repeater insertion</b> &rarr; delay becomes linear in <i>L</i>",
          "Power and area; repeaters can be 30% of a large SoC's dynamic power"],
         ["Resistance rises with scaling", "Smaller cross-section, surface scattering",
          "Thicker upper metal layers for global routes", "Fewer routing tracks"],
         ["Coupling capacitance dominates", "Tall narrow wires, close spacing",
          "Increase spacing; shield with ground lines", "Routing area"],
         ["Electromigration", "Current density in narrow wires",
          "Width rules, current limits", "Area; constrains power grid design"],
         ["IR drop", "Resistance of the power grid",
          "Grid density, decoupling capacitance", "Metal resources"]]))
    s.append("""<div class="ms"><b>Optimal repeater insertion</b> follows from minimising
    the total delay of a line broken into <i>k</i> segments each driven by a repeater of
    size <i>h</i>. The classic result is that the optimum makes the repeater's intrinsic
    delay comparable to the wire segment delay, giving
    <i>k</i><sub>opt</sub> = <i>L</i>&radic;(<i>R<sub>w</sub>C<sub>w</sub></i>/(2<i>R</i><sub>0</sub><i>C</i><sub>0</sub>)).
    The practical consequence for an IP vendor is that <b>a block's timing cannot be
    guaranteed independent of its physical size</b>: a 2&nbsp;mm-wide block has internal
    wire delays that a synthesis-only estimate will miss entirely. This is why serious IP
    deliverables include a floorplan hint or a hardened layout, and why "it met timing in
    synthesis" is not a claim a customer will accept for a large block.</div>""")

    s.append("<h2>B4.2 When a wire becomes a transmission line</h2>")
    s.append("""<div class="bs">A connection must be treated as a transmission line when
    its electrical length is a significant fraction of the signal's wavelength &mdash; in
    practice when the propagation delay exceeds roughly one tenth of the signal rise time.
    Since <i>t<sub>r</sub></i> shrinks with every process generation, the threshold length
    keeps falling.</div>""")
    s.append("""<div class="math">Z<sub>0</sub> = &radic;(L/C) &nbsp;&nbsp;&nbsp;
    v<sub>p</sub> = 1/&radic;(LC) = c/&radic;&epsilon;<sub>r</sub> &nbsp;&nbsp;&nbsp;
    &Gamma; = (Z<sub>L</sub>&minus;Z<sub>0</sub>)/(Z<sub>L</sub>+Z<sub>0</sub>)</div>""")
    s.append(tab("Transmission-line effects in a link",
        ["Effect", "Physical cause", "Frequency behaviour", "Consequence"],
        [["Conductor (skin) loss", "Current crowds into a skin depth &delta;&prop;1/&radic;<i>f</i>",
          "&prop; &radic;<i>f</i>", "Dominant loss below ~20 GHz on PCB"],
         ["Dielectric loss", "tan&delta; of the substrate", "&prop; <i>f</i>",
          "Dominant at high frequency; chooses the laminate"],
         ["Reflections", "Impedance discontinuities (vias, connectors)",
          "Resonant dips", "Return loss; creates ISI that FFE cannot fully fix"],
         ["Crosstalk (NEXT/FEXT)", "Mutual L and C between traces",
          "Rises with <i>f</i>", "Limits lane density"],
         ["Fibre weave effect", "Inhomogeneous &epsilon;<sub>r</sub> of woven glass",
          "&mdash;", "Skew between differential pair halves"],
         ["Mode conversion", "Asymmetry in a differential pair", "&mdash;",
          "Differential energy becomes common mode &rarr; EMI"]]))
    s.append("""<div class="ms"><b>Why skin effect makes channel loss go as &radic;<i>f</i>
    and why that shapes the equaliser.</b> Skin depth &delta;&nbsp;=&nbsp;&radic;(2&rho;/&omega;&mu;)
    shrinks as 1/&radic;<i>f</i>, so the effective conductor cross-section shrinks and
    resistance rises as &radic;<i>f</i>. The resulting channel magnitude response is
    approximately exp(&minus;<i>k</i>&radic;<i>f</i>), which in the time domain produces a
    <b>long, slowly decaying pulse tail</b> rather than a sharp one. That specific tail
    shape is why decision-feedback equalisation works so well on wireline channels: the
    post-cursor ISI is long but the symbols causing it have already been decided, so they
    can be subtracted exactly without noise enhancement. <b>The physics of the conductor
    selects the equaliser architecture.</b> An engineer who knows only that "DFE cancels
    post-cursor ISI" cannot explain why a different channel &mdash; say a multipath radio
    channel with pre-cursor energy &mdash; needs a different structure.</div>""")

    s.append("<h2>B4.3 S-parameters</h2>")
    s.append(tab("Scattering parameters for a two-port",
        ["Parameter", "Meaning", "Specification name"],
        [["<i>S</i><sub>11</sub>", "Input reflection", "<b>Return loss</b> (dB, negative is good)"],
         ["<i>S</i><sub>21</sub>", "Forward transmission", "<b>Insertion loss</b>"],
         ["<i>S</i><sub>12</sub>", "Reverse transmission", "Isolation"],
         ["<i>S</i><sub>22</sub>", "Output reflection", "Output return loss"],
         ["<i>S<sub>dd</sub></i>, <i>S<sub>cc</sub></i>", "Differential / common mode",
          "Mixed-mode S-parameters"],
         ["<i>S<sub>cd</sub></i>, <i>S<sub>dc</sub></i>", "Mode conversion",
          "<b>Asymmetry metric</b> &mdash; an EMI predictor"]]))
    s.append("""<div class="ms">S-parameters are used because at high frequency you
    cannot measure voltage and current at a port without perturbing it, but you can
    measure incident and reflected power waves. For a modelling engineer the practical
    point is the <b>conversion to a time-domain model</b>: a channel is delivered as a
    Touchstone (<code>.s4p</code>) file, and a link simulation needs its pulse response.
    Doing that conversion correctly requires enforcing <b>causality and passivity</b> on
    measured data that generally violates both because of measurement noise and band
    limitation. Non-causal channel models produce link simulations that are optimistic in
    a way that is very hard to notice. <b>A channel-model conditioning tool is a small,
    genuinely sellable piece of software</b>, and it is squarely modelling-team work.</div>""")

    s.append("<h2>B4.4 Power delivery and simultaneous switching noise</h2>")
    s.append("""<div class="math">V<sub>noise</sub> = L<sub>package</sub> &middot; dI/dt
    &nbsp;+&nbsp; R<sub>grid</sub> &middot; I</div>""")
    s.append(tab("Power integrity mechanisms",
        ["Mechanism", "Where", "Mitigation"],
        [["Static IR drop", "On-chip grid resistance", "Grid density, more straps"],
         ["<b>d<i>I</i>/d<i>t</i> noise (SSN)</b>", "Package and board inductance",
          "Decoupling capacitance at three levels: on-die, package, board"],
         ["Resonance", "<i>L</i><sub>pkg</sub> with on-die <i>C</i>",
          "<b>Anti-resonance peak typically 50&ndash;200 MHz</b>; add damping"],
         ["Ground bounce", "Shared return inductance", "More ground pins, differential IO"],
         ["Supply-induced jitter", "<i>V<sub>DD</sub></i> modulates delay",
          "Regulate locally; use supply-insensitive delay cells in clock paths"]]))
    s.append("""<div class="ms">Supply-induced jitter is the mechanism by which a
    <i>digital</i> design decision damages an <i>analogue</i> specification. A large
    synchronous block that starts and stops &mdash; a clock-gated accelerator, a burst-mode
    FEC decoder &mdash; produces a current step at the burst rate, which modulates the
    supply, which modulates the delay of the PLL's delay cells, which appears as a
    spur in the phase noise, which appears as periodic jitter (PJ) in the link budget.
    <b>The FEC block is the root cause of a jitter specification failure</b>, and nothing
    in either block's own verification would reveal it. This class of cross-domain
    coupling is why chip-level power-aware simulation exists, and why an IP datasheet
    should state the block's <i>current profile</i>, not merely its average power.</div>""")
    return "\n".join(s)


def ch_analog():
    s = ['<h1 id="b5">B5. Analogue Building Blocks</h1>']
    s.append("""<p>A digital IP house does not design these, but it must model them,
    specify them, and understand which digital block can compensate which analogue
    imperfection &mdash; because that compensation is often the sellable part.</p>""")

    s.append("<h2>B5.1 Amplifiers</h2>")
    s.append(tab("Amplifier topologies",
        ["Topology", "Gain", "Bandwidth", "Where used"],
        [["Common source", "&minus;<i>g<sub>m</sub>r<sub>o</sub></i>", "Moderate", "Basic gain stage"],
         ["Cascode", "&minus;<i>g<sub>m</sub></i>(<i>g<sub>m</sub>r<sub>o</sub></i>)<i>r<sub>o</sub></i>",
          "High (reduced Miller)", "High-gain stages"],
         ["Differential pair", "&mdash;", "&mdash;",
          "<b>Rejects common-mode noise</b>; the basis of nearly everything"],
         ["Folded cascode", "High", "Good", "Wide input range op-amps"],
         ["Two-stage Miller", "Very high", "Compensated", "General-purpose op-amp"],
         ["<b>CTLE</b>", "peaked", "&mdash;",
          "Source degeneration creates a zero that boosts high frequency"],
         ["TIA", "&minus;<i>R<sub>f</sub></i>", "&mdash;", "Photodiode front end"]]))
    s.append("""<div class="ms"><b>Why a CTLE amplifies noise and an FFE does not have
    to.</b> A CTLE is a linear analogue filter placed <i>before</i> the point where noise
    is added by the rest of the receiver, but <i>after</i> the channel has already
    attenuated the signal and after thermal noise from the channel and the front end.
    Boosting high frequency therefore boosts the noise already present in that band by the
    same factor. A digital FFE placed after the ADC has exactly the same problem. A
    <b>DFE</b> escapes it because it subtracts a <i>decided</i> symbol &mdash; a noiseless
    quantity &mdash; rather than amplifying a received one. This is the whole reason
    receivers combine a modest CTLE with a DFE instead of using a large CTLE alone, and
    it is a piece of reasoning that a modelling engineer must be able to reproduce when
    asked to justify an architecture.</div>""")

    s.append("<h2>B5.2 Comparators and references</h2>")
    s.append(tab("Comparator and reference issues",
        ["Block", "Key imperfection", "Digital compensation"],
        [["Strong-arm latch", "Input-referred offset (mismatch)",
          "<b>Offset calibration DAC</b> trimmed digitally"],
         ["", "<b>Metastability</b> when inputs are close",
          "Allow regeneration time; detect and flag"],
         ["", "Kickback onto the input", "Sample-and-hold isolation"],
         ["Bandgap reference", "Curvature over temperature", "Piecewise digital trim"],
         ["", "Start-up failure mode", "Start-up circuit plus watchdog"],
         ["Current DAC", "Element mismatch", "<b>Dynamic element matching</b> (digital)"]]))
    s.append("""<div class="ms">Each row's right-hand column is a digital block with a
    clean specification, and that is the commercial observation: <b>the calibration and
    trim logic around an analogue block is frequently larger than the analogue block
    itself, and it is synthesisable</b>. A design house that cannot build a comparator can
    still own the offset-calibration engine, the DEM scrambler, and the background
    interleaving-mismatch corrector. These are sold as part of converter IP, and they are
    where the modelling effort concentrates because their correctness is statistical
    rather than logical.</div>""")

    s.append("<h2>B5.3 PLLs and clock generation</h2>")
    s.append("""<div class="math">H(s) = K<sub>PD</sub>K<sub>VCO</sub>F(s) /
    (s + K<sub>PD</sub>K<sub>VCO</sub>F(s)/N)</div>""")
    s.append(tab("PLL noise transfer",
        ["Noise source", "Transfer to output", "Design implication"],
        [["Reference noise", "<b>Low-pass</b> (&times;<i>N</i> in band)",
          "In-band noise is multiplied by 20 log<sub>10</sub><i>N</i>"],
         ["VCO noise", "<b>High-pass</b>", "Wide loop suppresses VCO noise"],
         ["Divider noise", "Low-pass", "&mdash;"],
         ["Charge-pump noise", "Low-pass", "Dominates in-band floor"],
         ["&Sigma;&Delta; quantisation (fractional-N)", "High-pass shaped",
          "<b>Loop must be narrow enough to filter it</b>"]]))
    s.append("""<div class="ms">The opposing shapes create the <b>optimal loop bandwidth</b>:
    wide enough to suppress VCO phase noise, narrow enough to suppress reference and
    fractional-<i>N</i> quantisation noise. The optimum is where the two contributions
    cross. This is a genuinely quantitative design decision that a system modeller can and
    should compute, and it is directly connected to the link jitter budget of
    Chapter A4 &mdash; the integrated phase noise becomes the RJ term that is multiplied
    by 14 at 10<sup>&minus;12</sup> BER. <b>Chapters A4, B4 and B5 are three views of the
    same budget</b>, and one of the marks of a senior engineer is holding them together.</div>""")

    s.append("<h2>B5.4 Data converters</h2>")
    s.append(tab("ADC architectures",
        ["Architecture", "Speed", "Resolution", "Principle", "Digital support needed"],
        [["Flash", "Highest", "&le;6 bit", "2<sup><i>N</i></sup>&minus;1 comparators",
          "Thermometer&rarr;binary, bubble correction"],
         ["<b>SAR</b>", "Moderate&ndash;high", "8&ndash;14 bit", "Binary search with a DAC",
          "<b>Redundancy and digital error correction</b>"],
         ["Pipeline", "High", "10&ndash;14 bit", "Stages with residue amplification",
          "Inter-stage gain calibration"],
         ["<b>&Sigma;&Delta;</b>", "Low&ndash;moderate", "16&ndash;24 bit",
          "Oversample and noise-shape", "<b>Decimation filter (CIC + FIR)</b>"],
         ["<b>Time-interleaved SAR</b>", "&gt;10 GS/s", "6&ndash;8 bit",
          "<i>M</i> SARs in parallel",
          "<b>Offset/gain/skew background calibration</b> &mdash; the 112G receiver case"],
         ["Folding/interpolating", "High", "8&ndash;10 bit", "Reduce comparator count", "&mdash;"]]))
    s.append("""<div class="ms"><b>&Sigma;&Delta; noise shaping</b> is worth stating
    exactly because it is the clearest example of trading bandwidth for resolution. An
    <i>L</i>th-order modulator with oversampling ratio OSR gives
    SNR gain &asymp; (6<i>L</i>+3)&nbsp;dB per doubling of OSR, versus 3&nbsp;dB for plain
    oversampling. The price is that the modulator output is a low-resolution, very fast
    stream that must be decimated &mdash; and <b>that decimation filter is a substantial
    digital IP block</b> whose passband ripple and stopband attenuation determine the
    converter's final specification. A converter vendor's datasheet number is in part a
    statement about a digital filter. This is the second time in this chapter that the
    saleable digital block sits next to an analogue one.</div>""")
    return "\n".join(s)
