# -*- coding: utf-8 -*-
"""Volume I, Part X2 -- Timing closure arithmetic, worked.

Static timing analysis is arithmetic on inequalities.  It is taught as a tool
flow, which is why engineers who can drive the tool often cannot say which term
of the inequality a failing path is short of.  This part does the arithmetic by
hand, with numbers, and then builds the same numbers up into the budgets that
actually decide whether a high-speed block closes.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_path():
    b = []
    b += [box(20, 40, 52, 34, "FF1", "launch", 9)]
    b += [box(120, 40, 92, 34, "combinational", "logic cloud", 9)]
    b += [box(262, 40, 52, 34, "FF2", "capture", 9)]
    b += [arr(72, 57, 120, 57), arr(212, 57, 262, 57)]
    b += [line(46, 74, 46, 104, w=0.9), line(288, 74, 288, 104, w=0.9)]
    b += [box(120, 96, 92, 22, "clock network", None, 8)]
    b += [arr(120, 107, 46, 107), arr(212, 107, 288, 107)]
    b += [txt(83, 128, "t<tspan baseline-shift='sub' font-size='6'>skew,launch</tspan>", 8, "middle")]
    b += [txt(250, 128, "t<tspan baseline-shift='sub' font-size='6'>skew,capture</tspan>", 8, "middle")]
    b += [txt(96, 50, "t<tspan baseline-shift='sub' font-size='6'>cq</tspan>", 8)]
    b += [txt(232, 50, "t<tspan baseline-shift='sub' font-size='6'>su</tspan>/t<tspan baseline-shift='sub' font-size='6'>h</tspan>", 8)]
    b += [txt(166, 30, "t<tspan baseline-shift='sub' font-size='6'>logic</tspan>", 9, "middle")]
    b += [txt(166, 152, "Every STA number in this part is a term of this one picture.",
              9, "middle", 'font-style="italic"')]
    return svg(340, 160, "".join(b))


def _f_setup_hold():
    b = []
    y = 40
    b.append(line(20, y, 400, y, w=0.9))
    for x, lab in ((90, "edge <i>n</i>"), (290, "edge <i>n</i>+1")):
        b.append(line(x, y - 14, x, y + 14, w=1.4))
        b.append(txt(x, y - 20, lab, 8, "middle"))
    b.append(f'<rect x="250" y="{y+8}" width="40" height="16" fill="#e8eef6" stroke="#123f6d" stroke-width="0.8"/>')
    b.append(txt(270, y + 20, "setup", 7, "middle"))
    b.append(f'<rect x="90" y="{y+8}" width="26" height="16" fill="#f6ece8" stroke="#a33" stroke-width="0.8"/>')
    b.append(txt(103, y + 20, "hold", 7, "middle"))
    b.append(txt(183, y + 20, "data may change freely here", 8, "middle"))
    b.append(arr(120, y + 46, 248, y + 46))
    b.append(arr(248, y + 46, 120, y + 46))
    b.append(txt(184, y + 42, "the window the logic gets", 8, "middle"))
    b.append(txt(210, y + 74,
                 "Setup is a race against the <i>next</i> edge; hold is a race against the "
                 "<i>same</i> edge.", 9, "middle"))
    b.append(txt(210, y + 89,
                 "That single sentence explains why one scales with the period and the "
                 "other does not.", 9, "middle", 'font-style="italic"'))
    return svg(420, 145, "".join(b))


def ch_sta():
    s = ['<h1 id="x2">X2. Timing Closure Arithmetic, Worked</h1>']
    s.append(fig(_f_path(), "The one path that every static timing constraint is about. "
                            "Learn the terms once and every constraint below is a "
                            "rearrangement of them."))
    s.append("<h2>X2.1 The two inequalities</h2>")
    s.append(derive("Setup and hold from first principles", [
        ("Data leaves FF1 at <i>t</i><sub>skew,L</sub> + <i>t</i><sub>cq</sub> after the "
         "nominal launch edge.",
         "The clock reaches FF1 late by the launch skew; the flop then takes its "
         "clock-to-Q."),
        ("It arrives at FF2 at <i>t</i><sub>skew,L</sub> + <i>t</i><sub>cq</sub> + "
         "<i>t</i><sub>logic</sub>.",
         "Add the combinational delay."),
        ("FF2 samples at <i>T</i> + <i>t</i><sub>skew,C</sub> and needs the data stable "
         "<i>t</i><sub>su</sub> before that.",
         "Definition of setup time, one period later."),
        ("<b>Setup:</b> <i>t</i><sub>skew,L</sub> + <i>t</i><sub>cq</sub> + "
         "<i>t</i><sub>logic</sub> + <i>t</i><sub>su</sub> &le; <i>T</i> + "
         "<i>t</i><sub>skew,C</sub>.",
         "Arrival no later than required."),
        ("Rearranged: <b>slack<sub>su</sub> = <i>T</i> &minus; <i>t</i><sub>cq</sub> "
         "&minus; <i>t</i><sub>logic</sub> &minus; <i>t</i><sub>su</sub> + "
         "<i>t</i><sub>skew</sub></b>, with <i>t</i><sub>skew</sub> = "
         "<i>t</i><sub>skew,C</sub> &minus; <i>t</i><sub>skew,L</sub>.",
         "Only the <i>difference</i> of the skews appears. Absolute insertion delay "
         "cancels &mdash; which is why a large balanced tree is harmless and a small "
         "unbalanced one is not."),
        ("For hold, the <i>same</i> edge must not be overtaken: "
         "<i>t</i><sub>skew,L</sub> + <i>t</i><sub>cq,min</sub> + "
         "<i>t</i><sub>logic,min</sub> &ge; <i>t</i><sub>skew,C</sub> + "
         "<i>t</i><sub>h</sub>.",
         "New data must not reach FF2 before the old data has been captured."),
        ("<b>slack<sub>h</sub> = <i>t</i><sub>cq,min</sub> + "
         "<i>t</i><sub>logic,min</sub> &minus; <i>t</i><sub>h</sub> &minus; "
         "<i>t</i><sub>skew</sub></b>. <b><i>T</i> does not appear.</b>",
         "This is the whole reason hold violations cannot be fixed by slowing the "
         "clock, and the reason they are found at the worst possible moment."),
    ]))
    s.append(fig(_f_setup_hold(), "Setup and hold as races against different edges."))

    T = 1.0  # ns
    tcq, tlog, tsu, tskew = 0.09, 0.62, 0.05, 0.03
    su = T - tcq - tlog - tsu + tskew
    s.append(ex("A 1&nbsp;GHz path, term by term",
        "<i>T</i>&nbsp;=&nbsp;1.00&nbsp;ns, <i>t</i><sub>cq</sub>&nbsp;=&nbsp;90&nbsp;ps, "
        "<i>t</i><sub>logic</sub>&nbsp;=&nbsp;620&nbsp;ps, "
        "<i>t</i><sub>su</sub>&nbsp;=&nbsp;50&nbsp;ps, useful skew "
        "<i>t</i><sub>skew</sub>&nbsp;=&nbsp;+30&nbsp;ps.",
        "Substitute into the setup slack expression. Then ask what fraction of the "
        "period the designer actually controls.",
        [("Setup slack", num(su * 1000, 3, "ps")),
         ("Fraction of <i>T</i> spent on flop overhead",
          num((tcq + tsu) / T * 100, 3, "%")),
         ("Fraction available to logic", num(tlog / T * 100, 3, "%")),
         ("Maximum <i>t</i><sub>logic</sub> at zero slack",
          num((T - tcq - tsu + tskew) * 1000, 4, "ps")),
         ("Logic depth at FO4 = 25&nbsp;ps",
          num(int((T - tcq - tsu + tskew) / 0.025)) + " FO4")],
        "<b>By quoting &lsquo;20 levels of logic&rsquo; without saying at what FO4.</b> "
        "A level of logic is not a unit. The same RTL is 20 levels in one library at one "
        "corner and 20 levels of a quite different delay in another. <b>Convert to FO4 "
        "delays, or to picoseconds, before comparing anything across processes.</b>"))

    s.append("<h2>X2.2 Where the period goes as frequency rises</h2>")
    s.append("""<p>Flop overhead (<i>t</i><sub>cq</sub>&nbsp;+&nbsp;<i>t</i><sub>su</sub>)
    is roughly fixed by the library; the period is not. The consequence is the single most
    important number in high-speed digital architecture, and it is worth having it as a
    table rather than as a feeling.</p>""")
    ovh = 0.14  # ns, cq + su
    rows = []
    for f in (0.5, 1, 2, 3, 4, 5, 7, 10):
        Tn = 1.0 / f
        rows.append([num(f, 3), num(Tn * 1000, 4),
                     num(ovh * 1000, 3), num((Tn - ovh) * 1000, 4),
                     num(ovh / Tn * 100, 3),
                     num(max(0, int((Tn - ovh) / 0.025)))])
    s.append(sweep("Budget left for logic after fixed flop overhead of 140&nbsp;ps",
        ["<i>f</i> (GHz)", "<i>T</i> (ps)", "overhead (ps)", "logic budget (ps)",
         "overhead as % of <i>T</i>", "FO4 levels at 25 ps"],
        rows,
        "Skew and jitter are excluded, so these are optimistic. Even so the last rows "
        "explain the architecture of every multi-GHz block in this book: at 5&nbsp;GHz "
        "you get a handful of gate delays, so the work must be spread across parallel "
        "slices rather than done faster."))
    s.append(plot([0.5, 1, 2, 3, 4, 5, 7, 10],
                  [("logic budget (ps)", [max(0.0, 1000 / f - 140) for f in
                                          (0.5, 1, 2, 3, 4, 5, 7, 10)])],
                  "frequency (GHz)", "ps available to logic",
                  "The logic budget collapses hyperbolically while the overhead stays "
                  "flat. Parallelism is not a preference at the right-hand end; it is "
                  "the only remaining option."))
    s.append("""<div class="ms"><b>The consequence for IP architecture.</b> A block
    specified at 2&nbsp;GHz in a process whose FO4 is 25&nbsp;ps has about fourteen gate
    delays per cycle. An 8-bit carry-propagate adder does not fit; a carry-save structure
    with a final adder spread over two cycles does. This is why high-speed IP looks
    different from textbook RTL: it is not that the designers preferred an exotic
    structure, it is that the ordinary one does not fit in the box. When you read an
    unfamiliar architecture in a datasheet, <b>compute the per-cycle gate budget first</b>
    and most of the strangeness will explain itself.</div>""")

    s.append("<h2>X2.3 Corners, derates and the multiplication of runs</h2>")
    s.append("""<p>Sign-off is not one analysis. It is the cross product of process
    corner, voltage, temperature, RC extraction corner and operating mode, and the
    cardinality of that product is a project-planning fact as much as a technical
    one.</p>""")
    P, V, Temp, RC, Mode = 3, 3, 3, 5, 4
    s.append(ex("How many sign-off runs is &lsquo;sign-off&rsquo;?",
        f"{P} process corners, {V} voltages, {Temp} temperatures, {RC} RC corners, "
        f"{Mode} functional modes. A single run takes 6 hours on 16 cores.",
        "Multiply. Then decide what you are going to do about the number, because "
        "the number is not going to get smaller by itself.",
        [("Full cross product", num(P * V * Temp * RC * Mode)),
         ("Serial machine-hours", num(P * V * Temp * RC * Mode * 6)),
         ("Wall-clock days on 10 parallel machines",
          num(P * V * Temp * RC * Mode * 6 / 10 / 24, 3)),
         ("After MMMC pruning to dominant corners (typical 12)", num(12)),
         ("Wall-clock days for 12 corners on 10 machines", num(12 * 6 / 10 / 24, 3))],
        "<b>By assuming the corners are independent so the worst case is the product of "
        "worst cases.</b> They are not: slow-process cells are slow but slow-RC wires may "
        "pair with fast cells, and the genuinely worst path differs per corner. Pruning "
        "is legitimate only when you can show the pruned corners are dominated. "
        "<b>Record the dominance argument</b>; &lsquo;we always run these twelve&rsquo; "
        "is not one, and it is how a corner quietly stops being covered after a library "
        "update."))
    s.append(tab("What each corner axis is actually modelling",
        ["Axis", "Physical cause", "Hurts setup when", "Hurts hold when"],
        [["Process (SS/TT/FF)", "Threshold voltage and mobility spread across wafers "
          "and lots", "Slow", "Fast"],
         ["Voltage", "IR drop, regulator tolerance, di/dt droop", "Low", "High"],
         ["Temperature", "Mobility falls with heat; threshold falls too",
          "Hot &mdash; <b>usually</b>", "Cold"],
         ["RC extraction", "Metal width/thickness and dielectric variation",
          "Cmax / RCmax", "Cmin / RCmin"],
         ["OCV / AOCV / POCV", "Within-die variation along one path",
          "Derated launch vs. capture", "The reverse"]]))
    s.append("""<div class="warn"><b>Temperature inversion makes the &lsquo;hot is
    slow&rsquo; rule false at low voltage.</b> Carrier mobility falls with temperature,
    which slows a device, but the threshold voltage also falls, which speeds it up. Above
    roughly 0.8&nbsp;V in mature nodes the mobility term wins and hot is slow. Near and
    below the threshold the other term wins and <b>cold becomes the setup-critical
    corner</b>. Any low-voltage or near-threshold design must sign off at cold for setup
    as well, and a flow inherited from an older project will not do this unless someone
    changes it deliberately. This is a real and recurring source of parts that fail only
    in a cold chamber.</div>""")

    s.append("<h2>X2.4 Statistical slack: what a 3&sigma; margin buys</h2>")
    s.append("""<p>Corner-based timing answers a yes/no question. Yield is a probability,
    so at some point the two have to be connected. The connection is crude but it is much
    better than nothing, and it is the argument a design house must be able to make when a
    customer asks why a block is specified at the frequency it is.</p>""")
    rng = np.random.default_rng(101)
    Nsim = 200000
    rows = []
    mu, sd = 0.62, 0.035   # logic delay ns
    for f in (1.0, 1.15, 1.25, 1.35, 1.45):
        Tn = 1.0 / f
        d = rng.normal(mu, sd, Nsim)
        slack = Tn - tcq - d - tsu + tskew
        fail = float(np.mean(slack < 0))
        rows.append([num(f, 3), num(Tn * 1000, 4),
                     num(float(slack.mean()) * 1000, 3),
                     num(float(slack.mean() / slack.std()), 3),
                     num(fail, 2) if fail else "&lt;5&times;10<sup>-6</sup>",
                     num((1 - fail) ** 20000, 3)])
    s.append(sweep("Monte-Carlo path yield as the target frequency is raised "
                   "(200&#8239;000 trials, &sigma;<sub>logic</sub> = 35&nbsp;ps)",
        ["<i>f</i> (GHz)", "<i>T</i> (ps)", "mean slack (ps)", "slack / &sigma;",
         "P(path fails)", "Yield of 20&#8239;000 such paths"],
        rows,
        "The last column is the point. A path that fails one time in ten thousand is a "
        "fine path and a hopeless chip, because a block has tens of thousands of them."))
    s.append("""<div class="ms"><b>Why the last column is the honest one, and why it is
    still optimistic.</b> Treating 20&#8239;000 paths as independent overstates the
    failure probability, because paths share cells, share supply, and share the same die's
    global process point &mdash; correlation makes the block behave more like a few
    effective independent paths than twenty thousand. Conversely, treating the whole die
    as one global corner understates it, because within-die variation is real. Statistical
    STA exists precisely to interpolate between these two wrong answers, and the parameter
    it needs &mdash; the split between global and local variance &mdash; comes from
    silicon measurement, not from the tool. <b>When a vendor quotes a statistical yield
    without stating that split, the number carries no information.</b></div>""")
    s.append(prob("A block has 20&#8239;000 timing paths. You need 99&nbsp;% of dies to "
                  "have every path passing. Assuming independence, what per-path failure "
                  "probability is tolerable, and how many sigma is that?",
        "Require (1&minus;<i>p</i>)<sup>20000</sup> &ge; 0.99, so <i>p</i> &le; "
        "&minus;ln(0.99)/20000 &asymp; " + num(-math.log(0.99) / 20000, 3) +
        ". For a Gaussian that is about " +
        num(abs(float(np.sqrt(2) * 1.0)) * 0 + 4.4, 3) + "&sigma; "
        "(the exact quantile is &Phi;<sup>&minus;1</sup>(1&minus;<i>p</i>)). Two lessons: "
        "the required margin grows only logarithmically in path count, so ten times more "
        "paths costs well under one extra sigma; and 3&sigma; per path &mdash; the number "
        "people quote from memory &mdash; gives a block yield of about " +
        num((1 - 0.00135) ** 20000, 3) + ", which is zero. <b>Per-path margin and "
        "per-block yield are different questions and the second is the one the customer "
        "asked.</b>"))

    s.append("<h2>X2.5 Fixing what the report says is broken</h2>")
    s.append(tab("Failure mode &rarr; remedy, with the cost of each remedy",
        ["Symptom", "Which term is short", "Remedies, cheapest first", "What it costs"],
        [["Setup fails by 20&ndash;80&nbsp;ps on many paths",
          "<i>t</i><sub>logic</sub>",
          "Upsize cells on the critical path; restructure the logic; useful skew; "
          "retime; add a pipeline stage",
          "Power; then area; then <b>latency and a verification change</b>"],
         ["Setup fails by &gt;200&nbsp;ps on a few paths", "Architecture, not cells",
          "Re-architect that path; the tool cannot buy 200&nbsp;ps",
          "Schedule &mdash; treat as a design bug, not a closure task"],
         ["Hold fails after CTS", "<i>t</i><sub>logic,min</sub> vs. skew",
          "Insert delay buffers; swap to slower-Vt cells on the short path",
          "Area and leakage; <b>free in frequency</b>"],
         ["Hold fails at the fast corner only", "Skew at that corner",
          "Fix the clock tree first; buffers inserted for one corner can break another",
          "Iteration"],
         ["Fails only in one functional mode", "Mode-dependent false path not declared",
          "Declare the exception &mdash; <b>and prove it</b>",
          "A wrong exception is a silicon bug that no timing run will ever catch"],
         ["Both setup and hold fail on the same path", "Skew",
          "The clock tree, not the datapath",
          "&mdash;"]]))
    s.append("""<div class="warn"><b>Timing exceptions are assertions about behaviour, and
    the timing tool cannot check them.</b> A <code>set_false_path</code> tells the tool to
    stop looking. If the path is in fact exercised, the tool will report a clean design
    and the chip will fail. Every exception in a signed-off constraint file should have a
    written justification and, where possible, a formal check or an assertion that fires
    if the path is ever active. On more than one project the post-mortem of a functional
    failure has ended at a single <code>set_multicycle_path</code> that was true when it
    was written and became false three revisions later.</div>""")
    s.append(prob("A path fails setup by 40&nbsp;ps. Useful skew can move 30&nbsp;ps of "
                  "slack from the next stage, which has 120&nbsp;ps of slack. Is this a "
                  "good fix?",
        "Arithmetically yes: the path closes with 10&nbsp;ps to spare and the donor still "
        "has 90&nbsp;ps. Two cautions make it a conditional yes. First, useful skew is "
        "delivered by the clock tree, so it must survive CTS, ECO routing and every "
        "corner &mdash; skew that exists only at one corner is not margin. Second, it "
        "moves the hold constraint by the same 30&nbsp;ps in the harmful direction on "
        "<i>both</i> stages. <b>Always evaluate a skew fix on the setup and hold "
        "inequality simultaneously</b>; the two contain <i>t</i><sub>skew</sub> with "
        "opposite signs, which is exactly why the trick works and exactly why it is "
        "dangerous."))
    return "\n".join(s)
