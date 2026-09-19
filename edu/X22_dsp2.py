# -*- coding: utf-8 -*-
"""Volume I, Part X22 -- Resampling, timing recovery and the Farrow structure."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_resample():
    s = ['<h1 id="x22">X22. Resampling and Timing Recovery, Worked</h1>']
    s.append("""<p>Whenever two clocks that are not derived from each other meet a data
    stream, something must resample. In an audio codec it is a sample-rate converter; in a
    receiver it is the timing-recovery interpolator; in a video pipeline it is a scaler.
    The mathematics is the same and the hardware structure that solves it &mdash; the
    Farrow filter &mdash; is worth knowing in detail because it appears everywhere and is
    rarely taught.</p>""")

    s.append("<h2>X22.1 The problem: a sample that was never taken</h2>")
    s.append(derive("Interpolation as filtering, and why a fixed filter is not enough", [
        ("An ideal band-limited signal can be reconstructed exactly from its samples by "
         "convolution with a sinc.", "Sampling theorem."),
        ("So the value at any intermediate instant &mu; is a weighted sum of "
         "neighbouring samples, with weights sinc(<i>k</i>&nbsp;&minus;&nbsp;&mu;).",
         "Evaluate the reconstruction at that instant. <b>The weights depend on "
         "&mu;.</b>"),
        ("For a fixed &mu; this is one FIR filter, and a set of <i>L</i> fixed filters "
         "gives <i>L</i> discrete phases.",
         "The polyphase interpolator: fine when the phase set is known in advance."),
        ("<b>Timing recovery needs a &mu; that varies continuously and is not known in "
         "advance.</b>",
         "The sampling phase drifts with the frequency offset between transmitter and "
         "receiver, by an amount nobody can tabulate."),
        ("Farrow's insight: approximate each weight as a <i>polynomial in &mu;</i>, "
         "<i>h<sub>k</sub></i>(&mu;) = &Sigma;<i>c<sub>k,m</sub></i>&mu;<sup><i>m</i></sup>.",
         "Then the interpolator becomes <i>M</i>+1 <b>fixed</b> FIR filters whose "
         "outputs are combined by Horner's rule in &mu;."),
        ("<b>The coefficients are constant; only &mu; changes.</b>",
         "So the multipliers can be constant-coefficient, and a continuously variable "
         "delay costs <i>M</i> general multiplies rather than a new filter per "
         "phase."),
    ]))
    # measure interpolation error of cubic Farrow
    def farrow_cubic(x, mu, n):
        """Cubic (Catmull-Rom style) Farrow interpolation at index n + mu."""
        xm1, x0, x1, x2 = x[n - 1], x[n], x[n + 1], x[n + 2]
        c3 = (-xm1 + 3 * x0 - 3 * x1 + x2) / 6.0
        c2 = (xm1 - 2 * x0 + x1) / 2.0
        c1 = (-2 * xm1 - 3 * x0 + 6 * x1 - x2) / 6.0
        c0 = x0
        return ((c3 * mu + c2) * mu + c1) * mu + c0
    rows = []
    N = 4096
    n = np.arange(N)
    for fnorm in (0.02, 0.05, 0.10, 0.20, 0.35, 0.45):
        x = np.sin(2 * np.pi * fnorm * n)
        errs = []
        for mu in np.linspace(0.0, 1.0, 21):
            idx = np.arange(4, N - 4)
            got = np.array([farrow_cubic(x, mu, int(i)) for i in idx[::37]])
            want = np.sin(2 * np.pi * fnorm * (idx[::37] + mu))
            errs.append(np.abs(got - want).max())
        e = float(np.max(errs))
        rows.append([num(fnorm, 3), num(fnorm * 2, 3), num(e, 3),
                     num(-20 * math.log10(max(e, 1e-16)), 4)])
    s.append(sweep("Measured worst-case error of a cubic Farrow interpolator against "
                   "input frequency, swept over all fractional delays",
        ["Normalised frequency", "Fraction of Nyquist", "Max |error|",
         "Equivalent SNR (dB)"], rows,
        "Computed directly by comparing against the exact sine. <b>The interpolator is "
        "excellent well below Nyquist and degrades rapidly above about a third of "
        "it</b>, which is the whole reason receivers oversample: the interpolator's "
        "accuracy, not the sampling theorem, sets the required rate."))
    s.append(plot([0.02, 0.05, 0.10, 0.20, 0.35, 0.45],
                  [("SNR (dB)", [float(r[3]) for r in rows])],
                  "normalised input frequency", "interpolator SNR (dB)",
                  "Cubic Farrow interpolation accuracy. Choosing the oversampling ratio "
                  "is choosing a point on this curve."))
    s.append(ex("How much oversampling does a link need for its interpolator?",
        "A receiver needs the interpolator to contribute no more than &minus;40&nbsp;dB "
        "of error, and the signal occupies the full symbol bandwidth.",
        "Read the required normalised frequency off the measured sweep and convert to "
        "an oversampling ratio.",
        [("Target interpolator SNR", num(40, 3, "dB")),
         ("Normalised frequency achieving it (from the sweep)",
          "between " + num(0.10, 3) + " and " + num(0.20, 3)),
         ("Oversampling ratio needed", "roughly 5&ndash;10&times; the signal bandwidth"),
         ("At 2 samples per symbol, signal edge sits at", num(0.25, 3)),
         ("Verdict at 2 samples/symbol with a cubic",
          "<b>marginal &mdash; use a higher-order Farrow or more oversampling</b>"),
         ("Cost of a higher order", "one more fixed FIR and one more Horner stage")],
        "<b>By choosing the oversampling ratio from the sampling theorem alone.</b> "
        "Nyquist says two samples per symbol suffices to represent the signal; it says "
        "nothing about reconstructing an intermediate sample with a short polynomial. "
        "<b>The interpolator, not the theorem, sets the rate</b>, and the trade is "
        "between ADC power (which scales with rate) and interpolator order (which scales "
        "with area). Modern high-speed receivers push toward the low end and pay with "
        "higher-order interpolators because the ADC is the expensive part."))

    s.append("<h2>X22.2 The timing-recovery loop around it</h2>")
    s.append(tab("The pieces of a digital timing recovery loop",
        ["Block", "Job", "Choice that matters"],
        [["Interpolator", "Produce a sample at the wanted instant",
          "Order, from the sweep above"],
         ["<b>Timing error detector</b>", "<b>Estimate how wrong the instant is</b>",
          "<b>Gardner needs 2 samples/symbol and is modulation-independent; "
          "Mueller&ndash;M&uuml;ller works at 1 sample/symbol and is the standard in "
          "high-speed links for exactly that reason</b>"],
         ["Loop filter", "Proportional plus integral",
          "The proportional term sets bandwidth, the integral term removes frequency "
          "offset"],
         ["NCO / phase accumulator", "Turn the filtered error into &mu; and a "
          "strobe", "Its wrap handling is where the sample-slip logic lives"]]))
    s.append("""<div class="ms"><b>Why the integral term is not optional, stated
    precisely.</b> A proportional-only loop has finite DC gain, so a constant frequency
    offset between transmitter and receiver produces a constant residual phase error
    &mdash; the loop settles to the wrong place and stays there. Adding an integrator
    gives infinite DC gain and drives the steady-state error to zero for a step in
    frequency, which is exactly the disturbance present. The cost is a second-order loop
    with the usual stability question, and the usual answer: the damping factor sets the
    overshoot and the natural frequency sets the tracking bandwidth, both bounded above by
    the loop delay from Part&nbsp;X21. <b>Every CDR, PLL and equaliser adaptation in this
    book has this same second-order structure</b>, and recognising it saves deriving the
    stability condition four times.</div>""")
    s.append(prob("Why do high-speed SerDes receivers use Mueller&ndash;M&uuml;ller "
                  "timing detection rather than Gardner, when Gardner is simpler?",
        "Because Gardner requires two samples per symbol and at 50&nbsp;GBd that doubles "
        "the ADC rate, which is the single most expensive resource in the receiver. "
        "Mueller&ndash;M&uuml;ller estimates the timing error from one sample per symbol "
        "and the decisions, using the correlation between the current decision and the "
        "previous sample; it is decision-directed, so it needs the decisions to be mostly "
        "correct, which is fine in a working link and is a chicken-and-egg problem during "
        "acquisition. <b>The practical consequences are two</b>: acquisition needs help "
        "&mdash; a frequency-acquisition aid, a training pattern, or a temporary "
        "alternative detector &mdash; and the detector's characteristic depends on the "
        "channel response, so the loop gain is not a constant of the design but varies "
        "with the equaliser state. <b>That second point is the interacting-loops hazard "
        "of Part&nbsp;X21 in its most common real form</b>: the timing loop's gain "
        "depends on the equaliser, and the equaliser's error depends on the timing."))
    return "\n".join(s)
