# -*- coding: utf-8 -*-
"""Volume I, Part X42 -- Reset, initialisation and the states nobody simulates."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_reset():
    s = ['<h1 id="x42">X42. Reset, Initialisation and the States Nobody Simulates</h1>']
    s.append("""<p>Reset is the least interesting part of a design and the source of a
    disproportionate share of silicon bugs, for a simple reason: simulation starts from a
    clean state and silicon does not. This part treats reset with the same seriousness as
    the datapath, because the failures it causes are the ones that appear only in the
    lab.</p>""")

    s.append("<h2>X42.1 Synchronous, asynchronous, and the one that is actually used</h2>")
    s.append(tab("Reset styles",
        ["Style", "Assertion", "De-assertion", "Cost", "Problem"],
        [["Synchronous", "On a clock edge", "On a clock edge",
          "Wider reset net timing; <b>needs a running clock</b>",
          "<b>Cannot reset a block whose clock has not started</b>"],
         ["Asynchronous", "Immediate", "Immediate",
          "Cheap &mdash; the flop's async pin",
          "<b>De-assertion can violate recovery/removal and cause metastability</b>"],
         ["<b>Asynchronous assert, synchronous de-assert</b>",
          "<b>Immediate</b>", "<b>Synchronised to the clock</b>",
          "<b>A two-flop synchroniser per domain</b>",
          "<b>None &mdash; this is the standard answer</b>"],
         ["No reset (initialised by first write)", "&mdash;", "&mdash;",
          "Free &mdash; saves the reset net on datapath flops",
          "<b>X-propagation until written; needs care in verification</b>"]]))
    s.append(derive("Why de-assertion is the dangerous edge", [
        ("A flop with an asynchronous reset has <i>recovery</i> and <i>removal</i> "
         "times: the reset must be stable for a window around the clock edge.",
         "Exactly analogous to setup and hold, and checked by the same static timing "
         "analysis."),
        ("Reset assertion is asynchronous and harmless: the flop goes to its reset "
         "value whenever it arrives.",
         "There is no race, because the destination is unconditional."),
        ("<b>De-assertion races the clock.</b>",
         "If reset releases within the recovery window, the flop may go metastable or "
         "may capture the pre-reset value."),
        ("With one clock, the tool checks and fixes it.",
         "Recovery and removal are ordinary timing checks."),
        ("<b>With a large design, the reset tree's own skew means different flops "
         "leave reset on different cycles.</b>",
         "<b>A state machine can then advance while part of its state is still "
         "reset</b>, reaching a state the designer never enumerated. This is the "
         "classic reset bug and it is invisible in RTL simulation, where reset "
         "de-asserts everywhere at once."),
        ("Remedy: synchronise the de-assertion in each clock domain, and treat the "
         "reset tree like a clock tree.",
         "<b>Balanced, buffered, and timed.</b>"),
    ]))
    s.append("""<div class="warn"><b>Reset de-assertion skew produces states that no
    simulation visits, and gate-level simulation with timing is the only place it appears
    before silicon.</b> In RTL simulation the reset signal changes at one instant for
    every flop. In silicon it is a buffered tree with tens or hundreds of picoseconds of
    skew &mdash; more if it is not treated as a timed net &mdash; so flops leave reset on
    different clock edges. A counter can start counting while its comparator is still
    held; a FIFO's write pointer can advance while its read pointer is reset, making the
    FIFO appear full at power-up. <b>The two defences are structural</b>: synchronise
    de-assertion per domain so all flops in a domain release on the same edge, and design
    state machines so that a partially-reset state is not reachable &mdash; usually by
    holding the whole machine in an idle state until an explicit enable.</div>""")

    s.append("<h2>X42.2 X-propagation: where simulation lies in both directions</h2>")
    s.append(tab("How simulators treat unknown values, and why it matters",
        ["Situation", "RTL simulation", "Silicon", "Consequence"],
        [["Uninitialised flop read", "<code>X</code>",
          "<b>A definite 0 or 1, randomly</b>",
          "Simulation may be more pessimistic than reality"],
         ["<b><code>if (x)</code> where x is X</b>",
          "<b>Takes the else branch</b>", "Takes one branch definitely",
          "<b>X-optimism: the bug is hidden</b>"],
         ["<code>case</code> with X selector", "May take the default",
          "Takes a real branch", "Same optimism"],
         ["Mux with X select", "Output X if inputs differ; <b>output the value if "
          "they are equal</b>", "Real value", "Can hide or expose"],
         ["Flop with X data", "Captures X", "Captures a real value",
          "<b>X-pessimism: X spreads where silicon would not</b>"]]))
    s.append("""<div class="ms"><b>X-optimism and X-pessimism are both wrong, in opposite
    directions, and the remedies differ.</b> Optimism hides bugs: a branch on an unknown
    silently resolves, so a design that depends on an uninitialised value appears to work
    in simulation and behaves randomly in silicon. Pessimism wastes time: X floods through
    a design that silicon would run correctly, and engineers add resets they do not need
    to make simulation quiet &mdash; which costs area and reset-tree power on every flop.
    <b>The industrial answers are three</b>: X-propagation-aware simulation modes that
    make branches on X produce X rather than choosing; <b>random initialisation</b>, where
    every uninitialised flop starts at a random value and the regression is run with many
    seeds, which converts X-optimism into an ordinary functional failure the testbench can
    catch; and gate-level simulation, which has no X-optimism because the gates are real.
    <b>Random initialisation is the cheapest and the most effective</b>, and it is
    available in every simulator.</div>""")
    rows = []
    for flops_no_reset, seeds in ((100, 1), (100, 10), (100, 100),
                                  (1000, 10), (1000, 100)):
        p_catch = 1 - 0.5 ** seeds
        rows.append([num(flops_no_reset), num(seeds), num(p_catch, 6),
                     num((1 - p_catch) * 100, 3)])
    s.append(sweep("Probability of catching a dependence on one uninitialised bit, "
                   "with random initialisation",
        ["Unreset flops", "Random seeds run", "P(at least one seed exposes it)",
         "P(missed) (%)"], rows,
        "Assuming the bug manifests when that bit takes one particular value. "
        "<b>Ten seeds give a 99.9&nbsp;% chance of exposing it and a hundred make it "
        "negligible</b> &mdash; and seeds are the cheapest thing in a regression. "
        "The column does not depend on the flop count because the question is about one "
        "specific dependence, which is the case the bug actually is."))

    s.append("<h2>X42.3 Power-up: the sequence and what it must guarantee</h2>")
    s.append(tab("The power-up sequence, and what breaks if a step is skipped",
        ["Step", "Guarantee", "If skipped"],
        [["Supplies ramp in the specified order",
          "No forward-biased junction, no latch-up",
          "<b>Permanent damage, not a functional failure</b>"],
         ["Reset asserted before and during ramp",
          "No spurious activity, no contention on shared buses",
          "Bus contention, high current, possible damage"],
         ["Clocks stable before reset release",
          "Synchronous de-assertion works",
          "<b>The synchroniser has no clock, so de-assertion is asynchronous after "
          "all</b>"],
         ["Reset held for the specified number of cycles",
          "Every flop in every domain has seen an edge",
          "Partially reset state &mdash; X42.1"],
         ["PLL locked before its output is used",
          "Frequency is what the timing assumed",
          "Logic clocked far outside its timing corners"],
         ["Fuses and trim loaded", "Calibration applied",
          "Analogue blocks at their untrimmed operating point"],
         ["<b>Only then: release to software</b>", "A defined starting state",
          "<b>An intermittent boot failure &mdash; the hardest class of bug to "
          "debug</b>"]]))
    s.append(ex("How many reset cycles does a block need?",
        "A block with three clock domains at 500&nbsp;MHz, 100&nbsp;MHz and "
        "32&nbsp;kHz, each with a two-flop reset synchroniser.",
        "Reset must be held long enough for the slowest domain to see the required "
        "edges, not the fastest &mdash; and this is the number a datasheet must state.",
        [("Fastest domain period", num(2, 3, "ns")),
         ("Slowest domain period", num(1 / 32768 * 1e6, 5, "&micro;s")),
         ("Edges needed per synchroniser", num(3)),
         ("Hold time for the 500&nbsp;MHz domain", num(6, 3, "ns")),
         ("Hold time for the 32&nbsp;kHz domain",
          num(3 / 32768 * 1e6, 5, "&micro;s")),
         ("<b>Required reset assertion</b>",
          "<b>" + num(3 / 32768 * 1e6, 5) + "&nbsp;&micro;s &mdash; set by the "
          "slowest domain</b>"),
         ("Common error", "specifying it in cycles of the fast clock")],
        "<b>By quoting the reset requirement in clock cycles without saying which "
        "clock.</b> &lsquo;Assert reset for 16 cycles&rsquo; is ambiguous in a "
        "multi-clock block and is wrong by four orders of magnitude if the reader picks "
        "the fast clock. <b>State the requirement in absolute time, and state it for the "
        "slowest clock the block can be configured with</b> &mdash; including the case "
        "where a clock is stopped, which requires either that reset be held until it "
        "starts or that the domain be reset asynchronously and independently."))
    s.append(prob("Your block occasionally fails to come out of reset, roughly one boot "
                  "in a thousand. Where do you look?",
        "The frequency is the clue: one in a thousand is a race, not a logic error, "
        "because a logic error would be deterministic. Three candidates, in order. "
        "<b>Reset de-assertion recovery</b>: if any domain's reset is not synchronised, "
        "de-assertion races the clock and metastability resolves the wrong way "
        "occasionally &mdash; the rate is computable from Part&nbsp;X3's MTBF formula "
        "with the reset edge as the asynchronous event, and one in a thousand boots is "
        "entirely consistent with an unsynchronised reset. <b>Clock-before-reset "
        "ordering</b>: if reset is released in the same window that a PLL locks or a "
        "clock gate opens, some flops see edges and some do not, giving the partial-reset "
        "state of X42.1; this shows a dependence on temperature or supply, because they "
        "change the lock time. <b>An uninitialised state element that is usually "
        "benign</b>: a flop without reset whose value normally does not matter, except in "
        "the rare case &mdash; and this is what random-initialisation regression is for. "
        "<b>The diagnostic that separates them is to vary the reset pulse width and the "
        "clock start time</b>: a recovery race moves with clock phase, an ordering "
        "problem moves with pulse width, and an uninitialised value moves with "
        "neither."))
    return "\n".join(s)
