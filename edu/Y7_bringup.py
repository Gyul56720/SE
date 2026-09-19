# -*- coding: utf-8 -*-
"""Volume III, Part Y7 -- Debug and bring-up, with the arithmetic."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_bringup2():
    s = ['<h1 id="y7">Y7. Debug and Bring-Up, With the Arithmetic</h1>']
    s.append("""<p>Bring-up is the phase in which the difference between engineers is
    largest, and most of that difference is method rather than knowledge. The method is
    binary search over hypotheses, executed with discipline, and it can be made
    quantitative: each observation should halve the space of possible causes, and an
    observation that does not is a waste of an afternoon.</p>""")

    s.append("<h2>Y7.1 Debugging as information gain</h2>")
    s.append(derive("Why the right measurement is the one that splits the space evenly", [
        ("Let there be <i>N</i> plausible causes, each with prior probability "
         "<i>p<sub>i</sub></i>.",
         "The hypothesis space after reading the symptom."),
        ("A test partitions the space: outcome A is consistent with a subset, outcome B "
         "with the rest.", "Any observation does this, well or badly."),
        ("The information gained is the entropy reduction, maximised when the two "
         "subsets have equal probability mass.",
         "<b>Not equal <i>count</i> &mdash; equal probability.</b> Splitting off one "
         "unlikely cause teaches almost nothing."),
        ("<i>k</i> ideal tests reduce <i>N</i> equiprobable causes to "
         "<i>N</i>/2<sup><i>k</i></sup>.",
         "So twenty causes need about five tests, not twenty."),
        ("<b>A test whose outcome you can predict has zero information.</b>",
         "If you are confident what will happen, do not run it. This single rule "
         "eliminates most wasted bring-up time."),
    ]))
    rows = []
    for N in (4, 8, 16, 32, 64):
        rows.append([num(N), num(math.ceil(math.log2(N))),
                     num(N), num(N / 2, 3),
                     num(math.ceil(math.log2(N)) / N * 100, 3)])
    s.append(sweep("Tests needed under binary search versus one-at-a-time elimination",
        ["Plausible causes", "Ideal tests (log<sub>2</sub>)",
         "One-at-a-time, worst case", "One-at-a-time, average",
         "Ideal as % of worst case"], rows,
        "A bring-up with 32 plausible causes is five good measurements or thirty-two "
        "bad ones. <b>The whole skill is in choosing tests that split the space rather "
        "than tests that confirm a favourite hypothesis.</b>"))
    s.append("""<div class="ms"><b>The favourite-hypothesis trap has a specific
    signature.</b> An engineer who believes the problem is in module X runs tests that
    would be consistent with X, gets results consistent with X, and becomes more
    confident &mdash; while every one of those tests was also consistent with Y and Z.
    The discipline that prevents it is to <b>write down what each outcome would rule
    out before running the test</b>. If the answer is &lsquo;nothing, either way&rsquo;,
    the test is confirmation and not evidence. This is the same rule as the verification
    one in Part&nbsp;X8: a test that no broken implementation would fail is not a
    test.</div>""")

    s.append("<h2>Y7.2 The bring-up sequence, in dependency order</h2>")
    s.append(tab("Bring up in this order, because each step depends on the previous",
        ["Step", "Check", "If it fails"],
        [["1. Power", "Every rail at the right voltage, in the right sequence, with "
          "the ripple in spec",
          "Nothing above this means anything. <b>Sequence violations can damage "
          "parts</b>"],
         ["2. Clocks", "Every clock present, at the right frequency, with acceptable "
          "jitter",
          "Measure at the die if possible; a clock present at the oscillator is not a "
          "clock present at the block"],
         ["3. Reset", "Asserted long enough, released cleanly and synchronously",
          "<b>The most common silent failure</b> &mdash; a block that half-resets "
          "produces a state that no simulation ever visited"],
         ["4. Register access", "Read an ID register; write and read back a scratch "
          "register",
          "If this fails, everything above is suspect; if it works, the bus, clock, "
          "reset and power are all proven at once"],
         ["5. Static configuration", "Program the block; read back every register",
          "Read-back mismatch localises to the register file immediately"],
         ["6. Loopback", "Internal loopback first, then external",
          "<b>Separates the block from the channel</b> &mdash; the single most "
          "valuable feature to design in"],
         ["7. One transaction", "One packet, one frame, one transfer",
          "Debuggable; a stream is not"],
         ["8. Line rate", "Continuous traffic",
          "Reveals everything the single transaction hid: buffering, back pressure, "
          "rate adaptation, alignment"],
         ["9. Corner conditions", "Temperature, voltage, rate extremes",
          "Where the margin problems live"]]))
    s.append("""<div class="warn"><b>Step 4 is worth more than its position suggests.</b>
    A readable identification register with a known constant value proves, in one
    transaction, that the supply is up, the clock is running, the reset released, the bus
    is connected, the address decode is right and the endianness matches. There is no
    other single test with that much power, and providing one costs a design a dozen
    gates. <b>An IP block without an ID register and a scratch register is harder to bring
    up by a factor that is hard to overstate</b>, and their absence is a reasonable reason
    for a customer to choose a competitor.</div>""")
    s.append(ex("Why internal loopback pays for itself in one bring-up",
        "A SerDes-attached block fails to pass traffic. Without loopback there are, "
        "say, 24 plausible causes spanning the transmitter, the channel, the connector, "
        "the far end and the receiver. Internal loopback splits them into 'inside the "
        "chip' and 'outside'.",
        "Apply the information argument: count the tests needed with and without the "
        "feature, at roughly two hours per test including setup.",
        [("Plausible causes", num(24)),
         ("Ideal tests without loopback", num(math.ceil(math.log2(24)))),
         ("Causes remaining after a loopback result", num(12)),
         ("Ideal tests after loopback", num(1 + math.ceil(math.log2(12)))),
         ("Hours saved if each test costs 2 h", num(0, 3)),
         ("But: tests without loopback are <i>not</i> even splits",
          "<b>this is the real saving</b>"),
         ("Realistic sequence without loopback", "10&ndash;15 tests, several requiring "
          "board rework"),
         ("Realistic sequence with loopback", "4&ndash;6 tests, none requiring rework")],
        "<b>By counting only the ideal test count, which barely changes.</b> The value of "
        "loopback is not that it reduces log<sub>2</sub><i>N</i> by one; it is that "
        "<b>without it, no available test splits the space evenly</b> &mdash; every "
        "measurement is at one end of the chain and rules out little. A feature that "
        "creates an even split where none existed is worth far more than its effect on "
        "the count suggests. The same argument justifies per-stage error counters, "
        "snapshot registers and a pattern generator: each one manufactures a clean "
        "partition of the hypothesis space."))

    s.append("<h2>Y7.3 Reading a symptom</h2>")
    s.append(tab("Symptom to first hypothesis",
        ["Symptom", "Most likely class", "The distinguishing test"],
        [["Works at low rate, fails at high rate", "Timing or bandwidth",
          "Vary the rate and find the exact threshold; a sharp threshold means timing, "
          "a gradual one means buffering"],
         ["Fails after a fixed time, always the same",
          "A counter wrapping, or a buffer filling",
          "Compute what wraps in that time at that rate &mdash; the arithmetic usually "
          "names the register"],
         ["Fails randomly, low rate of failure",
          "Metastability, marginal timing, or a rare data pattern",
          "Vary temperature and voltage: timing moves, a data pattern does not"],
         ["<b>Works in simulation, fails in silicon</b>",
          "<b>Something not modelled</b>",
          "Reset, clock, power, X-propagation, or an unmodelled analogue behaviour. "
          "<b>List what the simulation did not contain</b>"],
         ["Fails only with a specific partner", "Interoperability",
          "Capture the link and compare against the specification, not against your "
          "other partner"],
         ["First transaction after idle fails", "A power or clock state exit",
          "Disable the low-power state and see if it disappears"],
         ["Corrupt data with a regular period", "Rate mismatch or an alignment marker",
          "Compute the period in symbols and compare with the marker interval"]]))
    s.append(prob("A link passes traffic for exactly 71 minutes and then drops a frame, "
                  "reliably. What wraps in 71 minutes?",
        "Do the arithmetic rather than guessing. At 1&nbsp;Gbit/s and 8 bits per byte a "
        "byte counter increments 125&nbsp;million times a second; 71 minutes is about "
        "4260&nbsp;s, giving roughly 5.3&times;10<sup>11</sup> bytes &mdash; close to "
        "2<sup>39</sup>. At a 156.25&nbsp;MHz clock, 4260&nbsp;s is about "
        "6.7&times;10<sup>11</sup> cycles, near 2<sup>39.3</sup>. So look for a counter "
        "of about 39 or 40 bits &mdash; a 40-bit statistics counter, or a timestamp. "
        "<b>The technique generalises: convert the failure period into counts of every "
        "periodic event in the system and see which lands on a power of two.</b> It "
        "also works for suspiciously round numbers in other bases: 71 minutes is not "
        "obviously special, which is exactly why the conversion is necessary. A failure "
        "at 49.7 days would be a 32-bit millisecond counter and is recognisable on "
        "sight; the same reasoning found it."))
    s.append(prob("Silicon fails a case that simulation passes. Where do you look first, "
                  "and what does that tell you about your verification plan?",
        "Look at the list of things the simulation did not model, because that is where "
        "the answer is by definition. The usual entries: <b>reset</b> &mdash; simulation "
        "often starts from an initialised state that silicon never has, so an "
        "uninitialised register that simulation reads as a known value reads as garbage "
        "in silicon; <b>X-propagation</b> &mdash; a simulator's optimistic X handling can "
        "let an unknown resolve to a definite value through a multiplexer, hiding exactly "
        "this class of bug, which is why X-pessimistic or four-state gate-level "
        "simulation exists; <b>clock and power sequencing</b>, rarely modelled at all; "
        "<b>analogue behaviour</b>, from supply droop to the settling of an off-chip "
        "device; and <b>real timing</b>, since RTL simulation is untimed. What this says "
        "about the plan is concrete: each of these has a known mitigation &mdash; "
        "randomised reset values, X-pessimistic simulation, gate-level simulation with "
        "back-annotated timing, and a modelled power sequence &mdash; and <b>the plan "
        "should name which ones it uses and which it consciously declines</b>. A plan "
        "that does not mention them has not declined them; it has forgotten them, and the "
        "difference shows up here."))
    return "\n".join(s)
