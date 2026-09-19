# -*- coding: utf-8 -*-
"""Volume I, Part X25 -- Detection and estimation, the receiver's mathematics."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

Q = lambda x: 0.5 * math.erfc(x / math.sqrt(2))


def ch_detect():
    s = ['<h1 id="x25">X25. Detection and Estimation, the Receiver&rsquo;s '
         'Mathematics</h1>']
    s.append("""<p>A receiver makes two kinds of decision: which symbol was sent
    (detection) and what the channel is doing (estimation). Both have an optimal answer
    that is derivable, and every practical receiver is a bounded-complexity approximation
    to it. Knowing the optimum is what lets you say how much a shortcut costs.</p>""")

    s.append("<h2>X25.1 The likelihood ratio is the whole of detection</h2>")
    s.append(derive("From a cost to the optimal decision rule", [
        ("Two hypotheses <i>H</i><sub>0</sub>, <i>H</i><sub>1</sub> with priors "
         "<i>P</i><sub>0</sub>, <i>P</i><sub>1</sub>; observation <b>r</b>.",
         "The setup for any binary decision."),
        ("Minimising the probability of error means choosing the hypothesis with the "
         "larger posterior <i>P</i>(<i>H<sub>i</sub></i>|<b>r</b>).",
         "Each wrong choice costs one; pick the more likely."),
        ("By Bayes, this is "
         "<i>p</i>(<b>r</b>|<i>H</i><sub>1</sub>)<i>P</i><sub>1</sub> &gtrless; "
         "<i>p</i>(<b>r</b>|<i>H</i><sub>0</sub>)<i>P</i><sub>0</sub>.",
         "The evidence term cancels."),
        ("<b>&Lambda;(<b>r</b>) = <i>p</i>(<b>r</b>|<i>H</i><sub>1</sub>) / "
         "<i>p</i>(<b>r</b>|<i>H</i><sub>0</sub>) &gtrless; "
         "<i>P</i><sub>0</sub>/<i>P</i><sub>1</sub></b>",
         "The likelihood ratio test. <b>Every optimal detector is this</b>; only the "
         "densities change."),
        ("For additive white Gaussian noise the log of &Lambda; is linear in <b>r</b>, "
         "giving a <b>matched filter</b> followed by a threshold.",
         "Take logs of the Gaussian density: the quadratic terms that depend on "
         "<b>r</b> alone cancel in the ratio, leaving an inner product. <b>This is why "
         "the matched filter is optimal and not merely intuitive.</b>"),
        ("Working with log&Lambda; rather than &Lambda; turns products into sums.",
         "<b>Which is why hardware carries log-likelihood ratios</b>: combining "
         "independent observations becomes addition, and the dynamic range collapses "
         "from astronomical to a few bits."),
    ]))
    rows = []
    for snr_db in (0, 3, 6, 9, 12, 15):
        eb_n0 = 10 ** (snr_db / 10)
        bpsk = Q(math.sqrt(2 * eb_n0))
        qpsk = Q(math.sqrt(2 * eb_n0))
        qam16 = 3.0 / 4 * math.erfc(math.sqrt(4.0 / 10 * eb_n0 * 2) / math.sqrt(2))
        rows.append([num(snr_db), num(bpsk, 2), num(qpsk, 2), num(qam16, 2),
                     num(1, 3), num(2, 3), num(4, 3)])
    s.append(sweep("Uncoded bit error rate against <i>E<sub>b</sub></i>/<i>N</i><sub>0</sub>",
        ["<i>E<sub>b</sub></i>/<i>N</i><sub>0</sub> (dB)", "BPSK", "QPSK", "16-QAM",
         "bits/symbol BPSK", "QPSK", "16-QAM"], rows,
        "BPSK and QPSK have identical bit error rate at equal "
        "<i>E<sub>b</sub></i>/<i>N</i><sub>0</sub> &mdash; QPSK sends twice the bits in "
        "the same bandwidth for the same energy per bit, which is why it is the default "
        "everywhere. <b>16-QAM doubles the rate again and pays several dB</b>, which is "
        "the trade every adaptive-modulation scheme is making."))
    s.append(plot([0, 3, 6, 9, 12, 15],
                  [("BPSK/QPSK", [math.log10(max(Q(math.sqrt(2 * 10 ** (d / 10))), 1e-16))
                                  for d in (0, 3, 6, 9, 12, 15)]),
                   ("16-QAM", [math.log10(max(0.75 * math.erfc(
                       math.sqrt(0.8 * 10 ** (d / 10)) / math.sqrt(2)), 1e-16))
                       for d in (0, 3, 6, 9, 12, 15)])],
                  "Eb/N0 (dB)", "log10 BER",
                  "The waterfall curves. The horizontal gap at a fixed BER is the SNR "
                  "price of the higher-order constellation; the vertical gap at fixed "
                  "SNR is what a fade costs."))

    s.append("<h2>X25.2 Soft information: why a hard decision throws away 2&nbsp;dB</h2>")
    s.append("""<p>A slicer that outputs only a bit discards the receiver's confidence.
    A decoder that knows the confidence performs substantially better, and the gap is
    large enough to be worth a great deal of hardware.</p>""")
    rng = np.random.default_rng(17)
    rows = []
    n = 200000
    for snr_db in (0, 2, 4, 6):
        sigma = 10 ** (-snr_db / 20)
        x = rng.choice([-1.0, 1.0], n)
        y = x + rng.normal(0, sigma, n)
        hard = np.sign(y)
        # repetition-3 code: hard majority vs soft sum
        x3 = np.repeat(x[: n // 3], 3)
        y3 = x3 + rng.normal(0, sigma, x3.size)
        maj = np.sign(np.sign(y3).reshape(-1, 3).sum(1))
        soft = np.sign(y3.reshape(-1, 3).sum(1))
        ref = x[: n // 3]
        rows.append([num(snr_db), num(float(np.mean(hard != x)), 2),
                     num(float(np.mean(maj != ref)), 2),
                     num(float(np.mean(soft != ref)), 2),
                     num(float(np.mean(maj != ref)) /
                         max(float(np.mean(soft != ref)), 1e-9), 4)])
    s.append(sweep("Measured hard-decision majority vote against soft-decision sum, "
                   "repetition-3 code, 200&#8239;000 bits",
        ["SNR (dB)", "Raw BER", "Hard majority", "Soft sum",
         "Hard / soft error ratio"], rows,
        "The same received samples decoded two ways. <b>Soft combining is simply "
        "adding the three received values; hard combining first destroys the "
        "magnitudes and then votes.</b> The ratio column is what that destruction "
        "costs, on the simplest possible code."))
    s.append("""<div class="ms"><b>The classical figure of about 2&nbsp;dB.</b> For a
    binary-input AWGN channel, hard-decision decoding loses roughly 2&nbsp;dB relative to
    soft-decision decoding at rates and error rates of practical interest. That is a very
    large number in a link budget &mdash; Part&nbsp;X4's waterfall says 2&nbsp;dB can be
    three orders of magnitude of BER &mdash; and it is why every modern FEC uses soft
    input. The hardware consequence is specific: <b>the slicer must produce a
    quantised LLR rather than a bit</b>, typically 4 to 6 bits, and every stage between
    the slicer and the decoder must carry that width. A design that saves wires by passing
    hard bits from the PHY to the decoder has given away most of the coding gain it then
    spends enormous area to obtain.</div>""")
    rows = []
    for bits in (1, 2, 3, 4, 5, 6):
        # capacity of quantised BI-AWGN, rough: uniform quantiser over +-3 sigma
        levels = 2 ** bits
        snr = 1.0
        z = np.linspace(-4, 4, 20001)
        p1 = np.exp(-(z - 1) ** 2 / 2)
        p0 = np.exp(-(z + 1) ** 2 / 2)
        edges = np.linspace(-3, 3, levels + 1)
        idx = np.clip(np.digitize(z, edges[1:-1]), 0, levels - 1)
        c = 0.0
        for k in range(levels):
            m = idx == k
            a = float(np.trapezoid(p1[m], z[m])) if m.any() else 0.0
            b_ = float(np.trapezoid(p0[m], z[m])) if m.any() else 0.0
            if a > 0 and b_ > 0:
                c += 0.5 * a * math.log2(2 * a / (a + b_)) + \
                     0.5 * b_ * math.log2(2 * b_ / (a + b_))
        tot = float(np.trapezoid(p1, z))
        rows.append([num(bits), num(levels), num(c / tot, 5),
                     num(c / tot / 0.5, 4)])
    s.append(sweep("Measured capacity of a quantised binary-input Gaussian channel "
                   "(unit signal, unit noise), computed by numerical integration",
        ["LLR bits", "Levels", "Capacity (bits/use)", "Relative to 1 bit of quantisation"],
        rows,
        "Integrated numerically over a uniform quantiser spanning &plusmn;3&sigma;. "
        "<b>The gain from 1 to 3 bits is large and from 4 to 6 is small</b> &mdash; "
        "which is why real decoders settle at 4 to 6 bits and why asking for more is "
        "paying for nothing."))

    s.append("<h2>X25.3 Estimation: the bound that tells you when to stop improving</h2>")
    s.append(derive("The Cram&eacute;r&ndash;Rao bound", [
        ("For an unbiased estimator of a parameter &theta; from data with density "
         "<i>p</i>(<b>r</b>;&theta;), var(&theta;&#770;) &ge; 1/<i>I</i>(&theta;).",
         "The Cram&eacute;r&ndash;Rao inequality."),
        ("<i>I</i>(&theta;) = E[(&part;ln <i>p</i>/&part;&theta;)<sup>2</sup>] is the "
         "Fisher information.",
         "How sharply the likelihood peaks &mdash; a flat likelihood means the data "
         "barely constrain &theta;."),
        ("For <i>N</i> independent observations, <i>I</i> scales with <i>N</i>.",
         "<b>So the standard deviation falls as 1/&radic;<i>N</i></b>, and no "
         "estimator does better. Quadrupling the averaging halves the error, always."),
        ("For frequency estimation from <i>N</i> samples the bound scales as "
         "<i>N</i><sup>&minus;3/2</sup>.",
         "<b>Much faster than 1/&radic;<i>N</i></b>, because a frequency error "
         "accumulates phase over the observation, so a longer observation is "
         "disproportionately informative. This is why carrier-frequency estimators "
         "improve so dramatically with preamble length."),
        ("An estimator that meets the bound is <i>efficient</i>.",
         "<b>The practical use of the bound is to know when to stop</b>: if your "
         "estimator is within a dB of it, further cleverness is wasted and the remaining "
         "error is the physics."),
    ]))
    rng3 = np.random.default_rng(23)
    rows = []
    for N in (16, 32, 64, 128, 256, 512):
        sigma = 0.3
        trials = 2000
        errs = []
        for _ in range(trials):
            f0 = 0.1
            n_ = np.arange(N)
            ph = 2 * np.pi * f0 * n_
            r = np.exp(1j * ph) + (rng3.normal(0, sigma, N) +
                                   1j * rng3.normal(0, sigma, N)) / math.sqrt(2)
            # simple estimator: average phase increment
            d = np.angle(r[1:] * np.conj(r[:-1]))
            errs.append(float(np.mean(d) / (2 * np.pi)) - f0)
        e = float(np.std(errs))
        snr = 1 / sigma ** 2
        crb = math.sqrt(6 / ((2 * math.pi) ** 2 * snr * N * (N * N - 1))) / (2 * math.pi) * (2 * math.pi)
        rows.append([num(N), num(e, 3), num(crb, 3), num(e / crb, 4),
                     num(20 * math.log10(e / crb), 4)])
    s.append(sweep("A simple frequency estimator against the Cram&eacute;r&ndash;Rao "
                   "bound, 2000 trials per point",
        ["Samples <i>N</i>", "Measured &sigma;<sub>&fnof;</sub>", "CRB",
         "Ratio", "Gap (dB)"], rows,
        "The phase-difference estimator is cheap &mdash; one complex multiply and an "
        "arctangent per sample &mdash; and the ratio column says how far from optimal "
        "that cheapness leaves it. <b>Knowing the gap is what makes the choice "
        "informed</b>: a designer can then decide whether the more expensive "
        "maximum-likelihood estimator is worth its cost for this link."))
    s.append(prob("Your carrier-frequency estimator is 3&nbsp;dB from the "
                  "Cram&eacute;r&ndash;Rao bound. Is it worth improving?",
        "Ask what the 3&nbsp;dB buys downstream, not whether 3&nbsp;dB is a lot. "
        "Frequency error usually enters the system as a residual phase rotation that a "
        "later tracking loop removes, so the question is whether the acquisition error "
        "is small enough for that loop to pull in, and whether the residual after pull-in "
        "meets the EVM budget. If both are comfortable, the 3&nbsp;dB is free and the "
        "improvement is wasted effort. If the tracking loop's pull-in range is the "
        "binding constraint &mdash; which it often is, because pull-in range trades "
        "against loop bandwidth and therefore against jitter tolerance (Part&nbsp;X12) "
        "&mdash; then closing the gap directly buys acquisition reliability, which is a "
        "field-failure-rate issue and worth real hardware. <b>The general rule is that a "
        "bound tells you how much room is left, and only the system tells you whether the "
        "room is worth occupying.</b>"))
    s.append(prob("Why do practical receivers estimate the channel rather than use a "
                  "blind equaliser, when blind methods need no training overhead?",
        "Because training overhead is cheap and convergence risk is not. A pilot or "
        "preamble costs a known, small fraction of the throughput &mdash; a few per cent "
        "&mdash; and in exchange gives a <b>convex</b> estimation problem with a closed "
        "form, a deterministic convergence time and a verifiable result. Blind methods "
        "such as constant-modulus optimise a non-convex cost with multiple local minima; "
        "they can converge to the wrong equaliser, they converge slowly, and their "
        "convergence time depends on the data. <b>For a product, a bounded worst case "
        "beats a better average</b>: a link that occasionally takes ten times as long to "
        "acquire is a field complaint, and one that occasionally locks to a spurious "
        "solution is a returned part. Blind methods retain a real place where training "
        "genuinely cannot be inserted &mdash; monitoring an existing link, or tracking "
        "between infrequent pilots &mdash; and in those roles they are usually "
        "initialised from a trained state rather than from nothing, which converts the "
        "non-convex problem into a local one."))
    return "\n".join(s)
