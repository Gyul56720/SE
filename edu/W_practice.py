# -*- coding: utf-8 -*-
"""Volume III -- Industrial practice: the one-person design house."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line


def _f_flow():
    b = []
    st = ["Select", "Specify", "Golden model", "RTL", "Verify",
          "Synthesise", "Document", "Deliver"]
    x, y = 22, 32
    for i, n in enumerate(st):
        b.append(box(x, y, 118, 36, n, None, 9))
        if i % 4 != 3:
            b.append(arr(x+118, y+18, x+138, y+18))
        x += 138
        if i == 3:
            b += [arr(574, 50, 592, 50), line(592, 50, 592, 96),
                  line(592, 96, 22, 96), arr(22, 96, 22, 114)]
            x, y = 22, 114
    b += [line(300, 150, 300, 166, "3,3"), arr(300, 166, 80, 166),
          txt(440, 164, "mismatch ⇒ revise the SPEC, not just the RTL", 8)]
    b.append(txt(310, 192, "Each arrow is a gate with a written exit criterion",
                 9, "middle", 'font-style="italic"'))
    return svg(630, 204, "".join(b))


def ch_house():
    s = ['<h1 id="w1">W1. What a One-Person Design House Actually Sells</h1>']
    s.append("""<p>The central proposition of this volume is that a customer does not buy
    RTL. They buy <b>transferred risk</b>. A competent customer could usually write the
    block themselves; what they cannot cheaply produce is the evidence that it is correct,
    the documentation that makes it integrable, and a commitment to fix it when it is not.
    <b>Sellability is therefore a property of the evidence package, not of the code.</b>
    Everything in this volume follows from that.</p>""")

    s.append("<h2>W1.1 The deliverable set</h2>")
    s.append(tab("Minimum viable IP package",
        ["#", "Deliverable", "Content", "What its absence signals to a buyer"],
        [["1", "<b>Product brief</b> (2&ndash;4 pp)",
          "Function, performance, resources, interfaces, standards conformance",
          "Not a product"],
         ["2", "<b>User guide</b>",
          "Parameters and legal combinations, ports with timing diagrams, register map, "
          "integration procedure, reset and clocking requirements",
          "Integration will consume the vendor's time, not the customer's"],
         ["3", "<b>Synthesisable RTL</b>",
          "Parameterised, lint-clean, no tool-specific constructs",
          "&mdash;"],
         ["4", "<b>Reference model</b> (C/C++ or Python)",
          "Bit-accurate; usable in the customer's own environment",
          "The customer cannot verify integration independently"],
         ["5", "<b>Testbench and vectors</b>",
          "Self-checking, runnable on an open simulator if possible; standard vectors included",
          "No acceptance test is possible"],
         ["6", "<b>Verification report</b>",
          "Method, coverage achieved, tests passed, <b>known limitations</b>",
          "<b>The most common omission and the most revealing</b>"],
         ["7", "<b>Constraints (SDC) and synthesis scripts</b>",
          "Clock definitions, exceptions with justification, a reproduction recipe",
          "Customer cannot reproduce the timing claim"],
         ["8", "<b>PPA report</b>",
          "Area, frequency, power &mdash; with process, library, corner, utilisation stated",
          "The numbers are unusable"],
         ["9", "<b>Example design</b>",
          "Minimal system on a named FPGA board or simulation target",
          "Evaluation takes weeks instead of a day"],
         ["10", "<b>Release notes and versioning</b>",
          "Change history, compatibility policy", "No basis for a long-term commitment"],
         ["11", "<b>Licence and third-party notices</b>",
          "Scope of use, open-source bill of materials", "Blocked in legal review"],
         ["12", "IP-XACT metadata (recommended)",
          "Machine-readable ports, parameters, register map", "Manual integration"]]))
    s.append("""<div class="warn"><b>Stating known limitations increases the probability
    of a sale.</b> This is counter-intuitive and consistently true. The reviewer is an
    engineer who knows that every block has boundaries; a report without them reads as
    either incomplete verification or concealment. A limitation stated precisely &mdash;
    "throughput is guaranteed only when the sink asserts <code>ready</code> at least once
    every four cycles" &mdash; is information the integrator needs, and it demonstrates
    that the vendor has characterised their own block.</div>""")

    s.append("<h2>W1.2 Choosing the first product</h2>")
    s.append(tab("Suitability screen for a solo developer",
        ["Criterion", "Good", "Bad", "Reason"],
        [["Source of truth", "Public standard with test vectors",
          "Proprietary or informal", "A solo developer cannot arbitrate correctness"],
         ["Demand", "Mandated by a standard", "Nice to have",
          "The customer must <i>need</i> it, not merely like it"],
         ["Size", "One function, 3&ndash;5 kLOC", "Subsystem",
          "Verification volume scales superlinearly"],
         ["Domain", "Digital, process-independent", "Analogue/mixed-signal",
          "PDK, tools and measurement equipment are out of reach"],
         ["Interface", "One standard bus", "Custom protocol", "Reuse and integration"],
         ["Lifetime", "Consumer/datacentre", "Automotive/aerospace",
          "10&ndash;20 year support obligations"],
         ["Novelty", "<b>Well-understood algorithm</b>", "Novel algorithm",
          "<b>Proving novelty costs more than implementing it</b>"]]))
    s.append("""<div class="ms">The last row is the one most often got wrong by technical
    founders. An IP business sells power, performance, area, interfaces, verification and
    support &mdash; not algorithmic novelty. A well-known algorithm has an external
    oracle, comparable prior implementations to benchmark against, and a customer who
    already knows they need it. A novel algorithm has none of these, and the first
    question every customer asks ("how do I know it works?") has no cheap answer.
    <b>Existing implementations are an asset, not competition: they give you a baseline to
    quantify against.</b></div>""")

    s.append("<h2>W1.3 Licensing and contracts</h2>")
    s.append(tab("Licence structures",
        ["Model", "Mechanics", "Suits"],
        [["Per-design licence", "Fixed fee, one tape-out", "Most common; predictable for both sides"],
         ["Multi-use / site", "Fee for unlimited designs in a period", "Larger customers"],
         ["Royalty per unit", "Fee per shipped device", "High-volume; requires audit rights"],
         ["Hybrid", "Reduced up-front plus royalty", "Industry norm for significant IP"],
         ["Source vs obfuscated", "RTL source, encrypted RTL, or netlist",
          "<b>Source access materially increases price</b>"],
         ["Maintenance", "15&ndash;20% of licence per year",
          "<b>The recurring revenue that makes a solo practice viable</b>"]]))
    s.append(tab("Contract clauses that matter most to a solo vendor",
        ["Clause", "Position to take", "Why"],
        [["Scope of use", "Enumerate designs, derivatives, resale explicitly",
          "The most frequent source of dispute"],
         ["Acceptance criteria", "<b>Name the exact tests</b> that constitute acceptance",
          "Otherwise payment can be withheld indefinitely"],
         ["Warranty period", "Bounded (e.g. 12 months) defect correction", "Unbounded is uninsurable"],
         ["Limitation of liability", "<b>Cap at fees received</b>",
          "A consequential-damage claim on a tape-out would end a solo business"],
         ["IP indemnity", "<b>&lsquo;To the best of knowledge&rsquo;, capped</b>",
          "Unlimited patent indemnity is not survivable"],
         ["Third-party components", "Disclose the open-source bill of materials", "Legal review will ask"],
         ["Escrow", "Offer it", "Removes the &lsquo;what if you disappear&rsquo; objection cheaply"],
         ["Support response", "Define business-hours response, not resolution", "Resolution cannot be promised"]]))
    s.append("""<div class="ms"><b>The indemnity clause deserves specific preparation.</b>
    An unqualified promise that the IP infringes no patent exposes a one-person business
    to a liability unrelated to its size. The defensible position combines three things:
    a knowledge qualifier, a liability cap tied to fees received, and &mdash; crucially
    &mdash; <b>evidence that a search was actually performed</b>. A documented patent
    search, even a modest one, changes the character of any later dispute and is worth the
    few days it takes. Record the databases searched, the classification codes, the date,
    and the conclusions, exactly as you would record a verification campaign.</div>""")
    return "\n".join(s)


def ch_process():
    s = ['<h1 id="w2">W2. The Solo Process, Stage by Stage</h1>']
    s.append(fig(_f_flow(), "The development flow. What makes it a process rather than a "
                            "sequence of activities is that each arrow has a written exit "
                            "criterion."))
    s.append(tab("Stage gates",
        ["Stage", "Output", "Exit criterion (all must be true)"],
        [["<b>Select</b>", "Prior-art note",
          "A named standard mandates it &bull; prior implementations listed <b>by name and "
          "size</b> &bull; the specification text is obtainable &bull; a patent search has "
          "been performed and recorded"],
         ["<b>Specify</b>", "Specification document",
          "Every parameter has a range and legal-combination rules &bull; undefined "
          "behaviour is marked as such &bull; <b>word lengths, rounding, overflow policy "
          "and reset values are written down</b> &bull; reset and clocking requirements "
          "stated"],
         ["<b>Golden model</b>", "Reference model + self-tests",
          "Standard vectors pass &bull; <b>deliberate mutation of the model turns the "
          "tests red</b> &bull; the model is deterministic &bull; a second independent "
          "implementation or an external oracle agrees"],
         ["<b>RTL</b>", "Synthesisable RTL",
          "Lint clean &bull; no inferred latches &bull; CDC static analysis clean &bull; "
          "synthesises without warnings at the target frequency"],
         ["<b>Verify</b>", "Testbench, coverage, regression logs",
          "Zero mismatches against the model &bull; functional coverage goals met &bull; "
          "<b>no unexplained intermittent failures</b> &bull; mutation testing performed"],
         ["<b>Synthesise</b>", "PPA report",
          "Timing closed at the stated corner &bull; conditions fully documented"],
         ["<b>Document</b>", "The twelve deliverables",
          "No section empty &bull; the example design runs from a clean checkout"],
         ["<b>Deliver</b>", "Release", "Acceptance tests defined and demonstrated"]]))
    s.append("""<div class="ms"><b>The gate that solo developers skip is the third one:
    verifying the reference model.</b> Because the model defines correctness, there is a
    natural tendency to treat it as correct by definition. It is not, and an error there
    propagates into the RTL (which is written to match it) and into the testbench (which
    checks against it), so the regression is green and the silicon is wrong. The three
    cheap defences are standard vectors, a second independent implementation, and mutation
    testing of the model's own checks. <b>In a one-person operation, where independence
    between designer and modeller cannot be organisational, these substitutes are the only
    thing standing in for it.</b></div>""")

    s.append("<h2>W2.1 Specification: the parts that are always missing</h2>")
    s.append(tab("Specification checklist for numerical blocks",
        ["Item", "Question to answer explicitly"],
        [["Word lengths", "Every signal's Q format, including internal accumulators"],
         ["Rounding", "Truncate, round-half-up, or round-half-even &mdash; at every reduction point"],
         ["Overflow", "<b>Saturate or wrap</b>, per signal &mdash; they are not interchangeable"],
         ["Reset values", "What is every state element after reset"],
         ["Accumulation order", "Fixed or unspecified &mdash; it matters under saturation"],
         ["Latency", "Exact cycle count, and whether it is data-dependent"],
         ["Throughput", "Initiation interval and any conditions on backpressure"],
         ["Error behaviour", "What happens on illegal input &mdash; and is it flagged"],
         ["Undefined regions", "Marked as such, with the expectation that DV masks them"]]))
    s.append("""<div class="warn"><b>A measured illustration of why reset values belong in
    the specification.</b> In a feedback structure (DFE, IIR, accumulator), a mismatch in
    the initial register value causes the first outputs to differ, and the feedback carries
    the difference forward. In one measured comparison, 103 of 200 vectors mismatched;
    after aligning the model's and the RTL's reset value the count fell to 10, and the
    remaining ten had a separate cause. <b>Half the apparent failures were one unwritten
    specification line.</b> Debugging that without the specification costs days; writing
    it costs a sentence.</div>""")

    s.append("<h2>W2.2 Building the golden model</h2>")
    s.append(tab("Reference model construction rules",
        ["Rule", "Rationale"],
        [["<b>Do not use host arithmetic for fixed or floating point</b>",
          "Results become machine-dependent; use explicit integer or SoftFloat"],
         ["Hide state access behind accessors",
          "Allows the representation to change without touching every operation"],
         ["One file (or function) per operation where possible",
          "Extensions are additive; the Spike ISS is the model for this"],
         ["Make it fast", "It will run millions of times in regression"],
         ["Make it deterministic", "Seeded randomness only; no wall-clock, no hash order"],
         ["Emit a trace", "The DV team cannot compare what it cannot see"],
         ["<b>Annotate with specification section numbers</b>",
          "Three years later, this is the only record of why"],
         ["<b>Write tests that bite</b>",
          "Deliberately break the model and confirm the tests fail"]]))
    s.append("""<div class="ms"><b>A concrete pattern for &ldquo;tests that bite&rdquo;.</b>
    For an error-correcting decoder, a test that injects zero errors passes even if the
    decoder does nothing at all. The useful test injects <i>exactly</i> <i>t</i> errors and
    requires full correction, injects <i>t</i>+1 and requires that the original is
    <i>not</i> recovered, and separately counts detected failures versus mis-corrections.
    Then it breaks the decoder on purpose &mdash; forcing the syndrome to zero &mdash; and
    asserts that the first test now fails. A suite that does not contain that last step
    has never been tested itself.</div>""")

    s.append("<h2>W2.3 Parameterisation</h2>")
    s.append(tab("Parameter design rules",
        ["Rule", "Mechanism", "Effect"],
        [["Expose orthogonal axes only", "Design, not syntax", "Prevents combinatorial explosion"],
         ["Document legal combinations", "A table in the user guide", "Customer cannot guess"],
         ["<b>Enforce them at elaboration</b>",
          "<code>$error</code> inside <code>generate</code>; <code>static_assert</code> in C++",
          "<b>Illegal configurations fail to build rather than misbehave</b>"],
         ["Declare the verified set", "A table of tested combinations",
          "Honest scope statement; exhaustive testing is impossible"],
         ["Safe defaults", "Most conservative values", "Wrong usage degrades, not breaks"]]))
    s.append("""<div class="ms"><b>Elaboration-time enforcement is the cheapest quality
    feature available.</b> An illegal parameter combination that merely produces wrong
    behaviour will be discovered by the customer, late, and reported as a bug in your IP.
    The same combination rejected with a clear message at elaboration costs the customer
    five minutes. The difference in support burden over a product's life is large, and it
    requires perhaps twenty lines of code.</div>""")
    return "\n".join(s)


def ch_auto():
    s = ['<h1 id="w3">W3. Automation: Running Verification Around the Clock</h1>']
    s.append("""<p>A solo developer cannot out-work a verification team, but can
    out-schedule one: machines run while people sleep. The objective is a loop that,
    unattended, generates stimulus, compares against the golden model, classifies
    failures, and leaves a prioritised queue for the morning.</p>""")

    s.append("<h2>W3.1 The continuous verification loop</h2>")
    s.append(tab("Loop stages",
        ["Stage", "Action", "Requirement"],
        [["1. Generate", "Random parameters and stimulus from declared legal ranges",
          "Seeds recorded"],
         ["2. Run model", "Reference model produces expected output", "Fast and deterministic"],
         ["3. Run RTL", "Open-source simulator (Verilator/Icarus) or vendor tool",
          "Scriptable, headless"],
         ["4. Compare", "Scoreboard with the correct ordering semantics", "See H1.4"],
         ["5. Classify", "Group failures by signature", "Automated triage"],
         ["6. Minimise", "<b>Shrink a failing case to a minimal reproducer</b>",
          "The single highest-value automation step"],
         ["7. Report", "Ranked queue with reproduction commands", "&mdash;"],
         ["8. Coverage", "Accumulate and identify gaps", "Feeds back into stage 1"]]))
    s.append("""<div class="ms"><b>Stage 6 is where automation earns its keep.</b> A
    randomly generated failing case may be thousands of transactions long; a human cannot
    read it. Delta-debugging &mdash; repeatedly removing parts of the stimulus and
    re-running to see whether the failure persists &mdash; typically reduces such a case to
    a handful of transactions in a few minutes of machine time. The engineer then arrives
    to a minimal reproducer rather than a log file. <b>This is the difference between an
    overnight run that produces work and one that produces guilt.</b></div>""")

    s.append("<h2>W3.2 Where AI helps and where it must not be trusted</h2>")
    s.append(tab("Machine assistance in an IP flow",
        ["Task", "Suitability", "Condition"],
        [["Writing testbench boilerplate", "<b>High</b>", "Reviewed; it is code like any other"],
         ["Generating directed tests from a specification table",
          "<b>High</b>", "The table is the source of truth, not the model"],
         ["Triage and clustering of failures", "<b>High</b>", "Statistical, low risk"],
         ["Test case minimisation", "<b>High</b>", "Mechanical; verifiable by re-running"],
         ["Documentation drafting", "Moderate", "Every number must be regenerated from data"],
         ["Suggesting RTL fixes", "Moderate", "<b>Must be re-verified from scratch</b>"],
         ["Writing the reference model", "<b>Low</b>",
          "<b>It would share the same misreading as generated RTL &mdash; independence is lost</b>"],
         ["Judging whether coverage is sufficient", "<b>Low</b>", "Requires domain judgement"],
         ["Deciding that an intermittent failure is benign", "<b>None</b>",
          "This is the judgement that must never be delegated"]]))
    s.append("""<div class="warn"><b>The independence argument constrains automation more
    than capability does.</b> Verification works because two implementations were derived
    separately. If the same tool writes the model and the RTL from the same prompt, the
    two share every misunderstanding and the regression proves only internal consistency.
    Automation is therefore safest on the <i>mechanical</i> parts of the loop &mdash;
    generation, execution, comparison, minimisation, reporting &mdash; and least safe on
    the parts that define what correct means. <b>Automate the pipeline; keep the oracle
    human or standards-derived.</b></div>""")

    s.append("<h2>W3.3 Infrastructure a solo practice needs</h2>")
    s.append(tab("Toolchain",
        ["Function", "Open-source option", "Note"],
        [["RTL simulation", "<b>Verilator</b> (cycle-based), Icarus Verilog (event)",
          "Verilator is fast enough for overnight regressions"],
         ["Testbench", "<b>cocotb</b> (Python) or plain SystemVerilog",
          "cocotb lets the golden model and testbench share a language"],
         ["Formal", "SymbiYosys / Yosys", "Sufficient for arbiters, FIFOs, protocol properties"],
         ["Synthesis (estimation)", "Yosys + an open PDK",
          "<b>Relative</b> area/timing trends, not sign-off numbers"],
         ["Lint", "Verilator <code>--lint-only</code>, Verible", "&mdash;"],
         ["Coverage", "Verilator coverage, simulator built-ins", "&mdash;"],
         ["Waveforms", "GTKWave, Surfer", "&mdash;"],
         ["CI", "Any runner", "<b>The regression must run on a clean checkout</b>"],
         ["Documentation", "Generated from the same source as the RTL", "See W2.3"]]))
    s.append("""<div class="ms"><b>On open-source synthesis results: report trends, not
    absolutes.</b> Yosys with an open PDK will not reproduce a commercial tool's area or
    frequency, and quoting its numbers as a specification invites embarrassment. What it
    <i>does</i> reliably show is <i>relative</i> behaviour &mdash; that configuration B is
    40% larger than A, that removing a pipeline stage raises the critical path by 30%.
    Those comparisons are legitimate, useful during architecture, and free. <b>State the
    tool and PDK next to every number and the report stays honest.</b></div>""")
    return "\n".join(s)


def ch_labs():
    s = ['<h1 id="w4">W4. Worked Exercises</h1>']
    s.append("""<p>Each exercise below is a self-contained project that can be completed
    with open tools and produces an artefact of the kind described in W1. They are ordered
    so that each reuses the infrastructure built by the previous one.</p>""")

    s.append("<h2>Exercise 1 &mdash; A verified GF(2<sup>m</sup>) arithmetic library</h2>")
    s.append(tab("Exercise 1",
        ["Element", "Specification"],
        [["Objective", "Parameterised finite-field arithmetic in software, with a test "
          "suite that verifies the <i>field axioms</i> rather than sample values"],
         ["Deliverable", "Library, test suite, short note on the primitive-polynomial requirement"],
         ["Key decisions", "Log/antilog tables versus direct reduction; whether the "
          "polynomial is a parameter or a constant"],
         ["<b>Tests that bite</b>",
          "Every non-zero element has an inverse and <i>a</i>&middot;<i>a</i><sup>&minus;1</sup>=1; "
          "the exponent table is a bijection onto the non-zero elements; a "
          "<b>non-primitive polynomial is rejected</b> rather than silently accepted; "
          "corrupting the multiply makes the axiom tests fail"],
         ["Why it matters", "Every code and cipher block rests on this. A silent error "
          "here is invisible everywhere above it"]]))
    s.append("""<div class="ms"><b>The non-primitive-polynomial test is the instructive
    one.</b> An irreducible polynomial that is not primitive still defines a field, but
    &alpha;&nbsp;=&nbsp;<i>x</i> no longer generates the whole multiplicative group, so a
    log/antilog implementation built on it is wrong &mdash; and wrong in a way that
    ordinary arithmetic tests may not reveal, because most products are still correct.
    The defence is to verify at construction that the powers of &alpha; enumerate all
    2<sup><i>m</i></sup>&minus;1 non-zero elements, and to refuse otherwise. <b>A library
    that validates its own parameters is the difference between a component and a
    hazard.</b></div>""")

    s.append("<h2>Exercise 2 &mdash; Reed&ndash;Solomon encoder and decoder (model)</h2>")
    s.append(tab("Exercise 2",
        ["Element", "Specification"],
        [["Objective", "RS(<i>n</i>,<i>k</i>) over the library from Exercise 1: systematic "
          "encoder, syndrome/BM/Chien/Forney decoder"],
         ["Parameters", "<i>n</i>, <i>k</i>, first consecutive root &mdash; all arguments, "
          "because the standard's values may not yet be confirmed"],
         ["<b>Tests that bite</b>",
          "Encoder output has zero syndrome; <b>exactly <i>t</i> errors are always "
          "corrected with zero mis-corrections</b>; <b><i>t</i>+1 errors are never "
          "recovered</b>, and the detected-versus-mis-corrected split is counted rather "
          "than assumed; a test with zero injected errors is explicitly flagged as "
          "meaningless; forcing the syndrome to zero makes the suite fail"],
         ["Honest reporting", "Do not claim that all errors beyond <i>t</i> are detected. "
          "Measure the mis-correction rate and state it"]]))
    s.append("""<div class="ms"><b>Parameterising the unknown constants is the
    professional move here.</b> When the standard's field polynomial and first-root index
    have not been confirmed from the specification text, hard-coding a plausible value
    creates a model that is confidently wrong. Making them arguments, defaulting to a
    documented guess, and marking the guess as unverified in the code keeps the work
    moving without creating a false record. <b>The tests verify <i>properties</i> &mdash;
    <i>t</i> corrected, <i>t</i>+1 not recovered &mdash; which hold for any legal
    parameter choice, so they remain valid when the constants are later confirmed.</b></div>""")

    s.append("<h2>Exercise 3 &mdash; RTL and co-simulation</h2>")
    s.append(tab("Exercise 3",
        ["Element", "Specification"],
        [["Objective", "Synthesisable RTL for the Exercise 2 decoder's syndrome stage, "
          "co-simulated against the model"],
         ["Method", "DPI-C or cocotb; random vectors; seeds recorded"],
         ["<b>Tests that bite</b>",
          "Break the RTL deliberately and confirm the comparison fails; break the "
          "<i>model</i> deliberately and confirm it also fails &mdash; a harness that has "
          "only ever seen a correct design has not been tested"],
         ["Extension", "Sweep the parallelism parameter and plot cells versus throughput "
          "with Yosys; report the trend, not absolute area"]]))

    s.append("<h2>Exercise 4 &mdash; Fixed-point conversion</h2>")
    s.append(tab("Exercise 4",
        ["Element", "Specification"],
        [["Objective", "Convert a floating-point reference to fixed point and find the "
          "minimum word length meeting an accuracy target"],
         ["Method", "Sweep integer and fractional bits; measure the metric that matters "
          "(BER, SNR, residual) rather than raw error"],
         ["<b>Required experiments</b>",
          "Saturation versus wrap-around at each width; rounding mode comparison; "
          "<b>reset-value alignment between model and RTL</b>"],
         ["Expected finding",
          "The correct overflow policy is block-dependent: a CIC needs wrap, an LLR-based "
          "decoder needs saturation. <b>Reproduce both results</b> rather than accepting "
          "the claim"]]))
    s.append("""<div class="warn"><b>Check the operating point before believing any
    fixed-point result.</b> If the floating-point baseline is already failing &mdash; BER
    near 0.5, a decoder not converging, a sampling phase misaligned &mdash; then every
    quantisation comparison made on top of it is meaningless, and the numbers will look
    plausible. The discipline is to sweep first for a healthy operating point, assert that
    the baseline metric lies in a sensible range, and only then vary word length. An
    assertion such as <code>0.02 &lt; BLER &lt; 0.6</code> in the test harness makes this
    automatic.</div>""")

    s.append("<h2>Exercise 5 &mdash; A complete deliverable package</h2>")
    s.append(tab("Exercise 5",
        ["Element", "Specification"],
        [["Objective", "Assemble the twelve deliverables of W1.1 for the Exercise 3 block"],
         ["Hardest parts", "The verification report's <i>known limitations</i> section; "
          "the PPA report's <i>conditions</i>; the example design that runs from a clean "
          "checkout"],
         ["Self-test", "Hand the package to someone else and ask them to integrate it "
          "without speaking to you. <b>Every question they ask is a documentation defect</b>"],
         ["Outcome", "This is the artefact that demonstrates capability to an employer or "
          "a customer &mdash; not the RTL alone"]]))
    return "\n".join(s)


def ch_papers():
    s = ['<h1 id="w5">W5. From Literature to a Block</h1>']
    s.append("<h2>W5.1 What published work is for</h2>")
    s.append(tab("Four uses of literature in an IP practice",
        ["Use", "What to extract", "Where to look", "Trap"],
        [["Architecture selection", "Which structure, and under what conditions",
          "JSSC, ISSCC, VLSI Symposia, DAC/ICCAD",
          "Reported numbers come from the authors' best operating point"],
         ["Algorithmic justification", "Correctness conditions, convergence bounds",
          "IEEE Transactions, arXiv", "Confusing a theory paper with an implementable one"],
         ["Attack awareness", "Whether a countermeasure is already broken",
          "CHES, CCS, USENIX Security, IACR ePrint",
          "<b>Mandatory for security IP</b>"],
         ["Standards rationale", "Why a specification says what it says",
          "<b>Standards-body contribution archives</b>",
          "Contributions are proposals; not all were adopted"]]))
    s.append("""<div class="ms"><b>Standards contributions are the most under-used
    resource.</b> The published standard states <i>what</i>; the working-group
    contributions that preceded it state <i>why</i>, with the measurements and the
    alternatives that were rejected. For IEEE 802 these are publicly archived. Reading the
    contributions for the clause you are implementing typically answers the questions the
    standard's terse language leaves open, and it does so faster than deriving the answer.
    <b>It also reveals which parameter choices were contentious, which is exactly where
    implementations are most likely to differ.</b></div>""")

    s.append("<h2>W5.2 Reading efficiently</h2>")
    s.append(tab("A triage procedure",
        ["Step", "Action", "Decision"],
        [["1", "Read the figures and tables first", "What was measured?"],
         ["2", "Find the experimental conditions", "Is this comparable to my case?"],
         ["3", "Identify the baseline", "<b>Is the comparison fair?</b>"],
         ["4", "Find the crossover", "Where does the claimed advantage disappear?"],
         ["5", "Only now read the method", "How does it work?"],
         ["6", "Read limitations and future work", "What do the authors already know is wrong?"]]))
    s.append("""<div class="warn"><b>Record your confidence level with every citation.</b>
    A note that says "full text read", "abstract only", or "search snippet only" costs
    nothing to write and prevents the most damaging failure mode in technical work:
    building a plan on a claim nobody actually verified. If a design decision rests on a
    paper you have not read in full, that fact should be visible in the document where
    the decision is recorded. <b>Unverified citations propagate quietly and are discovered
    late.</b></div>""")

    s.append("<h2>W5.3 Turning a paper into a specification</h2>")
    s.append(tab("Translation checklist",
        ["Question", "Why it must be answered before design starts"],
        [["What exactly is the input and output format?",
          "Papers routinely omit scaling, ordering and normalisation conventions"],
         ["What are the numerical requirements?",
          "Most papers assume floating point; the word lengths are yours to determine"],
         ["What is the initialisation?",
          "Iterative methods rarely state the starting point; it affects convergence"],
         ["What is the termination condition?",
          "&lsquo;Until converged&rsquo; is not implementable; fixed iteration counts are"],
         ["Which parameters were tuned to the reported data set?",
          "Those parameters will not transfer"],
         ["What is the failure behaviour?",
          "Papers report average performance; you must specify the worst case"],
         ["Is there a patent?",
          "<b>Published does not mean free to use</b>"]]))
    s.append("""<div class="ms"><b>The termination-condition question separates research
    from engineering.</b> An algorithm described as iterating until a residual falls below
    a threshold has data-dependent latency, which a streaming datapath cannot accept. The
    engineering translation is a fixed iteration count chosen so that the worst case in
    the operating region still meets the accuracy requirement &mdash; and then the
    accuracy becomes a design-time constant rather than a run-time property. This is
    exactly what the Jacobi SVD does with a fixed sweep count, what an LDPC decoder does
    with a maximum iteration limit, and what K-best detection does relative to sphere
    decoding. <b>Converting an adaptive algorithm into a fixed-latency one is a recurring
    and characteristic act of hardware design</b>, and the specification must record the
    accuracy that the fixed budget guarantees.</div>""")
    return "\n".join(s)


def ch_career():
    s = ['<h1 id="w6">W6. Working on a Modelling Team</h1>']
    s.append("<h2>W6.1 The first week</h2>")
    s.append(tab("Questions to ask, and what the answers reveal",
        ["Question", "What a good answer looks like", "What a poor answer means"],
        [["What is our golden model, and who owns it?",
          "A named artefact with an owner", "Correctness is decided ad hoc"],
         ["How does the model connect to the RTL?",
          "A defined trace interface (RVFI-like) or DPI harness",
          "<b>Building one is your first project</b>"],
         ["How often does the regression run, and how long does it take?",
          "Nightly, under eight hours", "Feedback is too slow to steer design"],
         ["What is the specification?",
          "A standard document or a maintained internal spec",
          "<b>The model <i>is</i> the specification &mdash; large responsibility</b>"],
         ["How is undefined behaviour handled?",
          "Explicitly marked and masked in comparison",
          "The model may have been tuned to match the RTL &mdash; independence lost"],
         ["Who verifies the model?",
          "Standard vectors, a second implementation, mutation testing",
          "<b>Nobody &mdash; this is your highest-value contribution</b>"],
         ["What escaped in the last year, and why?",
          "A specific analysis", "No escape analysis means no learning loop"]]))
    s.append("""<div class="ms"><b>The last question is the most informative one you can
    ask.</b> An organisation that can describe a specific escape, its root cause, and the
    check that was added in response has a functioning improvement loop. One that cannot
    recall any escape either has not shipped much or does not trace failures back. The
    answer tells you more about how the team works than any description of its
    methodology.</div>""")

    s.append("<h2>W6.2 Habits that compound</h2>")
    s.append(tab("Working practices",
        ["Practice", "Effect"],
        [["Annotate model code with specification section numbers",
          "Makes the model auditable and survivable"],
         ["Record the seed and the exact command with every failure",
          "<b>Turns an anecdote into a reproducible fact</b>"],
         ["Minimise a failing case before reporting it",
          "Preserves the designer's trust and time"],
         ["Suspect the comparison before the design",
          "Most mismatches are scoreboard or timing issues"],
         ["Write the check that would have caught it",
          "Converts each bug into permanent coverage"],
         ["Deliberately break things to test the tests",
          "The only way to know a suite is alive"],
         ["State confidence levels in reports",
          "Distinguishes measured from assumed"],
         ["Never close an unreproduced intermittent failure",
          "<b>Removes evidence, not the bug</b>"]]))
    s.append("""<div class="ms"><b>&ldquo;Suspect the comparison first&rdquo; is worth
    making a reflex.</b> In a mature project the ordering of likelihood is: the scoreboard
    or its timing assumptions, then the model, then the RTL. Reporting a suspected RTL bug
    that turns out to be a testbench issue twice in a row is enough to make the third
    report &mdash; the real one &mdash; go unexamined for a week. Running the model and the
    RTL separately on the same stimulus and reading both logs takes an hour and settles
    the question before anyone else is involved.</div>""")

    s.append("<h2>W6.3 Writing that gets read</h2>")
    s.append(tab("Reporting a discrepancy",
        ["Section", "Content"],
        [["One-line summary", "What differs, where, under what condition"],
         ["Minimal reproducer", "Exact command, seed, and the shortest failing stimulus"],
         ["Evidence", "Model output and RTL output side by side, with the first "
          "differing cycle identified"],
         ["Triage", "Which of the three causes has been ruled out, and how"],
         ["Specification reference", "The clause or section that decides the question"],
         ["Proposed disposition", "Model change, RTL change, or specification clarification"],
         ["<b>Confidence</b>", "<b>What you verified versus what you inferred</b>"]]))
    s.append("""<div class="note">The last row is the habit that most distinguishes
    experienced engineers in written communication. A report that separates &ldquo;I
    measured this&rdquo; from &ldquo;I believe this follows&rdquo; can be acted on
    immediately; one that blends them forces every reader to re-derive the distinction.
    Over a project's life this single discipline saves more time than any tool.</div>""")
    return "\n".join(s)
