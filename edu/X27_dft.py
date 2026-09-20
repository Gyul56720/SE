# -*- coding: utf-8 -*-
"""Volume I, Part X27 -- Design for test: scan, BIST and ATPG, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_scan():
    b = []
    for i, x in enumerate((40, 128, 216)):
        b.append(box(x, 40, 62, 34, f"FF{i+1}", None, 9))
        if i:
            b.append(arr(x - 22, 57, x, 57))
        b.append(f'<rect x="{x-20}" y="{46}" width="18" height="22" fill="#eef2f7" '
                 f'stroke="#000" stroke-width="0.8"/>')
        b.append(txt(x - 11, 61, "M", 7, "middle"))
    b.append(arr(6, 57, 20, 57))
    b.append(txt(4, 50, "scan_in", 7))
    b.append(arr(278, 57, 300, 57))
    b.append(txt(304, 60, "scan_out", 7))
    b.append(line(40, 90, 278, 90, w=0.9))
    b.append(txt(159, 104, "scan_enable", 8, "middle"))
    for x in (20, 108, 196):
        b.append(arr(x, 20, x, 46))
    b.append(txt(159, 14, "functional inputs from the logic cloud", 8, "middle"))
    b.append(txt(159, 128, "Every flop becomes observable and controllable at the cost "
                           "of one multiplexer.", 9, "middle"))
    b.append(txt(159, 142, "That single change is what makes a chip testable at all.",
                 9, "middle", 'font-style="italic"'))
    return svg(360, 152, "".join(b))


def ch_dft():
    s = ['<h1 id="x27">X27. Design for Test: Scan, BIST and ATPG, Worked</h1>']
    s.append("""<p>Test is the activity that decides whether the chips you sell work, and
    it is the one an IP vendor is most often asked about and least often prepared for. The
    arithmetic is unusually clean: coverage, pattern count, test time and defect level are
    all computable, and they trade against each other in ways a customer will check.</p>""")
    s.append(fig(_f_scan(), "A scan chain. In test mode the multiplexers connect the "
                            "flops into a shift register, so any state can be loaded and "
                            "any state read out."))

    s.append("<h2>X27.1 Why scan, and what it costs</h2>")
    s.append(derive("From an untestable machine to a testable one", [
        ("A sequential circuit's state is reachable only through its inputs over many "
         "cycles.",
         "To test a fault deep in the state space you must first drive the machine "
         "there, which may take an unknown and enormous number of cycles."),
        ("Test generation for sequential circuits is therefore intractable in general.",
         "The search is over input <i>sequences</i>, not input <i>vectors</i>."),
        ("<b>Scan converts every flop into a shift-register stage in test mode.</b>",
         "Now any state is loadable in <i>L</i> shifts and any state is observable in "
         "<i>L</i> shifts."),
        ("The combinational logic between flops is then testable as a pure "
         "combinational circuit.",
         "<b>And combinational test generation is tractable</b> &mdash; still NP-hard, "
         "but with structure that ATPG exploits well in practice."),
        ("Cost: one multiplexer per flop (5&ndash;10&nbsp;% area), one delay in the "
         "<i>D</i> path, plus routing for the chain and the enable.",
         "<b>The timing cost is the one that surprises</b>: the scan mux sits in the "
         "functional data path and adds to setup time on every flop in the design."),
    ]))
    rows = []
    for flops in (1e3, 1e4, 1e5, 1e6):
        for chains in (1,):
            pass
        for nch in (1, 8, 32, 128):
            L = flops / nch
            rows.append([num(int(flops)), num(nch), num(int(L)),
                         num(L * 1000 / 1e6 * 1e3, 5),
                         num(nch * 2)])
    s.append(sweep("Scan shift time for 1000 patterns at 100&nbsp;MHz shift clock",
        ["Flops", "Chains", "Chain length", "Shift time (ms)", "Extra pins"], rows,
        "Shift time is patterns &times; chain length &divide; shift frequency. "
        "<b>Tester time is billed by the second</b>, so the chain count is a direct cost "
        "trade against pin count &mdash; and pins on a production tester are scarce, "
        "which is why compression exists."))
    s.append(ex("What scan compression buys",
        "A 1-million-flop design, 5000 patterns, 100&nbsp;MHz shift clock, "
        "32 scan pins available.",
        "Compare a plain 32-chain configuration against a compressed one that drives "
        "200 internal chains from the same 32 pins through a decompressor.",
        [("Plain: chain length", num(int(1e6 / 32))),
         ("Plain: shift cycles", num(int(5000 * 1e6 / 32))),
         ("Plain: test time at 100&nbsp;MHz",
          num(5000 * 1e6 / 32 / 1e8, 4, "s")),
         ("Compressed: internal chains", num(200)),
         ("Compressed: chain length", num(int(1e6 / 200))),
         ("Compressed: test time",
          num(5000 * 1e6 / 200 / 1e8, 4, "s")),
         ("Compression ratio", num(200 / 32, 4) + "&times;"),
         ("Tester cost saved at $0.05/s over 10M units",
          num((5000 * 1e6 / 32 - 5000 * 1e6 / 200) / 1e8 * 0.05 * 1e7 / 1e6, 4,
              "M USD"))],
        "<b>By evaluating compression as an area cost rather than a revenue item.</b> "
        "The decompressor and compactor are a fraction of a per cent of area and the "
        "tester saving over a production run is measured in millions. <b>The constraint "
        "that limits the ratio is not area but the patterns themselves</b>: compression "
        "works because ATPG patterns are mostly don't-cares, and the achievable ratio is "
        "set by how many care bits a pattern has. A design with unusually constrained "
        "patterns &mdash; deep logic, many constraints &mdash; compresses less, which is "
        "a reason to talk to the test engineer during design rather than after."))

    s.append("<h2>X27.2 Fault models, and what each one misses</h2>")
    s.append(tab("Fault models in industrial use",
        ["Model", "Assumes", "Catches", "Misses"],
        [["<b>Stuck-at</b>", "A node is permanently 0 or 1",
          "<b>Gross defects: opens, shorts to rails</b>",
          "Anything timing related; resistive defects"],
         ["<b>Transition / at-speed</b>",
          "A node is slow to rise or slow to fall",
          "<b>Resistive opens, weak drivers, process marginality</b>",
          "Needs two patterns and at-speed launch &mdash; costly"],
         ["Path delay", "A specific path is too slow", "Marginal critical paths",
          "Exponentially many paths &mdash; only a chosen few are tested"],
         ["Bridging", "Two nodes shorted", "Metal defects between neighbours",
          "Requires layout to choose realistic pairs"],
         ["IDDQ", "A defect draws static current", "Shorts invisible to logic tests",
          "<b>Unusable in modern processes &mdash; leakage swamps it</b>"],
         ["Cell-aware", "Defects inside a standard cell",
          "<b>Defects the gate-level models cannot express</b>",
          "Requires transistor-level analysis per cell &mdash; the library vendor must "
          "supply it"]]))
    s.append("""<div class="warn"><b>Stuck-at coverage of 99&nbsp;% is not 99&nbsp;% of
    defects, and conflating them is the commonest error in a test discussion.</b> The
    stuck-at model is a convenient abstraction, not a description of physics; real defects
    are resistive opens and shorts whose effect is timing-dependent. A part that passes a
    full stuck-at suite can fail in the customer's system because a resistive via makes a
    path 20&nbsp;% slow &mdash; a defect the model cannot express. <b>This is why at-speed
    transition testing became mandatory below about 90&nbsp;nm</b>, and why cell-aware
    test was added on top. The honest statement in a datasheet is coverage <i>per model</i>,
    with the models named.</div>""")
    rows = []
    for cov in (0.90, 0.95, 0.98, 0.99, 0.995, 0.999):
        for y in (0.85,):
            dl = 1 - y ** (1 - cov)
        rows.append([num(cov * 100, 4), num(y * 100, 3),
                     num(dl * 1e6, 5), num(dl * 1e6 * 10, 5),
                     num(1 / max(dl, 1e-12) / 1e3, 4)])
    s.append(sweep("Defect level against fault coverage at 85&nbsp;% yield "
                   "(Williams&ndash;Brown: DL = 1 &minus; <i>Y</i><sup>1&minus;<i>C</i></sup>)",
        ["Coverage (%)", "Yield (%)", "Defect level (ppm)",
         "Escapes per 10M units", "Units per escape (thousands)"], rows,
        "The model is the standard first-order estimate. <b>The step from 99&nbsp;% to "
        "99.9&nbsp;% coverage removes an order of magnitude of field returns</b>, which "
        "is why automotive programmes push coverage to places that look "
        "disproportionate from a pattern-count perspective."))
    s.append(plot([90, 95, 98, 99, 99.5, 99.9],
                  [("log10 defect level (ppm)",
                    [math.log10(max((1 - 0.85 ** (1 - c / 100)) * 1e6, 1e-6))
                     for c in (90, 95, 98, 99, 99.5, 99.9)])],
                  "fault coverage (%)", "log10 defects per million",
                  "Defect level falls roughly a decade per decade of uncovered faults. "
                  "The curve is why the last per cent of coverage is bought."))

    s.append("<h2>X27.3 BIST: testing without a tester</h2>")
    s.append(tab("Built-in self test",
        ["Kind", "Mechanism", "Why it exists"],
        [["<b>Memory BIST</b>", "An on-chip engine walks March algorithms through the "
          "array",
          "<b>Memories are most of the transistors and their faults are array-specific "
          "(coupling, retention, address decoder)</b>; a scan test cannot express them"],
         ["Logic BIST", "An LFSR generates pseudo-random patterns; a MISR compacts the "
          "responses",
          "In-field self test for safety; reduces pattern storage"],
         ["<b>Repair</b>", "Spare rows and columns swapped in by fuses",
          "<b>Turns a failing die into a good one &mdash; Part&nbsp;X16's yield "
          "arithmetic</b>"],
         ["In-system test", "BIST run at power-up or periodically",
          "<b>ISO 26262 latent-fault metric &mdash; Part&nbsp;X16</b>"]]))
    s.append(ex("Why random patterns alone are not enough, measured",
        "A logic block whose faults require, on average, a specific value on 12 "
        "particular inputs to be detected. Pseudo-random patterns set each input "
        "independently to 0 or 1.",
        "Compute the probability that one random pattern detects such a fault, and how "
        "many patterns are needed for high confidence &mdash; then note what happens for "
        "the hardest faults.",
        [("Probability one pattern detects", num(2.0 ** -12, 3)),
         ("Patterns for 99&nbsp;% detection of that fault",
          num(int(math.ceil(math.log(0.01) / math.log(1 - 2.0 ** -12))))),
         ("If the fault needs 20 specific inputs", num(2.0 ** -20, 3)),
         ("Patterns then",
          num(int(math.ceil(math.log(0.01) / math.log(1 - 2.0 ** -20))))),
         ("At 100&nbsp;MHz, time for those patterns",
          num(math.ceil(math.log(0.01) / math.log(1 - 2.0 ** -20)) / 1e8, 4, "s")),
         ("Standard remedy", "<b>test points, or deterministic top-up patterns</b>")],
        "<b>By reporting the average and ignoring the tail.</b> Most faults are detected "
        "by the first few hundred random patterns; a small number are random-pattern "
        "resistant and dominate the remaining coverage. The two standard responses are to "
        "<b>insert test points</b> &mdash; observation or control nodes that break the "
        "deep dependency, at a small area cost &mdash; or to follow random patterns with "
        "deterministic ATPG patterns aimed exactly at the survivors. <b>Both require "
        "knowing which faults survived, which means the coverage report must be read "
        "rather than summarised.</b>"))
    s.append(prob("A customer asks for your IP's fault coverage. What do you actually "
                  "give them, and what do you need from them?",
        "You cannot give a single number, and explaining why is part of the answer. "
        "Coverage depends on the customer's scan insertion, their chain configuration, "
        "their ATPG constraints and their test modes &mdash; none of which exist in your "
        "standalone block. <b>What you supply is testability rather than coverage</b>: "
        "confirmation that the RTL is scan-friendly (no gated clocks without test "
        "bypass, no internally generated resets without test control, no latches, no "
        "combinational loops, no black boxes without wrappers), a list of any "
        "non-scannable elements with the reason, the test modes your block needs (memory "
        "BIST hooks, bypass for any analogue or hard macro), and any DFT constraints your "
        "block imposes on theirs. <b>What you need from them is their DFT strategy</b>, "
        "because compression, at-speed testing and any safety requirement change what the "
        "RTL must provide. <b>Doing this exchange at integration rather than at design is "
        "how blocks end up with untestable islands</b>, and a vendor who raises it "
        "unprompted is signalling experience."))
    return "\n".join(s)
