# -*- coding: utf-8 -*-
"""Volume I, Part A -- Mathematical and physical foundations."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line, poly


def _f_lti():
    b = [box(190, 40, 150, 46, "LTI system", "h[n]", 10)]
    b += [arr(60, 63, 190, 63), txt(62, 55, "x[n]", 10),
          arr(340, 63, 470, 63), txt(398, 55, "y[n] = (x * h)[n]", 10),
          txt(265, 112, "Linearity + time invariance ⇒ one impulse response is the whole system",
              9, "middle", 'font-style="italic"'),
          txt(265, 134, "Y(z) = H(z)·X(z)   —  convolution becomes multiplication", 10, "middle")]
    return svg(520, 148, "".join(b))


def _f_roc():
    b = [line(30, 120, 330, 120), line(180, 15, 180, 225)]
    b.append('<circle cx="180" cy="120" r="72" fill="none" stroke="#000" stroke-width="1.2"/>')
    b.append('<circle cx="180" cy="120" r="108" fill="none" stroke="#888" '
             'stroke-dasharray="4,3" stroke-width="1"/>')
    for x, y in ((225, 88), (150, 165), (232, 150)):
        b.append(f'<text x="{x}" y="{y}" font-size="13" text-anchor="middle">×</text>')
    b += [txt(258, 114, "|z| = 1", 9), txt(300, 60, "ROC", 9),
          txt(180, 246, "Causal + stable ⇔ all poles inside the unit circle", 9, "middle",
              'font-style="italic"')]
    return svg(360, 258, "".join(b))


def ch_lti():
    s = ['<h1 id="a1">A1. Signals, Systems and Linearity</h1>']
    s.append("""<p>Every digital IP block is a <i>system</i>: it maps input sequences to
    output sequences. Before discussing any particular block we fix the vocabulary that
    makes such maps analysable, and &mdash; more importantly for a hardware engineer
    &mdash; we identify exactly which property of a system makes it <b>cheap</b> to
    build and which makes it <b>expensive</b>.</p>""")

    s.append("<h2>A1.1 Definitions</h2>")
    s.append(tab("System properties and their hardware consequences",
        ["Property", "Definition", "Hardware consequence"],
        [["<b>Memoryless</b>", "<i>y</i>[<i>n</i>] depends only on <i>x</i>[<i>n</i>]",
          "Pure combinational logic; no registers, no state to reset or scan"],
         ["<b>Causal</b>", "<i>y</i>[<i>n</i>] depends only on <i>x</i>[<i>k</i>], "
          "<i>k</i>&nbsp;&le;&nbsp;<i>n</i>",
          "Required for real-time streaming. Non-causal filters are realised by "
          "<b>adding latency</b>, not by seeing the future"],
         ["<b>Linear</b>", "Superposition holds",
          "Enables decomposition into impulse responses; permits frequency-domain design"],
         ["<b>Time-invariant</b>", "Delay in &rarr; same delay out",
          "Coefficients are constants &rarr; can be hard-wired or stored once"],
         ["<b>BIBO stable</b>", "Bounded input &rarr; bounded output",
          "&sum;|<i>h</i>[<i>n</i>]| &lt; &infin;. In fixed point, determines whether "
          "accumulators can overflow"],
         ["<b>Passive / lossless</b>", "Energy not increased", "Guarantees no growth in word length"]]))
    s.append(fig(_f_lti(), "An LTI system is completely characterised by its impulse "
                           "response. This single fact underpins all filter design."))

    s.append("""<div class="ms">The practical importance of linearity is not elegance but
    <b>separability of verification</b>. If a block is LTI you can characterise it with a
    single impulse and predict its response to every input; a random-stimulus campaign is
    then a redundancy check rather than the primary evidence. If it is <i>not</i> LTI
    &mdash; a decision-feedback equaliser, a &mu;-law compander, a saturating accumulator,
    any adaptive loop &mdash; superposition fails and you must verify over the operating
    region, which is exponentially more work. <b>The first architectural question about
    any new block is therefore "where exactly is the nonlinearity?"</b> Isolating it into
    the smallest possible sub-block is a verification cost decision, not an aesthetic
    one.</div>""")

    s.append("<h2>A1.2 Convolution and its cost</h2>")
    s.append("""<div class="math">y[n] = &sum;<sub>k=0</sub><sup>N&minus;1</sup>
    h[k] x[n&minus;k]</div>""")
    s.append(tab("Realisations of the same convolution",
        ["Method", "Operations per output", "Latency", "When preferred"],
        [["Direct convolution", "<i>N</i> MACs", "0 (plus pipeline)", "<i>N</i> &lesssim; 64"],
         ["Overlap-add FFT", "~(2 log<sub>2</sub><i>L</i> + 1) per sample",
          "One block (<i>L</i> samples)", "Long filters; latency tolerable"],
         ["Overlap-save FFT", "Same order", "One block", "Streaming; avoids add stage"],
         ["Frequency-domain adaptive", "FFT + per-bin update", "One block",
          "Long adaptive filters (echo cancellation)"],
         ["Distributed arithmetic", "LUT reads only", "<i>W</i> cycles",
          "Fixed coefficients, LUT-rich fabric"],
         ["Multiplierless (CSD)", "Shifts and adds", "0", "Fixed coefficients, ASIC area critical"]]))
    s.append("""<div class="ms">The crossover between direct and FFT-based convolution is
    not a fixed number of taps; it depends on the <b>cost ratio of a multiplier to a
    memory word</b> in the target technology, and on whether block latency is acceptable.
    In an ASIC at an advanced node, multipliers are comparatively cheap and SRAM is
    comparatively expensive, which pushes the crossover <i>up</i>. On an FPGA with hard
    DSP slices and abundant block RAM it moves the other way. <b>Quoting a fixed
    crossover (&ldquo;use FFT above 128 taps&rdquo;) without naming the technology is a
    common and costly error in architecture documents.</b></div>""")

    s.append("<h2>A1.3 Correlation, matched filtering and the origin of SNR gain</h2>")
    s.append("""<p>Cross-correlation is convolution with a time-reversed conjugated
    kernel. When the kernel is the transmitted pulse itself, the operation is a
    <b>matched filter</b>, and it maximises output SNR for a signal in additive white
    Gaussian noise.</p>""")
    s.append("""<div class="math">SNR<sub>out,max</sub> = 2E<sub>s</sub> / N<sub>0</sub></div>""")
    s.append("""<div class="ms">The result is worth internalising because it recurs in
    radar, in spread spectrum, in synchronisation preambles and in every correlator IP.
    <b>The gain comes from integrating signal coherently while noise adds
    incoherently</b>: over <i>M</i> samples, signal amplitude grows as <i>M</i> while
    noise amplitude grows as &radic;<i>M</i>, hence power SNR improves by <i>M</i>
    (10&nbsp;log<sub>10</sub><i>M</i>&nbsp;dB). Two engineering consequences follow.
    First, coherent integration requires <b>phase stability over the integration
    window</b>; if the oscillator drifts, gain saturates &mdash; this is the practical
    limit on radar integration time and on preamble length. Second, the correlator's
    dynamic range must accommodate the <i>M</i>-fold growth, which is a fixed-point
    word-growth problem, not a signal-processing one.</div>""")

    s.append("<h2>A1.4 Group delay, phase linearity and why FIR dominates</h2>")
    s.append("""<div class="math">&tau;<sub>g</sub>(&omega;) = &minus; d&phi;(&omega;)/d&omega;</div>""")
    s.append("""<div class="bs">A filter has <b>linear phase</b> when &tau;<sub>g</sub> is
    constant: all frequency components are delayed equally, so pulse shapes are preserved
    and only shifted. An FIR filter with symmetric (or antisymmetric) coefficients has
    exactly linear phase. An IIR filter cannot, except trivially.</div>""")
    s.append("""<div class="ms">This is the decisive argument for FIR in data
    transmission. Non-constant group delay <b>spreads a pulse asymmetrically</b>, which is
    indistinguishable from channel dispersion and therefore directly closes the eye. In
    audio the ear is comparatively insensitive to phase and IIR is preferred for its
    efficiency; in a wireline receiver an IIR equaliser would introduce the very
    distortion it is meant to remove. <b>The same mathematics leads to opposite
    engineering choices in two domains, and knowing why is the difference between
    applying a rule and understanding it.</b> Note also the hardware corollary: symmetric
    FIR coefficients permit the <i>folded</i> structure that halves the multiplier count,
    so linear phase is not only free, it is cheaper.</div>""")

    s.append("<h2>A1.5 Stability in the Z domain</h2>")
    s.append(fig(_f_roc(), "Pole&ndash;zero plot and region of convergence. For a causal "
                           "system the ROC is outside the outermost pole; stability "
                           "additionally requires that the ROC contain the unit circle."))
    s.append(tab("Pole location and behaviour",
        ["Pole radius |p|", "Behaviour", "Fixed-point implication"],
        [["|p| &lt; 1", "Decaying; stable", "Accumulator bounded by 1/(1&minus;|p|)"],
         ["|p| = 1", "Marginally stable (oscillator, integrator)",
          "<b>Accumulator grows without bound</b> &mdash; needs explicit leakage or reset"],
         ["|p| &gt; 1", "Divergent", "Unusable"],
         ["|p| &rarr; 1<sup>&minus;</sup>", "Very narrow band; long memory",
          "<b>Coefficient quantisation can push the pole outside</b> &mdash; the classic "
          "failure mode of high-order direct-form IIR"]]))
    s.append("""<div class="ms">Quantifying the last row: for a direct-form IIR of order
    <i>N</i>, the sensitivity of pole <i>p<sub>i</sub></i> to a denominator coefficient
    <i>a<sub>k</sub></i> is
    &part;<i>p<sub>i</sub></i>/&part;<i>a<sub>k</sub></i> =
    &minus;<i>p<sub>i</sub></i><sup><i>N</i>&minus;<i>k</i></sup> /
    &prod;<sub><i>j</i>&ne;<i>i</i></sub>(<i>p<sub>i</sub></i>&minus;<i>p<sub>j</sub></i>).
    The denominator is a product of <i>pole separations</i>: <b>clustered poles make the
    sensitivity explode</b>. Cascaded second-order sections avoid this because each
    section contains only one conjugate pair, so no small separations appear in its own
    denominator. This is the quantitative reason behind the universal practice of
    implementing high-order IIR filters as cascaded biquads, and it is worth being able
    to state it rather than merely follow it.</div>""")
    return "\n".join(s)


def ch_transform():
    s = ['<h1 id="a2">A2. Transforms and Spectral Representation</h1>']
    s.append(tab("The transform family",
        ["Transform", "Domain", "Kernel", "Principal use in IP work"],
        [["CTFT", "continuous time &rarr; &omega;", "<i>e</i><sup>&minus;j&omega;t</sup>",
          "Analogue filter and antenna analysis"],
         ["Laplace", "continuous time &rarr; <i>s</i>", "<i>e</i><sup>&minus;st</sup>",
          "PLL loop dynamics, control, transmission lines"],
         ["DTFT", "discrete time &rarr; &omega;", "<i>e</i><sup>&minus;j&omega;n</sup>",
          "Theoretical filter response (continuous in &omega;)"],
         ["<b>DFT / FFT</b>", "finite sequence &rarr; bins",
          "<i>e</i><sup>&minus;j2&pi;kn/N</sup>", "Everything computable"],
         ["Z", "discrete time &rarr; <i>z</i>", "<i>z</i><sup>&minus;n</sup>",
          "Poles, zeros, stability, filter structures"],
         ["Hilbert", "real &rarr; analytic", "&minus;j&nbsp;sgn(&omega;)",
          "I/Q generation, envelope, SSB"],
         ["DCT", "finite &rarr; cosine basis", "cos", "Image/video coding (energy compaction)"],
         ["Wavelet", "time&ndash;scale", "scaled basis", "Transient detection, JPEG2000"]]))

    s.append("<h2>A2.1 The DFT is not the DTFT</h2>")
    s.append("""<p>The DFT computes samples of the DTFT of a <b>windowed, periodically
    extended</b> sequence. Three artefacts follow, and all three appear as bugs in
    practice.</p>""")
    s.append(tab("DFT artefacts",
        ["Artefact", "Cause", "Symptom", "Mitigation"],
        [["<b>Spectral leakage</b>", "Implicit rectangular window",
          "A pure tone smears across bins", "Apply a window (Hann, Blackman&ndash;Harris)"],
         ["<b>Scalloping loss</b>", "Tone falls between bin centres",
          "Up to 3.9&nbsp;dB amplitude error (rectangular)", "Window, or interpolate the peak"],
         ["<b>Picket fence</b>", "Only <i>N</i> samples of a continuum",
          "Frequency resolution limited to <i>f<sub>s</sub></i>/<i>N</i>",
          "Zero-pad (interpolates, does <b>not</b> add resolution)"],
         ["Circular convolution", "Periodic extension",
          "Wrap-around in fast convolution", "Zero-pad to <i>N</i>&ge;<i>L</i>+<i>M</i>&minus;1"]]))
    s.append("""<div class="warn">Zero-padding is routinely misdescribed as improving
    resolution. It does not. <b>Resolution is set by the observation time</b>
    <i>T</i>&nbsp;=&nbsp;<i>N</i>/<i>f<sub>s</sub></i>; two tones closer than
    &asymp;1/<i>T</i> cannot be separated no matter how many zeros are appended. Padding
    interpolates the displayed spectrum, which makes peaks easier to <i>locate</i> but
    not easier to <i>resolve</i>. In a specification, resolution and interpolation must
    be stated separately.</div>""")
    s.append(tab("Common windows",
        ["Window", "Main-lobe width (bins)", "First sidelobe", "Use"],
        [["Rectangular", "2", "&minus;13 dB", "Transient capture; maximum resolution"],
         ["Hann", "4", "&minus;31 dB", "General purpose"],
         ["Hamming", "4", "&minus;41 dB", "Slightly better near sidelobe"],
         ["Blackman&ndash;Harris (4-term)", "8", "&minus;92 dB",
          "<b>Spur hunting in converter test</b>"],
         ["Kaiser (&beta; adjustable)", "tunable", "tunable", "Design-to-spec"],
         ["Flat-top", "~9", "&minus;90 dB", "<b>Amplitude accuracy</b> (calibration)"]]))

    s.append("<h2>A2.2 Parseval, power spectral density, and dB conventions</h2>")
    s.append("""<div class="math">&sum;<sub>n</sub>|x[n]|<sup>2</sup> =
    (1/N)&sum;<sub>k</sub>|X[k]|<sup>2</sup></div>""")
    s.append(tab("Decibel conventions that are routinely confused",
        ["Unit", "Reference", "Note"],
        [["dB", "ratio", "10&nbsp;log for power, 20&nbsp;log for amplitude"],
         ["dBm", "1 mW", "Absolute power"],
         ["dBc", "carrier", "Spur levels, phase noise"],
         ["dBFS", "converter full scale", "<b>Digital</b> level; not a physical power"],
         ["dBm/Hz", "1 mW per Hz", "Spectral density; thermal floor &minus;174 dBm/Hz @ 290 K"],
         ["dBc/Hz", "carrier per Hz", "Phase noise <i>L</i>(&Delta;<i>f</i>)"]]))
    s.append("""<div class="ms">A recurring measurement error is comparing a
    <b>single-bin</b> FFT magnitude with a <b>spectral density</b>. The FFT bin contains
    power integrated over the equivalent noise bandwidth of the window, which for a Hann
    window is 1.5&nbsp;bins, not 1. Reporting &ldquo;noise floor at &minus;110&nbsp;dBFS&rdquo;
    without stating <i>N</i>, <i>f<sub>s</sub></i> and the window is not a measurement,
    because the number changes when any of the three changes. <b>Processing gain
    10&nbsp;log<sub>10</sub>(<i>N</i>/2) is often mistaken for converter
    performance.</b></div>""")
    return "\n".join(s)


def ch_sampling():
    s = ['<h1 id="a3">A3. Sampling, Reconstruction and Quantisation</h1>']
    s.append("<h2>A3.1 The sampling theorem and its practical corollaries</h2>")
    s.append("""<div class="math">X<sub>s</sub>(f) = f<sub>s</sub> &sum;<sub>k</sub>
    X(f &minus; k f<sub>s</sub>)</div>""")
    s.append(tab("Sampling regimes",
        ["Regime", "Condition", "Where used", "Hardware cost"],
        [["Nyquist", "<i>f<sub>s</sub></i> &gt; 2<i>B</i>, baseband",
          "Most baseband DSP", "Anti-alias filter must be steep"],
         ["<b>Oversampling</b> (OSR &gt; 1)", "<i>f<sub>s</sub></i> &Gt; 2<i>B</i>",
          "&Sigma;&Delta; converters, relaxed AAF",
          "Quantisation noise spread over wider band: +3 dB SNR per doubling"],
         ["<b>Bandpass / undersampling</b>",
          "2<i>f<sub>H</sub></i>/<i>n</i> &le; <i>f<sub>s</sub></i> &le; 2<i>f<sub>L</sub></i>/(<i>n</i>&minus;1)",
          "RF direct sampling receivers",
          "Sampler analogue bandwidth must exceed <i>f<sub>H</sub></i>, not <i>f<sub>s</sub></i>"],
         ["<b>Time-interleaved</b>", "<i>M</i> converters at <i>f<sub>s</sub></i>/<i>M</i>",
          "&gt;10 GS/s ADCs (112G SerDes uses 32&ndash;64 way)",
          "Offset / gain / <b>timing skew</b> mismatch creates spurs at <i>kf<sub>s</sub></i>/<i>M</i>"]]))
    s.append("""<div class="ms"><b>Time-interleaving is where the design house earns its
    fee.</b> An <i>M</i>-way interleaved ADC has three mismatch mechanisms, each producing
    a distinct spur family: offset mismatch gives tones at <i>kf<sub>s</sub></i>/<i>M</i>
    independent of input; gain mismatch gives sidebands at
    <i>kf<sub>s</sub></i>/<i>M</i>&nbsp;&plusmn;&nbsp;<i>f<sub>in</sub></i>; timing skew
    gives the same sideband locations but with amplitude proportional to
    <i>f<sub>in</sub></i>. <b>The frequency dependence is the diagnostic</b>: sweep the
    input and see which spur grows. Digital background calibration of all three is a
    standard deliverable in a modern ADC-DSP receiver, and it is a <i>digital</i> block
    &mdash; which means a fabless digital IP vendor can sell it even though the converter
    itself is analogue. This is a concrete example of finding a sellable digital block
    adjacent to an analogue one you cannot build.</div>""")

    s.append("<h2>A3.2 Quantisation noise</h2>")
    s.append("""<div class="math">SQNR<sub>dB</sub> = 6.02 B + 1.76 +
    10 log<sub>10</sub>(OSR)</div>""")
    s.append(tab("Where the ideal formula breaks",
        ["Effect", "Mechanism", "Consequence", "Design response"],
        [["Aperture jitter", "Sampling instant uncertainty &sigma;<sub>t</sub>",
          "SNR = &minus;20 log<sub>10</sub>(2&pi;<i>f<sub>in</sub></i>&sigma;<sub>t</sub>)",
          "<b>Dominates above ~1 GHz input</b>; clock design becomes the ADC spec"],
         ["Thermal noise", "kT/C of sampling capacitor",
          "Floors SNR regardless of bits", "Increase C (costs power and bandwidth)"],
         ["DNL / INL", "Element mismatch", "Harmonic distortion, missing codes",
          "Calibration, dynamic element matching"],
         ["Comparator metastability", "Finite regeneration time",
          "Rare large errors", "More regeneration time or error detection"],
         ["Correlated quantisation", "Low-amplitude periodic input",
          "Quantisation noise becomes tonal, not white",
          "<b>Dither</b> &mdash; deliberately added noise to decorrelate"]]))
    s.append("""<div class="ms">The dither entry deserves emphasis because it is
    counter-intuitive: <b>adding noise improves the result</b>. Quantisation error is
    only white and signal-independent when the signal moves over many LSBs; for a small
    or slowly varying signal the error becomes periodic and produces discrete tones,
    which are far more objectionable than an equivalent amount of broadband noise (in
    audio they are audible; in a radar they look like targets). Subtractive dither &mdash;
    add a known pseudo-random sequence before quantising and subtract it after &mdash;
    removes the tones without the SNR penalty. <b>A dither generator is a small, precisely
    specifiable digital block and therefore exactly the kind of thing a one-person IP
    house can build and sell as part of a converter-adjacent package.</b></div>""")

    s.append("<h2>A3.3 Reconstruction</h2>")
    s.append(tab("Reconstruction effects",
        ["Effect", "Expression", "Compensation"],
        [["Zero-order hold droop", "sinc(<i>f</i>/<i>f<sub>s</sub></i>)",
          "&minus;3.92 dB at Nyquist; pre-compensate with an inverse-sinc FIR"],
         ["Image replicas", "at <i>kf<sub>s</sub></i> &plusmn; <i>f</i>",
          "Reconstruction (anti-imaging) filter"],
         ["Interpolation", "up-sample then low-pass",
          "Moves images away so the analogue filter can be gentle"],
         ["<b>Mismatch-shaping DAC</b>", "&mdash;",
          "Pushes element mismatch error out of band; a digital technique for an analogue defect"]]))
    return "\n".join(s)


def ch_prob():
    s = ['<h1 id="a4">A4. Probability, Random Processes and Noise</h1>']
    s.append("<h2>A4.1 Distributions that occur in hardware</h2>")
    s.append(tab("Distributions and where they arise",
        ["Distribution", "Arises from", "Appears in"],
        [["Gaussian", "Sum of many small independent effects (CLT)",
          "Thermal noise, random jitter, process variation"],
         ["Rayleigh", "Magnitude of complex Gaussian",
          "Fading envelope, noise magnitude"],
         ["Rician", "Complex Gaussian + deterministic component", "Fading with line of sight"],
         ["Poisson", "Rare independent events", "Shot noise, soft-error (SER) counts"],
         ["Uniform", "Quantisation residue (ideal)", "Quantisation noise model"],
         ["Exponential", "Waiting time between Poisson events", "Time between soft errors"],
         ["Log-normal", "Product of many factors", "Shadowing, some reliability lifetimes"],
         ["Weibull", "Weakest-link failure", "<b>Oxide breakdown, reliability</b>"],
         ["Binomial", "<i>n</i> Bernoulli trials", "Bit errors in a block, yield"],
         ["Chi-square", "Sum of squared Gaussians", "Energy detection, CFAR statistics"]]))

    s.append("<h2>A4.2 Physical noise mechanisms</h2>")
    s.append(tab("Noise sources in silicon",
        ["Mechanism", "Spectrum", "Expression", "Design lever"],
        [["<b>Thermal (Johnson)</b>", "White",
          "<i>v<sub>n</sub></i><sup>2</sup> = 4<i>kTR&Delta;f</i>", "Lower R; lower T; narrower band"],
         ["<b>Channel thermal (MOS)</b>", "White",
          "<i>i<sub>n</sub></i><sup>2</sup> = 4<i>kT&gamma;g<sub>m</sub>&Delta;f</i>",
          "Higher <i>g<sub>m</sub></i> improves noise <i>figure</i> though noise power rises"],
         ["<b>Flicker (1/f)</b>", "1/<i>f</i>",
          "&prop; <i>K</i>/(<i>WLC</i><sub>ox</sub><i>f</i>)",
          "<b>Larger devices</b>; chopping; auto-zeroing"],
         ["Shot", "White", "<i>i<sub>n</sub></i><sup>2</sup> = 2<i>qI&Delta;f</i>",
          "Present where carriers cross a barrier (junctions, photodiodes)"],
         ["kT/C", "Sampled", "<i>v</i><sup>2</sup> = <i>kT</i>/<i>C</i>",
          "<b>Independent of resistance</b>; only C helps"],
         ["Substrate / supply coupling", "Structured",
          "&mdash;", "Guard rings, separate supplies, differential design"],
         ["Phase noise", "1/<i>f</i><sup>3</sup>, 1/<i>f</i><sup>2</sup>, flat",
          "Leeson model", "Higher Q, higher power, lower flicker"]]))
    s.append("""<div class="ms"><b>Why flicker noise sets the architecture of precision
    analogue.</b> 1/<i>f</i> noise is not reducible by filtering, because it lives at the
    frequencies where the signal of interest often lives (DC to kHz). The standard
    responses &mdash; chopping and auto-zeroing &mdash; both work by <i>moving the signal
    to a higher frequency where only white noise remains</i>, and both require digital
    support: a chopping clock, demodulation, and residual-ripple filtering. In a modern
    mixed-signal IP the digital half of that scheme is a well-defined block with a clean
    interface, and it is again a piece that a digital design house can own.</div>""")

    s.append("<h2>A4.3 Jitter and phase noise &mdash; the same thing in two languages</h2>")
    s.append("""<div class="math">&sigma;<sub>t</sub><sup>2</sup> = (1/(2&pi;f<sub>0</sub>)<sup>2</sup>)
    &int; 2&thinsp;L(f) df</div>""")
    s.append(tab("Jitter taxonomy used in link specifications",
        ["Type", "Symbol", "Statistics", "Cause", "How it is separated"],
        [["Random jitter", "RJ", "Gaussian, unbounded",
          "Thermal, flicker", "Fit tails of the bathtub curve"],
         ["Deterministic jitter", "DJ", "Bounded",
          "&mdash;", "Peak-to-peak; decomposed below"],
         ["&emsp;Periodic", "PJ", "Sinusoidal", "Supply coupling, spurs",
          "FFT of the jitter sequence"],
         ["&emsp;Data-dependent", "DDJ / ISI", "Pattern-correlated",
          "Channel loss", "Compare per-pattern edge times"],
         ["&emsp;Duty-cycle distortion", "DCD", "Two-valued",
          "Rise/fall asymmetry, threshold offset", "Even/odd UI comparison"],
         ["Bounded uncorrelated", "BUJ", "Bounded, random",
          "Crosstalk", "Statistical separation"],
         ["Total jitter at BER", "TJ(BER)", "RJ&otimes;DJ convolution",
          "&mdash;", "<b>TJ = DJ + 2&middot;Q(BER)&middot;RJ<sub>rms</sub></b>"]]))
    s.append("""<div class="ms">The last row is the one that appears in every SerDes
    specification, and the factor <i>Q</i>(BER) is why: at BER&nbsp;10<sup>&minus;12</sup>,
    <i>Q</i>&nbsp;=&nbsp;7.03, so TJ&nbsp;=&nbsp;DJ&nbsp;+&nbsp;14.07&nbsp;RJ<sub>rms</sub>.
    <b>Random jitter is multiplied by fourteen.</b> This is why a small improvement in
    oscillator phase noise is worth a large amount of design effort, and why jitter
    separation &mdash; distinguishing RJ from DJ in a measurement &mdash; is a required
    capability rather than a nicety. A modelling engineer asked to produce a link budget
    must implement this convolution correctly; adding RMS values in quadrature, which is
    the intuitive move, is wrong because DJ is bounded and does not add that way.</div>""")

    s.append("<h2>A4.4 Random processes</h2>")
    s.append(tab("Concepts and their use",
        ["Concept", "Statement", "Use in IP design"],
        [["Stationarity (WSS)", "Mean constant, autocorrelation depends on lag only",
          "Precondition for spectral analysis"],
         ["Ergodicity", "Time average = ensemble average",
          "<b>Justifies measuring one long record instead of many devices</b>"],
         ["Wiener&ndash;Khinchin", "PSD = FT of autocorrelation", "Links time and spectrum"],
         ["Markov chain", "Memoryless state evolution",
          "Bus arbitration analysis, FIFO occupancy, error models"],
         ["Gauss&ndash;Markov", "Correlated Gaussian", "Coloured noise models"],
         ["Cyclostationarity", "Statistics periodic in time",
          "<b>All digitally modulated signals</b>; exploited for blind synchronisation"],
         ["Point process", "Random event times", "Soft errors, packet arrivals"]]))
    s.append("""<div class="ms">Cyclostationarity is the theoretical basis for
    <b>blind</b> timing and carrier recovery: a modulated signal has periodically varying
    statistics at the symbol rate, so a suitable nonlinearity produces a spectral line at
    that rate even though the signal itself has no such line. Gardner and Mueller&ndash;Müller
    timing detectors are practical exploitations of this. Knowing the principle rather
    than the recipe is what lets an engineer design a detector for a modulation format
    that has no textbook detector &mdash; a situation that occurs constantly in
    proprietary links.</div>""")
    return "\n".join(s)


def ch_linalg():
    s = ['<h1 id="a5">A5. Linear Algebra and Numerical Methods for Hardware</h1>']
    s.append("<h2>A5.1 Decompositions and their hardware character</h2>")
    s.append(tab("Matrix decompositions as IP blocks",
        ["Decomposition", "Form", "Cost", "Streaming?", "Numerical character"],
        [["<b>LU</b>", "<i>A</i> = <i>LU</i>", "<i>n</i><sup>3</sup>/3",
          "No (pivoting needs lookahead)", "Needs pivoting for stability"],
         ["<b>Cholesky</b>", "<i>A</i> = <i>LL</i>*", "<i>n</i><sup>3</sup>/6",
          "<b>Yes</b>", "<b>No pivoting needed</b> for SPD; half the work of LU"],
         ["<b>QR (Givens)</b>", "<i>A</i> = <i>QR</i>", "2<i>mn</i><sup>2</sup>",
          "<b>Yes</b>", "Backward stable; rotations are well conditioned"],
         ["QR (Householder)", "same", "fewer ops", "Less so", "Best stability"],
         ["<b>SVD</b>", "<i>A</i> = <i>U&Sigma;V</i>*", "iterative",
          "No", "<b>Most robust</b>; reveals rank and conditioning"],
         ["Eigen (symmetric)", "<i>A</i> = <i>Q&Lambda;Q</i>*", "iterative", "No",
          "Jacobi parallelises well"],
         ["Schur / Hessenberg", "&mdash;", "<i>n</i><sup>3</sup>", "No", "Control applications"]]))
    s.append("""<div class="ms"><b>The streaming column is the commercial column.</b>
    Cholesky and Givens QR touch each input element once and can therefore be built with
    an <code>hls::stream</code>-style interface and no external memory; SVD and LU must
    revisit the array and therefore need an AXI master and a buffer. That single
    architectural difference changes the IP's integration story, its area, and its price.
    When a customer asks for &ldquo;a matrix inverse block&rdquo;, the first engineering
    question is whether the matrix is symmetric positive definite &mdash; because if it
    is, Cholesky gives a streaming solution at half the arithmetic, and if it is not, you
    are quoting a much larger block.</div>""")

    s.append("<h2>A5.2 Conditioning</h2>")
    s.append("""<div class="math">&kappa;(A) = &sigma;<sub>max</sub>/&sigma;<sub>min</sub>
    &nbsp;&nbsp;&nbsp; relative error &lesssim; &kappa;(A) &middot; &epsilon;<sub>machine</sub></div>""")
    s.append("""<div class="ms">The rule of thumb that follows is directly usable:
    <b>you lose roughly log<sub>10</sub>&kappa; decimal digits</b>. In fixed point,
    substitute &epsilon; = 2<sup>&minus;<i>F</i></sup> for <i>F</i> fractional bits and the
    statement becomes a word-length requirement:
    <i>F</i> &gtrsim; log<sub>2</sub>&kappa; + (bits of accuracy required). This is how a
    modelling engineer converts a mathematical property of the customer's data into a
    hardware parameter. It also explains why <b>iterative refinement</b> works: solve in
    low precision, compute the residual in high precision, correct, repeat. Each
    iteration roughly squares the accuracy, so three refinements from a rough start can
    reach near-full precision &mdash; but only if the condition number is modest, because
    &kappa; enters the convergence factor. <b>Measured behaviour: for a well-conditioned
    (isotropic) system the scheme reached 24.2 bits of accuracy; at correlation 0.99 it
    reached only 12.4 bits.</b> An IP that advertises mixed-precision refinement must
    therefore state a conditioning limit, or it will fail at a customer whose data is
    correlated.</div>""")

    s.append("<h2>A5.3 Iterative solvers and their hardware mapping</h2>")
    s.append(tab("Iterative methods",
        ["Method", "Update", "Parallelism", "Convergence"],
        [["Jacobi", "uses only previous iterate", "<b>Fully parallel</b>",
          "Slow; needs diagonal dominance"],
         ["Gauss&ndash;Seidel", "uses updated values immediately", "Sequential within a sweep",
          "Roughly twice Jacobi's rate"],
         ["SOR", "over-relaxed GS", "Sequential", "Tunable &omega;"],
         ["<b>Conjugate gradient</b>", "Krylov subspace", "Parallel (dot products)",
          "<i>n</i> steps exactly; &radic;&kappa; in practice"],
         ["Richardson", "<i>x</i> &larr; <i>x</i> + &alpha;(<i>b</i>&minus;<i>Ax</i>)",
          "<b>Fully parallel</b>", "Simplest; &alpha; must be tuned"]]))
    s.append("""<div class="ms">There is a physical realisation worth knowing because it
    is repeatedly rediscovered and mis-described. An RC network that solves
    <i>C</i>&nbsp;d<b>v</b>/d<i>t</i> = &minus;(<i>A</i><b>v</b> &minus; <b>b</b>) settles to
    <i>A</i><sup>&minus;1</sup><b>b</b>, and is often presented as an &ldquo;analogue
    Gauss&ndash;Seidel solver&rdquo;. <b>It is not</b>: because all nodes evolve
    simultaneously from the same previous state, the continuous-time limit corresponds to
    <b>Jacobi / Richardson</b>, not Gauss&ndash;Seidel, which is defined by sequential
    in-sweep updates. The settling time is governed by
    1/&lambda;<sub>min</sub>, i.e. by the condition number again. Under a normalisation
    that fixes &lambda;<sub>max</sub>&nbsp;=&nbsp;1, the measured settling-time-to-condition
    ratio was constant at 13.2 &mdash; the analogue solver buys constant factors, not
    asymptotic ones. <b>Being able to state this precisely prevents a design house from
    accepting a proposal whose speedup claim rests on a misidentification.</b></div>""")
    return "\n".join(s)
