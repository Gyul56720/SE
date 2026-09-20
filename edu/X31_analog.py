# -*- coding: utf-8 -*-
"""Volume I, Part X31 -- Analogue building blocks a digital designer must budget."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

K = 1.380649e-23
T = 300.0
QE = 1.602176634e-19


def ch_analog2():
    s = ['<h1 id="x31">X31. Analogue Building Blocks, Budgeted</h1>']
    s.append("""<p>A digital designer does not size transistors, but does have to say
    whether an analogue requirement is reasonable before committing to an architecture.
    The quantities that answer that are few and computable: thermal noise, matching,
    gain-bandwidth and settling. This part gives them.</p>""")

    s.append("<h2>X31.1 <i>kT</i>/<i>C</i> &mdash; the noise floor you cannot design away</h2>")
    s.append(derive("Why sampled noise depends only on the capacitor", [
        ("A switch has resistance <i>R</i>; its thermal noise density is "
         "4<i>kTR</i> V&sup2;/Hz.",
         "Johnson&ndash;Nyquist."),
        ("The RC network's noise bandwidth is 1/(4<i>RC</i>).",
         "Integrating a single-pole response gives &pi;/2 times the 3&nbsp;dB "
         "bandwidth."),
        ("So the sampled noise power is 4<i>kTR</i> &middot; 1/(4<i>RC</i>) = "
         "<b><i>kT</i>/<i>C</i></b>.",
         "<b>The resistance cancels.</b> A better switch does not help; only a bigger "
         "capacitor does."),
        ("Doubling resolution means halving the noise voltage, which means "
         "<b>quadrupling the capacitor</b>.",
         "And capacitance is area, and it is also the load the driver must charge, so "
         "power rises too."),
        ("<b>Each extra bit of a sampled system costs 4&times; the capacitor and "
         "roughly 4&times; the power.</b>",
         "This single relation explains the shape of every converter's "
         "energy-per-conversion curve above about 10 bits."),
    ]))
    rows = []
    for C in (10e-15, 100e-15, 1e-12, 10e-12, 100e-12):
        vn = math.sqrt(K * T / C)
        for vfs in (1.0,):
            snr = 20 * math.log10(vfs / (2 * math.sqrt(2)) / vn)
        rows.append([num(C * 1e15, 5), num(vn * 1e6, 5), num(snr, 4),
                     num((snr - 1.76) / 6.02, 4), num(C * 1e15 * 0.5, 5)])
    s.append(sweep("<i>kT</i>/<i>C</i> noise and the resolution it permits "
                   "(1&nbsp;V full scale, 300&nbsp;K)",
        ["Capacitance (fF)", "RMS noise (&micro;V)", "SNR (dB)", "ENOB",
         "Approx. area (&micro;m&sup2; at 2&nbsp;fF/&micro;m&sup2;)"], rows,
        "Computed from <i>kT</i>/<i>C</i> alone, ignoring every other noise source, so "
        "these are optimistic. <b>A 14-bit sampled system needs picofarads</b>, and "
        "the area and power that implies is why high-resolution converters are large "
        "and why oversampling architectures, which trade speed for resolution, "
        "exist."))
    s.append(ex("Can this ADC specification be met?",
        "A customer asks for a 16-bit, 100&nbsp;MS/s SAR ADC on 1&nbsp;V supply, "
        "&lsquo;small area&rsquo;.",
        "Work the <i>kT</i>/<i>C</i> requirement, then the settling requirement, then "
        "compare against what the process offers.",
        [("Required SNR for 16 bits", num(6.02 * 16 + 1.76, 5, "dB")),
         ("Signal RMS at 1&nbsp;V full scale",
          num(1.0 / (2 * math.sqrt(2)) * 1e3, 4, "mV")),
         ("Permitted noise RMS",
          num(1.0 / (2 * math.sqrt(2)) / 10 ** ((6.02 * 16 + 1.76) / 20) * 1e6, 4,
              "&micro;V")),
         ("Required capacitance",
          num(K * T / (1.0 / (2 * math.sqrt(2)) /
                       10 ** ((6.02 * 16 + 1.76) / 20)) ** 2 * 1e12, 5, "pF")),
         ("Array area at 2&nbsp;fF/&micro;m&sup2;",
          num(K * T / (1.0 / (2 * math.sqrt(2)) /
                       10 ** ((6.02 * 16 + 1.76) / 20)) ** 2 * 1e15 / 2, 5,
              "&micro;m&sup2;")),
         ("Settling time available at 100&nbsp;MS/s, 16 SAR cycles",
          num(1 / 100e6 / 16 * 1e12, 4, "ps")),
         ("Time constants needed for 16-bit settling",
          num(16 * math.log(2), 4)),
         ("Required RC", num(1 / 100e6 / 16 / (16 * math.log(2)) * 1e12, 4, "ps")),
         ("Verdict", "<b>the capacitor and the settling requirement are in direct "
          "conflict</b>")],
        "<b>By treating &lsquo;16-bit&rsquo; and &lsquo;100&nbsp;MS/s&rsquo; as "
        "independent requirements.</b> The noise requirement forces a large capacitor; "
        "the speed requirement forces that capacitor to settle in picoseconds, which "
        "forces a very low switch resistance and therefore an enormous switch, which "
        "loads the previous stage. This is why 16 bits at 100&nbsp;MS/s is a "
        "time-interleaved or pipelined architecture and not a single SAR, and why the "
        "answer to the customer is a <b>question about their actual SNR requirement in "
        "the signal band</b> &mdash; if they need 16 bits over 1&nbsp;MHz rather than "
        "over 50&nbsp;MHz, oversampling changes the arithmetic completely."))

    s.append("<h2>X31.2 Matching: why analogue area is set by statistics</h2>")
    s.append(derive("Pelgrom's law", [
        ("Threshold voltage varies between nominally identical devices because of "
         "random dopant fluctuation and line-edge roughness.",
         "A counting phenomenon: fewer dopants under a smaller gate means larger "
         "relative variation."),
        ("The standard deviation of the mismatch between two devices is "
         "&sigma;<sub>&Delta;<i>V</i>th</sub> = "
         "<i>A</i><sub>VT</sub>/&radic;(<i>WL</i>).",
         "Pelgrom's law, verified across many processes. <i>A</i><sub>VT</sub> is a "
         "process constant of a few mV&middot;&micro;m."),
        ("<b>So halving the mismatch requires four times the area.</b>",
         "The same 4&times; law as <i>kT</i>/<i>C</i>, arriving from a completely "
         "different mechanism."),
        ("A comparator's input-referred offset is this mismatch; a current mirror's "
         "error is proportional to it.",
         "Which sets the minimum size of every matched pair in a converter."),
        ("<b>Digital calibration converts area into computation.</b>",
         "Measure the offset once, store it, subtract it. <b>This is the dominant trend "
         "in mixed-signal design</b> and the reason the digital content of converters "
         "keeps growing."),
    ]))
    rows = []
    AVT = 3.5e-3
    for area in (0.01, 0.1, 1.0, 10.0, 100.0):
        sig = AVT / math.sqrt(area)
        for vfs in (1.0,):
            bits_ok = math.log2(vfs / (6 * sig)) if sig > 0 else 0
        rows.append([num(area, 4), num(sig * 1e3, 4), num(6 * sig * 1e3, 4),
                     num(bits_ok, 4), num(area * 2, 4)])
    s.append(sweep("Pelgrom matching against device area "
                   "(<i>A</i><sub>VT</sub> = 3.5&nbsp;mV&middot;&micro;m)",
        ["<i>WL</i> (&micro;m&sup2;)", "&sigma;<sub>&Delta;<i>V</i>th</sub> (mV)",
         "3&sigma; spread (mV)", "Bits resolvable without calibration at 1&nbsp;V FS",
         "Pair area (&micro;m&sup2;)"], rows,
        "<b>Without calibration, matching alone limits an uncalibrated comparator to "
        "about eight bits at sane areas.</b> Every converter above that resolution "
        "calibrates, and the calibration engine is digital &mdash; which is how a "
        "digital designer ends up owning a large part of an analogue block."))
    s.append("""<div class="ms"><b>The calibration trade, stated as arithmetic.</b> Suppose
    a comparator needs 1&nbsp;mV of offset. Pelgrom says that costs about
    12&nbsp;&micro;m&sup2; of gate area per device, and in a 64-way time-interleaved ADC
    that is repeated 64 times, in the fastest and most power-hungry part of the chip.
    Alternatively, build a minimum-size comparator with 10&nbsp;mV of offset and add a
    trim DAC plus a digital loop that measures and cancels it. The trim DAC is small, the
    loop is a counter and a comparator, and the whole thing is synthesised. <b>The
    crossover is far to the digital side and moves further every process node</b>, because
    digital area shrinks and <i>A</i><sub>VT</sub> improves only slowly. This is the
    single clearest instance of the general trend this book keeps meeting: <b>buy analogue
    precision with digital computation.</b></div>""")

    s.append("<h2>X31.3 Gain, bandwidth and settling</h2>")
    rows = []
    for bits in (8, 10, 12, 14, 16):
        eps = 2.0 ** -(bits + 1)
        taus = -math.log(eps)
        dc_gain_db = 20 * math.log10(2 ** (bits + 1))
        rows.append([num(bits), num(eps, 3), num(taus, 4),
                     num(dc_gain_db, 4), num(taus / (2 * math.pi), 4)])
    s.append(sweep("What a resolution demands of an amplifier",
        ["Bits", "Settling accuracy", "Time constants needed",
         "Minimum open-loop DC gain (dB)", "Settling in units of 1/GBW"], rows,
        "Static accuracy needs loop gain (finite gain leaves a proportional error); "
        "dynamic accuracy needs time constants. <b>16-bit accuracy needs about "
        "100&nbsp;dB of DC gain and twelve time constants</b>, and those two "
        "requirements fight each other because high gain means more stages means more "
        "poles means harder compensation."))
    s.append(tab("The analogue specifications a digital architect should be able to "
                 "sanity check",
        ["Quantity", "Rule of thumb", "If the requirement exceeds it"],
        [["Sampled SNR", "<i>kT</i>/<i>C</i>; 14 bits needs &gt;1&nbsp;pF at 1&nbsp;V",
          "Oversample, or relax full scale, or use a different architecture"],
         ["Uncalibrated comparator offset",
          "Pelgrom; ~8 bits at sensible area", "<b>Add digital calibration</b>"],
         ["Amplifier DC gain", "~6&nbsp;dB per bit",
          "Gain boosting, or a correlated-double-sampling scheme"],
         ["<b>Aperture jitter</b>",
          "<b>SNR = &minus;20log(2&pi;<i>f</i><sub>in</sub>&sigma;<sub><i>t</i></sub>) "
          "&mdash; Part&nbsp;X12</b>",
          "<b>A better clock, not a better converter</b>"],
         ["Reference noise", "Appears directly at the output",
          "Filter it; and remember the filter capacitor is area too"],
         ["Supply rejection", "Falls with frequency; poor above the loop bandwidth",
          "This is why the PDN of Part&nbsp;X32 matters to analogue blocks"]]))
    s.append(prob("Your digital block shares a supply with an ADC and the customer "
                  "reports spurs at your clock frequency. Whose problem is it?",
        "Both of yours, and the useful response is to find out which mechanism rather "
        "than which party. There are three paths and they are distinguishable by "
        "measurement. <b>Supply coupling</b>: your switching current modulates the shared "
        "rail, and the converter's finite power-supply rejection turns that into an input "
        "offset; test by changing your block's activity and watching whether the spur "
        "amplitude tracks, and by separating the supplies if the board permits. "
        "<b>Substrate coupling</b>: switching current injects into the substrate and "
        "reaches the converter's sensitive nodes; this is layout, and the remedies are "
        "guard rings, deep n-well isolation and distance. <b>Clock coupling</b>: your "
        "clock capacitively couples into the sampling network, which is the worst of the "
        "three because it lands exactly at a fixed frequency and its harmonics. "
        "<b>The digital side's contribution, and it is a real one, is to reduce di/dt</b>: "
        "spread the clock tree's switching with deliberate skew, gate clocks aggressively "
        "so the average current is lower, add on-chip decoupling, and avoid large "
        "simultaneous switching events. <b>None of that is exotic, and all of it is far "
        "cheaper than asking the analogue designer for another 20&nbsp;dB of supply "
        "rejection</b>, which may not be available at any price."))
    return "\n".join(s)
