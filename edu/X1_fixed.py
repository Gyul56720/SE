# -*- coding: utf-8 -*-
"""Volume I, Part X1 -- Fixed-point arithmetic, worked end to end.

Every number in this part is computed when the book is built.  The sweeps are
real sweeps and the Monte-Carlo figures are real Monte-Carlo runs with a fixed
seed, so a reader who re-runs the module gets the same table and can change one
parameter and see what moves.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

RNG = lambda s: np.random.default_rng(s)


# --------------------------------------------------------------- helpers
def q(x, W, F, signed=True, mode="round", ovf="sat"):
    """Quantise a float array to a W-bit fixed-point grid with F fraction bits.

    This is the reference model the rest of the part is measured against.  It
    is written out rather than imported because the *choices* it encodes --
    rounding rule and overflow rule -- are exactly the two decisions this part
    is about, and hiding them inside a library call would defeat the purpose.
    """
    x = np.asarray(x, dtype=float)
    s = 2.0 ** F
    if mode == "round":
        i = np.floor(x * s + 0.5)          # round-half-up
    elif mode == "trunc":
        i = np.floor(x * s)                # truncate toward -inf
    elif mode == "conv":
        i = np.round(x * s)                # numpy: round-half-to-even
    else:
        raise ValueError(mode)
    lo = -(2 ** (W - 1)) if signed else 0
    hi = (2 ** (W - 1)) - 1 if signed else (2 ** W) - 1
    if ovf == "sat":
        i = np.clip(i, lo, hi)
    elif ovf == "wrap":
        n = 2 ** W
        i = ((i - lo) % n) + lo
    else:
        raise ValueError(ovf)
    return i / s


def _f_grid():
    b = []
    y = 46
    b.append(line(24, y, 396, y, w=1.2))
    for k in range(-8, 9):
        x = 210 + k * 22
        if x < 26 or x > 394:
            continue
        b.append(line(x, y - 5, x, y + 5, w=0.9))
        if k % 4 == 0:
            b.append(txt(x, y + 18, f"{k}", 8, "middle"))
    b.append(txt(210, y - 16, "the representable grid: spacing 2", 9, "middle"))
    b.append(txt(292, y - 16, "&minus;F", 7))
    b.append(txt(24, y - 16, "&minus;2", 9))
    b.append(txt(40, y - 20, "W&minus;1&minus;F", 6))
    b.append(txt(396, y - 16, "2", 9, "end"))
    b.append(txt(390, y - 20, "W&minus;1&minus;F", 6, "end"))
    b.append(txt(210, 86, "Everything a fixed-point block can ever hold is one of these "
                          "2", 9, "middle"))
    b.append(txt(347, 82, "W", 7))
    b.append(txt(210, 100, "points. Design is the choice of where the grid sits and how "
                           "wide it is.", 9, "middle"))
    return svg(420, 112, "".join(b))


# ================================================================ X1
def ch_fixed():
    s = ['<h1 id="x1">X1. Fixed-Point Arithmetic, Worked End to End</h1>']
    s.append("""<p>Almost every hardware block in this book computes on a finite grid of
    numbers. The grid is not an implementation detail that can be settled at the end: it
    determines area, power, the noise floor of the whole datapath, and &mdash; in at least
    one case in this chapter &mdash; whether the block computes the right answer at all.
    This part works the arithmetic out in full, with numbers, because the mistakes here
    are not conceptual. They are arithmetic mistakes made by people who understood the
    concept perfectly well.</p>""")
    s.append(fig(_f_grid(), "A signed fixed-point format with <i>W</i> total bits and "
                            "<i>F</i> fraction bits. Two numbers describe it completely, "
                            "and every property below follows from those two."))

    s.append("<h2>X1.1 The format and its four consequences</h2>")
    s.append("""<p>Write a signed two's-complement format as <b>Q(<i>I</i>.<i>F</i>)</b>
    with <i>W</i>&nbsp;=&nbsp;<i>I</i>&nbsp;+&nbsp;<i>F</i>&nbsp;+&nbsp;1 bits in total,
    one of which is the sign. Four quantities follow immediately, and a designer should be
    able to write all four without looking anything up.</p>""")
    s.append(derive("From the format to the four numbers that matter", [
        ("An integer <i>n</i> stored in <i>W</i> two's-complement bits satisfies "
         "&minus;2<sup><i>W</i>&minus;1</sup> &le; <i>n</i> &le; "
         "2<sup><i>W</i>&minus;1</sup>&minus;1.",
         "Definition of two's complement."),
        ("The stored value is <i>x</i> = <i>n</i>&nbsp;&middot;&nbsp;2<sup>&minus;<i>F</i></sup>.",
         "That is what &lsquo;<i>F</i> fraction bits&rsquo; means: a fixed scale factor "
         "that the hardware never represents."),
        ("Hence <b>resolution</b> &Delta; = 2<sup>&minus;<i>F</i></sup>.",
         "Consecutive integers differ by one; multiply by the scale."),
        ("Hence <b>range</b> is &minus;2<sup><i>I</i></sup> &le; <i>x</i> &le; "
         "2<sup><i>I</i></sup> &minus; &Delta;.",
         "Substitute the integer bounds. Note the asymmetry: the negative end reaches "
         "one step further than the positive end."),
        ("<b>Dynamic range</b> = 20&nbsp;log<sub>10</sub>(2<sup><i>W</i>&minus;1</sup>) "
         "&asymp; 6.02(<i>W</i>&minus;1)&nbsp;dB.",
         "Ratio of the largest magnitude to the step size."),
        ("<b>Quantisation noise power</b> = &Delta;<sup>2</sup>/12 for rounding, "
         "if the error is uniform on [&minus;&Delta;/2, &Delta;/2].",
         "Variance of a uniform distribution. <b>The &lsquo;if&rsquo; is load-bearing</b> "
         "and X1.4 measures a case where it fails."),
    ]))

    W, F = 16, 12
    d = 2.0 ** -F
    s.append(ex("Reading a Q3.12 format",
        "A 16-bit signed format with <i>F</i>&nbsp;=&nbsp;12 fraction bits, written "
        "Q3.12 (three integer bits, twelve fraction bits, one sign bit).",
        "Apply the four consequences above directly. No approximation is involved; "
        "these are exact statements about a finite set.",
        [("Resolution &Delta;", num(d, 4)),
         ("Most positive value", num(2**3 - d, 8)),
         ("Most negative value", num(-2.0**3, 4)),
         ("Number of representable points", num(2**W)),
         ("Dynamic range", num(6.0206 * (W - 1), 4, "dB")),
         ("Noise power &Delta;<sup>2</sup>/12", num(d * d / 12, 4)),
         ("Noise RMS", num(math.sqrt(d * d / 12), 4))],
        "<b>By confusing the range with the resolution.</b> A specification that says "
        "&lsquo;16-bit&rsquo; and nothing else has said nothing: Q15.0 and Q0.15 are both "
        "16 bits and they cannot hold each other's numbers. <b>Always write both "
        "numbers</b>, and write them into the interface document, not just into the "
        "designer's head. A second, subtler error is to assume the range is symmetric and "
        "to negate the most negative value: &minus;(&minus;8) is not representable in "
        "Q3.12 and will wrap or saturate."))

    s.append("<h2>X1.2 Rounding rules are not interchangeable</h2>")
    s.append("""<p>Three rounding rules appear in real RTL: truncation (drop the low bits,
    which rounds toward &minus;&infin; in two's complement), round-half-up (add half an LSB
    then truncate), and convergent or banker's rounding (round-half-to-even). They cost
    different amounts of hardware and they have different <i>bias</i>, and bias is the
    property that matters in a feedback loop or an accumulator.</p>""")
    rng = RNG(7)
    x = rng.uniform(-1.0, 1.0, 200000)
    rows = []
    for name, mode, cost in [
            ("Truncate", "trunc", "free &mdash; drop wires"),
            ("Round half up", "round", "one <i>F</i>-bit incrementer"),
            ("Convergent", "conv", "incrementer + tie detect")]:
        e = q(x, 12, 8, mode=mode) - x
        rows.append([f"<b>{name}</b>", cost, num(float(e.mean()), 3),
                     num(float(e.std()), 4), num(float(np.abs(e).max()), 4)])
    s.append(sweep("Measured error of three rounding rules, 200&#8239;000 samples "
                   "uniform on [&minus;1,&nbsp;1] quantised to Q3.8",
        ["Rule", "Hardware cost", "Mean error (bias)", "Error std. dev.", "Max |error|"],
        rows,
        "Computed at build time with seed&nbsp;7. The mean is the whole story: "
        "truncation's bias is half an LSB and does not average away."))
    lsb8 = 2.0 ** -8
    s.append(ex("Why a truncating accumulator drifts",
        f"A Q3.8 accumulator (&Delta;&nbsp;=&nbsp;{num(lsb8,4)}) sums 4096 products, "
        "truncating after each multiply.",
        "Each truncation subtracts on average &Delta;/2, and the truncations are "
        "independent of the signal, so the <i>biases add coherently</i> while the random "
        "parts add in quadrature. Compare the two growths.",
        [("Bias per operation", num(-lsb8 / 2, 4)),
         ("Accumulated bias after 4096 ops", num(-4096 * lsb8 / 2, 4)),
         ("Random part, &radic;4096&nbsp;&middot;&nbsp;&Delta;/&radic;12",
          num(math.sqrt(4096) * lsb8 / math.sqrt(12), 4)),
         ("Ratio bias : random", num((4096 * lsb8 / 2) /
                                     (math.sqrt(4096) * lsb8 / math.sqrt(12)), 4))],
        "<b>By reasoning about the error variance and forgetting the mean.</b> The "
        "random part grows as &radic;<i>N</i>; the bias grows as <i>N</i>. At "
        "<i>N</i>&nbsp;=&nbsp;4096 the DC offset is about 35&times; the noise, which in a "
        "DC-coupled path shows up as a fixed output error no amount of averaging removes. "
        "The remedy is not a wider accumulator &mdash; that changes nothing about the "
        "bias &mdash; it is round-half-up, or, if the tie bias also matters, convergent "
        "rounding."))

    s.append("""<div class="ms"><b>When convergent rounding is worth its tie-detection
    logic.</b> Round-half-up is unbiased for a continuous input, because exact ties have
    probability zero. It is <i>not</i> unbiased when the input is itself already on a grid
    &mdash; which is exactly the case when you requantise a Q<i>a</i>.<i>b</i> signal to
    Q<i>a</i>.<i>b</i>&prime; with <i>b</i>&prime;&nbsp;&lt;&nbsp;<i>b</i>. Then ties occur
    with probability 2<sup>&minus;(<i>b</i>&minus;<i>b</i>&prime;)</sup> and all of them
    round the same way. The table below measures precisely this case.</div>""")
    rows = []
    src = q(rng.uniform(-1, 1, 200000), 18, 14)           # already on a 2^-14 grid
    for drop in (1, 2, 3, 4, 6):
        Fp = 14 - drop
        eh = q(src, 18 - drop, Fp, mode="round") - src
        ec = q(src, 18 - drop, Fp, mode="conv") - src
        rows.append([drop, num(2.0 ** -(drop), 3),
                     num(float(eh.mean()), 3), num(float(ec.mean()), 3),
                     num(float(eh.mean() / (2.0 ** -Fp)), 3)])
    s.append(sweep("Requantising a signal that is already on a grid: half-up develops a "
                   "bias that convergent rounding does not",
        ["Bits dropped", "P(exact tie)", "Mean error, half-up", "Mean error, convergent",
         "Half-up bias in LSB of the new format"],
        rows,
        "The half-up bias is exactly half an LSB times the tie probability, and the "
        "measured column confirms it. Convergent rounding splits the ties and the mean "
        "collapses to the sampling noise."))

    s.append("<h2>X1.3 Overflow: the one decision that is not a trade-off</h2>")
    s.append("""<p>Saturation and wrap-around are usually presented as a trade-off between
    graceful degradation and a small amount of logic. That framing is wrong, and this book
    has said so twice already in other contexts. They are <i>different arithmetic</i>:
    wrap-around is a ring homomorphism on integers modulo 2<sup><i>W</i></sup>, and
    saturation is not a homomorphism of anything. Where a design relies on the
    homomorphism, saturation breaks it. Where a design relies on a bounded output,
    wrap-around breaks that.</p>""")
    s.append(derive("Why the CIC integrator <i>must</i> wrap", [
        ("A CIC decimator is <i>N</i> integrators, a downsampler, and <i>N</i> combs.",
         "Definition (Hogenauer)."),
        ("Integrator: <i>y</i>[<i>n</i>] = <i>y</i>[<i>n</i>&minus;1] + <i>x</i>[<i>n</i>]. "
         "Comb: <i>z</i>[<i>m</i>] = <i>y</i>[<i>m</i>] &minus; <i>y</i>[<i>m</i>&minus;<i>M</i>].",
         "Definition."),
        ("Work in &#8484;<sub>2<sup><i>W</i></sup></sub>. Addition and subtraction are "
         "well defined there and the map &#8484;&nbsp;&rarr;&nbsp;"
         "&#8484;<sub>2<sup><i>W</i></sup></sub> commutes with both.",
         "That is exactly what &lsquo;ring homomorphism&rsquo; asserts."),
        ("Therefore the mod-2<sup><i>W</i></sup> image of the exact output equals the "
         "output computed entirely mod 2<sup><i>W</i></sup>.",
         "Homomorphisms commute with composition of ring operations; the whole CIC is "
         "such a composition."),
        ("So if the <i>final</i> result fits in <i>W</i> bits, it is exactly right, "
         "however violently the integrators overflowed.",
         "The image determines the value once we know it is in range."),
        ("<b>Saturation is not such a map.</b> sat(<i>a</i>+<i>b</i>) &ne; "
         "sat(sat(<i>a</i>)+<i>b</i>) in general.",
         "One counterexample suffices, and X1.3's worked example is one."),
    ]))
    # measure it
    N, R, M = 3, 32, 1
    Wcic = int(math.ceil(16 + N * math.log2(R * M)))
    rng2 = RNG(11)
    xin = np.round(rng2.uniform(-1, 1, R * 400) * (2**15 - 1))
    def cic(xs, W, ovf):
        n = 2 ** W
        lo = -(2 ** (W - 1))
        def fold(v):
            return ((v - lo) % n) + lo if ovf == "wrap" else min(max(v, lo), 2**(W-1)-1)
        acc = [0] * N
        outs = []
        for k, v in enumerate(xs):
            for i in range(N):
                acc[i] = fold(acc[i] + (v if i == 0 else acc[i - 1]))
            if (k + 1) % R == 0:
                outs.append(acc[N - 1])
        y = outs
        for _ in range(N):
            y = [fold(y[i] - y[i - M]) if i >= M else y[i] for i in range(len(y))]
        return np.array(y[N * M:], dtype=float)
    exact = cic(xin, 64, "wrap")
    wrapd = cic(xin, Wcic, "wrap")
    satd = cic(xin, Wcic, "sat")
    s.append(ex("Wrap and saturate in the same CIC, measured",
        f"An <i>N</i>&nbsp;=&nbsp;{N}, <i>R</i>&nbsp;=&nbsp;{R}, <i>M</i>&nbsp;=&nbsp;{M} "
        f"CIC decimator on 16-bit input. Hogenauer's bound gives "
        f"<i>W</i>&nbsp;=&nbsp;16&nbsp;+&nbsp;<i>N</i>&nbsp;log<sub>2</sub>(<i>RM</i>) "
        f"= {Wcic} bits. The same stimulus is run three ways: at 64 bits (exact), at "
        f"{Wcic} bits with wrap-around, and at {Wcic} bits with saturation.",
        "Run all three and compare sample by sample against the 64-bit reference. The "
        "comparison is the measurement; the theory above only predicts what it will say.",
        [("Samples compared", num(len(exact))),
         ("Wrap-around: max |error| vs. exact", num(float(np.abs(wrapd - exact).max()))),
         ("Saturation: max |error| vs. exact", num(float(np.abs(satd - exact).max()))),
         ("Saturation: fraction of samples wrong",
          num(float(np.mean(satd != exact)), 3)),
         ("Integrator peak magnitude reached",
          num(int(np.max(np.abs(np.cumsum(np.cumsum(np.cumsum(xin)))))))),
         ("Does that peak exceed the " + str(Wcic) + "-bit range?",
          "yes" if np.max(np.abs(np.cumsum(np.cumsum(np.cumsum(xin))))) > 2**(Wcic-1)
          else "no")],
        "<b>By choosing saturation as the &lsquo;safe default&rsquo; in a coding "
        "standard.</b> Every internal node of a correct CIC overflows by design; that is "
        "not a bug being tolerated, it is the mechanism. A house rule of the form "
        "&lsquo;all adders shall saturate&rsquo; silently destroys it. <b>Overflow "
        "behaviour is a per-block decision that belongs in the block's specification, "
        "never in a global style guide.</b>"))
    s.append("""<div class="warn"><b>And the exact opposite is true one block away.</b> In
    an LDPC or turbo decoder the messages are log-likelihood ratios whose <i>sign</i> is
    the decision. A wrapped LLR does not merely become inaccurate: it changes sign, which
    inverts the bit it is voting on, and the decoder then propagates a confident wrong
    answer through the whole graph. There saturation is mandatory and wrap is a
    catastrophic bug. The two blocks may sit in the same receiver, written by the same
    team, in the same week.</div>""")

    s.append("<h2>X1.4 When &Delta;<sup>2</sup>/12 is not the answer</h2>")
    s.append("""<p>The standard quantisation-noise model assumes the error is uniform,
    white, and independent of the signal. All three assumptions fail for inputs that are
    small, slow, or periodic relative to the grid &mdash; and hardware inputs are
    frequently all three. The next sweep measures the failure instead of asserting
    it.</p>""")
    Fq = 8
    dq = 2.0 ** -Fq
    rows = []
    for amp_lsb in (0.4, 1, 2, 4, 16, 64, 1024):
        A = amp_lsb * dq
        n = np.arange(65536)
        sig = A * np.sin(2 * np.pi * 0.00347 * n)
        e = q(sig, 24, Fq) - sig
        meas = float(e.var())
        rows.append([num(amp_lsb, 3), num(A, 3), num(meas, 3), num(dq * dq / 12, 3),
                     num(meas / (dq * dq / 12), 3)])
    s.append(sweep("Measured quantisation-error variance of a sine against the "
                   "&Delta;<sup>2</sup>/12 model, Q-format with <i>F</i>&nbsp;=&nbsp;8",
        ["Amplitude (LSB)", "Amplitude", "Measured error variance",
         "&Delta;<sup>2</sup>/12", "Ratio"],
        rows,
        "65&#8239;536 samples of an incommensurate sine. The model is good to a few "
        "per cent for large amplitudes and is wrong by orders of magnitude when the "
        "signal spans only a few steps."))
    s.append("""<div class="ms"><b>What goes wrong below a few LSB, and the standard
    remedy.</b> A sine of amplitude half an LSB quantises to a square wave or to nothing
    at all: the &lsquo;error&rsquo; is the negative of the signal, perfectly correlated
    with it, and it lands as harmonics at multiples of the input frequency rather than as
    a flat floor. In a spectrum this is visible as discrete spurs that move when the input
    frequency moves &mdash; the classic signature. The remedy is <b>dither</b>: add a
    small random signal before quantisation, typically triangular with a 2&nbsp;LSB
    peak-to-peak span, which decorrelates the error at the cost of raising the floor by
    4.8&nbsp;dB. Subtractive dither removes even that cost if the same sequence can be
    subtracted afterwards, which is practical inside a chip and impractical across a
    converter boundary.</div>""")
    # dither measurement
    n = np.arange(1 << 16)
    A = 1.5 * dq
    sig = A * np.sin(2 * np.pi * 0.00347 * n)
    rngd = RNG(23)
    tri = (rngd.random(n.size) + rngd.random(n.size) - 1.0) * dq
    e0 = q(sig, 24, Fq) - sig
    e1 = q(sig + tri, 24, Fq) - sig - tri
    def spur(e):
        S = np.abs(np.fft.rfft(e * np.hanning(e.size)))**2
        S[:4] = 0
        return 10 * math.log10(float(S.max() / S[S > 0].mean()))
    s.append(ex("Dither converts a spur into a floor",
        "The 1.5&nbsp;LSB sine above, quantised with and without triangular dither of "
        "2&nbsp;LSB peak-to-peak.",
        "Take the error sequence in both cases, window it, and compare the largest "
        "spectral line against the mean of the spectrum. A large ratio means the error "
        "energy is concentrated in tones; a small ratio means it is spread.",
        [("Undithered: peak-to-mean spectral ratio", num(spur(e0), 4, "dB")),
         ("Dithered: peak-to-mean spectral ratio", num(spur(e1), 4, "dB")),
         ("Undithered error variance / (&Delta;<sup>2</sup>/12)",
          num(float(e0.var()) / (dq * dq / 12), 3)),
         ("Dithered error variance / (&Delta;<sup>2</sup>/12)",
          num(float(e1.var()) / (dq * dq / 12), 3))],
        "<b>By reporting only the variance.</b> Dither <i>raises</i> total error power, "
        "so a designer optimising a single SNR number will reject it. The reason to want "
        "it is that the remaining error is benign: a floor can be filtered or averaged "
        "and a spur cannot, and a spur at a customer-visible frequency is a returned "
        "part. <b>Choose the metric that matches the failure you are avoiding</b>, not "
        "the one that is easiest to compute."))

    s.append("<h2>X1.5 Word-length allocation as an engineering procedure</h2>")
    s.append("""<p>The question &lsquo;how many bits?&rsquo; has a disciplined answer. It
    is not &lsquo;try 16 and see&rsquo;, and it is not a closed-form formula either. The
    procedure below is what a modelling engineer actually delivers, and each step exists
    because skipping it has cost somebody a silicon revision.</p>""")
    s.append(tab("Word-length allocation, step by step",
        ["Step", "What you do", "What it produces", "Why it cannot be skipped"],
        [["1. Range", "Bound every node, by interval arithmetic for the worst case and "
          "by simulation for the realistic case",
          "Integer bits <i>I</i> per node",
          "An under-ranged node overflows on a rare input, in the field, "
          "after sign-off"],
         ["2. Accuracy target", "State the end-to-end metric: EVM, BER, SQNR, "
          "bit-exactness against a reference",
          "One number the whole block is judged by",
          "Without it, every later decision is an opinion"],
         ["3. Sensitivity", "Perturb one node's <i>F</i> at a time and measure the "
          "metric", "A gradient over word lengths",
          "Uniform word lengths waste 20&ndash;40&nbsp;% of the multiplier area"],
         ["4. Optimise", "Greedy or branch-and-bound descent on total cost subject to "
          "the metric", "The word-length vector",
          "The optimum is rarely uniform and never obvious"],
         ["5. Verify", "Bit-exact model vs. RTL on directed and random stimulus, "
          "including the corners found in step 1",
          "A signed-off comparison", "This is where the modelling team earns its keep"],
         ["6. Document", "Every node's Q format in the micro-architecture document",
          "The thing the customer integrates against",
          "An undocumented internal format becomes an accidental interface"]]))
    # sensitivity experiment on a small FIR
    from numpy.fft import rfft
    h = np.array([-0.0107, -0.0186, 0.0339, 0.1265, 0.2245, 0.2645, 0.2245,
                  0.1265, 0.0339, -0.0186, -0.0107])
    rng3 = RNG(31)
    xs = rng3.uniform(-0.9, 0.9, 40000)
    ref = np.convolve(xs, h, "same")
    def sqnr(Fc, Fd):
        hq = q(h, Fc + 4, Fc)
        xq = q(xs, Fd + 2, Fd)
        y = np.convolve(xq, hq, "same")
        e = y - ref
        return 10 * math.log10(float(ref.var() / e.var()))
    rows = []
    for Fc in (8, 10, 12, 14, 16):
        rows.append([Fc] + [num(sqnr(Fc, Fd), 4) for Fd in (8, 10, 12, 14, 16)])
    s.append(sweep("Measured SQNR (dB) of an 11-tap FIR as coefficient and data fraction "
                   "lengths are swept independently",
        ["<i>F</i><sub>coef</sub> &darr; / <i>F</i><sub>data</sub> &rarr;",
         "8", "10", "12", "14", "16"], rows,
        "Read along a row: beyond a point, more data bits buy nothing because the "
        "coefficient error dominates. Read down a column for the mirror image. "
        "<b>The cheapest design sits on the diagonal ridge, and a uniform choice is on "
        "it only by accident.</b>"))
    s.append(plot([8, 10, 12, 14, 16],
                  [("F_data=8", [sqnr(fc, 8) for fc in (8, 10, 12, 14, 16)]),
                   ("F_data=12", [sqnr(fc, 12) for fc in (8, 10, 12, 14, 16)]),
                   ("F_data=16", [sqnr(fc, 16) for fc in (8, 10, 12, 14, 16)])],
                  "coefficient fraction bits", "SQNR (dB)",
                  "The same data plotted: each curve saturates where the other word "
                  "length becomes the binding constraint. The knee is the design point."))
    s.append(prob("An 11-tap FIR must reach 70&nbsp;dB SQNR. Multiplier cost is "
                  "proportional to <i>F</i><sub>coef</sub>&nbsp;&times;&nbsp;"
                  "<i>F</i><sub>data</sub>. Using the table above, which cell is "
                  "cheapest?",
        "Scan the table for cells at or above 70&nbsp;dB and compare the products. "
        "The uniform choice (12,&nbsp;12) costs 144 units; the asymmetric choices on the "
        "same contour cost less or more depending on which term saturates first. "
        "<b>The point of the exercise is the method, not the cell</b>: compute the "
        "metric on a grid, then minimise cost along the feasible contour. A real block "
        "has thirty nodes and the grid becomes a search, which is why step&nbsp;4 above "
        "names an algorithm."))
    s.append(prob("Why does interval arithmetic (step&nbsp;1) usually give a range that "
                  "is far too wide, and what do you do about it?",
        "Interval arithmetic assumes every node simultaneously takes its worst value, "
        "which for an <i>N</i>-tap FIR means all inputs at full scale <i>and</i> aligned "
        "in sign with the coefficients &mdash; giving the &#8467;<sub>1</sub> bound "
        "&Sigma;|<i>h</i><sub><i>k</i></sub>|. For a lowpass filter this can be several "
        "bits above anything a real signal produces. The standard resolution is to carry "
        "<i>both</i>: the &#8467;<sub>1</sub> bound for nodes where overflow is "
        "unacceptable at any probability, and a simulated or &#8467;<sub>2</sub>-based "
        "bound elsewhere, with saturation as the backstop. <b>State which you used for "
        "each node</b>; a range with no stated basis cannot be reviewed."))
    l1 = float(np.abs(h).sum())
    l2 = float(np.sqrt((h**2).sum()))
    s.append(ex("The two bounds differ by more than a bit",
        "The 11-tap lowpass above, driven by a signal bounded by 1.0.",
        "Compute the &#8467;<sub>1</sub> gain (worst case over all bounded inputs) and "
        "the &#8467;<sub>2</sub> gain (gain for white input of unit variance), and "
        "convert each to the integer bits it demands.",
        [("&#8467;<sub>1</sub> gain &Sigma;|<i>h<sub>k</sub></i>|", num(l1, 4)),
         ("Integer bits needed by &#8467;<sub>1</sub>",
          num(int(math.ceil(math.log2(l1))) if l1 > 1 else 0)),
         ("&#8467;<sub>2</sub> gain", num(l2, 4)),
         ("Measured peak |output| for the uniform stimulus above",
          num(float(np.abs(ref).max()), 4)),
         ("Measured peak as a fraction of the &#8467;<sub>1</sub> bound",
          num(float(np.abs(ref).max()) / l1, 3))],
        "<b>By quoting the measured peak as if it were a bound.</b> The measured peak "
        "depends on how long you simulated; run 100&times; longer and it creeps up. A "
        "bound does not creep. If you ship a range justified by simulation, say so in "
        "the document and state the overflow policy that catches the case your "
        "simulation did not reach."))
    return "\n".join(s)
