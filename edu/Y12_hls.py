# -*- coding: utf-8 -*-
"""Volume III, Part Y12 -- High-level synthesis in a small design house."""
import sys, os, math, json
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_hls2():
    s = ['<h1 id="y12">Y12. High-Level Synthesis in a Small Design House</h1>']
    s.append("""<p>High-level synthesis promises to turn C++ into RTL, which for a
    one-person house sounds like a way to multiply headcount. It is a real tool with a
    real place, and the place is narrower than the marketing and wider than the
    scepticism. This part states where it wins, where it does not, and what this
    repository measured when it tried to synthesise a production C++ library with an
    open-source tool.</p>""")

    s.append("<h2>Y12.1 What HLS actually decides for you</h2>")
    s.append(derive("The three transformations, and which one is the hard one", [
        ("<b>Scheduling</b>: assign each operation to a clock cycle, respecting data "
         "dependences and the target period.",
         "The tool solves a constrained scheduling problem, typically with a "
         "list-scheduling heuristic or an ILP formulation for small regions."),
        ("<b>Allocation</b>: decide how many of each resource exist.",
         "Two multiplies in different cycles may share one multiplier."),
        ("<b>Binding</b>: assign operations to specific resource instances, and "
         "variables to registers or memories.",
         "Introduces multiplexers, which is where a naive binding loses the timing the "
         "scheduler thought it had."),
        ("All three are driven by <b>pragmas</b>, not by the C++ semantics.",
         "<b>This is the fact that determines everything else.</b> The same C++ with "
         "different pragmas produces designs differing by orders of magnitude in area "
         "and throughput, which means the C++ is not the design &mdash; the C++ plus "
         "the pragmas plus the tool version is the design."),
        ("So HLS source is not portable between tools in any practical sense.",
         "The pragma dialects differ, the library types (<code>ap_fixed</code>, "
         "<code>hls::stream</code>) differ, and the scheduling behaviour differs. "
         "<b>Measured in this repository</b>: a production Xilinx Vitis library did not "
         "build under an open-source HLS tool without modification."),
    ]))
    s.append(tab("Where HLS wins and where it does not",
        ["Situation", "HLS", "Why"],
        [["Datapath-heavy, regular loops (filters, transforms, linear algebra)",
          "<b>Strong</b>",
          "Scheduling a loop nest is exactly what the tool is good at"],
         ["Design-space exploration &mdash; ten variants of one algorithm",
          "<b>Very strong</b>",
          "Changing a pragma is minutes; rewriting RTL is days. <b>This is the best "
          "argument for HLS</b>"],
         ["Algorithm still changing", "Strong",
          "The C++ stays readable as the algorithm moves"],
         ["Control-dominated protocol logic", "Weak",
          "A state machine expressed as C++ control flow is harder to read and to "
          "verify than the FSM it becomes"],
         ["Cycle-exact interface timing", "Weak",
          "The tool owns the schedule; you are negotiating with it"],
         ["Area- or timing-critical blocks at the frequency limit", "Weak",
          "The last 20&nbsp;% needs control the abstraction removes"],
         ["Code you must hand to a customer as portable RTL", "<b>Fine</b>",
          "Ship the generated RTL; <b>the customer never needs the C++</b>"]]))
    s.append("""<div class="ms"><b>The strongest case for HLS in a small house is
    exploration, not production.</b> The question &lsquo;what does this algorithm cost at
    four different parallelism factors?&rsquo; takes an afternoon in HLS and a fortnight
    in RTL, and the answer changes the architecture. Having taken the decision, writing
    the production block in RTL is often still the right call &mdash; and the HLS model
    remains useful as a golden reference, since it is C++ that is known to produce the
    same numbers. <b>Used this way, HLS is a modelling tool that happens to emit
    RTL</b>, which fits the role this book is written for.</div>""")

    s.append("<h2>Y12.2 What this repository measured</h2>")
    try:
        p = "/home/user/SE/survey/synth/합성결과.md"
        if os.path.exists(p):
            txt_ = open(p, encoding="utf-8").read()
            n = len(txt_.splitlines())
            s.append(f"""<p>This repository built an open-source HLS tool from source and
            attempted to synthesise a production vendor C++ library with it. The findings
            are recorded in <code>survey/synth/&#54633;&#49457;&#44208;&#44284;.md</code>
            ({n} lines) and are summarised here because they are the kind of result that
            is rarely written down.</p>""")
        else:
            s.append("<p>The synthesis findings file was not found in this checkout.</p>")
    except Exception as e:
        s.append(f'<div class="warn">{E(str(e))}</div>')
    s.append(tab("Three independent blockers, isolated by single-variable experiments",
        ["Blocker", "Evidence", "What it means for a user"],
        [["<b>Pragma dialect</b>",
          "Vendor pragmas are not recognised by the other tool; the code compiles and "
          "schedules differently",
          "<b>HLS source does not port.</b> Budget a rewrite, not a recompile"],
         ["<b>Library types</b>",
          "A crash in the tool's own pass while handling a streaming class passed by "
          "value",
          "The vendor's stream and fixed-point classes are part of the vendor's tool, "
          "not part of C++"],
         ["<b>Template instantiation cost</b>",
          "Heavily templated fixed-point code expands enormously before synthesis "
          "begins",
          "Compile time can exceed the time budget before any hardware is generated"]]))
    s.append("""<div class="warn"><b>Two lessons from that exercise are worth more than
    the result itself.</b> First, <b>the blockers were only separable by controlled
    experiments</b>: all three appeared as &lsquo;it does not work&rsquo; until each was
    isolated with one variable changed at a time, and before that isolation it would have
    been easy &mdash; and wrong &mdash; to report a single cause. Second, an early
    attempt to name the cause was withdrawn because the run had timed out before reaching
    the pass in question, so the claim was a guess and not a measurement. <b>The rule that
    produced both corrections is the one this whole book applies: a number or a cause you
    have not measured is not a finding, however confident you are.</b></div>""")

    s.append("<h2>Y12.3 Verifying HLS output</h2>")
    s.append(tab("The three levels of HLS verification",
        ["Level", "What it compares", "Catches", "Cost"],
        [["C simulation", "The C++ against your test vectors",
          "Algorithm bugs", "Seconds &mdash; run constantly"],
         ["<b>C/RTL co-simulation</b>",
          "<b>The generated RTL against the same C++ on the same vectors</b>",
          "<b>Tool bugs and pragma misunderstandings</b>", "Minutes to hours"],
         ["RTL verification", "The generated RTL in its real environment",
          "Interface and integration problems the co-simulation harness hides",
          "As for any RTL"]]))
    s.append("""<div class="bs"><b>Why C/RTL co-simulation is not optional.</b> It is
    tempting to reason that if the C++ is correct and the tool is correct then the RTL is
    correct. The second premise is the problem: HLS tools have bugs, and more commonly the
    <i>pragmas do not mean what the writer thought</i> &mdash; a dependence the tool was
    told to ignore was real, a loop it was told to pipeline could not be, an interface
    protocol was inferred differently from what the integrator expects. Co-simulation
    catches all of these for the cost of running the vectors twice. <b>It is also the only
    thing that makes the C++ usable as a golden model afterwards</b>, since it establishes
    that the two really do agree.</div>""")
    s.append(ex("When HLS pays for itself, as arithmetic",
        "An exploration of one algorithm at four parallelism factors and three word "
        "lengths &mdash; twelve design points. RTL: 3 days per point. HLS: 2 days to "
        "set up plus 2 hours per point. Both need the results to be trustworthy.",
        "Count the days for each route, including the HLS learning and verification "
        "overhead that is easy to omit.",
        [("Design points", num(12)),
         ("RTL route, days", num(12 * 3)),
         ("HLS setup, days", num(2)),
         ("HLS per point, days", num(2 / 8, 3)),
         ("HLS route, days", num(2 + 12 * 2 / 8, 3)),
         ("Plus co-simulation of the chosen point, days", num(2)),
         ("HLS total", num(4 + 12 * 2 / 8, 3)),
         ("Saving", num(36 - (4 + 12 * 2 / 8), 3) + " days")],
        "<b>By counting the saving and then shipping the HLS output without the "
        "verification days.</b> The arithmetic above holds only because the last two "
        "rows are included; an HLS flow without co-simulation is faster and produces RTL "
        "nobody should trust. The second common error is to count the setup as a one-off "
        "when it is per-project: tool versions, library versions and pragma behaviour "
        "change, and a flow that worked last year needs re-establishing. <b>Budget the "
        "setup every time and the saving is still large for exploration and small or "
        "negative for a single production block</b> &mdash; which is exactly the "
        "recommendation in Y12.1, now with numbers behind it."))
    s.append(prob("A customer asks whether your block was written in RTL or generated "
                  "from HLS. Does it matter, and how do you answer?",
        "It matters to them for three legitimate reasons and you should answer plainly. "
        "<b>Maintainability</b>: if they must modify the block, generated RTL is "
        "unpleasant to edit, so they need either the C++ and the flow, or a commitment "
        "that you will make changes. <b>Quality of results</b>: generated RTL is usually "
        "larger and slower than good hand RTL at the same function, and if they are "
        "area- or frequency-constrained that is their business. <b>Predictability</b>: "
        "regenerating with a different tool version can change the result, so they will "
        "want to know the RTL they receive is frozen and verified as delivered, not "
        "regenerated on demand. <b>The answer that satisfies all three is to ship frozen, "
        "verified RTL with its synthesis and timing reports, and to state the "
        "provenance</b>. Concealing it is the bad option: it is discoverable from the "
        "generated code's shape in about five minutes, and being caught concealing "
        "something harmless costs more than the thing concealed."))
    return "\n".join(s)
