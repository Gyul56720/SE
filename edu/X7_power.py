# -*- coding: utf-8 -*-
"""Volume I, Part X7 -- Power and energy, worked.

Power is the constraint that decides most modern architectures, and it is the
one most often reasoned about qualitatively.  This part gives the arithmetic:
where the joules go, what each technique returns, and why the returns are not
additive.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_power():
    s = ['<h1 id="x7">X7. Power and Energy, Worked</h1>']
    s.append("""<p>A design house is asked for three numbers about power: how much the
    block burns, how much of that is unavoidable, and what a customer can do about it.
    All three are computable, and a vendor who can produce them with their assumptions
    stated is selling something the competitor who quotes a single milliwatt figure is
    not.</p>""")

    s.append("<h2>X7.1 The three terms</h2>")
    s.append(derive("Where the joules go", [
        ("Charging a node of capacitance <i>C</i> to <i>V</i> takes "
         "<i>CV</i><sup>2</sup> from the supply, of which <i>CV</i><sup>2</sup>/2 is "
         "stored and <i>CV</i><sup>2</sup>/2 is dissipated in the pull-up.",
         "Integrate <i>iv</i> over the transient; the result is independent of the "
         "resistance, which is why making transistors faster does not save switching "
         "energy."),
        ("Discharging dissipates the stored half in the pull-down.",
         "So a full cycle costs <i>CV</i><sup>2</sup>, and a 0&rarr;1&rarr;0 pair is "
         "one cycle."),
        ("<b><i>P</i><sub>dyn</sub> = &alpha;<i>CV</i><sup>2</sup><i>f</i></b>, "
         "with &alpha; the probability a node switches per clock.",
         "Rate times energy. <b>&alpha; is the only term the RTL designer controls "
         "directly</b>, and it is the term power estimates get wrong."),
        ("<i>P</i><sub>short</sub> arises while both devices conduct during a "
         "transition; it scales with input slew.",
         "Typically 5&ndash;15&nbsp;% of dynamic. Controlled by slew limits, not by "
         "architecture."),
        ("<i>P</i><sub>leak</sub> = <i>V</i> &middot; <i>I</i><sub>off</sub>, with "
         "<i>I</i><sub>off</sub> &prop; e<sup>&minus;<i>V</i><sub>th</sub>/(<i>nkT/q</i>)</sup>.",
         "Subthreshold conduction. <b>Exponential in threshold and in temperature</b>, "
         "which is why leakage is a thermal-runaway risk and dynamic power is not."),
    ]))
    C, V, f, a = 1e-12, 0.8, 1e9, 0.15
    s.append(ex("A gate-level power estimate from first principles",
        "A block with 200&#8239;000 gates, average switched capacitance 1&nbsp;fF per "
        "gate, <i>V</i>&nbsp;=&nbsp;0.8&nbsp;V, <i>f</i>&nbsp;=&nbsp;1&nbsp;GHz, "
        "activity factor &alpha;&nbsp;=&nbsp;0.15. Clock network adds 30&nbsp;% and its "
        "&alpha; is 1.",
        "Apply &alpha;<i>CV</i><sup>2</sup><i>f</i> to the logic and to the clock "
        "separately, because their activity factors differ by nearly an order of "
        "magnitude and averaging them is the commonest source of a wrong estimate.",
        [("Logic dynamic power",
          num(0.15 * 200000 * C * V * V * f * 1e3, 4, "mW")),
         ("Clock network capacitance (30&nbsp;% of logic)",
          num(0.3 * 200000 * C * 1e12, 4, "pF")),
         ("Clock dynamic power (&alpha;&nbsp;=&nbsp;1)",
          num(1.0 * 0.3 * 200000 * C * V * V * f * 1e3, 4, "mW")),
         ("Clock as a fraction of total dynamic",
          num(0.3 / (0.15 + 0.3) * 100, 3, "%")),
         ("Total dynamic",
          num((0.15 + 0.3) * 200000 * C * V * V * f * 1e3, 4, "mW")),
         ("Energy per cycle",
          num((0.15 + 0.3) * 200000 * C * V * V * 1e12, 4, "pJ"))],
        "<b>By applying one activity factor to the whole design.</b> The clock toggles "
        "every cycle by definition; logic in a typical datapath toggles on ten to twenty "
        "per cent of cycles. An estimate that uses &alpha;&nbsp;=&nbsp;0.2 uniformly "
        "understates the clock by 5&times; and, since the clock here is two thirds of the "
        "total, understates the block by a factor approaching two. <b>Clock gating is the "
        "first power optimisation for exactly this reason</b>, and its benefit is visible "
        "in this table before any tool is run."))

    s.append("<h2>X7.2 Voltage scaling: the quadratic and its limit</h2>")
    rows = []
    Vth, n_, kT = 0.30, 1.3, 0.026
    for Vd in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4):
        # alpha-power law delay model
        alpha_p = 1.3
        d = Vd / max((Vd - Vth), 1e-3) ** alpha_p
        d0 = 1.0 / (1.0 - Vth) ** alpha_p
        dyn = (Vd / 1.0) ** 2 * (d0 / d)         # at max frequency for that voltage
        leak = Vd / 1.0 * math.exp((1.0 - Vd) * 0)  # supply term only; DIBL omitted
        rows.append([num(Vd, 3), num(d / d0, 4), num(1 / (d / d0), 4),
                     num(dyn, 4), num((Vd / 1.0) ** 2, 4),
                     num((Vd / 1.0) ** 2 * (d / d0), 4)])
    s.append(sweep("Voltage scaling with an &alpha;-power-law delay model "
                   "(<i>V</i><sub>th</sub> = 0.30&nbsp;V, &alpha; = 1.3), normalised "
                   "to 1.0&nbsp;V",
        ["<i>V</i><sub>dd</sub> (V)", "Relative delay", "Relative <i>f</i><sub>max</sub>",
         "Relative power at <i>f</i><sub>max</sub>", "Relative power at fixed <i>f</i>",
         "<b>Relative energy per operation</b>"], rows,
        "The last column is the one that matters for a battery: energy per operation "
        "falls monotonically as the voltage drops, which is why near-threshold operation "
        "is attractive, while the frequency column says what it costs in throughput. "
        "Leakage is deliberately excluded here and X7.3 puts it back."))
    s.append(plot([1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
                  [("energy/op", [(Vd ** 2) * ((Vd / max(Vd - 0.30, 1e-3) ** 1.3) /
                                               (1.0 / (1 - 0.30) ** 1.3))
                                  for Vd in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4)]),
                   ("relative fmax", [((1.0 / (1 - 0.30) ** 1.3) /
                                       (Vd / max(Vd - 0.30, 1e-3) ** 1.3))
                                      for Vd in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4)])],
                  "supply voltage (V)", "normalised",
                  "Energy per operation and maximum frequency against supply. The "
                  "curves cross; where they cross is a design decision, not a fact."))
    s.append("""<div class="ms"><b>Parallelism converts the voltage curve into a genuine
    win, and this is the single most important architectural consequence of the table
    above.</b> Suppose a block must deliver throughput <i>T</i>. Run one copy at
    1.0&nbsp;V, or two copies at the voltage that halves the frequency. The two copies
    have twice the capacitance but each switches half as often per unit of work, so
    dynamic power is 2 &times; (<i>V</i>&prime;/<i>V</i>)<sup>2</sup> &times; &frac12; =
    (<i>V</i>&prime;/<i>V</i>)<sup>2</sup> of the original. From the table, halving the
    frequency permits roughly a 0.65&nbsp;V supply, giving about
    0.42&times; the power for the same throughput at rather more than twice the area.
    <b>This calculation is the reason modern chips are wide and slow rather than narrow
    and fast</b>, and it is worth being able to do it on a whiteboard.</div>""")

    s.append("<h2>X7.3 Leakage, and why it changes the shape of everything</h2>")
    rows = []
    for T in (0, 25, 50, 75, 100, 125):
        kTq = 8.617e-5 * (T + 273.15)
        rel = math.exp(-0.30 / (1.3 * kTq)) / math.exp(-0.30 / (1.3 * 8.617e-5 * 298.15))
        rows.append([num(T), num(kTq * 1000, 4), num(rel, 3),
                     num(rel * 0.20 / (rel * 0.20 + 0.80) * 100, 3)])
    s.append(sweep("Subthreshold leakage against temperature, normalised to 25&nbsp;&deg;C "
                   "(<i>V</i><sub>th</sub> = 0.30&nbsp;V, <i>n</i> = 1.3), and its share "
                   "of a block that is 20&nbsp;% leakage at room temperature",
        ["<i>T</i> (&deg;C)", "<i>nkT/q</i> (mV)", "Relative leakage",
         "Leakage share of total (%)"], rows,
        "Computed from the subthreshold exponential alone; DIBL and gate leakage would "
        "steepen it further. The share column shows why a block that is a fifth leakage "
        "on the bench can be nearly half leakage in a hot enclosure."))
    s.append("""<div class="warn"><b>Leakage and temperature form a positive feedback
    loop.</b> Leakage raises power, power raises junction temperature, and higher
    temperature raises leakage exponentially. Below a certain thermal resistance the loop
    has a stable operating point; above it there is none, and the part runs away. This is
    not a theoretical concern in high-leakage processes: it is why datasheets specify a
    maximum junction temperature <i>and</i> a maximum case-to-ambient thermal resistance,
    and why a customer who improves cooling is not merely buying margin but may be buying
    stability. An IP vendor should state the leakage current at the maximum rated
    temperature, not at 25&nbsp;&deg;C.</div>""")
    s.append(tab("Power reduction techniques, what each attacks, and what it costs",
        ["Technique", "Attacks", "Typical saving", "Cost", "Who decides"],
        [["<b>Clock gating</b>", "&alpha; on the clock tree", "<b>20&ndash;40&nbsp;%</b>",
          "A few gates; <b>timing on the enable</b>", "The RTL designer &mdash; "
          "automatic gating catches most of it"],
         ["Operand isolation", "&alpha; in unused datapath", "5&ndash;15&nbsp;%",
          "Muxes in the datapath", "RTL designer"],
         ["Multi-<i>V</i><sub>th</sub> cells", "Leakage", "2&ndash;5&times; on leakage",
          "Slower cells on non-critical paths", "Implementation, automatic"],
         ["<b>Power gating</b>", "<b>Leakage, to near zero</b>",
          "<b>&gt;90&nbsp;% when idle</b>",
          "Switch area, IR drop, wake latency, <b>state retention</b>",
          "Architecture &mdash; it changes the reset and verification plan"],
         ["DVFS", "<i>V</i><sup>2</sup><i>f</i>", "2&ndash;5&times; at low load",
          "Regulator, level shifters, <b>characterisation at every operating point</b>",
          "System, with IP support"],
         ["Architectural parallelism", "<i>V</i><sup>2</sup> via lower <i>f</i>",
          "2&ndash;3&times;", "Area, latency", "Architecture, early &mdash; it cannot "
          "be retrofitted"],
         ["Memory banking / sub-banking", "<i>C</i> per access",
          "10&ndash;30&nbsp;% of memory power", "Decode logic, floorplan",
          "Architecture"]]))
    s.append(ex("The savings are not additive &mdash; a worked composition",
        "A block is 100&nbsp;mW: 60&nbsp;mW clock, 25&nbsp;mW logic, 15&nbsp;mW leakage. "
        "Clock gating removes 60&nbsp;% of clock power; multi-<i>V</i><sub>th</sub> "
        "removes 60&nbsp;% of leakage; operand isolation removes 30&nbsp;% of logic "
        "power.",
        "Apply each to its own term and re-total. Then compute what a naive addition of "
        "the three quoted percentages would have predicted.",
        [("Clock after gating", num(60 * 0.4, 3, "mW")),
         ("Logic after isolation", num(25 * 0.7, 3, "mW")),
         ("Leakage after multi-<i>V</i><sub>th</sub>", num(15 * 0.4, 3, "mW")),
         ("New total", num(60 * 0.4 + 25 * 0.7 + 15 * 0.4, 4, "mW")),
         ("Actual saving", num(100 - (60 * 0.4 + 25 * 0.7 + 15 * 0.4), 4, "mW")),
         ("Actual saving (%)", num(100 - (60 * 0.4 + 25 * 0.7 + 15 * 0.4), 3, "%")),
         ("Naive sum of the three quoted percentages", num(60 + 60 + 30, 3, "%")),
         ("Clock share before / after",
          num(60, 3) + "% / " + num(60 * 0.4 / (60 * 0.4 + 25 * 0.7 + 15 * 0.4) * 100, 3) + "%")],
        "<b>By adding percentages that are percentages of different things.</b> Each "
        "technique reduces one term, and after it has done so that term is a smaller "
        "share, which is why the second technique applied always returns less than its "
        "headline. The corollary is a procedure: <b>always attack the largest term "
        "first</b>, re-profile, and only then choose the next technique. A power plan "
        "written as a list of techniques without a breakdown to apply them to is not a "
        "plan."))
    s.append(prob("A customer reports that your block consumes 2&times; the datasheet "
                  "figure. List the measurements that distinguish the possible causes, "
                  "in the order you would make them.",
        "<b>1. Compare activity factors.</b> The datasheet figure was measured with some "
        "stimulus; ask what theirs is. A block specified on random data and used on "
        "highly correlated data &mdash; or the reverse &mdash; can differ by a factor of "
        "two with nothing wrong. This is the most common cause and the cheapest to check. "
        "<b>2. Check the clock-gating enables are actually asserting</b>, by toggling "
        "coverage or by a scope on the gated clock; an integration that ties an enable "
        "high disables the largest single saving. <b>3. Split dynamic from leakage</b> by "
        "measuring at two temperatures: leakage doubles over 40&nbsp;&deg;C or so and "
        "dynamic does not, so two points separate the terms. <b>4. Check the supply</b> "
        "&mdash; a 10&nbsp;% overvoltage is a 21&nbsp;% dynamic increase. <b>5. Only then "
        "suspect the block.</b> Note that the first four are questions about the "
        "customer's system, and asking them requires having recorded your own measurement "
        "conditions; a datasheet power figure without its stimulus, voltage and "
        "temperature is unfalsifiable and therefore worthless in exactly this "
        "conversation."))
    return "\n".join(s)
