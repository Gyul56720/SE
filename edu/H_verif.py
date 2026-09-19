# -*- coding: utf-8 -*-
"""Volume I, Part H -- Verification, EDA flow, and security."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line


def _f_tri():
    b = []
    b.append(box(35, 28, 178, 50, "Design team", "RTL: SystemVerilog / VHDL"))
    b.append(box(368, 28, 178, 50, "Modelling team", "Reference model: C / C++"))
    b.append(box(200, 155, 182, 56, "Verification team", "testbench + scoreboard"))
    b += [arr(124, 78, 268, 155), arr(457, 78, 318, 155)]
    b += [txt(140, 124, "RTL trace", 9, "middle"), txt(448, 124, "expected", 9, "middle")]
    b.append(box(200, 245, 182, 38, "mismatch = bug", None, 10, "#fbeaea"))
    b.append(arr(291, 211, 291, 245))
    b.append(txt(291, 305, "The operational definition of a bug in a regression",
                 9, "middle", 'font-style="italic"'))
    return svg(585, 318, "".join(b))


def ch_verif():
    s = ['<h1 id="h1">H1. Verification: Theory and Organisation</h1>']
    s.append(fig(_f_tri(), "The three-team structure. It exists to make "
                           "&ldquo;correct&rdquo; an operational, testable notion."))
    s.append("""<p>Verification consumes more effort than design in every serious IP
    project &mdash; commonly cited at 60&ndash;70% of the schedule. Understanding why it
    is organised as it is prevents a great deal of wasted work.</p>""")

    s.append("<h2>H1.1 Why two independent implementations</h2>")
    s.append("""<div class="bs">A specification written in prose is ambiguous; a single
    implementation is self-consistent by construction and therefore cannot reveal its own
    misreadings. Two implementations built independently from the same specification will
    agree only where both read it the same way. <b>Disagreement localises ambiguity.</b>
    This is the same principle as dissimilar redundancy in avionics, applied to
    development rather than to operation.</div>""")
    s.append("""<div class="ms"><b>The argument fails if the two implementations are not
    independent.</b> If the modeller and the designer sit together, share an
    interpretation, and one consults the other's code when unsure, the common-mode error
    rate rises and the regression turns green on a shared misunderstanding. Organisations
    counter this in three ways: physical or organisational separation; deriving one
    implementation from a <b>formal, executable specification</b> (the RISC-V Sail model
    is the canonical example, generating both prose and a C emulator from one source); and
    an <b>external oracle</b> &mdash; standard test vectors from NIST, IEEE or a
    conformance suite. <b>The third is the strongest and the cheapest, and it is the
    reason standards-based blocks are the best first product for a small IP house.</b></div>""")

    s.append("<h2>H1.2 The verification stack</h2>")
    s.append(tab("Verification levels",
        ["Level", "Checks", "Catches", "Cannot catch"],
        [["Lint", "Coding rules", "Latches, width mismatches, incomplete sensitivity",
          "Anything functional"],
         ["CDC / RDC static", "Crossing structure", "Missing synchronisers, reconvergence",
          "Functional protocol errors"],
         ["Unit simulation", "Block behaviour vs model", "Most functional bugs",
          "Integration, timing"],
         ["<b>Formal property</b>", "Exhaustive over state space",
          "Deadlock, unreachable states, protocol violations",
          "Deep datapath equivalence (state explosion)"],
         ["<b>Formal equivalence (LEC)</b>", "RTL vs netlist",
          "Synthesis and ECO errors", "Specification errors"],
         ["Integration / SoC sim", "Blocks together", "Interface mismatches, arbitration",
          "Long-running system behaviour"],
         ["Gate-level with timing", "Netlist + SDF", "X-propagation, timing-dependent bugs",
          "Slow; limited coverage"],
         ["<b>Emulation / FPGA prototype</b>", "Real software on real RTL",
          "Software-visible bugs, long sequences", "Analogue, timing corners"],
         ["Post-silicon", "Actual device", "Everything else", "&mdash; but fixes are expensive"]]))
    s.append("""<div class="warn"><b>X-propagation deserves a specific warning because it
    is asymmetric between RTL and gates.</b> In RTL simulation, an <code>if (x)</code>
    with an unknown condition may take a branch and produce a definite value, hiding the
    uncertainty &mdash; this is <i>X-optimism</i>. In gate-level simulation the same
    unknown spreads &mdash; <i>X-pessimism</i>. A design that relies on registers being
    initialised by data flow rather than by reset can therefore pass RTL simulation and
    fail in gates, or vice versa. The remedies are X-propagation-aware simulation modes
    and, better, <b>explicit initialisation of any register whose value is read before it
    is written</b>. For an IP vendor this is also a deliverable question: if your block
    requires <i>n</i> cycles of reset before its outputs are valid, say so.</div>""")

    s.append("<h2>H1.3 Coverage and closure</h2>")
    s.append(tab("Coverage metrics",
        ["Metric", "Measures", "Automatic?", "Weakness"],
        [["Line / block", "Statements executed", "Yes", "Says nothing about values"],
         ["Branch / condition", "Decisions taken", "Yes", "&mdash;"],
         ["Expression (MC/DC)", "Each condition independently affects the outcome", "Yes",
          "Required for DO-254 / ISO 26262"],
         ["Toggle", "Every bit changed both ways", "Yes", "Weak functional signal"],
         ["FSM state / transition", "States and arcs visited", "Yes", "&mdash;"],
         ["<b>Functional (covergroups)</b>", "Scenarios the engineer defined", "<b>No</b>",
          "<b>Blind to scenarios nobody thought of</b>"],
         ["Assertion", "Properties actually exercised", "Partly",
          "Vacuous passes must be excluded"],
         ["<b>Mutation / fault injection</b>", "Whether the testbench would notice a bug",
          "Yes", "<b>The only metric that tests the testbench</b>"]]))
    s.append("""<div class="ms"><b>Mutation coverage is the metric that answers the
    question the others avoid: would this testbench detect a bug if there were one?</b>
    The procedure is to inject a small, semantically meaningful change &mdash; invert a
    comparison, drop a term, stick a bit &mdash; and confirm the regression turns red. A
    mutant that survives identifies a check that does not exist or a stimulus that never
    reaches the code. This is cheap to automate and routinely reveals that a large
    fraction of a mature suite is inert. <b>The same technique applies to the reference
    model itself</b>, which is otherwise unverified: break the model deliberately and
    confirm the model's own self-checks fail. A verified reference model is a
    differentiator that very few IP vendors can claim.</div>""")

    s.append("<h2>H1.4 The scoreboard problem</h2>")
    s.append(tab("Comparison strategies",
        ["Situation", "Strategy", "Pitfall"],
        [["In-order, fixed latency", "FIFO compare", "&mdash;"],
         ["In-order, variable latency", "FIFO + timeout", "Timeout too tight &rarr; false failures"],
         ["Out-of-order, tagged", "<b>Per-tag queues</b>",
          "<b>A single queue produces both false failures and false passes</b>"],
         ["Multiple legal orders", "Compare against a <b>set</b> of allowed outcomes",
          "Requires the model to enumerate them"],
         ["Don't-care fields", "Mask before comparing", "Masking too much hides real bugs"],
         ["Weak memory model", "<b>Litmus tests</b>, not trace comparison",
          "Trace comparison is simply invalid here"]]))
    s.append("""<div class="ms">The AXI case is worth stating concretely because it is so
    common. AXI guarantees ordering only <i>within</i> an ID; transactions with different
    IDs may complete in any order. A scoreboard with one queue will report a failure when
    the DUT legitimately reorders across IDs, and &mdash; more dangerously &mdash; may
    accept a genuine intra-ID reordering as long as the totals match. <b>The correct
    structure is one queue per ID</b>, and knowing this is a direct consequence of having
    read the protocol specification rather than inferring behaviour from waveforms. It is
    a frequent and productive point of contact between the modelling and verification
    teams.</div>""")

    s.append("<h2>H1.5 Regression engineering</h2>")
    s.append(tab("Regression discipline",
        ["Practice", "Reason"],
        [["Record the seed with every run", "<b>Without it a failure is not reproducible</b>"],
         ["Classify failures automatically", "Triage time dominates otherwise"],
         ["Track failure <i>signatures</i>, not counts", "Distinguishes new from known"],
         ["Never close an intermittent failure as &lsquo;flaky&rsquo;",
          "<b>Intermittent failures are usually real races</b>"],
         ["Keep a golden log of the last known-good", "Enables bisection"],
         ["Measure regression runtime", "A suite nobody can run nightly is not a suite"],
         ["Separate infrastructure failures", "Licence and disk errors must not be counted as bugs"]]))
    s.append("""<div class="warn">The prohibition on dismissing intermittent failures is
    the most frequently violated rule in this book. An intermittent failure means the
    outcome depends on something the test does not control &mdash; a race, an
    uninitialised value, a timing-dependent path. All three exist in the silicon too.
    <b>Closing such a ticket does not remove the bug; it removes the evidence.</b> The
    correct disposition is to keep it open with the failing seed recorded, even if it
    cannot be root-caused immediately.</div>""")
    return "\n".join(s)


def ch_eda():
    s = ['<h1 id="h2">H2. The Implementation Flow</h1>']
    s.append(tab("From RTL to GDSII",
        ["Step", "Input &rarr; output", "Key decisions", "Common failure"],
        [["Elaboration", "RTL &rarr; generic netlist", "Parameter resolution",
          "Unintended latch inference"],
         ["<b>Logic synthesis</b>", "generic &rarr; standard cells",
          "Constraints, effort, <i>V<sub>TH</sub></i> mix",
          "Over-constrained clock &rarr; area and power explosion"],
         ["DFT insertion", "+ scan chains", "Chain count and length", "Scan shift timing"],
         ["Floorplan", "&mdash;", "Block placement, pin assignment, power grid",
          "<b>The decision with the largest downstream impact</b>"],
         ["Placement", "cells &rarr; locations", "Congestion vs timing", "Routing congestion"],
         ["<b>CTS</b>", "+ clock tree", "Skew target, useful skew", "Clock power, OCV"],
         ["Routing", "&mdash;", "Layer assignment, shielding", "DRC violations, crosstalk"],
         ["Sign-off STA", "&mdash;", "Corners, derating, SI", "Missing a corner"],
         ["Physical verification", "DRC, LVS, antenna", "&mdash;", "&mdash;"],
         ["Extraction + final timing", "RC &rarr; delays", "&mdash;", "&mdash;"]]))
    s.append("""<div class="ms"><b>Floorplanning is where an IP block's shape becomes a
    commercial issue.</b> A block delivered as RTL will be placed by the customer, whose
    aspect ratio, pin locations and macro placement may be nothing like the vendor's. If
    the block's internal timing depends on a particular arrangement &mdash; a wide
    datapath that must stay compact, a memory that must sit next to its controller &mdash;
    then the RTL alone is not a sufficient deliverable. Serious IP therefore ships a
    <b>floorplan guideline</b>, sometimes a hardened macro, and always a statement of the
    assumed aspect ratio and utilisation. <b>A block that met timing in the vendor's flow
    and misses in the customer's is the single most damaging support event a small IP
    house can have</b>, because it is expensive to debug remotely and it destroys
    confidence.</div>""")
    s.append(tab("Sign-off corners",
        ["Axis", "Values", "Why"],
        [["Process", "SS, TT, FF, SF, FS", "Global and local variation"],
         ["Voltage", "min, nominal, max", "IR drop and regulation tolerance"],
         ["Temperature", "&minus;40, 25, 125 &deg;C",
          "<b>Both extremes</b> &mdash; temperature inversion makes cold the worst case at low <i>V</i>"],
         ["RC extraction", "Cmin, Cmax, RCmin, RCmax", "Metal thickness variation"],
         ["Mode", "functional, scan, BIST, low power", "Different constraints apply"],
         ["Ageing", "fresh, end-of-life", "NBTI/PBTI drift"]]))
    s.append("""<div class="ms"><b>The corner count multiplies.</b> Five process points
    &times; three voltages &times; three temperatures &times; four RC &times; four modes is
    720 combinations; full sign-off on all of them is not affordable. The industry response
    is <b>statistical or parametric OCV</b> (POCV), which models variation as a
    distribution rather than enumerating corners, plus careful selection of dominant
    corners. For an IP vendor the practical obligation is to state <b>which corners were
    signed off</b> in the PPA report. "500 MHz" without a corner is not a specification,
    and a customer who assumes typical-typical will be disappointed at
    slow&ndash;slow.</div>""")
    s.append(tab("High-level synthesis in the flow",
        ["Aspect", "Reality"],
        [["Input", "C/C++/SystemC with vendor pragmas &mdash; <b>not portable across tools</b>"],
         ["Strength", "Design-space exploration: one source, many area/throughput points"],
         ["Weakness", "Generated RTL is hard to read and debug; timing closure less predictable"],
         ["Where it wins", "Datapath-dominated blocks with regular loops (filters, transforms, crypto)"],
         ["Where it loses", "Control-dominated logic, precise cycle-level interfaces"],
         ["<b>Verification role</b>",
          "<b>The same C source doubles as the reference model</b>, because a general "
          "compiler ignores the pragmas &mdash; convenient, but it shares every algorithmic "
          "assumption with the design"]]))
    s.append("""<div class="warn">The last row is a genuine methodological trap. Using the
    HLS source as the golden model gives <i>zero</i> independence: the two implementations
    are literally the same text. It verifies the HLS tool, not the design. <b>If the HLS
    C is the design, the reference model must be written separately</b> &mdash; ideally in
    a different language, by a different person, from the specification.</div>""")
    return "\n".join(s)


def ch_sec():
    s = ['<h1 id="h3">H3. Hardware Security</h1>']
    s.append(tab("Threat model, mechanism, countermeasure",
        ["Threat", "Mechanism", "Countermeasure", "Verifiable by simulation?"],
        [["<b>Timing side channel</b>", "Execution time depends on secret",
          "Constant-time algorithms; no secret-dependent branches or table indices",
          "<b>Partly</b> &mdash; can check control flow"],
         ["<b>Power / EM (SPA, DPA, CPA)</b>", "Switching activity correlates with data",
          "Masking (Boolean or arithmetic), threshold implementations, DOM",
          "<b>No</b> &mdash; requires TVLA on silicon or power simulation"],
         ["<b>Fault injection</b> (laser, glitch, EM)",
          "Flip a bit to skip a round or corrupt a check",
          "Redundant/complementary FSMs, computation duplication, output checks",
          "<b>Partly</b> &mdash; by explicit fault simulation"],
         ["<b>Probing / FIB</b>", "Physically read an internal wire",
          "Shields, sensors, routing obfuscation", "No"],
         ["<b>Scan / debug access</b>", "Read state through test infrastructure",
          "Lock scan after test; life-cycle state control", "Yes"],
         ["<b>Rowhammer / memory disturb</b>", "Repeated activation flips neighbours",
          "Refresh management, tracking", "Partly"],
         ["<b>Supply chain</b>", "Trojan insertion, counterfeiting",
          "Split manufacturing, logic locking, PUF identity", "No"]]))
    s.append("""<div class="ms"><b>The fourth column is the key organisational insight for
    a modelling engineer.</b> A functional regression, no matter how complete, is blind to
    four of the seven rows. Saying &ldquo;the AES block is verified&rdquo; is therefore
    ambiguous, and in a security review the ambiguity will be challenged. The mature
    formulation is: <i>functional equivalence to FIPS-197 is verified by NIST vectors and
    constrained-random comparison against an independent model; side-channel resistance is
    assessed separately by TVLA on the test chip; fault resistance is assessed by
    gate-level fault injection.</i> <b>Three claims, three methods, three owners.</b></div>""")
    s.append(tab("Masking: the principle and its cost",
        ["Concept", "Statement", "Consequence"],
        [["Boolean masking", "<i>x</i> represented as (<i>x</i>&oplus;<i>m</i>, <i>m</i>)",
          "Each share is independent of <i>x</i> &rarr; first-order leakage removed"],
         ["Linear operations", "Apply to each share separately", "Nearly free"],
         ["<b>Nonlinear operations</b>", "Shares must interact",
          "<b>The expensive part</b> &mdash; this is why the AES S-box is rebuilt in arithmetic"],
         ["Glitches", "Transient values can momentarily depend on <i>x</i>",
          "Registers must separate share-combining stages"],
         ["<b>DOM</b>", "Domain separation + fresh randomness + registers",
          "Provably glitch-resistant; needs a continuous randomness supply"],
         ["Order <i>d</i> masking", "<i>d</i>+1 shares resist <i>d</i>-th order analysis",
          "Cost grows roughly as (<i>d</i>+1)<sup>2</sup>"]]))
    s.append("""<div class="ms"><b>Randomness becomes a system-level resource.</b> A
    DOM-protected S-box consumes fresh random bits on every evaluation. An AES core
    performing sixteen S-box lookups per round for fourteen rounds therefore needs a
    sustained random-bit rate that a slow true-RNG cannot supply, so the design includes a
    fast PRNG reseeded from the TRNG. That PRNG's quality, its reseed policy, and its
    behaviour when starved are now <b>functional</b> requirements of the cipher block, and
    they are verifiable. <b>A security countermeasure has turned into an ordinary
    functional specification with a throughput requirement</b> &mdash; which is precisely
    the kind of boundary a modelling engineer should be able to identify and take
    ownership of.</div>""")
    s.append(tab("Standards a security IP is measured against",
        ["Standard", "Scope"],
        [["FIPS 140-3", "Cryptographic module validation"],
         ["Common Criteria (ISO 15408)", "Evaluation assurance levels"],
         ["ISO/IEC 17825", "Side-channel test methods"],
         ["<b>NIST CAVP</b>", "Algorithm test vectors &mdash; the practical oracle"],
         ["SP 800-90A/B/C", "RNG construction, entropy, and validation"],
         ["FIPS 203/204/205", "<b>Post-quantum: ML-KEM, ML-DSA, SLH-DSA</b>"],
         ["OCP Caliptra", "Datacentre root of trust specification"],
         ["ISO 26262 / IEC 61508", "Functional safety (distinct from security)"]]))
    return "\n".join(s)
