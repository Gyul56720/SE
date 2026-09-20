# -*- coding: utf-8 -*-
"""Volume I, Part X32 -- The power delivery network, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_pdn():
    b = []
    items = [("VRM", 14, "ms"), ("bulk C", 88, "&micro;s"), ("board C", 162, "ns"),
             ("package C", 236, "ns"), ("on-die C", 310, "ps")]
    for nm, x, t in items:
        b.append(box(x, 30, 64, 30, nm, None, 9))
        if x > 14:
            b.append(arr(x - 10, 45, x, 45))
        b.append(txt(x + 32, 74, t, 8, "middle"))
    b.append(arr(384, 45, 406, 45))
    b.append(txt(410, 48, "load", 9))
    b.append(txt(200, 96, "Each stage covers a different decade of time.", 9, "middle"))
    b.append(txt(200, 110, "A gap between two of them is an impedance peak, and an "
                           "impedance peak is a droop.", 9, "middle",
                 'font-style="italic"'))
    return svg(450, 120, "".join(b))


def ch_pdn():
    s = ['<h1 id="x32">X32. The Power Delivery Network, Worked</h1>']
    s.append("""<p>Every timing number in Part&nbsp;X2 assumed a supply voltage. The
    network that delivers it is a distributed RLC structure whose impedance must be low
    across six decades of frequency, and when it is not, the result is a voltage droop
    that shows up as a timing failure nobody can reproduce. This is a digital designer's
    problem even though it looks like an analogue one.</p>""")
    s.append(fig(_f_pdn(), "The power delivery hierarchy. Each element handles a "
                           "different timescale because each is limited by its own "
                           "parasitic inductance."))

    s.append("<h2>X32.1 Target impedance, and where the number comes from</h2>")
    s.append(derive("From a droop budget to an impedance specification", [
        ("The supply must stay within &plusmn;&delta; of nominal for the timing "
         "libraries to apply.",
         "Typically 5&nbsp;%. Outside it, the delays are not the ones you signed off "
         "with."),
        ("A current step &Delta;<i>I</i> produces a voltage "
         "<i>Z</i>(<i>f</i>)&Delta;<i>I</i>.",
         "Ohm's law for an impedance."),
        ("<b>Target impedance <i>Z</i><sub>t</sub> = "
         "&delta;<i>V</i><sub>dd</sub>/&Delta;<i>I</i><sub>max</sub>.</b>",
         "<b>The one number the whole PDN is designed to</b>, and it must be met at "
         "<i>every</i> frequency, not on average."),
        ("&Delta;<i>I</i><sub>max</sub> is the worst-case step, not the average "
         "current.",
         "A clock-gated block waking up, or a test pattern that toggles everything, "
         "is a far larger step than any functional average &mdash; which is why "
         "maximum-toggle test patterns can fail a part that works in its application."),
        ("Falling voltage and rising current per node make "
         "<i>Z</i><sub>t</sub> shrink every generation, quadratically.",
         "<b>This is why PDN design has become progressively harder</b> rather than "
         "benefiting from scaling."),
    ]))
    rows = []
    for vdd, i_max, node in ((1.8, 2.0, "180 nm"), (1.2, 10.0, "90 nm"),
                             (1.0, 40.0, "28 nm"), (0.8, 120.0, "7 nm"),
                             (0.75, 250.0, "5 nm")):
        zt = 0.05 * vdd / i_max
        rows.append([node, num(vdd, 3), num(i_max, 4), num(zt * 1e3, 4),
                     num(vdd * i_max, 5), num(0.05 * vdd * 1e3, 4)])
    s.append(sweep("Target impedance across process generations (5&nbsp;% droop budget)",
        ["Node", "<i>V</i><sub>dd</sub> (V)", "Peak current (A)",
         "<i>Z</i><sub>t</sub> (m&Omega;)", "Peak power (W)", "Droop budget (mV)"],
        rows,
        "The current figures are indicative of a large SoC at each generation rather "
        "than any specific part. <b>The impedance target falls by more than two orders "
        "of magnitude across the table</b>, which is why on-die decoupling and "
        "integrated voltage regulators appeared."))
    s.append(ex("Sizing on-die decoupling capacitance",
        "A block draws 5&nbsp;A when active and is clock-gated. On wake-up the current "
        "rises in 2&nbsp;ns. The package inductance is 100&nbsp;pH and the droop budget "
        "is 40&nbsp;mV.",
        "The package cannot supply current faster than its inductance allows, so "
        "on-die capacitance must cover the interval until the package catches up. "
        "Compute the charge needed and hence the capacitance.",
        [("Current step", num(5, 3, "A")),
         ("Rise time", num(2, 3, "ns")),
         ("<i>L</i> d<i>i</i>/d<i>t</i> if the package had to supply it",
          num(100e-12 * 5 / 2e-9 * 1e3, 4, "mV")),
         ("Droop budget", num(40, 3, "mV")),
         ("Verdict", "<b>the package alone exceeds the budget by 6&times;</b>"),
         ("Charge to supply during the step", num(5 * 2e-9 * 0.5 * 1e9, 4, "nC")),
         ("Capacitance for a 40&nbsp;mV droop",
          num(5 * 2e-9 * 0.5 / 40e-3 * 1e9, 4, "nF")),
         ("Area at 10&nbsp;fF/&micro;m&sup2; (MOS cap)",
          num(5 * 2e-9 * 0.5 / 40e-3 / 10e-15 / 1e6, 4, "mm&sup2;"))],
        "<b>By budgeting only the resistive drop.</b> At a nanosecond timescale the "
        "package is an inductor, not a wire, and <i>L</i>d<i>i</i>/d<i>t</i> dominates "
        "the static <i>IR</i> term by a large factor. <b>The remedy is not lower "
        "resistance but local charge storage</b>, and the area it costs is real &mdash; "
        "on-die decoupling is commonly several per cent of die area and in some designs "
        "more than ten. A second, cheaper remedy belongs to the digital designer: "
        "<b>ramp the current instead of stepping it</b>, by staging the clock-gate "
        "release across several cycles, which is a few gates of logic and can reduce the "
        "required capacitance by a large factor."))

    s.append("<h2>X32.2 Resonance: the peak that puts the droop where you are not "
             "looking</h2>")
    rows = []
    for L, C, R in ((1e-9, 100e-9, 5e-3), (1e-9, 1e-6, 5e-3), (100e-12, 100e-9, 2e-3),
                    (100e-12, 10e-9, 2e-3), (10e-12, 100e-9, 1e-3)):
        f0 = 1 / (2 * math.pi * math.sqrt(L * C))
        z0 = math.sqrt(L / C)
        qf = z0 / R
        rows.append([num(L * 1e12, 5), num(C * 1e9, 5), num(R * 1e3, 4),
                     num(f0 / 1e6, 5), num(qf, 4), num(qf * R * 1e3, 4)])
    s.append(sweep("Resonant peaks formed by each inductance with the capacitance "
                   "below it",
        ["<i>L</i> (pH)", "<i>C</i> (nF)", "<i>R</i> (m&Omega;)",
         "Resonant frequency (MHz)", "<i>Q</i>", "Peak impedance (m&Omega;)"], rows,
        "Every inductance in the hierarchy resonates with the capacitance on the load "
        "side of it, and at resonance the impedance is <i>Q</i> times the series "
        "resistance. <b>A high-<i>Q</i> peak is the dangerous case</b>: if the current "
        "spectrum has energy there, the droop is far worse than the target impedance "
        "suggests."))
    s.append("""<div class="warn"><b>The first-droop, second-droop, third-droop language
    engineers use is just this resonance hierarchy, and the dangerous one is usually the
    mid-frequency droop.</b> The first droop (hundreds of megahertz) is handled by on-die
    capacitance; the third (kilohertz) by the regulator's control loop. The second &mdash;
    tens to a couple of hundred megahertz, set by package inductance against on-die
    capacitance &mdash; sits in a gap between the two remedies and is where the highest-Q
    peak usually lands. <b>It is also, unhelpfully, right where a processor's activity
    changes</b>: a loop that alternates between a heavy and a light phase at that rate
    excites it directly, which is the origin of the classic &lsquo;this benchmark fails
    and that one does not&rsquo; report. The digital remedies are to add damping (series
    resistance in some decoupling, deliberately), to spread activity in time, and to use
    an adaptive clock that stretches the period when a droop is detected &mdash; which
    converts a functional failure into a small performance loss and is now common in
    large processors.</div>""")

    s.append("<h2>X32.3 Electromigration and the static budget</h2>")
    rows = []
    for w_um in (0.1, 0.2, 0.5, 1.0, 2.0):
        jmax = 1.5e6                       # A/cm2, indicative
        thick = 0.2e-4                     # cm
        area_cm2 = (w_um * 1e-4) * thick
        imax = jmax * area_cm2
        rows.append([num(w_um, 3), num(area_cm2 * 1e8, 5), num(imax * 1e3, 5),
                     num(imax * 1e3 / w_um, 5), num(1 / (w_um * 1e-4) * 2.2e-6 * 1e6, 5)])
    s.append(sweep("Current a wire can carry before electromigration limits its life "
                   "(indicative 1.5&times;10<sup>6</sup> A/cm&sup2;, 0.2&nbsp;&micro;m "
                   "thick)",
        ["Width (&micro;m)", "Cross-section (&times;10<sup>&minus;8</sup>&nbsp;cm&sup2;)",
         "Max current (mA)", "mA per &micro;m of width",
         "Resistance per &micro;m length (&micro;&Omega;)"], rows,
        "<b>Indicative constants, not a PDK.</b> The useful content is the third column: "
        "a few milliamps per micron of width is the order of magnitude, so a 5&nbsp;A "
        "block needs of the order of a millimetre of total metal width to feed it &mdash; "
        "which is why power grids are wide, numerous and on the thick upper metal "
        "layers."))
    s.append(prob("Your block passes timing in every corner and fails intermittently in "
                  "silicon at high activity. How do you decide whether it is the PDN?",
        "Look for the signature, which is specific and distinguishable. <b>A PDN-induced "
        "failure is activity dependent rather than pattern dependent</b>: it appears when "
        "many things switch at once, not when a particular logical case occurs, so a test "
        "that toggles a lot fails while a functionally harder but quieter test passes. "
        "<b>It moves with supply and with frequency in a particular way</b>: raising the "
        "supply helps more than it should for a simple timing problem, because it "
        "increases the margin against droop as well as speeding the logic. <b>It "
        "correlates with di/dt, not with average power</b>, so a test with the same "
        "average current but smoother activity passes. The measurements that settle it "
        "are an on-die droop monitor if one exists &mdash; and if none exists, that is "
        "the lesson for the next design, because a ring-oscillator-based droop detector "
        "is a few hundred gates &mdash; and an experiment that staggers the wake-up of "
        "the block's clock-gating domains, which changes only di/dt. <b>If staggering "
        "fixes it, the PDN is the cause and the cheapest fix is the staggering you just "
        "used to diagnose it.</b>"))
    return "\n".join(s)
