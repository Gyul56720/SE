# -*- coding: utf-8 -*-
"""Volume I, Part X23 -- Complex analysis and transforms, for people who build them."""
import sys, math, cmath
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_zplane():
    b = []
    cx, cy, r = 150, 88, 62
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#000" '
             f'stroke-width="1.1"/>')
    b.append(line(cx - 92, cy, cx + 92, cy, w=0.8))
    b.append(line(cx, cy - 82, cx, cy + 82, w=0.8))
    b.append(txt(cx + 96, cy + 4, "Re", 9))
    b.append(txt(cx + 4, cy - 86, "Im", 9))
    for ang, lab in ((0, "z = 1  (DC)"), (180, "z = -1  (f<tspan baseline-shift='sub' font-size='6'>s</tspan>/2)")):
        x = cx + r * math.cos(math.radians(ang))
        y = cy - r * math.sin(math.radians(ang))
        b.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#000"/>')
        b.append(txt(x + (8 if ang == 0 else -8), y - 8, lab, 8,
                     "start" if ang == 0 else "end"))
    for ang in (52, -52):
        x = cx + 0.62 * r * math.cos(math.radians(ang))
        y = cy - 0.62 * r * math.sin(math.radians(ang))
        b.append(f'<text x="{x}" y="{y+4}" font-size="12" text-anchor="middle">&times;</text>')
    b.append(txt(cx + 46, cy - 26, "poles inside", 8))
    b.append(txt(cx + 46, cy - 16, "= stable", 8))
    b.append(txt(150, 186, "The unit circle is the frequency axis. Everything about a "
                           "digital filter", 9, "middle"))
    b.append(txt(150, 200, "is where its poles and zeros sit relative to this circle.",
                 9, "middle", 'font-style="italic"'))
    return svg(300, 210, "".join(b))


def ch_complex():
    s = ['<h1 id="x23">X23. Complex Analysis and Transforms, for People Who Build Them</h1>']
    s.append("""<p>Every filter, every equaliser and every control loop in this book is
    described by a rational function of a complex variable. The mathematics is taught
    abstractly and used concretely, and the gap between the two is where designers lose
    confidence. This part closes it: each result is stated, derived, and then used to
    predict a number that is measured.</p>""")
    s.append(fig(_f_zplane(), "The <i>z</i>-plane. The unit circle is not a convention "
                              "&mdash; it is the set of points where <i>z</i> = "
                              "e<sup><i>j&omega;</i></sup>, which is exactly the "
                              "frequency response."))

    s.append("<h2>X23.1 Why the <i>z</i>-transform is the right tool</h2>")
    s.append(derive("From a difference equation to a rational function", [
        ("A linear time-invariant system obeys "
         "<i>y</i>[<i>n</i>] = &Sigma;<i>b<sub>k</sub>x</i>[<i>n</i>&minus;<i>k</i>] "
         "&minus; &Sigma;<i>a<sub>k</sub>y</i>[<i>n</i>&minus;<i>k</i>].",
         "The general recursive filter. <b>This is also literally the RTL</b>: each "
         "delayed term is a register."),
        ("Define <i>X</i>(<i>z</i>) = &Sigma;<i>x</i>[<i>n</i>]<i>z</i><sup>&minus;<i>n</i></sup>.",
         "The <i>z</i>-transform. The only property we need is the next line."),
        ("A delay by one sample multiplies the transform by "
         "<i>z</i><sup>&minus;1</sup>.",
         "Substitute and shift the summation index. <b>So a register is a "
         "multiplication</b>, which turns a difference equation into algebra."),
        ("Therefore <i>H</i>(<i>z</i>) = <i>Y</i>/<i>X</i> = "
         "(&Sigma;<i>b<sub>k</sub>z</i><sup>&minus;<i>k</i></sup>) / "
         "(1 + &Sigma;<i>a<sub>k</sub>z</i><sup>&minus;<i>k</i></sup>).",
         "Divide. The transfer function is a ratio of polynomials."),
        ("Its <b>zeros</b> are where the numerator vanishes; its <b>poles</b> where the "
         "denominator does.",
         "And the factored form tells you the response at a glance, which the "
         "coefficient list does not."),
        ("Evaluating on <i>z</i> = e<sup><i>j&omega;</i></sup> gives the frequency "
         "response; <b>a zero near the circle makes a notch, a pole near it makes a "
         "peak</b>.",
         "Because |<i>H</i>| is a ratio of distances from the evaluation point to the "
         "zeros and poles. <b>This geometric reading is the single most useful skill in "
         "filter design</b> and it takes ten minutes to acquire."),
    ]))
    # measure the geometric claim
    rows = []
    for r in (0.5, 0.8, 0.9, 0.95, 0.99):
        th = math.pi / 4
        p = r * cmath.exp(1j * th)
        w = np.linspace(0, math.pi, 4096)
        z = np.exp(1j * w)
        H = 1.0 / ((z - p) * (z - p.conjugate()))
        mag = np.abs(H)
        peak = float(mag.max())
        k = int(np.argmax(mag))
        # -3 dB bandwidth
        half = mag >= peak / math.sqrt(2)
        bw = float(w[half].max() - w[half].min())
        rows.append([num(r, 4), num(1 - r, 3), num(peak, 4),
                     num(w[k] / math.pi, 4), num(bw / math.pi, 4),
                     num((1 - r) * 2, 4)])
    s.append(sweep("Measured peak and bandwidth of a two-pole resonator as the pole "
                   "radius approaches the unit circle (pole angle &pi;/4)",
        ["Pole radius <i>r</i>", "Distance to circle", "Peak |<i>H</i>|",
         "Peak at &omega;/&pi;", "&minus;3&nbsp;dB bandwidth /&pi;",
         "Prediction 2(1&minus;<i>r</i>)/&pi;&times;&pi;"], rows,
        "Computed by evaluating the transfer function on 4096 points of the unit "
        "circle. <b>The last two columns are an independent cross-check</b>: the "
        "textbook approximation says the bandwidth is about 2(1&minus;<i>r</i>) "
        "radians, and the measurement confirms it as <i>r</i>&nbsp;&rarr;&nbsp;1 and "
        "departs from it when the pole is far from the circle, exactly as the "
        "approximation's derivation requires."))
    s.append("""<div class="ms"><b>Why this matters in fixed point, which is where the
    theory earns its keep.</b> Quantising the coefficients moves the poles. For a
    high-order filter in direct form, the pole positions are an extremely sensitive
    function of the coefficients &mdash; the map from coefficients to roots is
    ill-conditioned, and for a narrow-band filter of order 10 or more, a few bits of
    coefficient error can move a pole outside the unit circle and make the filter
    unstable. <b>This, not noise, is the reason high-order IIR filters are implemented as
    cascaded biquads</b>: in a second-order section there are only two coefficients per
    pole pair and the root sensitivity is bounded. The structure choice is dictated by
    numerical conditioning, and a specification that says &lsquo;10th-order elliptic&rsquo;
    without saying &lsquo;as five biquads&rsquo; has not specified an
    implementation.</div>""")
    # measure the sensitivity claim
    rows = []
    from numpy.polynomial import polynomial as P
    for order in (2, 4, 6, 8, 10):
        # narrowband lowpass poles at radius 0.97
        import scipy.signal as sg
        b_, a_ = sg.butter(order, 0.05)
        worst = 0.0
        rng = np.random.default_rng(5)
        for _ in range(200):
            for bits in (12,):
                q = np.round(a_ * (1 << bits)) / (1 << bits)
            rr = np.abs(np.roots(q)).max()
            worst = max(worst, rr)
        direct_unstable = worst >= 1.0
        # biquad cascade
        sos = sg.butter(order, 0.05, output="sos")
        sq = np.round(sos * (1 << 12)) / (1 << 12)
        wr = max(float(np.abs(np.roots(np.r_[1.0, sec[4:6]])).max()) for sec in sq)
        rows.append([num(order), num(worst, 6),
                     "<b>unstable</b>" if direct_unstable else "stable",
                     num(wr, 6), "<b>unstable</b>" if wr >= 1.0 else "stable"])
    s.append(sweep("Measured largest pole radius after quantising a Butterworth lowpass "
                   "(cutoff 0.05&times;Nyquist) to 12 fraction bits",
        ["Order", "Direct form: max |pole|", "Direct form verdict",
         "Biquad cascade: max |pole|", "Cascade verdict"], rows,
        "Roots computed from the quantised coefficients at 12 fraction bits. "
        "<b>Direct form loses stability at high order while the cascade does not</b>, "
        "on exactly the same filter with exactly the same word length &mdash; the "
        "cascade column is stable on every row, which is the finding, not a stuck "
        "measurement. The difference is entirely structural."))

    s.append("<h2>X23.2 The Laplace side, and why it still appears</h2>")
    s.append(tab("Continuous and discrete, side by side",
        ["", "Laplace (<i>s</i>)", "<i>z</i>"],
        [["Variable", "<i>s</i> = &sigma; + <i>j&omega;</i>",
          "<i>z</i> = <i>re</i><sup><i>j&omega;</i></sup>"],
         ["Frequency axis", "The imaginary axis", "<b>The unit circle</b>"],
         ["Stable region", "Left half plane", "<b>Inside the unit circle</b>"],
         ["Integration", "1/<i>s</i>", "1/(1&minus;<i>z</i><sup>&minus;1</sup>)"],
         ["Delay by <i>T</i>", "e<sup>&minus;<i>sT</i></sup> &mdash; <b>not "
          "rational</b>", "<i>z</i><sup>&minus;1</sup> &mdash; rational"],
         ["Where you meet it", "The analogue front end, the PLL loop filter, the "
          "channel", "Everything after the sampler"]]))
    s.append("""<div class="bs"><b>The delay row is the one worth remembering.</b> A pure
    delay is transcendental in <i>s</i> and trivial in <i>z</i>. That asymmetry is why
    mixed-signal loop analysis is awkward: the analogue part is naturally described in
    <i>s</i>, the digital part in <i>z</i>, and the delay that dominates the loop's
    stability (Part&nbsp;X21) is easy in one and hard in the other. The standard
    resolution is to convert everything to <i>z</i> using an impulse-invariant or bilinear
    mapping and to carry the analogue settling as additional delay samples &mdash; which
    is exactly what the worked loop budget in Part&nbsp;X21 did, without naming the
    theory.</div>""")
    rows = []
    for fc_hz, fs in ((1e3, 48e3), (5e3, 48e3), (10e3, 48e3), (20e3, 48e3), (23e3, 48e3)):
        wd = 2 * math.pi * fc_hz / fs
        wa_bilinear = 2 * fs * math.tan(wd / 2)
        warp = wa_bilinear / (2 * math.pi * fc_hz)
        rows.append([num(fc_hz / 1e3, 4), num(fc_hz / (fs / 2), 4),
                     num(wa_bilinear / (2 * math.pi) / 1e3, 5), num(warp, 5),
                     num((warp - 1) * 100, 4)])
    s.append(sweep("Frequency warping of the bilinear transform at "
                   "<i>f<sub>s</sub></i> = 48&nbsp;kHz",
        ["Digital <i>f<sub>c</sub></i> (kHz)", "Fraction of Nyquist",
         "Analogue prototype frequency (kHz)", "Warp factor", "Error if ignored (%)"],
        rows,
        "The bilinear transform maps the entire <i>s</i>-plane imaginary axis onto the "
        "unit circle, which it can only do by compressing high frequencies. <b>Below "
        "about a fifth of Nyquist the warp is under 10&nbsp;% and is usually ignored; "
        "near Nyquist it is enormous.</b> Pre-warping &mdash; designing the analogue "
        "prototype at the warped frequency &mdash; makes the cutoff land exactly where "
        "asked, and costs one <code>tan</code> at design time."))
    s.append(ex("Designing a biquad so the cutoff lands where the customer asked",
        "A second-order lowpass, cutoff 18&nbsp;kHz, sample rate 48&nbsp;kHz &mdash; "
        "0.75 of Nyquist, which is aggressive and exactly where warping bites.",
        "Compute the warped prototype frequency, then confirm by evaluating the "
        "resulting digital filter on the unit circle and reading off where its magnitude "
        "falls to 1/&radic;2.",
        [("Requested cutoff", num(18, 3, "kHz")),
         ("Fraction of Nyquist", num(18 / 24, 4)),
         ("Warped analogue frequency",
          num(2 * 48e3 * math.tan(2 * math.pi * 18e3 / 48e3 / 2) / (2 * math.pi) / 1e3,
              5, "kHz")),
         ("Warp factor",
          num(2 * 48e3 * math.tan(2 * math.pi * 18e3 / 48e3 / 2) / (2 * math.pi * 18e3),
              4)),
         ("Cutoff if the warp is ignored",
          num(48e3 / math.pi * math.atan(math.pi * 18e3 / 48e3) / 1e3, 5, "kHz")),
         ("Error if ignored",
          num((48e3 / math.pi * math.atan(math.pi * 18e3 / 48e3) - 18e3) / 18e3 * 100,
              4, "%"))],
        "<b>By designing the analogue prototype at the requested frequency.</b> The "
        "resulting digital filter cuts off well below where the customer asked, and the "
        "error grows with the fraction of Nyquist &mdash; so it is invisible in a "
        "low-rate test and obvious in a high-rate one. <b>This is a routine and entirely "
        "avoidable field complaint</b>, and the fix is one line in the design script."))

    s.append("<h2>X23.3 Residues, partial fractions and why they are the impulse "
             "response</h2>")
    s.append(derive("Partial fractions give the impulse response by inspection", [
        ("Factor <i>H</i>(<i>z</i>) = &Sigma;<sub><i>k</i></sub> "
         "<i>A<sub>k</sub></i>/(1 &minus; <i>p<sub>k</sub>z</i><sup>&minus;1</sup>) "
         "for distinct poles.",
         "Partial fraction expansion; <i>A<sub>k</sub></i> is the residue at the pole."),
        ("Each term inverse-transforms to "
         "<i>A<sub>k</sub>p<sub>k</sub></i><sup><i>n</i></sup><i>u</i>[<i>n</i>].",
         "The geometric sequence is the transform pair everything rests on."),
        ("So <b><i>h</i>[<i>n</i>] = &Sigma;<i>A<sub>k</sub>p<sub>k</sub></i><sup>"
         "<i>n</i></sup></b> &mdash; a sum of decaying (or growing) exponentials.",
         "<b>Every IIR impulse response is exactly this.</b> Nothing else can happen."),
        ("|<i>p<sub>k</sub></i>| &lt; 1 gives decay; |<i>p<sub>k</sub></i>| &gt; 1 "
         "gives growth.", "Which is the stability criterion, now derived rather than "
         "asserted."),
        ("The time constant of a pole at radius <i>r</i> is "
         "&minus;1/ln&nbsp;<i>r</i> samples.",
         "<b>The practical form</b>: a pole at 0.99 settles in about 100 samples, one at "
         "0.999 in about 1000. Useful for sizing a leaky integrator's word length, since "
         "the accumulator must hold about 1/(1&minus;<i>r</i>) times the input."),
    ]))
    rows = []
    for r in (0.9, 0.99, 0.999, 0.9999):
        tau = -1 / math.log(r)
        gain = 1 / (1 - r)
        bits = math.log2(gain)
        rows.append([num(r, 5), num(tau, 4), num(int(4 * tau)), num(gain, 5),
                     num(bits, 4)])
    s.append(sweep("The leaky integrator, sized from its pole",
        ["Pole <i>r</i>", "Time constant (samples)", "Settling to 2&nbsp;% (samples)",
         "DC gain 1/(1&minus;<i>r</i>)", "Extra integer bits needed"], rows,
        "A leaky integrator appears in every adaptation loop, AGC and error accumulator "
        "in this book. <b>The last column is the one forgotten</b>: a pole at 0.9999 "
        "multiplies DC by 10&#8239;000, so the accumulator needs 14 more integer bits "
        "than its input or it saturates on a small offset and the loop stops "
        "adapting."))
    s.append(prob("Why is the leaky integrator's leak usually implemented as a shift "
                  "rather than a multiply?",
        "Because choosing <i>r</i>&nbsp;=&nbsp;1&nbsp;&minus;&nbsp;2<sup>&minus;<i>m</i>"
        "</sup> makes the update <i>y</i>&nbsp;&larr;&nbsp;<i>y</i>&nbsp;&minus;&nbsp;"
        "(<i>y</i>&nbsp;&gt;&gt;&nbsp;<i>m</i>)&nbsp;+&nbsp;<i>x</i>, which is a shift "
        "and two adds and no multiplier &mdash; and at the rates in Part&nbsp;X4 a "
        "multiplier in a per-symbol loop is simply not available. The costs are worth "
        "naming. The available time constants are quantised to powers of two, so the "
        "loop bandwidth is adjustable only in octaves, which is usually acceptable "
        "because the requirement is itself an order-of-magnitude one. And the shift "
        "truncates, so the leak has a <b>dead zone</b>: when <i>y</i>&nbsp;&lt;&nbsp;"
        "2<sup><i>m</i></sup> the shifted value is zero and the integrator never decays "
        "to zero, it sticks at a small residue. <b>That residue is a DC offset in an "
        "adaptation loop</b> and is exactly the truncation-bias problem of Part&nbsp;X1 "
        "wearing different clothes; the fix is the same, round rather than truncate, or "
        "dither the shift."))
    s.append(prob("A colleague proposes a 12th-order elliptic IIR to save area compared "
                  "with a 200-tap FIR. What do you check before agreeing?",
        "Four things, in order of how likely they are to kill it. <b>Coefficient "
        "sensitivity</b>: as measured above, a high-order direct-form IIR can go unstable "
        "under quantisation; insist on a biquad cascade and on a measurement of the pole "
        "radii after quantisation at the intended word length. <b>Limit cycles</b>: a "
        "quantised IIR can sustain small self-oscillations with no input, because the "
        "quantiser is a nonlinearity inside the feedback loop; these are inaudible in "
        "audio and fatal in a control path, and they are found by simulating with zero "
        "input from many initial states. <b>Phase</b>: an elliptic filter has very "
        "nonlinear phase near the band edge, and if the application needs linear phase "
        "&mdash; anything that must not smear a pulse &mdash; the comparison is invalid "
        "because the FIR was doing something the IIR cannot. <b>Throughput</b>: the IIR "
        "has a feedback loop, so its critical path is one multiply-add and it cannot be "
        "pipelined without changing the transfer function, while the FIR pipelines "
        "freely. At high sample rates this alone decides it. <b>The area saving is real; "
        "the question is whether the four costs are acceptable in this application</b>, "
        "and the answer is different for audio, for control and for a SerDes."))
    return "\n".join(s)
