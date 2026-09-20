# -*- coding: utf-8 -*-
"""Volume I, Part X17 -- Reading the current literature.

Sourcing note: this part discusses directions, not specific results.  Where a
named technique appears, it is one whose *mechanism* is described here from
first principles so the reader can check the reasoning; no performance figure is
attributed to a paper this repository has not read in full.  That restraint is
deliberate and is the repository's standing rule.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_modern2():
    s = ['<h1 id="x17">X17. Reading the Current Literature</h1>']
    s.append("""<p>A textbook that stops at settled material leaves the reader unable to
    read this year's proceedings. This part covers the directions that a designer entering
    the field now will meet, treated the way the rest of the book treats everything: by
    the arithmetic that makes each one attractive and the arithmetic that limits it. No
    performance claim is attributed to a specific paper here, because this repository's
    rule is that a citation carries a confidence level and an unread paper cannot carry a
    high one.</p>""")

    s.append("<h2>X17.1 Chiplets: the arithmetic that made them inevitable</h2>")
    s.append("""<p>Part&nbsp;X16 computed that yield falls superlinearly with die area.
    Chiplets exploit that directly, and the trade is entirely quantitative.</p>""")
    rows = []
    D0, alpha = 0.10, 3.0
    total = 600.0     # mm^2 of silicon needed
    for n in (1, 2, 4, 8):
        A = total / n / 100.0
        y = (1 + A * D0 / alpha) ** (-alpha)
        sysy = y ** n
        rows.append([num(n), num(total / n, 4), num(y, 4), num(sysy, 4),
                     num(1 / max(sysy, 1e-9), 4), num(n * (n - 1) // 2)])
    s.append(sweep("Splitting 600&nbsp;mm&sup2; of silicon into <i>n</i> chiplets, "
                   "yield only",
        ["Chiplets", "Area each (mm&sup2;)", "Die yield", "All-<i>n</i>-good yield",
         "Relative silicon cost", "Interfaces to design"], rows,
        "The fourth column assumes every chiplet must be good, which is the pessimistic "
        "case; known-good-die testing before assembly is what makes the scheme work at "
        "all, and its cost is the missing term. <b>The gain is real and the last column "
        "is why it is not free.</b>"))
    s.append(ex("What a die-to-die link costs, and why it decides the partition",
        "Two chiplets exchanging 1&nbsp;TB/s. A die-to-die interface achieves roughly "
        "1&nbsp;pJ/bit; an on-die wire of the same length costs roughly 0.05&nbsp;pJ/bit.",
        "Compute the power of the link and compare with a monolithic implementation. "
        "The number decides where the partition can be drawn.",
        [("Bits per second", num(8e12, 3)),
         ("Die-to-die power at 1&nbsp;pJ/bit", num(8e12 * 1e-12, 4, "W")),
         ("On-die equivalent at 0.05&nbsp;pJ/bit", num(8e12 * 0.05e-12, 4, "W")),
         ("Penalty", num(8e12 * 0.95e-12, 4, "W")),
         ("As a fraction of a 300&nbsp;W package", num(8e12 * 0.95e-12 / 300 * 100, 3, "%")),
         ("Bandwidth affordable in a 15&nbsp;W budget",
          num(15 / 1e-12 / 8e12, 3, "TB/s"))],
        "<b>By partitioning on functional boundaries instead of on bandwidth.</b> The "
        "correct cut is the one with the least traffic across it, which is frequently "
        "<i>not</i> the tidiest functional boundary: splitting compute from memory looks "
        "natural and puts the highest-bandwidth interface across the cut, while splitting "
        "compute from I/O puts a much lower-bandwidth interface there. <b>Draw the "
        "traffic graph before drawing the partition</b>, exactly as Part&nbsp;X11's "
        "bisection argument requires, and note that the answer changes with the workload "
        "&mdash; which is why chiplet partitions are argued about for months."))

    s.append("<h2>X17.2 Near- and in-memory computing</h2>")
    s.append(derive("Why moving computation to the data is attractive, and what bounds it", [
        ("Part X13 measured arithmetic intensity: most layers are memory bound.",
         "So the machine spends its energy on movement, not arithmetic."),
        ("Reading a 64-bit word from DRAM costs on the order of 100&times; the energy "
         "of a 64-bit add.",
         "The ratio varies with process and distance; the order of magnitude is the "
         "robust part."),
        ("If the computation happens where the data is, that ratio is avoided for "
         "whatever it can do there.",
         "<b>The gain is bounded by the fraction of work that can move</b>, which is "
         "Amdahl's law applied to data movement rather than to time."),
        ("Analogue in-memory computing performs the multiply&ndash;accumulate in the "
         "array itself, using conductance as the weight.",
         "One column sums currents; the addition is free and the multiply is Ohm's "
         "law."),
        ("Its limits are precision, variability and the converters.",
         "<b>The ADC at the bottom of each column frequently dominates area and "
         "power</b>, which returns the design to Part X12's converter arithmetic. "
         "A technique that removes one bottleneck by creating another has to be "
         "evaluated on the sum."),
    ]))
    rows = []
    for bits in (2, 4, 6, 8):
        # column ADC energy grows ~4x per 2 bits above thermal-limited region
        adc = 0.5 * 4 ** ((bits - 2) / 2)
        mac = 0.02
        rows.append([num(bits), num(mac, 3), num(adc, 4),
                     num(adc / (adc + mac) * 100, 3),
                     num(2 ** bits)])
    s.append(sweep("A crude accounting for an analogue in-memory column: the converter "
                   "dominates as precision rises (relative energy units)",
        ["Output bits", "Array MAC energy", "Column ADC energy",
         "ADC share of the column (%)", "Levels to resolve"], rows,
        "The model is illustrative, not measured, and is included to show the "
        "<i>shape</i> of the constraint rather than a value. <b>The shape is the "
        "point</b>: analogue in-memory computing is attractive at low output precision "
        "and loses its advantage as precision rises, which is why the published work "
        "concentrates on heavily quantised inference."))
    s.append("""<div class="warn"><b>Judge any in-memory result on the complete system,
    including the converters, the peripheral circuits and the data marshalling.</b> An
    array-only energy figure is the analogue equivalent of a TOPS number: true, and about
    a part of the system that was never the bottleneck. The questions that separate a
    result from a product are: what precision at the output, what does the ADC cost, how
    is a weight updated and how often, what happens to accuracy over temperature and
    drift, and what fraction of a real network maps onto the array at all. <b>Each of
    those is a question this book has asked about a conventional block somewhere, which
    is the point: the discipline transfers.</b></div>""")

    s.append("<h2>X17.3 Machine learning applied to the design flow itself</h2>")
    s.append(tab("Where learning is used in EDA, and what the oracle is",
        ["Application", "What is learned", "The oracle", "Why it can work"],
        [["Placement and floorplanning", "A policy for placing macros",
          "<b>The downstream tool's own metrics</b>",
          "The reward is computable, if slowly &mdash; a real oracle exists"],
         ["Routing congestion prediction", "A map from placement to congestion",
          "The router's result", "Plentiful labelled data from past runs"],
         ["Timing prediction before routing", "Post-route delay from pre-route features",
          "The signoff tool", "Saves iterations rather than replacing signoff"],
         ["Parameter tuning", "Good tool settings for a design",
          "The tool's output", "<b>The highest-return and least glamorous "
          "application</b>"],
         ["<b>RTL generation from natural language</b>", "<b>Code</b>",
          "<b>Nothing, unless you supply one</b>",
          "<b>This is the case that differs in kind, not degree</b>"],
         ["Testbench and assertion generation", "Properties and stimulus",
          "Coverage, mutation score", "An oracle exists and is measurable"]]))
    s.append("""<div class="ms"><b>The organising question for every row is: what
    verifies the output?</b> Where a slow but trustworthy oracle exists &mdash; the
    router, the timing signoff tool, a golden model &mdash; learning is search, and search
    with a good oracle is reliable and improves with compute. Where no oracle exists, the
    output must be read by a human, and the failure mode is code that looks correct, which
    is the most expensive kind. Part&nbsp;Y4's agent is built on exactly this
    distinction and is worth re-reading in this light: it searches a small space against a
    strong oracle and rejects candidates that pass only the data they were fitted to.
    <b>The strategic conclusion for a design house is that investment in golden models and
    checkers appreciates as generation improves</b>, because they are what converts an
    unreliable generator into a reliable one, and they are what a competitor who has only
    a generator cannot borrow.</div>""")
    s.append(prob("A tool vendor claims their learned placer improves timing by "
                  "10&nbsp;%. What do you ask?",
        "<b>Against what baseline, tuned how hard?</b> A learned placer compared against "
        "a default-configured conventional flow is compared against a strawman; a human "
        "expert spends days on tool settings, and the comparison must include that effort "
        "or exclude it from both sides. <b>On how many designs, and were they in the "
        "training set?</b> Improvement on designs resembling the training distribution is "
        "the expected result and says nothing about yours. <b>What is the variance?</b> "
        "Placement is stochastic; a 10&nbsp;% mean improvement with a 15&nbsp;% spread "
        "across seeds is not an improvement you can schedule around. <b>What does it cost "
        "in runtime and in setup?</b> A placer that needs a week of fine-tuning per design "
        "is a service, not a tool. <b>And what happens when it fails?</b> A conventional "
        "flow degrades predictably; a learned one may produce a result that is fine on "
        "the metric it optimised and bad on one it did not see. These are the same "
        "questions Part&nbsp;Y6 asks of any paper, which is the intended lesson: "
        "<b>the reading discipline does not change because the subject is fashionable.</b>"))
    s.append(prob("Your customer asks whether your IP is &lsquo;AI-generated&rsquo;. How "
                  "do you answer?",
        "Directly, because the question behind it is about provenance and liability "
        "rather than about tooling. Say what tools were used and for what; say what "
        "verification the output passed, which is the part that actually bounds the risk; "
        "and say what you can warrant about the origin of the code &mdash; that it is not "
        "derived from licensed or copyleft sources, and that you can produce a per-file "
        "record. <b>A customer's real concern is that they will inherit a legal problem "
        "or an unverified block</b>, and both are answerable with evidence you should "
        "have anyway. Evasion is the worst answer available: it converts a procurement "
        "question into a trust question, and Part&nbsp;Y5's argument about the "
        "known-issue list applies exactly &mdash; the supplier who volunteers the "
        "uncomfortable detail is the one who gets called next time."))
    return "\n".join(s)
