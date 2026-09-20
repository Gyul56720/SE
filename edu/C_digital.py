# -*- coding: utf-8 -*-
"""Volume I, Part C -- Digital design: arithmetic, control, CDC, power, test."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line, poly


def _f_adder():
    b = []
    rows = [("Ripple carry", 0.10, "O(n)", "smallest"),
            ("Carry-skip", 0.30, "O(√n)", "small"),
            ("Carry-select", 0.55, "O(√n)", "medium"),
            ("Carry-lookahead", 0.72, "O(log n)", "large"),
            ("Kogge–Stone", 1.00, "O(log n)", "largest, most wires")]
    y = 30
    for name, spd, big, area in rows:
        w = int(300 * spd)
        b.append(f'<rect x="150" y="{y}" width="{w}" height="26" fill="#123f6d" '
                 f'opacity="0.75"/>')
        b.append(txt(144, y + 18, name, 9, "end"))
        b.append(txt(156 + w, y + 18, f"{big}   area: {area}", 9))
        y += 34
    b.append(txt(300, y + 24, "Same function. Five points on the area–delay curve.",
                 9, "middle", 'font-style="italic"'))
    return svg(620, y + 36, "".join(b))


def ch_arith():
    s = ['<h1 id="c1">C1. Arithmetic Units &mdash; The Core of Every Datapath</h1>']
    s.append("<h2>C1.1 Addition</h2>")
    s.append(fig(_f_adder(), "Adder architectures span an area&ndash;delay curve of "
                             "roughly an order of magnitude in each axis."))
    s.append(tab("Adder architectures",
        ["Architecture", "Delay", "Area", "Notes"],
        [["Ripple carry", "O(<i>n</i>)", "O(<i>n</i>)", "Baseline; fine for <i>n</i>&le;8 at low frequency"],
         ["Carry-skip", "O(&radic;<i>n</i>)", "O(<i>n</i>)", "Cheap improvement"],
         ["Carry-select", "O(&radic;<i>n</i>)", "~2&times;", "Duplicate blocks, select on carry"],
         ["Carry-lookahead", "O(log <i>n</i>)", "O(<i>n</i> log <i>n</i>)", "Classic"],
         ["<b>Kogge&ndash;Stone</b>", "O(log <i>n</i>)", "Large, heavy wiring",
          "Minimum depth; <b>wire-limited in practice</b>"],
         ["Brent&ndash;Kung", "O(log <i>n</i>)", "Fewer wires", "Depth 2log<i>n</i>; better area"],
         ["<b>Carry-save</b>", "O(1) per add", "O(<i>n</i>)",
          "<b>Does not propagate carry</b> &mdash; the key to fast multipliers and accumulators"]]))
    s.append("""<div class="ms"><b>Carry-save is the single most useful idea in this
    table.</b> A carry-save adder takes three operands and produces two (sum and carry
    vectors) in constant time, because no carry propagates. A chain of them accumulates
    many terms at constant delay per term, and only the <i>final</i> conversion to a
    normal binary number requires a carry-propagate adder. This is why multiplier trees,
    FIR accumulators, and MAC units are built as "compress many partial products with
    carry-save, then one fast adder at the end". <b>In an accumulation loop &mdash; the
    feedback path that limits every recursive filter &mdash; keeping the state in
    carry-save form removes the carry-propagate delay from the loop entirely.</b> That
    single transformation has rescued more timing-critical datapaths than any other.</div>""")

    s.append("<h2>C1.2 Multiplication</h2>")
    s.append(tab("Multiplier construction",
        ["Stage", "Technique", "Effect"],
        [["Partial product generation", "<b>Booth radix-4</b>",
          "Halves the number of partial products; needs 2's-complement handling"],
         ["", "Booth radix-8", "Fewer still, but needs a 3&times; multiple (extra adder)"],
         ["Reduction", "<b>Wallace tree</b>", "O(log <i>n</i>) depth, irregular layout"],
         ["", "<b>Dadda tree</b>", "Slightly fewer adders than Wallace"],
         ["", "Array", "Regular layout, O(<i>n</i>) depth"],
         ["Final add", "Fast carry-propagate adder", "Kogge&ndash;Stone or similar"],
         ["Whole unit", "Pipelining", "Cut the tree with registers to raise <i>f</i><sub>max</sub>"]]))
    s.append("""<div class="ms"><b>Constant multiplication is a different problem</b> and
    is worth separating in any specification. When one operand is a compile-time constant
    &mdash; filter coefficients, twiddle factors, scaling constants &mdash; the multiplier
    collapses into shifts and adds. Canonical signed digit (CSD) representation minimises
    the number of non-zero digits, and <b>multiple constant multiplication (MCM)</b>
    algorithms share sub-expressions across a whole coefficient set. For a 32-tap FIR with
    fixed coefficients this routinely gives a 3&ndash;5&times; area reduction over generic
    multipliers. The commercial point: <b>an IP that is parameterised for
    <i>run-time</i> coefficients cannot use this, so "programmable coefficients" is an
    expensive feature</b> that should be priced and specified as such, not thrown in
    because it seems flexible.</div>""")

    s.append("<h2>C1.3 Division, square root, and reciprocal</h2>")
    s.append(tab("Division approaches",
        ["Method", "Convergence", "Hardware", "Use"],
        [["Restoring / non-restoring", "1 bit per cycle", "Adder + shifter",
          "Small area, high latency"],
         ["<b>SRT</b> (radix-4/8)", "2&ndash;3 bits per cycle", "Lookup for quotient digit",
          "<b>Standard in FPUs</b>"],
         ["<b>Newton&ndash;Raphson</b>", "Quadratic (doubles digits)",
          "Multipliers", "Reuses the multiplier; good when one exists"],
         ["Goldschmidt", "Quadratic", "Multipliers", "Better pipelining than Newton"],
         ["<b>Reciprocal LUT + refine</b>", "&mdash;", "Small ROM + multiplier",
          "<b>The usual answer in DSP</b>"]]))
    s.append("""<div class="warn"><b>The most important division fact for an IP designer
    is architectural, not numerical: never put a divider in a feedback loop.</b> Its
    latency enters the loop directly and sets the initiation interval. The standard
    transformation is to compute a reciprocal <i>once</i> outside the loop and multiply
    inside it. The Cholesky decomposition is a textbook example &mdash; the diagonal
    reciprocal is formed once per column and the column is then scaled by multiplication,
    which is why the inner loop can be pipelined at II&nbsp;=&nbsp;1. This is also a
    place where the reference model and the RTL can legitimately differ: the model may
    divide, the RTL multiplies by a reciprocal, and the two agree only to within the
    reciprocal's rounding. <b>The specification must state which one is normative.</b></div>""")

    s.append("<h2>C1.4 Fixed-point and floating-point units</h2>")
    s.append(tab("Number format decisions",
        ["Format", "Range", "Hardware cost", "Where it belongs"],
        [["Fixed point Q<i>m</i>.<i>n</i>", "Limited, uniform", "Adder/multiplier only",
          "<b>Most DSP and comms datapaths</b>"],
         ["Block floating point", "Shared exponent per block", "Small extra",
          "FFT, where dynamic range grows predictably"],
         ["IEEE 754 binary32", "Wide", "Align, normalise, round &mdash; expensive",
          "Scientific, some solvers"],
         ["binary16 / bfloat16", "Wide, low precision", "Cheaper", "Neural inference"],
         ["<b>Integer with saturation</b>", "Limited, clamped", "Compare and clamp",
          "Where wrap would be catastrophic (LLRs, audio)"],
         ["Posit / logarithmic", "Tapered", "Unusual", "Research; rarely in shipped IP"]]))
    s.append("""<div class="ms"><b>Block floating point deserves more attention than it
    gets.</b> In an FFT the signal magnitude grows by up to a factor of two per stage. Full
    floating point is overkill; fixed point requires either wide words or per-stage
    scaling that loses SNR. Block floating point keeps one exponent per stage (or per
    block) and normalises once, recovering most of floating point's dynamic range at a
    small fraction of the cost. <b>For a modelling engineer this format is a trap</b>,
    because a naive floating-point reference model will not match the hardware's
    block-normalised behaviour bit for bit &mdash; the reference must model the
    normalisation decisions too. Specifying "bit-accurate reference model" without
    specifying the scaling policy produces months of false mismatches.</div>""")
    return "\n".join(s)


def ch_control():
    s = ['<h1 id="c2">C2. Control: State Machines, Pipelines and Flow Control</h1>']
    s.append("<h2>C2.1 FSM encoding</h2>")
    s.append(tab("State encodings",
        ["Encoding", "Registers", "Next-state logic", "When"],
        [["Binary", "log<sub>2</sub><i>N</i>", "Complex", "Many states, area critical"],
         ["Gray", "log<sub>2</sub><i>N</i>", "Complex",
          "<b>Adjacent states differ by one bit</b> &mdash; low power, safer across CDC"],
         ["<b>One-hot</b>", "<i>N</i>", "Simple (one AND per transition)",
          "<b>FPGA default</b>; fast; easy to check"],
         ["Johnson", "<i>N</i>/2", "Simple", "Counters, ring sequencers"],
         ["<b>Hamming-protected</b>", "&gt;log<sub>2</sub><i>N</i>", "&mdash;",
          "<b>Safety/security</b>: illegal states detectable"]]))
    s.append("""<div class="ms"><b>Security-grade FSM encoding</b> is a concrete example
    of a requirement that comes from a threat model rather than from function. If an
    attacker can flip a state bit with a laser or a voltage glitch, a binary-encoded FSM
    may land in a valid but wrong state &mdash; for instance skipping rounds of a cipher.
    Countermeasures are: sparse encodings with large Hamming distance so that a single
    flip lands in an illegal state; a default branch that raises an alarm rather than
    doing nothing; and <b>duplicated FSMs with complementary encodings</b> whose outputs
    must remain complementary. The last technique requires a synthesis barrier so the
    tool does not optimise the inverters away and merge the two copies &mdash; if it
    does, the redundancy disappears while <i>functional verification still passes</i>.
    That silent failure mode is the reason such designs contain explicit buffer
    primitives whose only purpose is to stop the optimiser.</div>""")

    s.append("<h2>C2.2 Pipelining and its hazards</h2>")
    s.append(tab("Pipeline transformations",
        ["Transformation", "What it does", "Cost", "Limit"],
        [["Pipelining", "Insert registers between logic stages", "Latency, area",
          "<b>Cannot cut a feedback loop</b>"],
         ["Retiming", "Move existing registers across logic", "None (if legal)",
          "Total registers on each loop is invariant"],
         ["<b>Loop unrolling</b>", "Process <i>k</i> iterations per cycle", "<i>k</i>&times; area",
          "The loop's critical path is divided by <i>k</i> only in the feedforward part"],
         ["<b>Speculation</b>", "Compute all outcomes, select afterwards",
          "Exponential in the number of speculated bits",
          "<b>Removes the decision from the loop</b>"],
         ["C-slow", "Interleave <i>k</i> independent streams", "Registers &times;<i>k</i>",
          "Needs <i>k</i> independent problems"],
         ["Algebraic transform", "Restructure the recurrence itself", "Design effort",
          "<b>The only way past a fundamental loop bound</b>"]]))
    s.append("""<div class="ms"><b>The iteration bound</b> is the hard limit that these
    transformations negotiate with. For a recursive system, the minimum achievable
    iteration period is
    <i>T</i><sub>&infin;</sub> = max<sub>loops</sub> (<i>t</i><sub>loop</sub>/<i>w</i><sub>loop</sub>),
    where <i>t</i><sub>loop</sub> is the total computation delay around a loop and
    <i>w</i><sub>loop</sub> the number of registers in it. Retiming and pipelining cannot
    beat it; only changing the recurrence can. Recognising this quantity turns a vague
    "we need more speed" into a specific question: <i>which loop, and can its algebra be
    rewritten?</i> Look-ahead transformation (computing two steps of a recurrence in one)
    doubles <i>w</i> and thereby halves <i>T</i><sub>&infin;</sub>, at the cost of more
    arithmetic. <b>This is the abstract form of the unrolled DFE, radix-4 Viterbi ACS,
    and reformulated Berlekamp&ndash;Massey &mdash; three blocks that look unrelated and
    are the same transformation.</b></div>""")

    s.append("<h2>C2.3 Flow control and backpressure</h2>")
    s.append(tab("Handshake styles",
        ["Style", "Signals", "Property", "Hazard"],
        [["Valid only", "<code>valid</code>", "Producer never stalls",
          "Consumer must always accept &mdash; needs guaranteed rate"],
         ["<b>Valid/Ready</b>", "<code>valid</code>, <code>ready</code>",
          "Full backpressure", "<b>Combinational loop if ready depends on valid</b>"],
         ["Credit-based", "credits returned", "Decouples latency from throughput",
          "Credit accounting bugs"],
         ["Req/Ack (4-phase)", "handshake pairs", "Async-safe", "Slow (two round trips)"]]))
    s.append("""<div class="warn"><b>The valid/ready combinational loop</b> is one of the
    most common integration failures in modular RTL. If module A's <code>ready</code>
    depends combinationally on its input <code>valid</code>, and module B's
    <code>valid</code> depends combinationally on its input <code>ready</code>, connecting
    them creates a zero-delay cycle. Each module is individually correct and passes its
    own tests. The standard remedies are a <i>skid buffer</i> (also called a spill
    register), which breaks the path at the cost of one register stage and one entry of
    buffering, or a rule that <code>ready</code> is registered. <b>An IP that documents
    which of its interfaces are combinationally coupled &mdash; and ships a skid buffer
    &mdash; saves its customers a week each.</b> This is exactly the kind of detail that
    distinguishes a product from a piece of code.</div>""")

    s.append("<h2>C2.4 Arbitration</h2>")
    s.append(tab("Arbiter types",
        ["Type", "Fairness", "Latency", "Use"],
        [["Fixed priority", "None (starvation possible)", "Lowest", "Strict QoS classes"],
         ["<b>Round robin</b>", "Fair", "Low", "General purpose"],
         ["Weighted round robin", "Proportional", "Low", "Mixed traffic classes"],
         ["Matrix / LRU", "Fair, true least-recently-used", "Higher", "Caches"],
         ["Lottery", "Statistical", "Low", "Rare"],
         ["Age-based", "Strict FIFO fairness", "Higher", "Avoids starvation strictly"]]))
    s.append("""<div class="ms">Arbitration is where <b>fairness and forward progress</b>
    become formal properties rather than intentions. A round-robin arbiter is fair by
    construction; a fixed-priority arbiter is not, and a low-priority requester can starve
    forever. Whether starvation matters is a system question &mdash; it is acceptable for
    a debug port, fatal for a DMA that feeds a real-time codec. Because starvation is a
    <i>liveness</i> property ("eventually granted") rather than a safety property, it is
    natural to express and prove with formal tools, and arbiters are one of the few places
    where formal verification is both easy and genuinely valuable. <b>Shipping a formally
    proven arbiter with its properties is a differentiator that costs a design house
    little.</b></div>""")
    return "\n".join(s)


def ch_cdc():
    s = ['<h1 id="c3">C3. Clock Domain Crossing, Reset and Low Power</h1>']
    s.append("<h2>C3.1 The CDC problem stated precisely</h2>")
    s.append("""<div class="bs">A signal crossing between unrelated clock domains
    violates setup or hold at the receiving flip-flop with non-zero probability. The
    flip-flop may enter a metastable state whose resolution time is unbounded (though
    exponentially unlikely to be long). <b>This cannot be simulated</b>: a logic
    simulator has no metastable value and will always resolve to 0 or 1.</div>""")
    s.append(tab("CDC techniques by payload type",
        ["Payload", "Technique", "Why", "Failure if misapplied"],
        [["<b>1-bit level</b>", "Two-flop synchroniser", "Allows a full cycle to resolve",
          "&mdash;"],
         ["<b>1-bit pulse</b>", "Toggle synchroniser (level convert, then edge detect)",
          "A pulse shorter than the destination period would be lost", "Lost events"],
         ["<b>Multi-bit, unrelated</b>", "Synchronise a request; use a data hold register",
          "Bits arriving in different cycles corrupt the value",
          "<b>Corrupted data words</b>"],
         ["<b>Multi-bit counter</b>", "Gray code", "Only one bit changes per increment",
          "Wrong pointer &rarr; FIFO corruption"],
         ["<b>Stream</b>", "Asynchronous FIFO (Gray pointers, dual-port RAM)",
          "Decouples rate and phase", "&mdash;"],
         ["<b>Bus transaction</b>", "Handshake (req/ack) or credit",
          "Explicit acknowledgement", "&mdash;"],
         ["<b>Reset</b>", "Asynchronous assert, synchronous de-assert",
          "De-assertion must not violate recovery/removal",
          "Part of the design leaves reset a cycle late"]]))
    s.append("""<div class="ms"><b>Why Gray coding a FIFO pointer is safe even though
    the pointer is multi-bit.</b> The synchroniser may sample a Gray pointer mid-transition,
    but since only one bit changes per increment, the sampled value is either the old or
    the new pointer &mdash; never a third value. An off-by-one pointer makes the FIFO
    report itself slightly <i>fuller</i> or <i>emptier</i> than it is, which is
    conservative: the FIFO may stall a cycle early but never overflows or underflows.
    <b>The design is safe because its error mode is biased in the harmless
    direction.</b> This principle &mdash; arrange for uncertainty to fail conservatively
    &mdash; generalises far beyond FIFOs and is one of the most transferable ideas in
    digital design.</div>""")

    s.append("<h2>C3.2 Reset architecture</h2>")
    s.append(tab("Reset strategies",
        ["Strategy", "Advantage", "Problem"],
        [["Synchronous", "No recovery/removal issue; clean STA",
          "<b>Needs a running clock</b> &mdash; fails at power-up"],
         ["Asynchronous", "Works without a clock", "De-assertion can violate recovery"],
         ["<b>Async assert, sync de-assert</b>", "Both advantages",
          "Requires a reset synchroniser per domain &mdash; <b>the standard solution</b>"],
         ["Reset-less registers", "Area and routing saving",
          "Must be provably initialised by data flow; a verification obligation"]]))
    s.append("""<div class="warn"><b>Reset de-assertion order is a specification item that
    is almost always omitted.</b> If two blocks leave reset in different cycles and one
    samples the other's outputs, the receiving block may latch garbage. Within a block the
    designer controls this; across an IP boundary the <i>customer</i> controls it, and
    they cannot get it right unless the datasheet states the requirement. A good IP
    datasheet specifies: the reset polarity, whether it is synchronous or asynchronous,
    the minimum assertion width in cycles of each clock, and any required ordering between
    multiple resets. <b>Omitting this produces intermittent bring-up failures that are
    blamed on the IP.</b></div>""")

    s.append("<h2>C3.3 Low power design</h2>")
    s.append(tab("Power reduction techniques by level",
        ["Level", "Technique", "Saving", "Verification burden"],
        [["RTL", "<b>Clock gating</b>", "Large (clock tree is 20&ndash;40% of dynamic power)",
          "Low &mdash; tools insert it automatically"],
         ["RTL", "Operand isolation / data gating", "Moderate", "Low"],
         ["RTL", "Reduce switching activity (encoding, bus inversion)", "Moderate", "Low"],
         ["Architecture", "Parallelism + voltage scaling",
          "<b>Large</b> &mdash; power &prop; <i>V</i><sup>2</sup>", "Moderate"],
         ["Architecture", "Memory hierarchy (avoid far accesses)", "Large", "Moderate"],
         ["Physical", "Multi-<i>V<sub>TH</sub></i> cells", "Leakage", "None"],
         ["System", "<b>Power gating</b>", "Leakage &rarr; ~0",
          "<b>High</b>: isolation, retention, wake sequencing"],
         ["System", "DVFS", "Large", "High: timing at every operating point"],
         ["System", "Multiple power domains", "Large", "<b>Highest</b>: UPF, isolation cells"]]))
    s.append("""<div class="ms"><b>Parallelism as a power technique</b> is the least
    intuitive entry and the most powerful. Two copies of a block running at half the clock
    frequency deliver the same throughput; because they now have twice the time budget,
    the supply voltage can be lowered until the slower path just meets timing. Dynamic
    power scales as <i>V</i><sup>2</sup><i>f</i>, so halving <i>f</i> and reducing
    <i>V</i> by, say, 30% gives roughly 0.5&nbsp;&times;&nbsp;0.49 = 0.25 of the original
    power, at the cost of about twice the area. <b>This trade &mdash; area for energy
    &mdash; is the fundamental reason accelerators are more efficient than processors</b>,
    and it is the argument an IP vendor uses when selling a block against a software
    implementation. State it with the exponents and it is persuasive; state it as "our
    block is more efficient" and it is not.</div>""")

    s.append("<h2>C3.4 Design for test</h2>")
    s.append(tab("DFT structures",
        ["Structure", "Tests what", "Cost", "IP implication"],
        [["<b>Scan chains</b>", "All flip-flops and combinational logic",
          "Mux in every FF (~5&ndash;10% area, some delay)",
          "<b>IP must be scan-insertable</b>: no gated clocks without test bypass, "
          "no latches, no async loops"],
         ["<b>MBIST</b>", "Embedded memories", "Controller per memory group",
          "Memory interfaces must be accessible"],
         ["BSD (JTAG 1149.1)", "Board-level interconnect", "Boundary cells", "&mdash;"],
         ["LBIST", "Logic, in-field", "PRPG + MISR", "Automotive/safety"],
         ["ATPG coverage", "&mdash;", "&mdash;", "<b>Stuck-at &gt;99%, transition &gt;90% typical targets</b>"],
         ["Test compression", "&mdash;", "Decompressor/compactor", "Reduces tester time and cost"]]))
    s.append("""<div class="warn"><b>Scan is a security hole.</b> A scan chain can read
    and write every flip-flop in the design, including key registers. Production chips
    must therefore disable scan after manufacturing test, typically by blowing a fuse or
    advancing a life-cycle state. A security IP that does not document its scan-isolation
    requirement will be integrated insecurely. <b>Conversely, an IP that cannot be scanned
    at all is unsellable</b>, because the customer cannot achieve their test coverage
    target. The resolution &mdash; scannable, but with key registers excluded from the
    chain or cleared on scan entry &mdash; must be designed in, and it is a requirement
    that comes from neither function nor timing.</div>""")
    return "\n".join(s)
