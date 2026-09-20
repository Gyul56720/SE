# -*- coding: utf-8 -*-
"""Volume I, Part X12 -- Mixed-signal blocks a digital designer must budget for."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_ams():
    s = ['<h1 id="x12">X12. Data Converters and PLLs, Worked</h1>']
    s.append("""<p>Very few IP blocks are purely digital at their boundary. A SerDes has
    an analogue front end; a sensor interface has a converter; every synchronous block has
    a clock that came from a PLL. A digital designer does not have to design these, but
    does have to <i>budget</i> for them, and budgeting requires the same arithmetic the
    analogue designer uses. This part supplies it.</p>""")

    s.append("<h2>X12.1 The converter equations, and what they leave out</h2>")
    s.append(derive("SNR, ENOB and the 6.02<i>N</i>+1.76 formula", [
        ("Quantisation error is bounded by &plusmn;&Delta;/2 with variance "
         "&Delta;&sup2;/12, if it is uniform.",
         "Part X1 established this and also measured where it fails."),
        ("A full-scale sine of peak <i>A</i> = 2<sup><i>N</i>&minus;1</sup>&Delta; has "
         "power <i>A</i>&sup2;/2.",
         "RMS of a sinusoid."),
        ("SNR = 10log<sub>10</sub>(<i>A</i>&sup2;/2 &divide; &Delta;&sup2;/12) = "
         "<b>6.02<i>N</i> + 1.76&nbsp;dB</b>.",
         "Substitute and simplify. The 1.76 is 10log<sub>10</sub>(1.5), the sine's "
         "crest-factor advantage over a uniform signal."),
        ("Real converters fall short; the shortfall is expressed as "
         "<b>ENOB = (SNDR &minus; 1.76)/6.02</b>.",
         "Invert the formula using the <i>measured</i> signal-to-noise-and-distortion "
         "ratio. <b>ENOB is a measurement, <i>N</i> is a pin count</b>, and quoting the "
         "second as if it were the first is the standard datasheet deception."),
        ("Aperture jitter adds a noise term "
         "SNR<sub>jitter</sub> = &minus;20log<sub>10</sub>(2&pi;<i>f</i><sub>in</sub>"
         "&sigma;<sub><i>t</i></sub>).",
         "The sampled error is the signal's slew times the timing error; slew is "
         "proportional to input frequency. <b>This term does not depend on <i>N</i> at "
         "all</b> and eventually dominates every high-speed converter."),
    ]))
    rows = []
    for N in (8, 10, 12, 14, 16):
        ideal = 6.02 * N + 1.76
        for fin, jit in ((10e6, 1e-12),):
            pass
        cells = [num(N), num(ideal, 4)]
        for fin in (1e6, 10e6, 100e6, 1e9):
            j = 1e-12
            snr_j = -20 * math.log10(2 * math.pi * fin * j)
            tot = -10 * math.log10(10 ** (-ideal / 10) + 10 ** (-snr_j / 10))
            cells.append(num((tot - 1.76) / 6.02, 3))
        rows.append(cells)
    s.append(sweep("Effective bits achievable with 1&nbsp;ps RMS aperture jitter, "
                   "against nominal resolution and input frequency",
        ["Nominal <i>N</i>", "Ideal SNR (dB)", "ENOB at 1&nbsp;MHz", "at 10&nbsp;MHz",
         "at 100&nbsp;MHz", "at 1&nbsp;GHz"], rows,
        "Read down the last column: <b>at 1&nbsp;GHz input, 1&nbsp;ps of jitter caps the "
        "converter at about 8 bits no matter how many bits the part has.</b> Buying a "
        "16-bit converter without buying a cleaner clock buys nothing."))
    s.append(plot([1e6, 1e7, 1e8, 1e9],
                  [(f"{j*1e15:.0f} fs",
                    [-20 * math.log10(2 * math.pi * f * j) for f in (1e6, 1e7, 1e8, 1e9)])
                   for j in (1e-12, 3e-13, 1e-13)],
                  "input frequency (Hz)", "jitter-limited SNR (dB)",
                  "The jitter wall. Every curve falls 20 dB per decade of input "
                  "frequency; the only way up is a better clock.", logx=True))
    s.append(ex("Specifying the clock for an ADC, backwards from the requirement",
        "A receiver needs 11 effective bits on a 500&nbsp;MHz input. The converter's own "
        "thermal and distortion contribution is 13 ENOB.",
        "Convert the requirement to an SNR, subtract the converter's own contribution "
        "in the power domain to find the jitter budget, then invert the jitter formula.",
        [("Required SNDR", num(6.02 * 11 + 1.76, 4, "dB")),
         ("Converter's own SNR", num(6.02 * 13 + 1.76, 4, "dB")),
         ("Permitted jitter-noise SNR",
          num(-10 * math.log10(10 ** (-(6.02 * 11 + 1.76) / 10) -
                               10 ** (-(6.02 * 13 + 1.76) / 10)), 4, "dB")),
         ("Permitted RMS aperture jitter",
          num(10 ** (-(-10 * math.log10(10 ** (-(6.02 * 11 + 1.76) / 10) -
                                        10 ** (-(6.02 * 13 + 1.76) / 10))) / 20) /
              (2 * math.pi * 500e6) * 1e15, 3, "fs")),
         ("Is that achievable with an on-chip PLL?",
          "<b>demanding &mdash; it is at the edge of a good integrated LC PLL</b>")],
        "<b>By subtracting decibels instead of powers.</b> Noise contributions add in "
        "power, so budgets must be combined as 10<sup>&minus;SNR/10</sup> terms and only "
        "then converted back. Subtracting 11 from 13 in dB gives a meaningless number. "
        "The second error, subtler, is to forget that the <i>clock buffer</i> between the "
        "PLL and the sampler adds its own jitter, often more than the PLL, so a budget "
        "that spends the whole allowance on the PLL has already failed."))
    s.append(tab("Converter architectures and where each lives",
        ["Architecture", "Resolution", "Speed", "Latency", "Cost driver"],
        [["Flash", "4&ndash;6 bits", "<b>Highest</b>", "1 cycle",
          "2<sup><i>N</i></sup> comparators &mdash; area doubles per bit"],
         ["Pipelined", "10&ndash;14 bits", "High", "<b><i>N</i>/2 cycles</b>",
          "Op-amps; inter-stage gain accuracy"],
         ["SAR", "8&ndash;16 bits", "Moderate", "<i>N</i> cycles",
          "Capacitor matching; <b>scales beautifully with process</b>"],
         ["Sigma-delta", "16&ndash;24 bits", "Low signal bandwidth", "High (filter)",
          "Oversampling ratio; digital decimation filter"],
         ["Time-interleaved", "8&ndash;12 bits", "<b>Extreme</b>", "As the sub-ADC",
          "<b>Mismatch between channels</b> &mdash; gain, offset and timing skew, all "
          "needing digital calibration"]]))
    s.append("""<div class="ms"><b>Time interleaving is where the digital team earns its
    place in an analogue block.</b> Running <i>M</i> converters in round robin multiplies
    the sample rate by <i>M</i> and introduces three mismatches: offset, which appears as
    spurs at multiples of <i>f</i><sub>s</sub>/<i>M</i>; gain, which appears as spurs
    around the signal; and timing skew, which appears as signal-dependent spurs that grow
    with input frequency. None is removable by better layout alone at modern speeds; all
    three are corrected by <b>digital background calibration</b> that estimates the
    mismatch from the data and applies a correction. That estimator is a piece of DSP with
    a convergence time, a lock detector and a failure mode, and it is specified,
    modelled and verified by the digital side. <b>A SerDes receiver's ADC is
    time-interleaved 32 or 64 ways, and its calibration loops are a substantial part of
    the digital block's area.</b></div>""")

    s.append("<h2>X12.2 Phase-locked loops: the transfer functions that matter</h2>")
    s.append(derive("Why a PLL is a lowpass for reference noise and a highpass for VCO "
                    "noise", [
        ("Open loop: <i>G</i>(<i>s</i>) = <i>K</i><sub>pd</sub><i>F</i>(<i>s</i>)"
         "<i>K</i><sub>vco</sub>/<i>s</i>, divided by <i>N</i>.",
         "Phase detector gain, loop filter, VCO as a phase integrator, feedback divider."),
        ("Reference to output: <i>N G</i>/(1+<i>G</i>).",
         "Standard feedback algebra. At low frequency <i>G</i>&nbsp;&gg;&nbsp;1 so this "
         "is <i>N</i>; at high frequency it rolls off. <b>Lowpass.</b>"),
        ("VCO noise to output: 1/(1+<i>G</i>).",
         "The VCO's noise enters after the phase detector. At low frequency the loop "
         "suppresses it; above the bandwidth it passes. <b>Highpass.</b>"),
        ("<b>So the loop bandwidth is a crossover, not a quality setting.</b>",
         "Wide bandwidth tracks the reference and suppresses VCO noise; narrow bandwidth "
         "rejects reference noise and lets the VCO run free. The optimum is where the two "
         "noise densities cross, and that point is <b>measured</b>, not chosen by "
         "taste."),
        ("Total output jitter is the integral of the combined phase-noise spectrum over "
         "the band of interest.",
         "Which is why a jitter specification without an integration band is incomplete "
         "&mdash; the same part can be quoted at 200 fs or 2 ps depending on limits."),
    ]))
    rows = []
    for bw in (0.1e6, 0.5e6, 1e6, 2e6, 5e6):
        # toy model: ref noise -100 dBc/Hz flat, vco noise -80 dBc/Hz at 1MHz, -20dB/dec
        fs_ = np.logspace(4, 8, 2000)
        ref = 10 ** (-100 / 10) * np.ones_like(fs_)
        vco = 10 ** (-80 / 10) * (1e6 / fs_) ** 2
        lp = 1 / (1 + (fs_ / bw) ** 2)
        hp = 1 - lp
        tot = ref * lp * 400 + vco * hp        # N^2 = 400 for N=20
        j = math.sqrt(2 * np.trapezoid(tot, fs_)) / (2 * math.pi * 2.5e9) * 1e15
        rows.append([num(bw / 1e6, 3), num(10 * math.log10(float(tot[0])), 4),
                     num(10 * math.log10(float(np.interp(1e6, fs_, tot))), 4),
                     num(j, 4)])
    s.append(sweep("Integrated jitter of a 2.5&nbsp;GHz PLL against loop bandwidth, "
                   "with a toy noise model (reference &minus;100&nbsp;dBc/Hz flat, "
                   "VCO &minus;80&nbsp;dBc/Hz at 1&nbsp;MHz, <i>N</i>&nbsp;=&nbsp;20)",
        ["Loop bandwidth (MHz)", "Output phase noise at 10&nbsp;kHz (dBc/Hz)",
         "at 1&nbsp;MHz (dBc/Hz)", "Integrated RMS jitter 10&nbsp;kHz&ndash;100&nbsp;MHz (fs)"],
        rows,
        "Integrated numerically over the stated band. There is a minimum: too narrow and "
        "the VCO dominates, too wide and the reference multiplied by <i>N</i>&sup2; "
        "dominates. <b>The 20log<sub>10</sub><i>N</i> multiplication of reference noise "
        "is the term designers forget</b>, and it is 26&nbsp;dB here."))
    s.append("""<div class="warn"><b>A PLL specification needs five numbers and is usually
    given two.</b> Output frequency and jitter are not enough. The five are: output
    frequency range; <b>integrated jitter with its integration band</b>; spurious tone
    level, since a single reference spur can violate a mask that broadband jitter passes;
    lock time, which sets how long a power-gated block takes to become usable; and the
    <b>input reference's own phase noise</b>, since the PLL multiplies it by
    20log<sub>10</sub><i>N</i>. A block that is specified without the fifth will work on
    the vendor's evaluation board with a laboratory clock source and fail in the
    customer's system with a crystal oscillator.</div>""")
    rows = []
    for N in (2, 4, 10, 20, 50, 100):
        rows.append([num(N), num(20 * math.log10(N), 4),
                     num(-100 + 20 * math.log10(N), 4),
                     num(-130 + 20 * math.log10(N), 4)])
    s.append(sweep("Reference phase noise is multiplied by the divide ratio",
        ["Divide ratio <i>N</i>", "20log<sub>10</sub><i>N</i> (dB)",
         "Output noise from a &minus;100&nbsp;dBc/Hz reference",
         "Output noise from a &minus;130&nbsp;dBc/Hz reference"], rows,
        "In-band only &mdash; above the loop bandwidth the reference is filtered. "
        "This is the reason a high-speed SerDes wants a low reference multiplication, "
        "and the reason a 100&nbsp;MHz reference often beats a 25&nbsp;MHz one for the "
        "same output frequency."))
    s.append(prob("A clock-and-data-recovery loop and a frequency-synthesis PLL are both "
                  "PLLs. Why is the CDR's bandwidth chosen by a standard rather than by "
                  "the designer?",
        "Because in a CDR the loop bandwidth determines <b>jitter tolerance</b>, which is "
        "an interoperability property rather than a performance one. Jitter below the "
        "loop bandwidth is tracked by the receiver and causes no error; jitter above it "
        "is not tracked and eats the eye directly. So the receiver's bandwidth and the "
        "transmitter's permitted jitter spectrum are two halves of one specification: if "
        "each vendor chose its own bandwidth, a compliant transmitter and a compliant "
        "receiver could still fail together. Standards therefore specify a <b>jitter "
        "tolerance mask</b> &mdash; how much sinusoidal jitter the receiver must survive "
        "at each frequency &mdash; which constrains the loop bandwidth from below, and a "
        "<b>jitter transfer</b> limit, which constrains it from above so that jitter is "
        "not amplified around the loop's peaking and accumulated through a chain of "
        "repeaters. <b>The designer's freedom is what remains between the two masks</b>, "
        "and in modern standards that gap is narrow."))
    s.append(prob("Why does a fractional-<i>N</i> synthesiser need a delta-sigma "
                  "modulator, and what does it cost?",
        "A divider divides by an integer. To reach a fractional average the divide ratio "
        "must be switched between neighbouring integers, and the <i>pattern</i> of "
        "switching determines where the resulting phase error lands in frequency. A "
        "simple periodic pattern puts it at a low frequency inside the loop bandwidth, "
        "where it appears as a <b>fractional spur</b> &mdash; a discrete tone that "
        "violates masks. A delta-sigma modulator chooses the pattern so that the "
        "quantisation error is <i>shaped</i> to high frequency, where the loop filters "
        "it. The costs are real: the shaped noise is larger in total than the unshaped "
        "noise, so the loop bandwidth must be kept below the point where the shaping "
        "rises; a higher-order modulator shapes harder but can produce idle tones if its "
        "input sits near a simple fraction, which is why implementations dither the "
        "input; and the divider must now handle a range of ratios, which complicates its "
        "design. <b>This is a clean example of a digital block bought to relax an "
        "analogue constraint</b>, which is the dominant trend in mixed-signal design and "
        "the reason the boundary keeps moving toward the digital side."))
    return "\n".join(s)
