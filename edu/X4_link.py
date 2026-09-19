# -*- coding: utf-8 -*-
"""Volume I, Part X4 -- The wireline link budget, worked.

A SerDes specification is a budget that must balance.  This part builds one from
the channel response outward, computing every term, so that the reader can take a
datasheet number apart and say which term it came from.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

Q = lambda x: 0.5 * math.erfc(x / math.sqrt(2))


def _f_link():
    b = []
    names = [("TX\nFFE", 18), ("driver", 78), ("channel", 140), ("CTLE", 214),
             ("DFE", 274), ("slicer", 330)]
    for nm, x in names:
        b.append(box(x, 34, 54, 30, nm.replace("\n", " "), None, 8))
        if x > 18:
            b.append(arr(x - 6, 49, x, 49))
    b.append(arr(384, 49, 408, 49))
    b.append(txt(167, 24, "loss, reflections, crosstalk", 8, "middle"))
    b.append(txt(45, 82, "pre-emphasis", 8, "middle"))
    b.append(txt(241, 82, "continuous-time boost", 8, "middle"))
    b.append(txt(301, 82, "post-cursor cancel", 8, "middle"))
    b.append(txt(214, 108, "Everything before the slicer exists to make the eye open at "
                           "one instant in time.", 9, "middle", 'font-style="italic"'))
    return svg(430, 118, "".join(b))


def chan_pulse(loss_db_at_nyq, fb, nspui=16, ntaps=None):
    """Synthesise a pulse response for a channel with sqrt(f) loss.

    A real design uses measured or field-solved S-parameters.  A synthetic
    sqrt(f) channel is used here because the *shape* of the conclusion -- how
    much ISI there is, how many DFE taps it takes -- depends on the loss slope,
    not on the particular connector, and a synthetic channel is reproducible by
    the reader without a VNA.
    """
    fs = fb * nspui
    N = 4096
    f = np.fft.rfftfreq(N, 1 / fs)
    fn = fb / 2
    H = 10 ** (-loss_db_at_nyq * np.sqrt(np.maximum(f, 0) / fn) / 20.0)
    h = np.fft.irfft(H, N)
    h = np.roll(h, N // 8)
    p = np.convolve(h, np.ones(nspui), "same")   # one-UI rectangular pulse
    k = int(np.argmax(np.abs(p)))
    if ntaps is None:
        ntaps = 24
    cur = np.array([p[k + i * nspui] for i in range(-2, ntaps)
                    if 0 <= k + i * nspui < len(p)])
    return cur / np.abs(cur).max()


def ch_linkbudget():
    s = ['<h1 id="x4">X4. The Wireline Link Budget, Worked</h1>']
    s.append(fig(_f_link(), "The signal chain a link budget accounts for. Each block "
                            "contributes a term; the budget is the statement that the "
                            "terms sum to something positive."))

    s.append("<h2>X4.1 From loss in dB to intersymbol interference</h2>")
    s.append("""<p>A channel specification usually gives one number: insertion loss at the
    Nyquist frequency. That number is not directly usable. What the receiver has to deal
    with is the <i>pulse response</i> &mdash; what a single transmitted symbol looks like
    at the sampler, sampled once per unit interval. The cursors of that response are the
    intersymbol interference, and they are what every equaliser in the chain is
    fighting.</p>""")
    fb = 53.125e9
    rows = []
    for L in (5, 10, 15, 20, 25, 30, 35):
        c = chan_pulse(L, fb)
        k = int(np.argmax(np.abs(c)))
        main = abs(c[k])
        pre = float(np.abs(c[:k]).sum())
        post = float(np.abs(c[k + 1:]).sum())
        rows.append([L, num(main, 3), num(pre, 3), num(post, 3),
                     num(main - pre - post, 3),
                     "open" if main - pre - post > 0 else "<b>closed</b>"])
    s.append(sweep("Pulse-response cursors of a &radic;<i>f</i> channel at 53.125&nbsp;GBd "
                   "as insertion loss is swept",
        ["Loss at Nyquist (dB)", "Main cursor", "&Sigma;|pre-cursors|",
         "&Sigma;|post-cursors|", "Worst-case eye height", "Unequalised eye"],
        rows,
        "Cursors are normalised so the main cursor of the least-lossy case is 1. "
        "The fifth column is the classic worst-case opening, main &minus; &Sigma;|ISI|, "
        "which assumes every neighbouring symbol conspires against the one being "
        "sampled."))
    s.append("""<div class="ms"><b>Worst-case eye height goes negative long before the
    link is actually unusable, and that is not a contradiction.</b> The worst case demands
    a specific data pattern; at 10<sup>&minus;4</sup> bit error rate you care about
    patterns that occur with probability around 10<sup>&minus;4</sup>, not about the one
    worst pattern. This is why link analysis moved from peak-distortion analysis to
    <b>statistical eye</b> methods: convolve the probability distributions of the
    individual cursors rather than summing their magnitudes. Peak analysis is a bound;
    the statistical eye is the answer. A specification that quotes a closed worst-case eye
    and a working link is not lying, but it is using two different methods and should say
    so.</div>""")
    # statistical vs peak
    c = chan_pulse(25, fb)
    k = int(np.argmax(np.abs(c)))
    isi = np.concatenate([c[:k], c[k + 1:]])
    main = abs(c[k])
    rng = np.random.default_rng(3)
    d = rng.choice([-1.0, 1.0], (400000, isi.size))
    tot = d @ isi
    rows2 = []
    for ber in (1e-3, 1e-4, 1e-5, 1e-6):
        qq = np.quantile(np.abs(tot), 1 - ber)
        rows2.append([num(ber, 2), num(float(qq), 3), num(main - float(qq), 3),
                      num(float(np.abs(isi).sum()), 3), num(main - float(np.abs(isi).sum()), 3)])
    s.append(sweep("Statistical eye vs. peak-distortion eye, 25&nbsp;dB channel, "
                   "400&#8239;000 random patterns",
        ["Target BER", "ISI exceeded with that probability", "Statistical eye height",
         "Peak &Sigma;|ISI|", "Peak-distortion eye height"], rows2,
        "The last column is the same for every row because the peak bound does not "
        "depend on the target. The difference between columns three and five is the "
        "margin that peak analysis throws away &mdash; and it is often more than a "
        "whole equaliser's worth."))

    s.append("<h2>X4.2 What each equaliser can and cannot do</h2>")
    s.append(tab("Equaliser taxonomy, stated by what it operates on",
        ["Block", "Operates on", "Cancels", "Cannot", "Costs"],
        [["TX FFE", "The transmitted waveform, before the channel",
          "Pre- and post-cursors", "<b>Add energy</b> &mdash; it can only redistribute, "
          "so boosting high frequencies lowers the average launched amplitude",
          "Launch amplitude, hence SNR"],
         ["CTLE", "The analogue waveform, continuously",
          "Broad loss slope", "Distinguish signal from noise &mdash; it boosts both",
          "Noise enhancement; peaking bandwidth"],
         ["<b>DFE</b>", "<b>Decided symbols</b>",
          "<b>Post-cursors only, with no noise enhancement</b>",
          "Touch pre-cursors; survive a wrong decision without error propagation",
          "A feedback loop that must close in one UI"],
         ["MLSE / Viterbi", "A sequence", "Everything, optimally in the ML sense",
          "Be cheap: complexity is exponential in memory",
          "Area and power; latency"],
         ["FFE in the RX (post-ADC)", "The sampled waveform",
          "Pre- and post-cursors", "Avoid amplifying noise, like any linear equaliser",
          "ADC resolution and DSP power"]]))
    s.append("""<div class="warn"><b>The DFE's advantage and its constraint are the same
    fact.</b> Because it subtracts using <i>decisions</i> rather than the received
    waveform, it cancels post-cursor ISI without amplifying noise &mdash; the property
    that makes it indispensable on lossy channels. But that decision must be made,
    multiplied and subtracted before the next symbol is sampled, which at 53&nbsp;GBd
    means the whole loop in 18.8&nbsp;ps. Part&nbsp;X2's budget table says how many gate
    delays that is; the answer is close to zero, and the architectural response is
    <b>unrolling</b> (speculate on both possible decisions and select afterwards), which
    converts the timing problem into an area problem that grows as 2<sup><i>n</i></sup> in
    the number of unrolled taps.</div>""")
    ui = 1 / fb
    terms = [("Slicer clock-to-Q", 6e-12), ("Tap multiply (1-bit &times; coefficient)", 3e-12),
             ("Summer", 4e-12), ("Wire and buffering back to the summer", 5e-12),
             ("Slicer setup", 4e-12)]
    tot_ps = sum(v for _, v in terms)
    s.append(ex("The one-UI DFE budget at 53.125&nbsp;GBd",
        "A direct-feedback first tap. Symbol rate 53.125&nbsp;GBd. Component delays as "
        "listed, taken from a 7&nbsp;nm-class custom cell set.",
        "Sum the terms and compare with one unit interval. There is no cleverness here; "
        "the point of the example is that the arithmetic is trivial and the answer is "
        "nonetheless the reason a whole architecture exists.",
        [("Unit interval", num(ui * 1e12, 4, "ps"))] +
        [(k, num(v * 1e12, 3, "ps")) for k, v in terms] +
        [("Total loop delay", num(tot_ps * 1e12, 4, "ps")),
         ("Margin", num((ui - tot_ps) * 1e12, 3, "ps")),
         ("Verdict", "<b>does not close &mdash; must be unrolled</b>"
          if tot_ps > ui else "closes")],
        "<b>By budgeting the logic and forgetting the wire.</b> In this budget the wire "
        "and buffering term is comparable to the summer. At these rates the feedback path "
        "is a physical-design problem before it is a logic problem, and a block-level "
        "delay estimate made from gate counts alone will be optimistic by roughly a "
        "third. <b>Any loop budget that does not have a line for interconnect is "
        "incomplete.</b>"))
    rows3 = []
    for n in range(1, 7):
        rows3.append([n, num(2 ** n), num(2 ** n - 1),
                      num((2 ** n) * 1.0, 3), "yes" if n <= 3 else "impractical"])
    s.append(sweep("Cost of unrolling <i>n</i> DFE taps",
        ["Unrolled taps <i>n</i>", "Speculative slicers", "Select-mux inputs",
         "Relative slicer area", "Seen in production?"], rows3,
        "Slicers at these rates are analogue comparators with real offset-trim circuits, "
        "so the area is not notional. Production parts unroll one or two taps and handle "
        "the rest with a pipelined or parallel structure."))

    s.append("<h2>X4.3 Jitter, noise and the BER that results</h2>")
    s.append(derive("From an eye opening to a bit error rate", [
        ("At the sampling instant the decision variable is "
         "<i>v</i> = &plusmn;<i>A</i><sub>eff</sub> + <i>n</i>.",
         "<i>A</i><sub>eff</sub> is the residual eye half-height after equalisation; "
         "<i>n</i> is the total additive noise referred to that node."),
        ("An error occurs when <i>n</i> crosses <i>A</i><sub>eff</sub> in the wrong "
         "direction.", "Slicer threshold at zero."),
        ("For Gaussian <i>n</i> with standard deviation &sigma;, "
         "BER = <i>Q</i>(<i>A</i><sub>eff</sub>/&sigma;).",
         "Tail probability of a Gaussian. <b>The Gaussian assumption is the weak "
         "link</b> and X4.4 says why."),
        ("Timing error &Delta;<i>t</i> reduces the effective amplitude to "
         "<i>p</i>(<i>t</i><sub>0</sub>+&Delta;<i>t</i>), and near the peak that "
         "reduction is second order.",
         "The pulse response is smooth and stationary at its peak &mdash; "
         "<b>which is why a sensitivity measured exactly at the peak is zero by "
         "definition and means nothing.</b>"),
        ("So jitter must be evaluated where the slope is large, i.e. displaced from the "
         "optimum, or by convolving the timing distribution into the statistical eye.",
         "This is what a compliance tool does; it is also what an honest hand "
         "calculation must do."),
    ]))
    rows4 = []
    for snr_db in (10, 12, 14, 16, 18, 20):
        r = 10 ** (snr_db / 20)
        rows4.append([snr_db, num(r, 3), num(Q(r), 2),
                      num(Q(r * 0.9), 2), num(Q(r) / max(Q(r * 0.9), 1e-300), 2)])
    s.append(sweep("BER against amplitude-to-noise ratio, and the effect of losing "
                   "10&nbsp;% of the eye",
        ["<i>A</i>/&sigma; (dB)", "<i>A</i>/&sigma;", "BER", "BER at 0.9<i>A</i>",
         "Ratio"], rows4,
        "The last column is the lesson: near 10<sup>&minus;12</sup> a ten per cent eye "
        "loss costs two to three orders of magnitude of BER. <b>Link margin is not "
        "linear and small budget errors are not small.</b>"))
    s.append(plot([10, 12, 14, 16, 18, 20],
                  [("BER", [math.log10(max(Q(10 ** (d / 20)), 1e-300))
                            for d in (10, 12, 14, 16, 18, 20)]),
                   ("BER, 10% eye lost",
                    [math.log10(max(Q(0.9 * 10 ** (d / 20)), 1e-300))
                     for d in (10, 12, 14, 16, 18, 20)])],
                  "A/sigma (dB)", "log10 BER",
                  "The waterfall. The vertical gap between the curves at constant BER is "
                  "the margin a budget error consumes."))
    s.append(ex("Turning a jitter specification into an eye loss",
        "Random jitter 250&nbsp;fs RMS, deterministic jitter 2&nbsp;ps peak-to-peak, "
        "UI = 18.8&nbsp;ps, target BER 10<sup>&minus;4</sup> before FEC.",
        "Total jitter at a target BER is the dual-Dirac construction: "
        "TJ = DJ + 2<i>Q</i><sub>BER</sub>&nbsp;&middot;&nbsp;RJ, where "
        "<i>Q</i><sub>BER</sub> is the Gaussian quantile for that BER.",
        [("Q for BER 10<sup>&minus;4</sup>", num(3.719, 4)),
         ("Random contribution 2<i>Q</i>&middot;RJ", num(2 * 3.719 * 0.25, 4, "ps")),
         ("Deterministic contribution", num(2.0, 3, "ps")),
         ("Total jitter", num(2 * 3.719 * 0.25 + 2.0, 4, "ps")),
         ("As a fraction of the UI", num((2 * 3.719 * 0.25 + 2.0) / (ui * 1e12), 3)),
         ("Eye width remaining", num(ui * 1e12 - (2 * 3.719 * 0.25 + 2.0), 4, "ps"))],
        "<b>By using the Q for the wrong BER.</b> The same jitter is 3.9&nbsp;ps at "
        "10<sup>&minus;4</sup> and about 5.9&nbsp;ps at 10<sup>&minus;12</sup>; quoting a "
        "TJ number without its BER is meaningless, and the two numbers differ by enough "
        "to change an architecture. The second error is to add RJ and DJ in quadrature: "
        "DJ is bounded, not Gaussian, and it adds <i>linearly</i> to the Gaussian tail. "
        "Quadrature addition here understates the total."))

    s.append("<h2>X4.4 Where the Gaussian assumption fails, and what FEC changes</h2>")
    s.append("""<p>Two facts force a modern link away from the simple budget above. Noise
    at the slicer is not Gaussian &mdash; crosstalk is the sum of a few discrete
    interferers and has a bounded, multi-modal distribution &mdash; and errors are not
    independent, because a DFE that makes a wrong decision feeds it back and produces a
    short burst. Both matter for FEC design, which is the subject of Part&nbsp;F2 and of
    the block this book's practice volume builds.</p>""")
    s.append(tab("Assumption, reality, and the design consequence",
        ["Assumption in the simple budget", "What is actually true",
         "Consequence for the design"],
        [["Noise is Gaussian", "Crosstalk from <i>k</i> aggressors is a sum of "
          "<i>k</i> bounded terms; the tail is lighter than Gaussian but the body is "
          "wider",
          "Extrapolating a measured 10<sup>&minus;6</sup> BER to "
          "10<sup>&minus;15</sup> with a Gaussian fit can be wrong by decades <b>in "
          "either direction</b>"],
         ["Errors are independent", "DFE error propagation produces bursts of length "
          "comparable to the number of taps",
          "<b>The FEC must be chosen for a burst channel</b>: symbol-oriented codes "
          "(Reed&ndash;Solomon over GF(2<sup>10</sup>)) rather than bit-oriented ones"],
         ["The sampling instant is optimal", "The CDR tracks a noisy estimate and "
          "dithers about the optimum",
          "Budget a static phase offset as well as jitter"],
         ["The equaliser is converged", "Adaptation is a slow loop with its own noise "
          "and can converge to a local optimum",
          "<b>Specify and measure the converged state</b>; a measurement taken before "
          "convergence is not a measurement of the link"]]))
    s.append(prob("A link measures 10<sup>&minus;6</sup> raw BER. The FEC is "
                  "RS(544,514) over GF(2<sup>10</sup>), correcting 15 symbol errors per "
                  "codeword. Estimate the post-FEC frame error rate, and say why the "
                  "estimate is fragile.",
        "Each codeword is 544 ten-bit symbols. A symbol is wrong if any of its ten bits "
        "is wrong, so with independent bit errors the symbol error probability is about "
        "1&minus;(1&minus;10<sup>&minus;6</sup>)<sup>10</sup> &asymp; "
        "10<sup>&minus;5</sup>. The codeword fails when more than 15 of 544 symbols are "
        "wrong; with a mean of 544&times;10<sup>&minus;5</sup> &asymp; 5.4&times;"
        "10<sup>&minus;3</sup> errors per codeword the binomial tail at 16 is "
        "astronomically small, which is the intended answer. <b>The fragility is the "
        "independence assumption.</b> If a DFE burst corrupts several consecutive bits, "
        "they may fall inside <i>one</i> symbol &mdash; which helps, since a symbol code "
        "charges the same price for one wrong bit or ten &mdash; or straddle a symbol "
        "boundary and cost two. Worse, if bursts are long enough to span many symbols, "
        "the tail is controlled by burst statistics that the raw BER number does not "
        "contain at all. <b>Post-FEC performance cannot be computed from pre-FEC BER "
        "alone; it needs the error-clustering statistics</b>, which is why compliance "
        "specifications define stressed-eye tests rather than BER targets alone."))
    s.append(prob("Why does IEEE 802.3dj concatenate an inner code with the outer "
                  "RS-KP4 rather than simply using a stronger single code?",
        "Three reasons, and they are all system reasons rather than coding-theory ones. "
        "<b>Backward compatibility</b>: RS(544,514) is already deployed and an outer "
        "layer that leaves it intact protects an installed base of PCS implementations. "
        "<b>Latency and locality</b>: the inner code can be short and decoded close to "
        "the PHY with low latency, cleaning up the random errors, while the outer code "
        "handles what remains; a single long code with the same total redundancy would "
        "have higher decoding latency. <b>Burst breaking</b>: the inner decoder's "
        "residual errors, after interleaving, present the outer decoder with something "
        "closer to the independent-symbol channel that Reed&ndash;Solomon analysis "
        "assumes &mdash; which is precisely the assumption the previous problem showed to "
        "be the fragile one."))
    return "\n".join(s)
