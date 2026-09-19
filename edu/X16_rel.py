# -*- coding: utf-8 -*-
"""Volume I, Part X16 -- Reliability, yield and functional safety, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_reliability2():
    s = ['<h1 id="x16">X16. Reliability, Yield and Functional Safety, Worked</h1>']
    s.append("""<p>Three quantities decide whether a chip can be sold into an
    automotive, industrial or medical market, and all three are arithmetic: the fraction
    of dies that work, the rate at which working dies stop working, and the fraction of
    dangerous failures that are detected. A design house that can compute them can quote
    for markets that pay considerably more than consumer.</p>""")

    s.append("<h2>X16.1 Yield: the model and its parameter</h2>")
    s.append(derive("From defect density to die yield", [
        ("Defects fall on the wafer at an average density <i>D</i><sub>0</sub> per unit "
         "area.", "Empirical; the foundry supplies it and it falls over a process's life."),
        ("If defects were Poisson and independent, yield would be "
         "e<sup>&minus;<i>AD</i><sub>0</sub></sup>.",
         "Probability of zero defects in area <i>A</i>."),
        ("They are not independent &mdash; defects cluster &mdash; so Poisson is "
         "<b>pessimistic</b> for large dies.",
         "Clustering means some wafers are bad and others clean, which raises the "
         "average yield of the clean ones."),
        ("The negative-binomial (Murphy/Seeds) model adds a clustering parameter "
         "&alpha;: <i>Y</i> = (1 + <i>AD</i><sub>0</sub>/&alpha;)<sup>&minus;&alpha;</sup>.",
         "&alpha; &asymp; 2&ndash;5 in practice; &alpha;&nbsp;&rarr;&nbsp;&infin; "
         "recovers Poisson."),
        ("<b>Yield falls superlinearly with die area</b>, and total good dies per wafer "
         "falls faster still.",
         "Which is the whole argument for chiplets, and the reason a large monolithic "
         "die is a business decision as much as a technical one."),
    ]))
    rows = []
    D0, alpha = 0.10, 3.0     # defects per cm^2
    for A in (10, 25, 50, 100, 200, 400, 800):
        Acm = A / 100.0
        yp = math.exp(-Acm * D0)
        yn = (1 + Acm * D0 / alpha) ** (-alpha)
        # gross die per 300 mm wafer, crude
        wafer = math.pi * 15 ** 2
        gross = int(wafer / Acm * 0.92)
        rows.append([num(A), num(yp, 4), num(yn, 4), num(gross),
                     num(int(gross * yn)), num(1 / max(yn, 1e-9), 4)])
    s.append(sweep("Yield against die area at <i>D</i><sub>0</sub> = 0.10 /cm&sup2;, "
                   "&alpha; = 3, 300&nbsp;mm wafer",
        ["Die area (mm&sup2;)", "Poisson yield", "Negative-binomial yield",
         "Gross die/wafer", "Good die/wafer", "Relative cost per good die"], rows,
        "The last column is cost per working die relative to a perfect-yield part, "
        "holding wafer cost fixed. <b>An 800&nbsp;mm&sup2; die costs far more than "
        "eighty times a 10&nbsp;mm&sup2; one</b>, which is the economics that produced "
        "chiplets."))
    s.append(plot([10, 25, 50, 100, 200, 400, 800],
                  [("neg-binomial", [(1 + A / 100 * 0.10 / 3) ** -3
                                     for A in (10, 25, 50, 100, 200, 400, 800)]),
                   ("Poisson", [math.exp(-A / 100 * 0.10)
                                for A in (10, 25, 50, 100, 200, 400, 800)])],
                  "die area (mm^2)", "yield",
                  "The two models diverge exactly where the decision is hard. Using "
                  "Poisson for a large die understates yield and can kill a viable "
                  "product; using it for a small die makes no difference.", logx=True))
    s.append(ex("Redundancy in a memory, and when it pays",
        "A 16&nbsp;Mbit SRAM occupying 20&nbsp;mm&sup2;. Adding 2&nbsp;% area of spare "
        "rows and columns with laser or fuse repair can repair any single defect in a "
        "row or column.",
        "Compare the yield of the memory with and without repair, using the "
        "negative-binomial model, and weigh the 2&nbsp;% area against the yield gain.",
        [("Memory area", num(20, 3, "mm&sup2;")),
         ("Yield without repair",
          num((1 + 0.20 * 0.10 / 3) ** -3, 4)),
         ("With 2&nbsp;% area added",
          num((1 + 0.204 * 0.10 / 3) ** -3, 4)),
         ("Defects repairable (assume 80&nbsp;% are single row/column)", "80&nbsp;%"),
         ("Effective yield with repair",
          num(1 - (1 - (1 + 0.204 * 0.10 / 3) ** -3) * 0.2, 4)),
         ("Gain",
          num((1 - (1 - (1 + 0.204 * 0.10 / 3) ** -3) * 0.2) /
              ((1 + 0.20 * 0.10 / 3) ** -3) - 1, 3)),
         ("Area cost", num(2, 3, "%"))],
        "<b>By applying the same reasoning to random logic.</b> Memory repair works "
        "because memory is regular: a spare row is interchangeable with any row, so one "
        "spare covers a whole class of defects. Random logic has no such structure, and "
        "the equivalent &mdash; triple modular redundancy &mdash; costs over 200&nbsp;% "
        "rather than 2&nbsp;%. <b>This asymmetry is why yield-enhancement effort "
        "concentrates on memory</b>, and why a design that is 60&nbsp;% memory by area "
        "has a very different yield story from one that is 60&nbsp;% logic. It is worth "
        "knowing which yours is."))

    s.append("<h2>X16.2 Wear-out: the four mechanisms and their accelerations</h2>")
    s.append(tab("Why parts that passed test fail later",
        ["Mechanism", "Physics", "Accelerated by", "Design response"],
        [["<b>Electromigration</b>", "Momentum transfer from electrons moves metal "
          "atoms; voids open", "<b>Current density and temperature</b>",
          "Width rules per current; the tool checks them if told the currents"],
         ["<b>NBTI / PBTI</b>", "Interface traps shift the threshold voltage under bias",
          "Voltage, temperature, and <b>duty cycle</b>",
          "Guardband; some recovery when the stress is removed, which makes "
          "measurement subtle"],
         ["TDDB", "Gate oxide accumulates damage until it conducts",
          "Electric field, exponentially", "Voltage limits; thicker oxide for I/O"],
         ["Hot carrier injection", "Energetic carriers embed in the oxide",
          "Switching activity and short channels",
          "Slew limits; affects high-activity nodes such as clocks"],
         ["Soft errors", "Ionising particle upsets a node",
          "Altitude, cell size, node capacitance",
          "<b>ECC and scrubbing &mdash; Part&nbsp;X10</b>"]]))
    rows = []
    Ea = 0.7   # eV
    k = 8.617e-5
    for T in (55, 85, 105, 125, 150):
        af = math.exp(Ea / k * (1 / (55 + 273.15) - 1 / (T + 273.15)))
        rows.append([num(T), num(af, 4), num(10 / af, 4),
                     num(1000 / af, 4)])
    s.append(sweep("Arrhenius acceleration relative to 55&nbsp;&deg;C, "
                   "<i>E</i><sub>a</sub> = 0.7&nbsp;eV",
        ["Junction temperature (&deg;C)", "Acceleration factor",
         "Field years equivalent to 10 test hours",
         "Field years equivalent to 1000 test hours"], rows,
        "This is how a fifteen-year automotive lifetime is qualified in weeks: stress "
        "at 150&nbsp;&deg;C and multiply. <b>The activation energy is per mechanism and "
        "is the parameter the whole extrapolation rests on</b>; quoting a lifetime "
        "without naming <i>E</i><sub>a</sub> and the mechanism it was measured for is "
        "not a lifetime claim."))
    s.append("""<div class="warn"><b>Acceleration factors multiply the error in
    <i>E</i><sub>a</sub> enormously.</b> At 150&nbsp;&deg;C the factor above is roughly
    170; had <i>E</i><sub>a</sub> been 0.5&nbsp;eV instead of 0.7, it would be about 40.
    So a 10&nbsp;% uncertainty in an exponent's parameter becomes a factor of four in the
    predicted lifetime, and the direction of the error is not conservative &mdash;
    assuming a high <i>E</i><sub>a</sub> makes the test look more severe than it was.
    <b>This is the same structural hazard as the metastability &tau; of Part&nbsp;X3</b>:
    a quantity inside an exponent, measured with modest precision, on which a large claim
    rests. Both deserve the same treatment: use the worst plausible value, and say which
    value you used.</div>""")

    s.append("<h2>X16.3 Functional safety: what ISO&nbsp;26262 actually asks for</h2>")
    s.append(tab("The safety metrics, in plain arithmetic",
        ["Metric", "Definition", "ASIL B", "ASIL D"],
        [["SPFM", "Fraction of single-point faults that are safe or detected",
          "&ge; 90&nbsp;%", "<b>&ge; 99&nbsp;%</b>"],
         ["LFM", "Fraction of latent multi-point faults detected",
          "&ge; 60&nbsp;%", "<b>&ge; 90&nbsp;%</b>"],
         ["PMHF", "Probabilistic metric for random hardware failures",
          "&lt; 100 FIT", "<b>&lt; 10 FIT</b>"],
         ["FMEDA", "The document that computes all three, gate by gate",
          "Required", "Required"]]))
    s.append(ex("What a 99&nbsp;% SPFM target means for a block",
        "A block with 500&#8239;000 gates and a base failure rate of 10 FIT for the "
        "whole block. ASIL&nbsp;D requires SPFM &ge; 99&nbsp;%.",
        "Compute the undetected fault rate the target permits, and then ask what "
        "fraction of the design must be covered by a safety mechanism to reach it.",
        [("Block failure rate", num(10, 3, "FIT")),
         ("Permitted undetected single-point rate", num(0.1, 3, "FIT")),
         ("Fraction of faults needing detection", num(99, 3, "%")),
         ("Gates that must be covered (if faults are uniform)", num(495000)),
         ("Typical coverage of parity on registers", "60&ndash;80&nbsp;%"),
         ("Typical coverage of duplication and compare", "&gt; 99&nbsp;%"),
         ("Area cost to reach ASIL&nbsp;D on the datapath",
          "<b>duplication &mdash; over 100&nbsp;%</b>")],
        "<b>By assuming safety is a verification activity.</b> It is an architecture "
        "activity: 99&nbsp;% coverage is not reachable by testing harder, it is reachable "
        "by building detection into the design, and detection costs area that must be "
        "budgeted at the start. The usual structure is a <b>mixed</b> one &mdash; "
        "duplication on the control path, where it is small and a fault is dangerous; "
        "ECC or parity on memories, where the regularity makes it cheap; and end-to-end "
        "checks such as a CRC over a datapath, where a single check covers a great deal "
        "of logic. <b>A safety manual naming those mechanisms, with the coverage claimed "
        "for each, is a deliverable a customer pays for.</b>"))
    s.append(prob("Why is a &lsquo;latent&rsquo; fault treated separately, and why does "
                  "it need periodic testing?",
        "A latent fault is one in a <i>safety mechanism</i> rather than in the function: "
        "the comparator that would detect a duplication mismatch has itself failed stuck "
        "at &lsquo;equal&rsquo;. On its own it is harmless &mdash; the function still "
        "works &mdash; which is exactly why it is dangerous: nothing reveals it, so it "
        "accumulates, and when a real fault eventually occurs the detection that was "
        "counted on is absent. The metric that bounds this is LFM, and the mechanism that "
        "serves it is a <b>periodic self-test</b>: at start-up and at intervals during "
        "operation, deliberately inject a fault and confirm the detector fires. "
        "<b>This is the same argument as the verification agent's self-check in "
        "Part&nbsp;Y4 and as this repository's whole rule about checking the checker</b> "
        "&mdash; a detector that is never exercised is not known to work, and in a safety "
        "context that is not a style preference but a numbered requirement with a "
        "quantitative target."))
    return "\n".join(s)
