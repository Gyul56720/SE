# -*- coding: utf-8 -*-
"""Volume I, Part X30 -- OFDM and MIMO, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_ofdm():
    s = ['<h1 id="x30">X30. OFDM and MIMO, Worked</h1>']
    s.append("""<p>Every wireless standard of the last twenty years is OFDM, and most are
    MIMO. Both are, from a hardware point of view, ways of converting a hard problem into
    a large number of easy ones &mdash; and the conversion has costs that are computable
    and are the subject of most of the implementation literature.</p>""")

    s.append("<h2>X30.1 Why OFDM turns equalisation into division</h2>")
    s.append(derive("The cyclic prefix is the whole trick", [
        ("A multipath channel convolves the transmitted signal with an impulse "
         "response of length <i>L</i>.",
         "Linear convolution."),
        ("Circular convolution in time is multiplication in the DFT domain.",
         "The convolution theorem &mdash; but only for <i>circular</i> convolution."),
        ("A channel performs <i>linear</i> convolution, which is not circular, so the "
         "theorem does not apply.",
         "The blocks bleed into each other."),
        ("<b>Prepend the last <i>L</i>&minus;1 samples of each block to itself.</b>",
         "Now the tail that bleeds in is the same as what would have wrapped around, so "
         "over the retained window the linear convolution <i>is</i> circular."),
        ("Therefore <i>Y<sub>k</sub></i> = <i>H<sub>k</sub>X<sub>k</sub></i> + "
         "<i>N<sub>k</sub></i>, one complex multiply per subcarrier.",
         "<b>Equalisation becomes one complex division per subcarrier</b>, replacing a "
         "time-domain equaliser of length <i>L</i>. This is the entire reason OFDM "
         "exists."),
        ("Cost: the prefix is redundancy, so the rate falls by "
         "<i>N</i>/(<i>N</i>+<i>L</i>&minus;1).",
         "<b>And the peak-to-average ratio rises</b>, because a sum of many independent "
         "subcarriers is nearly Gaussian &mdash; X30.2."),
    ]))
    rows = []
    for name, N, cp, bw in (("802.11a", 64, 16, 20e6), ("802.11ax", 256, 32, 20e6),
                            ("LTE 20 MHz", 2048, 144, 20e6),
                            ("5G NR 100 MHz SCS30", 4096, 288, 100e6)):
        overhead = cp / (N + cp)
        sym = (N + cp) / bw
        guard_m = cp / bw * 3e8
        rows.append([name, num(N), num(cp), num(overhead * 100, 4),
                     num(sym * 1e6, 4), num(guard_m, 5)])
    s.append(sweep("Cyclic-prefix overhead and the delay spread it tolerates",
        ["Standard", "FFT size", "CP samples", "Rate lost (%)",
         "Symbol duration (&micro;s)", "Max echo path (m)"], rows,
        "The last column is the design driver: the prefix must exceed the channel's "
        "delay spread, and delay spread is set by the environment &mdash; tens of metres "
        "indoors, kilometres in a large cell. <b>The prefix is therefore not a free "
        "parameter but a property of the deployment</b>, which is why standards define "
        "several and negotiate."))
    s.append(ex("Sizing an OFDM receiver's FFT from the standard",
        "5G NR, 100&nbsp;MHz channel, 30&nbsp;kHz subcarrier spacing, 4096-point FFT, "
        "14 symbols per slot, 0.5&nbsp;ms slot.",
        "Compute the FFT rate the receiver must sustain, then apply Part&nbsp;X6's "
        "resource arithmetic to see what that implies.",
        [("Symbols per second", num(14 / 0.5e-3, 5)),
         ("FFT size", num(4096)),
         ("Complex multiplies per FFT",
          num(int(4096 / 2 * math.log2(4096)))),
         ("Complex multiplies per second",
          num(4096 / 2 * math.log2(4096) * 14 / 0.5e-3, 3)),
         ("At 500&nbsp;MHz, multipliers needed",
          num(math.ceil(4096 / 2 * math.log2(4096) * 14 / 0.5e-3 / 5e8))),
         ("Memory accesses per second (4 per butterfly)",
          num(4 * 4096 / 2 * math.log2(4096) * 14 / 0.5e-3, 3)),
         ("SRAM ports needed at 500&nbsp;MHz",
          num(math.ceil(4 * 4096 / 2 * math.log2(4096) * 14 / 0.5e-3 / 5e8)))],
        "<b>By sizing for one FFT and forgetting the antennas and the layers.</b> A "
        "four-antenna receiver needs four of these, and channel estimation needs more "
        "transforms again. The multiplier count is modest and the <b>memory port count "
        "is not</b> &mdash; which is Part&nbsp;X6's conclusion arriving in a specific "
        "product, and the reason an OFDM receiver's floorplan is dominated by buffer "
        "SRAM rather than by arithmetic."))

    s.append("<h2>X30.2 Peak-to-average ratio: the cost OFDM does not advertise</h2>")
    rng = np.random.default_rng(41)
    rows = []
    for N in (64, 256, 1024, 4096):
        trials = 400
        papr = []
        for _ in range(trials):
            X = (rng.choice([-1, 1], N) + 1j * rng.choice([-1, 1], N)) / math.sqrt(2)
            x = np.fft.ifft(X) * math.sqrt(N)
            p = np.abs(x) ** 2
            papr.append(float(p.max() / p.mean()))
        papr = np.array(papr)
        rows.append([num(N), num(float(10 * np.log10(papr.mean())), 4),
                     num(float(10 * np.log10(np.quantile(papr, 0.999))), 4),
                     num(float(10 * np.log10(papr.max())), 4),
                     num(10 * math.log10(N), 4)])
    s.append(sweep("Measured peak-to-average power ratio of QPSK-OFDM, 400 symbols "
                   "per point",
        ["Subcarriers <i>N</i>", "Mean PAPR (dB)", "99.9th percentile (dB)",
         "Observed max (dB)", "Theoretical worst case 10log<i>N</i> (dB)"], rows,
        "Computed by transforming random QPSK symbols. <b>The theoretical worst case "
        "is never approached</b> &mdash; it needs all subcarriers to align in phase, "
        "which has vanishing probability &mdash; but the 99.9th percentile grows slowly "
        "and is the number the power amplifier must be backed off by."))
    s.append("""<div class="warn"><b>PAPR is a power-amplifier problem, and the power
    amplifier is the most expensive and least efficient thing in a radio.</b> An amplifier
    must be operated below its compression point by the PAPR or the peaks clip, generating
    out-of-band emission that violates the spectral mask. Backing off 8&nbsp;dB means
    operating at a small fraction of the amplifier's capability, and amplifier efficiency
    falls steeply with back-off &mdash; which in a handset is battery life and in a base
    station is the electricity bill and the cooling. <b>This is why PAPR reduction
    (clipping and filtering, tone reservation, selected mapping) and digital
    pre-distortion exist</b>, and why single-carrier FDMA was chosen for the LTE uplink:
    the handset's amplifier is the constraint, so the uplink gave up OFDM's convenience to
    get several dB of PAPR back. <b>An architectural decision in a standard, driven
    entirely by one analogue component's efficiency curve.</b></div>""")
    rows = []
    for backoff in (3, 5, 7, 9, 11):
        eff = 0.78 * 10 ** (-backoff / 20)
        rows.append([num(backoff), num(eff * 100, 4), num(1 / eff, 4),
                     num((1 / eff - 1) * 1.0, 4)])
    s.append(sweep("Indicative amplifier efficiency against back-off "
                   "(class-AB model, 78&nbsp;% peak)",
        ["Back-off (dB)", "Efficiency (%)", "DC power per watt of RF",
         "Heat per watt of RF"], rows,
        "A first-order model, not a measurement of any particular device. <b>Its only "
        "job is to show the shape</b>: efficiency falls roughly as the voltage back-off, "
        "so every dB of PAPR costs real power, and a few dB of PAPR reduction pays for a "
        "great deal of digital signal processing."))

    s.append("<h2>X30.3 MIMO: capacity, and the detector that costs it</h2>")
    s.append(derive("Why multiple antennas multiply capacity", [
        ("With <i>N<sub>t</sub></i> transmit and <i>N<sub>r</sub></i> receive "
         "antennas, <b>y</b> = <b>Hx</b> + <b>n</b>.",
         "<b>H</b> is <i>N<sub>r</sub></i>&times;<i>N<sub>t</sub></i> complex."),
        ("Decompose <b>H</b> = <b>U&Sigma;V</b><sup>H</sup>; the channel becomes "
         "min(<i>N<sub>t</sub></i>,<i>N<sub>r</sub></i>) parallel scalar channels with "
         "gains &sigma;<sub><i>i</i></sub>.",
         "The singular value decomposition of Part&nbsp;X24, used as a change of "
         "basis."),
        ("Capacity = &Sigma; log<sub>2</sub>(1 + "
         "<i>P<sub>i</sub></i>&sigma;<sub><i>i</i></sub><sup>2</sup>/<i>N</i><sub>0</sub>).",
         "Sum of parallel Gaussian channels, with power allocated by water-filling."),
        ("<b>So capacity grows linearly with min(<i>N<sub>t</sub></i>,"
         "<i>N<sub>r</sub></i>)</b>, not logarithmically with power.",
         "<b>This is the whole point</b>: spatial multiplexing buys rate that more "
         "power cannot."),
        ("It requires the &sigma;<sub><i>i</i></sub> to be comparable &mdash; a "
         "well-conditioned <b>H</b>.",
         "<b>Line-of-sight channels are ill conditioned and give almost no "
         "multiplexing gain.</b> Rich scattering, which sounds like a bad channel, is "
         "what makes MIMO work &mdash; and Part&nbsp;X24's condition number is again "
         "the deciding quantity."),
    ]))
    rng2 = np.random.default_rng(43)
    rows = []
    for nt, nr in ((1, 1), (2, 2), (4, 4), (8, 8), (2, 4), (4, 2)):
        caps_rich, caps_los = [], []
        for _ in range(400):
            H = (rng2.normal(size=(nr, nt)) + 1j * rng2.normal(size=(nr, nt))) / math.sqrt(2)
            sv = np.linalg.svd(H, compute_uv=False)
            caps_rich.append(float(np.sum(np.log2(1 + 10.0 / nt * sv ** 2))))
            a = np.exp(1j * rng2.uniform(0, 2 * np.pi, nr))
            b_ = np.exp(1j * rng2.uniform(0, 2 * np.pi, nt))
            Hl = np.outer(a, b_)
            svl = np.linalg.svd(Hl, compute_uv=False)
            caps_los.append(float(np.sum(np.log2(1 + 10.0 / nt * svl ** 2))))
        rows.append([f"{nt}&times;{nr}", num(float(np.mean(caps_rich)), 4),
                     num(float(np.mean(caps_los)), 4),
                     num(float(np.mean(caps_rich)) / float(np.mean(caps_los)), 4),
                     num(min(nt, nr))])
    s.append(sweep("Measured ergodic capacity at 10&nbsp;dB SNR: rich scattering "
                   "against pure line of sight, 400 channel realisations",
        ["Configuration", "Rich scattering (bit/s/Hz)", "Line of sight",
         "Ratio", "min(<i>N<sub>t</sub></i>,<i>N<sub>r</sub></i>)"], rows,
        "A line-of-sight channel is rank one however many antennas it has, so its "
        "capacity does not grow with antenna count &mdash; the measurement confirms it. "
        "<b>The second column tracks the last column, which is the linear growth the "
        "derivation predicted.</b>"))
    s.append(tab("MIMO detectors, and what each costs",
        ["Detector", "Complexity", "Performance", "Hardware"],
        [["Zero forcing", "<i>O</i>(<i>N</i><sup>3</sup>) once per channel",
          "Poor at low SNR &mdash; noise enhancement (Part&nbsp;X24)",
          "A matrix inverse"],
         ["MMSE", "Same", "Better; regularised", "Same plus a diagonal add"],
         ["<b>Ordered SIC (V-BLAST)</b>", "<i>N</i> passes",
          "<b>Noticeably better than linear</b>",
          "Sequential &mdash; latency grows with <i>N</i>; error propagation"],
         ["<b>Sphere / K-best</b>", "Tree search, bounded",
          "<b>Near maximum likelihood</b>",
          "<b>A sorter and a tree walk &mdash; the standard hardware compromise</b>"],
         ["Maximum likelihood", "<i>M</i><sup><i>N<sub>t</sub></i></sup> candidates",
          "Optimal", "Infeasible beyond small cases: 16-QAM 4&times;4 is 65&#8239;536 "
          "candidates per symbol"]]))
    s.append(prob("Why does massive MIMO make the detector <i>easier</i> rather than "
                  "harder, despite having far more antennas?",
        "Because when <i>N<sub>r</sub></i> is much larger than <i>N<sub>t</sub></i> the "
        "columns of <b>H</b> become nearly orthogonal &mdash; a consequence of "
        "concentration of measure, since independent high-dimensional random vectors are "
        "nearly orthogonal with high probability. Nearly orthogonal columns mean "
        "<b>H</b><sup>H</sup><b>H</b> is nearly diagonal, so the simple matched filter "
        "(conjugate beamforming) is nearly optimal and the noise enhancement that makes "
        "zero forcing bad at low SNR essentially vanishes. <b>The hard detector problem "
        "is a symptom of having barely enough antennas</b>, and adding antennas at the "
        "base station &mdash; where size and power are affordable &mdash; dissolves it. "
        "The cost moves elsewhere and should be named: channel estimation for many "
        "antennas needs pilot resources and becomes the limiting factor (pilot "
        "contamination), the number of RF chains dominates cost and power, and the "
        "digital front end must move enormous sample rates from the antennas to the "
        "processing. <b>Massive MIMO trades a detection problem for an interconnect and "
        "calibration problem</b>, which is a trade the digital designer should recognise "
        "as favourable and should be ready to quantify."))
    return "\n".join(s)
