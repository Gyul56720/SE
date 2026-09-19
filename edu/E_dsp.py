# -*- coding: utf-8 -*-
"""Volume I, Part E -- DSP architectures as IP blocks."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line


def _f_fir():
    b = []
    x = 40
    for i in range(4):
        b.append(box(x, 28, 50, 28, "z⁻¹", None, 9))
        if i: b.append(arr(x-16, 42, x, 42))
        b.append(arr(x+25, 56, x+25, 84))
        b.append(box(x, 84, 50, 24, f"×h{i}", None, 9))
        b.append(arr(x+25, 108, x+25, 128))
        x += 68
    b += [arr(12, 42, 40, 42), txt(14, 35, "x[n]", 9)]
    b.append(box(40, 128, 254, 24, "Σ", None, 11))
    b += [arr(294, 140, 328, 140), txt(297, 133, "y[n]", 9)]
    b.append(txt(170, 176, "Direct form: adder tree depth grows with N", 9, "middle"))
    b.append(txt(170, 193, "Transposed form: critical path is one mult + one add, independent of N",
                 9, "middle", 'font-style="italic"'))
    return svg(350, 205, "".join(b))


def ch_filters():
    s = ['<h1 id="e1">E1. Digital Filters as Hardware</h1>']
    s.append(fig(_f_fir(), "Direct-form FIR. The tap count sets the multiplier count; "
                           "the <i>form</i> sets the critical path."))
    s.append(tab("FIR structures and their costs",
        ["Structure", "Multipliers", "Critical path", "Choose when"],
        [["Direct form", "<i>N</i>", "1 mult + log<i>N</i> adds", "<i>N</i> small"],
         ["<b>Transposed direct form</b>", "<i>N</i>", "<b>1 mult + 1 add (constant)</b>",
          "<b>Almost always, for speed</b>. Cost: high fanout on <i>x</i>[<i>n</i>]"],
         ["Symmetric (folded)", "&lceil;<i>N</i>/2&rceil;", "1 add + 1 mult + 1 add",
          "<b>Linear phase</b> &mdash; free 2&times; saving"],
         ["Polyphase", "<i>N</i>/<i>M</i> effective", "&mdash;",
          "Combined with rate change"],
         ["Distributed arithmetic", "0 (LUTs)", "<i>W</i> cycles", "Fixed coefficients, LUT fabric"],
         ["CSD / multiplierless", "0", "adds only", "Fixed coefficients, ASIC area"],
         ["Frequency domain", "&mdash;", "&mdash;", "<i>N</i> &gtrsim; 100 and block latency acceptable"]]))
    s.append("""<div class="ms"><b>The fanout cost of the transposed form is real and is
    often overlooked in architecture documents.</b> The input sample must reach all
    <i>N</i> multipliers in one cycle. For <i>N</i>&nbsp;=&nbsp;128 at 500&nbsp;MHz this
    is a significant buffer tree whose delay and power must be budgeted. The usual remedy
    is to <i>partition</i> the filter into segments with a pipelined input distribution
    network &mdash; effectively reintroducing a small amount of direct-form structure.
    <b>Real designs are hybrids, and a specification that names only "transposed FIR" is
    incomplete.</b></div>""")

    s.append("<h2>E1.2 Filter design methods</h2>")
    s.append(tab("FIR design methods",
        ["Method", "Optimality", "Control", "Use"],
        [["Windowing", "Suboptimal", "Simple", "Quick designs"],
         ["Frequency sampling", "Suboptimal", "Direct in frequency", "&mdash;"],
         ["<b>Parks&ndash;McClellan (Remez)</b>", "<b>Minimax optimal</b>",
          "Ripple in each band", "<b>Standard for equiripple specs</b>"],
         ["Least squares", "L2 optimal", "Weighted error", "When energy matters more than peak"],
         ["Convex optimisation", "Flexible", "Arbitrary constraints",
          "<b>Handles quantised coefficients directly</b>"]]))
    s.append("""<div class="ms"><b>Designing in floating point and rounding afterwards is
    a mistake that costs stopband attenuation.</b> Rounding a Parks&ndash;McClellan design
    to <i>B</i> bits perturbs each coefficient by up to half an LSB, and the resulting
    stopband degradation can be 10&ndash;20&nbsp;dB. The correct procedure is to include
    the quantisation in the design: either use an integer-programming or convex
    formulation that searches over representable coefficients, or re-optimise the
    remaining coefficients after fixing some. <b>For an IP vendor this is a concrete
    deliverable: ship the coefficient generator, not just the coefficients</b>, so the
    customer can retune for their own band plan without repeating the analysis.</div>""")

    s.append("<h2>E1.3 Multirate structures</h2>")
    s.append(tab("Rate conversion building blocks",
        ["Block", "Function", "Key property"],
        [["Decimator (&darr;<i>M</i>)", "Filter then discard <i>M</i>&minus;1 of every <i>M</i>",
          "<b>Filter first</b>, or aliasing is irreversible"],
         ["Interpolator (&uarr;<i>L</i>)", "Insert <i>L</i>&minus;1 zeros then filter",
          "Zeros create images; the filter removes them"],
         ["Polyphase decomposition", "Split the filter into <i>M</i> sub-filters",
          "<b>Avoids computing samples that are discarded</b> &mdash; <i>M</i>&times; saving"],
         ["<b>CIC</b>", "Integrator&ndash;comb cascade",
          "<b>No multipliers</b>; passband droop must be compensated"],
         ["Half-band", "Every other coefficient is zero", "~2&times; saving for 2:1 rates"],
         ["Farrow", "Polynomial interpolation with variable delay",
          "<b>Arbitrary, time-varying resampling ratio</b> &mdash; used in timing recovery"]]))
    s.append("""<div class="ms"><b>The CIC word-growth question is a classic fixed-point
    trap.</b> An <i>N</i>-stage CIC with rate change <i>R</i> and differential delay
    <i>M</i> has DC gain (<i>RM</i>)<sup><i>N</i></sup>, so the integrators need
    <i>W</i><sub>out</sub> = <i>W</i><sub>in</sub> + <i>N</i>log<sub>2</sub>(<i>RM</i>)
    bits. The textbook trick is to use <b>two's-complement wrap-around</b> in the
    integrators: intermediate values overflow, but because the comb stages later subtract,
    the overflow cancels exactly, provided the <i>final</i> result fits. This works
    because wrap-around arithmetic is a ring homomorphism. <b>Replace wrap with
    saturation &mdash; an apparently safer choice &mdash; and the cancellation is
    destroyed and the filter breaks.</b> A specification that says only "use saturating
    arithmetic throughout" would silently kill a correct CIC. This is why Part&nbsp;A's
    number-system chapter insists that overflow behaviour is a per-block decision.</div>""")

    s.append("<h2>E1.4 Adaptive filters</h2>")
    s.append(tab("Adaptive algorithms in hardware terms",
        ["Algorithm", "Update", "Multipliers per tap per update", "Convergence"],
        [["LMS", "<b>w</b> &larr; <b>w</b> + &mu;<i>e</i><b>x</b>*", "2",
          "Slow; sensitive to eigenvalue spread"],
         ["NLMS", "&mu; normalised by &#8214;<b>x</b>&#8214;<sup>2</sup>", "2 + norm",
          "Robust to input level"],
         ["Sign-error LMS", "uses sgn(<i>e</i>)", "1", "Slower"],
         ["Sign-data LMS", "uses sgn(<b>x</b>)", "1", "Slower"],
         ["<b>Sign-sign LMS</b>", "both signs", "<b>0 &mdash; adds only</b>",
          "Slowest; <b>used in every high-speed SerDes</b>"],
         ["RLS", "inverse correlation update", "O(<i>N</i>) per tap", "Fast; expensive"],
         ["Frequency-domain LMS", "block FFT", "&mdash;", "Fast for long filters"]]))
    s.append("""<div class="ms"><b>Why sign-sign LMS dominates at 56 GBd.</b> Two
    independent facts combine. First, the channel changes on a timescale of milliseconds
    while symbols arrive every 18&nbsp;ps &mdash; <b>adaptation can be nine orders of
    magnitude slower than the datapath</b>. Second, multipliers cannot run at the symbol
    rate at all. Taking only signs reduces the update to increment/decrement, which can be
    accumulated over thousands of symbols and applied occasionally. The resulting
    architecture has a <i>fast datapath</i> and a <i>slow adaptation loop</i> in a
    different clock domain. <b>For a modelling engineer this separation must be explicit
    in the model</b>, because a model that updates taps every symbol will not match RTL
    that updates them every 4096 symbols, even though both "implement sign-sign LMS".
    The update schedule is part of the specification.</div>""")
    return "\n".join(s)


def ch_fft():
    s = ['<h1 id="e2">E2. Transforms in Hardware: FFT and Friends</h1>']
    s.append(tab("FFT algorithm families",
        ["Algorithm", "Complex multiplies", "Structure", "Note"],
        [["Radix-2 DIT/DIF", "(<i>N</i>/2)log<sub>2</sub><i>N</i>", "Regular butterflies",
          "Simplest control"],
         ["Radix-4", "fewer", "4-point butterflies", "~25% fewer multiplies"],
         ["Split-radix", "fewest for radix-2<sup>k</sup>", "Irregular", "Control complexity"],
         ["Winograd / PFA", "Minimum multiplies", "Length must factor into coprimes", "Niche"],
         ["<b>Pipelined SDF</b>", "&mdash;", "One butterfly per stage + delay line",
          "<b>Streaming; the standard for OFDM</b>"],
         ["MDC", "&mdash;", "Multiple data paths", "Higher throughput"],
         ["<b>SSR / parallel</b>", "&mdash;", "Several samples per clock",
          "<b>When the data rate exceeds the clock rate</b>"]]))
    s.append("""<div class="ms"><b>The resource that actually limits an FFT is memory and
    the twiddle factors, not the butterflies.</b> A pipelined <i>N</i>-point SDF FFT needs
    log<sub>2</sub><i>N</i> butterflies but a total of <i>N</i>&minus;1 words of delay
    line, and a twiddle ROM whose size grows with <i>N</i>. For <i>N</i>&nbsp;=&nbsp;4096
    that is thousands of words of storage against a dozen arithmetic units. Two standard
    optimisations follow: exploit twiddle symmetry to store only one eighth of a period
    and derive the rest by sign and swap, or generate twiddles with a CORDIC instead of a
    ROM. <b>Which one wins depends on whether the target has cheap memory (FPGA) or cheap
    logic (ASIC)</b> &mdash; another instance of the rule that architecture choices are
    technology-dependent and must be re-derived, not memorised.</div>""")
    s.append("""<div class="warn"><b>Bit-reversed output order is an interface decision,
    not an implementation detail.</b> A DIF FFT naturally produces its output in
    bit-reversed order. Reordering costs a full <i>N</i>-word buffer and its bandwidth. In
    many systems the consumer &mdash; a channel equaliser, a magnitude detector &mdash;
    does not care about order, so the reordering is pure waste. Competent designs pass the
    bit-reversed order through and let the next block absorb it. <b>This means the
    reference model and the RTL will disagree about output order unless the specification
    says which convention is normative</b>, and a large fraction of "FFT mismatch" bug
    reports are exactly this.</div>""")
    s.append(tab("Numerical behaviour of fixed-point FFT",
        ["Issue", "Cause", "Handling"],
        [["Magnitude growth", "Each radix-2 stage can double magnitude",
          "Scale by &frac12; per stage (lose SNR), grow the word, or <b>block floating point</b>"],
         ["Twiddle quantisation", "Finite coefficient precision",
          "Adds a noise floor; usually 2&ndash;4 bits more than data width"],
         ["Rounding vs truncation", "Bias accumulates over log<i>N</i> stages",
          "Convergent rounding avoids DC bias"],
         ["Overflow detection", "Input-dependent", "Saturate and flag, or scale conservatively"]]))
    s.append(tab("Other transforms used in IP",
        ["Transform", "Property", "Application"],
        [["DCT-II", "Energy compaction for correlated signals",
          "JPEG, H.264/HEVC (integer approximations)"],
         ["Integer DCT", "Exactly invertible, multiplier-free",
          "<b>Video codecs</b> &mdash; avoids encoder/decoder drift"],
         ["Hadamard", "&plusmn;1 only", "Secondary transform, spreading"],
         ["Number-theoretic (NTT)", "Exact modular arithmetic",
          "<b>Post-quantum crypto (ML-KEM/ML-DSA)</b>, homomorphic encryption"],
         ["Wavelet (DWT)", "Time&ndash;frequency localisation", "JPEG2000, denoising"]]))
    s.append("""<div class="ms"><b>The integer DCT in video codecs is a beautiful example
    of specification-driven design.</b> An exact DCT requires irrational coefficients; any
    two implementations would round differently, and since the decoder's output feeds back
    into the encoder's prediction loop, the tiny differences would accumulate into visible
    <i>drift</i>. H.264 solved this by <b>defining the transform to be a specific integer
    matrix</b>, so every conforming implementation produces bit-identical results. The
    lesson generalises directly to IP work: <b>when an algorithm sits in a feedback loop
    that spans two independently implemented systems, the specification must be bit-exact,
    not mathematical.</b> The same reasoning applies to a DFE's tap update, to an
    adaptive equaliser shared between link partners, and to any distributed control
    loop.</div>""")
    return "\n".join(s)
