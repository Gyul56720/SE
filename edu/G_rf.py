# -*- coding: utf-8 -*-
"""Volume I, Part G -- RF, electromagnetics, radar."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line, poly


def _f_fmcw():
    b = []
    b += [line(30, 150, 330, 150), line(30, 150, 30, 30)]
    b.append('<path d="M40,140 L110,45 L110,140 L180,45 L180,140 L250,45 L250,140" '
             'stroke="#123f6d" stroke-width="1.6" fill="none"/>')
    b.append('<path d="M62,140 L132,45 L132,140 L202,45 L202,140 L272,45 L272,140" '
             'stroke="#a33" stroke-width="1.4" fill="none" stroke-dasharray="4,3"/>')
    b += [txt(300, 44, "TX", 9, "start", 'fill="#123f6d"'),
          txt(300, 62, "RX (delayed)", 9, "start", 'fill="#a33"'),
          txt(24, 28, "f", 10, "end"), txt(336, 154, "t", 10)]
    b.append(txt(180, 178, "Beat frequency f_b = 2·R·S/c   (S = chirp slope)", 10, "middle"))
    b.append(txt(180, 198, "Range from frequency; velocity from phase change across chirps",
                 9, "middle", 'font-style="italic"'))
    return svg(350, 210, "".join(b))


def ch_tline():
    s = ['<h1 id="g1">G1. Electromagnetics for the Digital Engineer</h1>']
    s.append("""<p>A digital IP engineer meets electromagnetics at three boundaries: the
    package and board that carry the block's signals, the channel a SerDes must equalise,
    and the antenna of a radio or radar system whose baseband processing is the block
    itself. This chapter covers what is needed at those boundaries.</p>""")
    s.append("<h2>G1.1 From Maxwell to circuits</h2>")
    s.append(tab("Regimes and the model that applies",
        ["Regime", "Condition", "Model", "Consequence"],
        [["Lumped", "size &Lt; &lambda;", "KCL/KVL, R L C",
          "Voltage is well defined everywhere"],
         ["Quasi-static", "size &lesssim; &lambda;/10", "Lumped + parasitics",
          "Inductance begins to matter"],
         ["<b>Distributed</b>", "size &gtrsim; &lambda;/10",
          "<b>Transmission line</b>", "Position matters; reflections occur"],
         ["Full wave", "structure comparable to &lambda;", "Maxwell solvers",
          "Radiation, resonance, modes"]]))
    s.append("""<div class="ms"><b>The threshold keeps moving toward the designer.</b>
    The criterion is not clock frequency but edge rate: significant spectral content
    extends to roughly 0.35/<i>t<sub>r</sub></i>. A 50&nbsp;ps edge has content to
    7&nbsp;GHz regardless of whether the clock is 100&nbsp;MHz, and at 7&nbsp;GHz a
    2&nbsp;cm trace is a transmission line. <b>Slow clocks do not protect you from fast
    edges.</b> This is why deliberately slowing output slew rates is a legitimate design
    technique &mdash; and why an IP's output driver strength is a specification item with
    EMI consequences, not just a timing one.</div>""")

    s.append("<h2>G1.2 Transmission lines</h2>")
    s.append("""<div class="math">Z<sub>0</sub> = &radic;((R + j&omega;L)/(G + j&omega;C))
    &nbsp;&rarr;&nbsp; &radic;(L/C) &nbsp;(lossless)</div>""")
    s.append(tab("Line types",
        ["Type", "Z<sub>0</sub> range", "Where"],
        [["Microstrip", "50&ndash;100 &Omega;", "Outer PCB layer; radiates more"],
         ["Stripline", "50&ndash;100 &Omega;", "Inner layer; better shielded, slower (higher &epsilon;<sub>eff</sub>)"],
         ["Coplanar waveguide", "tunable", "On-chip RF; ground on the same layer"],
         ["Differential pair", "85&ndash;100 &Omega; differential",
          "<b>The standard for high-speed serial</b>"],
         ["On-chip global wire", "&mdash;", "Usually RC-dominated, not a true TL"]]))
    s.append(tab("Termination strategies",
        ["Scheme", "Placement", "Power", "Note"],
        [["Series (source)", "At driver", "Low", "Doubles the driver's output swing requirement"],
         ["Parallel", "At receiver", "High (static)", "Best match"],
         ["Thevenin", "At receiver", "High", "Sets a DC bias"],
         ["AC-coupled", "In line", "Low", "<b>Requires DC-balanced coding</b> (8b/10b, 64b/66b)"],
         ["On-die termination (ODT)", "Inside the chip", "Moderate",
          "<b>Calibrated against an external precision resistor</b>"]]))
    s.append("""<div class="ms"><b>AC coupling and line coding are linked requirements.</b>
    A series capacitor blocks DC, so a long run of identical symbols causes the signal to
    droop toward the decision threshold &mdash; baseline wander. The line code must
    therefore bound the run length and keep the running disparity small. 8b/10b does this
    with an explicit disparity rule at 25% overhead; 64b/66b uses a scrambler and accepts a
    small probability of a long run, at 3% overhead. <b>The coding choice is thus
    determined by an analogue component.</b> An engineer who knows only the coding layer
    cannot explain why 64b/66b needs a scrambler with a particular polynomial, nor why
    certain data patterns are used as stress tests.</div>""")

    s.append("<h2>G1.3 Antennas and propagation</h2>")
    s.append("""<div class="math">P<sub>r</sub> = P<sub>t</sub>G<sub>t</sub>G<sub>r</sub>
    (&lambda;/4&pi;d)<sup>2</sup> &nbsp;&nbsp;(Friis)</div>""")
    s.append(tab("Antenna and propagation quantities",
        ["Quantity", "Definition", "Design relevance"],
        [["Gain <i>G</i>", "Directivity &times; efficiency", "Trades coverage for range"],
         ["Effective aperture", "<i>A<sub>e</sub></i> = <i>G</i>&lambda;<sup>2</sup>/4&pi;",
          "<b>Higher frequency &rarr; smaller aperture for the same gain</b>"],
         ["Beamwidth", "&asymp; 70&deg;&lambda;/<i>D</i>", "Array size sets angular resolution"],
         ["Path loss exponent", "2 (free space) to 4+ (urban)", "Link budget"],
         ["Multipath / delay spread", "&mdash;", "<b>Sets the equaliser or OFDM CP length</b>"],
         ["Doppler shift", "<i>f<sub>d</sub></i> = 2<i>v</i>/&lambda;",
          "Coherence time; tracking loop bandwidth"],
         ["Fading", "Rayleigh / Rician", "Diversity, MIMO"]]))
    s.append("""<div class="ms"><b>Delay spread converts directly into a hardware
    parameter.</b> If the channel's impulse response lasts &tau;<sub>max</sub>, a
    single-carrier receiver needs an equaliser spanning &tau;<sub>max</sub>/<i>T<sub>s</sub></i>
    symbols, and an OFDM receiver needs a cyclic prefix at least that long. The first
    costs taps (area, adaptation time); the second costs throughput (the CP is overhead).
    <b>This is the quantitative form of the choice between single-carrier and OFDM</b>,
    and it explains why wireline links &mdash; where delay spread is long but the channel
    is static &mdash; use equalisers, while wireless links with time-varying multipath use
    OFDM. The same physics, opposite conclusions, because the <i>rate of change</i>
    differs.</div>""")


    s.append("<h2>G1.4 Noise figure and receiver chains</h2>")
    s.append("""<div class="math">F<sub>total</sub> = F<sub>1</sub> +
    (F<sub>2</sub>&minus;1)/G<sub>1</sub> + (F<sub>3</sub>&minus;1)/(G<sub>1</sub>G<sub>2</sub>)
    + &hellip;</div>""")
    s.append("""<div class="ms"><b>Friis's formula justifies the entire architecture of a
    receiver front end.</b> Because later stages are divided by the cumulative gain ahead
    of them, the first amplifier dominates the noise figure &mdash; hence the low-noise
    amplifier, placed as close to the antenna as possible, often before any filter whose
    insertion loss would add directly to <i>F</i><sub>1</sub>. The counterweight is
    linearity: gain early in the chain means large signals later, so the cascaded
    third-order intercept point degrades as
    1/IIP3<sub>total</sub> = 1/IIP3<sub>1</sub> + <i>G</i><sub>1</sub>/IIP3<sub>2</sub> + &hellip;
    <b>Noise pushes gain forward; linearity pushes it backward.</b> Every receiver's gain
    distribution is a solution to that tension, and the digital back end inherits the
    result as its required dynamic range &mdash; which is to say, as its ADC bit count.</div>""")
    return "\n".join(s)


def ch_radar():
    s = ['<h1 id="g2">G2. Radar: Signal Processing as an IP Block Family</h1>']
    s.append("""<p>Automotive and industrial radar is one of the largest current markets
    for signal-processing IP, and its chain is a clean illustration of how physical
    parameters become hardware parameters.</p>""")
    s.append("""<div class="math">P<sub>r</sub> = P<sub>t</sub>G<sup>2</sup>&lambda;<sup>2</sup>&sigma;
    / ((4&pi;)<sup>3</sup>R<sup>4</sup>) &nbsp;&nbsp;(radar equation)</div>""")
    s.append("""<div class="bs">The fourth-power range dependence is the defining fact of
    radar: doubling the detection range requires sixteen times the received power. Since
    transmit power and antenna gain are bounded, the remaining lever is
    <b>processing gain</b> &mdash; coherent integration &mdash; which is entirely a
    digital matter and therefore entirely IP.</div>""")
    s.append(fig(_f_fmcw(), "FMCW radar. Range appears as a beat frequency; velocity "
                            "appears as phase progression across successive chirps."))

    s.append("<h2>G2.1 FMCW parameter derivation</h2>")
    s.append(tab("From requirement to hardware parameter",
        ["Requirement", "Relation", "Hardware consequence"],
        [["Range resolution &Delta;<i>R</i>", "&Delta;<i>R</i> = <i>c</i>/2<i>B</i>",
          "<b>Sweep bandwidth</b> &mdash; 4 GHz gives 3.75 cm"],
         ["Maximum range <i>R</i><sub>max</sub>",
          "<i>f<sub>b,max</sub></i> = 2<i>R</i><sub>max</sub><i>S</i>/<i>c</i>",
          "<b>ADC sample rate and IF bandwidth</b>"],
         ["Velocity resolution &Delta;<i>v</i>",
          "&Delta;<i>v</i> = &lambda;/(2<i>N<sub>c</sub>T<sub>c</sub></i>)",
          "<b>Number of chirps per frame</b> &rarr; frame memory"],
         ["Maximum velocity", "<i>v</i><sub>max</sub> = &lambda;/(4<i>T<sub>c</sub></i>)",
          "Chirp repetition period"],
         ["Angular resolution", "&asymp; &lambda;/(<i>N<sub>a</sub>d</i> cos&theta;)",
          "<b>Number of antennas</b> &rarr; number of RX chains"],
         ["Processing gain", "10log(<i>N<sub>s</sub>N<sub>c</sub></i>)",
          "FFT sizes &rarr; compute and memory"]]))
    s.append("""<div class="ms"><b>The range&ndash;Doppler map is a two-dimensional FFT</b>
    and its dimensions come straight from the table: a fast-time FFT across samples within
    one chirp yields range bins; a slow-time FFT across chirps at each range bin yields
    Doppler bins. A typical automotive frame &mdash; 256 samples &times; 128 chirps
    &times; 8 virtual antennas &mdash; requires a corner-turn between the two FFTs, and
    <b>that transpose, not the FFTs, dominates the memory bandwidth</b>. Designing the
    memory organisation (ping-pong banks, tiled transpose, or on-the-fly second-stage
    accumulation) is the real architectural work. This is a recurring theme: in
    data-intensive blocks the arithmetic is rarely the bottleneck.</div>""")

    s.append("<h2>G2.2 Detection</h2>")
    s.append(tab("CFAR detectors",
        ["Type", "Noise estimate", "Strength", "Weakness"],
        [["CA-CFAR", "Mean of surrounding cells", "Simple, efficient in homogeneous noise",
          "<b>Masks targets near clutter edges</b>"],
         ["GO-CFAR", "Greater of the two halves", "Handles clutter edges", "Loses closely spaced targets"],
         ["SO-CFAR", "Smaller of the two halves", "Resolves close targets", "High false alarm at edges"],
         ["<b>OS-CFAR</b>", "<i>k</i>-th order statistic", "<b>Robust to interfering targets</b>",
          "Needs a sorter &mdash; more hardware"],
         ["Adaptive / ML", "learned", "Best in complex scenes", "Verification difficulty"]]))
    s.append("""<div class="ms"><b>CFAR sets a threshold, not a decision.</b> The
    multiplier &alpha; is chosen so that the probability of false alarm is fixed regardless
    of the noise level &mdash; that is what "constant false alarm rate" means. For
    CA-CFAR with <i>N</i> reference cells,
    &alpha; = <i>N</i>(<i>P<sub>FA</sub></i><sup>&minus;1/<i>N</i></sup> &minus; 1). Two
    hardware consequences: the block needs a divider or a reciprocal table, and it needs
    the <i>N</i> reference cells buffered, which for a 2-D CFAR means a sliding window over
    a two-dimensional array. <b>OS-CFAR's sorter is the most hardware-hungry element in a
    typical radar back end</b>, and choosing between a full sorting network and an
    approximate selection is a genuine PPA decision that a design house can differentiate
    on.</div>""")

    s.append("<h2>G2.3 Angle estimation and MIMO</h2>")
    s.append(tab("Angle-of-arrival methods",
        ["Method", "Resolution", "Computation", "Robustness"],
        [["FFT beamforming", "Rayleigh limit", "One FFT", "Very robust"],
         ["Capon / MVDR", "Super-resolution", "<b>Matrix inverse</b> per snapshot",
          "Needs good covariance estimate"],
         ["<b>MUSIC</b>", "Super-resolution", "<b>Eigendecomposition</b>", "Needs the source count"],
         ["ESPRIT", "Super-resolution", "SVD + rotation", "Needs array structure"],
         ["Compressive sensing", "High", "Iterative solver", "Sensitive to model mismatch"]]))
    s.append("""<div class="ms"><b>This is where Part A's matrix decompositions become
    products.</b> MUSIC needs the eigendecomposition of an <i>N</i>&times;<i>N</i>
    covariance matrix per snapshot; Capon needs its inverse. For an 8&ndash;16 element
    array that is a small, dense, Hermitian, <b>positive-definite</b> problem &mdash;
    exactly the case where Cholesky applies and streams. A design house that owns a
    parameterised streaming Cholesky or Jacobi eigenvalue block can sell it into radar,
    into MIMO communications, and into adaptive beamforming, because all three reduce to
    the same kernel. <b>Recognising that one kernel serves three markets is how a small IP
    portfolio becomes viable.</b></div>""")
    s.append("""<div class="ms"><b>MIMO radar's virtual array</b> deserves a precise
    statement because it is the main reason automotive radar improved so quickly. With
    <i>N<sub>t</sub></i> transmitters and <i>N<sub>r</sub></i> receivers, transmitting
    orthogonal waveforms (time-, frequency-, or code-division) and separating them at the
    receiver yields <i>N<sub>t</sub></i>&times;<i>N<sub>r</sub></i> distinct
    transmit&ndash;receive paths, which behave like a physical array of that many
    elements. Three transmitters and four receivers give a twelve-element virtual array
    &mdash; a threefold improvement in angular resolution at the cost of <b>digital</b>
    separation logic rather than antennas and RF chains. <b>Once again the solution to a
    physical limit is a digital block.</b></div>""")
    return "\n".join(s)
