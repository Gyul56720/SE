# -*- coding: utf-8 -*-
"""Volume I, Part M -- Software interface, ML hardware, imaging, measurement."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def ch_hwsw():
    s = ['<h1 id="m1">M1. The Hardware&ndash;Software Interface</h1>']
    s.append("""<p>An IP block is useless until software can drive it. The interface
    between them is a design artefact in its own right, and getting it wrong produces
    integration cost that dwarfs the block's development.</p>""")
    s.append(tab("Interface mechanisms",
        ["Mechanism", "Direction", "Cost", "When appropriate"],
        [["<b>Memory-mapped registers</b>", "CPU &rarr; block", "Low",
          "Configuration, status; the default"],
         ["Polling", "CPU reads status", "<b>Wastes CPU cycles and power</b>",
          "Very short operations"],
         ["<b>Interrupt</b>", "block &rarr; CPU", "Latency and context switch",
          "Completion of long operations"],
         ["<b>DMA</b>", "block &harr; memory", "Bus bandwidth",
          "Bulk data; avoids CPU copying"],
         ["Descriptor rings", "&mdash;", "Memory traffic",
          "Streaming with many buffers (network, storage)"],
         ["Mailbox / doorbell", "bidirectional", "Low", "Command submission"],
         ["Shared memory + fences", "&mdash;", "Coherence traffic",
          "Tight coupling; <b>requires a memory model</b>"]]))
    s.append("""<div class="ms"><b>The single most consequential interface decision is
    who moves the data.</b> A block that requires the CPU to write its input and read its
    output word by word can be limited by the CPU even when the block itself is fast; a
    DMA-capable block moves data in bursts and leaves the CPU free. The difference is
    frequently an order of magnitude in system throughput, and it is invisible in
    block-level benchmarks. <b>For an IP vendor this means the example design matters as
    much as the block</b>: a customer who integrates it through programmed I/O will measure
    disappointing performance and conclude the IP is slow.</div>""")
    s.append(tab("Register map design rules",
        ["Rule", "Reason"],
        [["Generate RTL, header, documentation and tests from one source",
          "<b>Three hand-maintained copies always diverge</b>"],
         ["Reserve and document unused bits", "Forward compatibility"],
         ["Make read-clear and write-one-clear behaviour explicit",
          "Ambiguity here produces lost interrupts"],
         ["Provide an identification and version register",
          "Software can adapt to the actual hardware"],
         ["Group by function, align to natural boundaries", "Simplifies access"],
         ["Avoid side effects on read where possible",
          "<b>A debugger that dumps registers must not change behaviour</b>"],
         ["State atomicity for wide registers", "Prevents tearing"]]))
    s.append("""<div class="warn"><b>Read side effects break debuggers, and the failure is
    baffling when it happens.</b> If reading a FIFO status register pops an entry, then
    attaching a debugger that displays the register window silently consumes data, and the
    bug disappears when the debugger is detached. Where a read side effect is genuinely
    required &mdash; a pop-on-read data port, for example &mdash; it must be isolated in
    its own register and clearly marked, so that a debug tool can be told to avoid it.
    This is a small documentation duty with a disproportionate payoff.</div>""")
    s.append(tab("Driver and firmware concerns an IP vendor should anticipate",
        ["Concern", "What the IP must provide"],
        [["Initialisation sequence", "Exact required order, including any wait conditions"],
         ["Reset semantics", "What a soft reset does and does not clear"],
         ["Error reporting", "Sticky status bits with a defined clearing mechanism"],
         ["Concurrency", "Which registers may be accessed while the block is running"],
         ["Endianness and bit order", "<b>Stated explicitly</b>"],
         ["Timeouts", "Maximum time any operation can take"],
         ["Low-power entry/exit", "Sequence and state retention"]]))
    return "\n".join(s)


def ch_ml():
    s = ['<h1 id="m2">M2. Machine Learning Hardware</h1>']
    s.append(tab("Operations that dominate inference",
        ["Operation", "Share of compute", "Arithmetic intensity", "Hardware mapping"],
        [["Convolution", "High in CNNs", "High with tiling",
          "Systolic array or vector units"],
         ["<b>Matrix multiply (GEMM)</b>", "Dominant in transformers", "High",
          "<b>The universal accelerator primitive</b>"],
         ["Attention (QK<sup>T</sup>V)", "Dominant in LLMs", "Moderate",
          "<b>Memory bound at long sequence lengths</b>"],
         ["Element-wise / activation", "Low compute", "<b>Very low</b>",
          "Memory bound; fuse with the previous layer"],
         ["Normalisation", "Low", "Low", "Fuse; needs reductions"],
         ["Softmax", "Low", "Low", "Needs exp and a reduction; numerically delicate"],
         ["Embedding lookup", "&mdash;", "Very low", "Random memory access"]]))
    s.append("""<div class="ms"><b>Fusion is the main architectural lever and it follows
    directly from the roofline.</b> An activation function performs one operation per
    element and therefore has arithmetic intensity near zero &mdash; it is entirely memory
    bound. Executed as a separate pass it costs a full read and write of the tensor.
    Fused into the preceding matrix multiply's output stage it costs essentially nothing.
    Real accelerators therefore expose fused operations rather than primitive ones, and
    their compilers spend most of their effort deciding what to fuse. <b>An IP block that
    implements a single layer type in isolation will underperform in a system for reasons
    that have nothing to do with its internal quality.</b></div>""")
    s.append(tab("Quantisation approaches",
        ["Approach", "Accuracy loss", "Effort", "Hardware"],
        [["Post-training, per-tensor INT8", "Moderate", "Low", "One scale per tensor"],
         ["<b>Post-training, per-channel INT8</b>", "Small", "Low",
          "<b>Per-channel scale multiply &mdash; usually worth it</b>"],
         ["Quantisation-aware training", "Very small", "High", "Same as above"],
         ["INT4 with grouping", "Noticeable", "High", "Group-wise scales"],
         ["Mixed precision", "Small", "Moderate", "Sensitive layers kept wider"],
         ["Binary / ternary", "Large", "High", "<b>XNOR&ndash;popcount; no multipliers</b>"]]))
    s.append("""<div class="ms"><b>Quantisation is a fixed-point problem and the
    vocabulary of Chapter A3 applies unchanged.</b> A per-tensor scale is a single Q
    format for the whole tensor; per-channel scaling is the recognition that different
    channels have different dynamic ranges, which is exactly the block-floating-point idea
    from the FFT chapter. Understanding this correspondence prevents an engineer from
    treating ML quantisation as a separate discipline: the questions &mdash; where to
    round, when to saturate, how dynamic range grows through a computation &mdash; are the
    same, and the answers are reached the same way.</div>""")
    s.append(tab("Sparsity",
        ["Kind", "Speedup potential", "Hardware feasibility"],
        [["Unstructured (random zeros)", "High in theory",
          "<b>Poor</b> &mdash; irregular access defeats the memory system"],
         ["<b>Structured (2:4, block)</b>", "Moderate", "<b>Good</b> &mdash; regular indexing"],
         ["Channel / filter pruning", "Moderate", "Excellent &mdash; it is just a smaller dense model"],
         ["Activation sparsity (ReLU)", "Moderate", "Dynamic; needs run-time detection"]]))
    s.append("""<div class="warn"><b>Unstructured sparsity is the clearest case of a
    metric that does not translate into hardware.</b> A paper reporting 90% of weights
    pruned implies a tenfold reduction in operations, but realising it requires indexing
    individual non-zeros, which destroys the regular access patterns that give an
    accelerator its efficiency. The achieved speedup is commonly a small fraction of the
    nominal one, and can be below unity. <b>Structured sparsity exists because hardware
    needs regularity more than it needs fewer operations</b> &mdash; a principle that
    recurs whenever an algorithmic saving is proposed.</div>""")
    return "\n".join(s)


def ch_image():
    s = ['<h1 id="m3">M3. Image Signal Processing</h1>']
    s.append(tab("The ISP pipeline",
        ["Stage", "Function", "Why it is in hardware"],
        [["Black level and defect correction", "Sensor offset, dead pixels", "Per-pixel rate"],
         ["Lens shading correction", "Vignetting", "Per-pixel with a gain surface"],
         ["<b>Demosaic</b>", "Bayer &rarr; RGB", "<b>Neighbourhood operation at pixel rate</b>"],
         ["White balance", "Illuminant compensation", "Per-pixel gains"],
         ["Colour correction matrix", "Sensor &rarr; standard colour space", "3&times;3 per pixel"],
         ["Gamma / tone mapping", "Perceptual encoding", "LUT per pixel"],
         ["Noise reduction", "Spatial and temporal filtering",
          "<b>Line buffers dominate the area</b>"],
         ["Sharpening", "Edge enhancement", "Convolution"],
         ["Scaling", "Resize", "Polyphase filter"]]))
    s.append("""<div class="ms"><b>Line buffers, not arithmetic, determine ISP cost.</b> A
    5&times;5 neighbourhood operation at 4K resolution requires four lines of 3840 pixels
    each held on chip; at 12 bits per component that is roughly 184&nbsp;kbit per stage
    before any compute. A pipeline with several such stages spends most of its silicon on
    storage. The architectural consequences are standard: process in tiles rather than
    full lines, fuse stages so that a neighbourhood is read once and used by several
    operations, and choose separable filters wherever possible. <b>This is the same
    memory-versus-compute analysis as the roofline of Chapter J2, applied to a different
    domain.</b></div>""")
    s.append(tab("Colour and vision concepts that reach the hardware",
        ["Concept", "Meaning", "Implementation note"],
        [["Bayer pattern", "One colour per photosite", "Demosaic must interpolate two of three"],
         ["Colour space (sRGB, YCbCr)", "&mdash;",
          "YCbCr separates luma for chroma subsampling"],
         ["Chroma subsampling (4:2:0)", "Half resolution chroma",
          "Exploits lower chroma acuity &mdash; halves the data"],
         ["Gamma", "Non-linear encoding", "<b>Must be undone before linear operations</b>"],
         ["HDR / tone mapping", "Wide dynamic range compressed for display",
          "Local operators need neighbourhood statistics"],
         ["Rolling shutter", "Rows exposed at different times", "Motion artefacts; a system issue"]]))
    s.append("""<div class="warn"><b>Performing linear operations on gamma-encoded data is
    a persistent and quiet error.</b> Gamma encoding is non-linear, so averaging two
    gamma-encoded pixels does not give the gamma encoding of their average. Scaling,
    blending and filtering must therefore be done in linear light, which means decoding
    before and re-encoding after. The visible symptom is subtly wrong brightness at edges
    &mdash; easy to miss in a test pattern and obvious on real images. <b>Specify the
    colour encoding of every interface</b>, in the same way and for the same reason that
    fixed-point formats must be specified.</div>""")
    return "\n".join(s)


def ch_measure():
    s = ['<h1 id="m4">M4. Measurement and Characterisation</h1>']
    s.append("""<p>Everything in this book that is stated as a number came from a
    measurement, and the difference between a useful number and a misleading one is
    usually in the method rather than the instrument.</p>""")
    s.append(tab("Instruments and what they actually measure",
        ["Instrument", "Measures", "Principal limitation"],
        [["Oscilloscope", "Voltage versus time", "Bandwidth and probe loading"],
         ["Real-time versus sampling scope", "&mdash;",
          "Sampling scopes need a repetitive signal"],
         ["Spectrum analyser", "Power versus frequency",
          "<b>Resolution bandwidth changes the displayed noise floor</b>"],
         ["Vector network analyser", "S-parameters", "Calibration plane definition"],
         ["<b>BER tester</b>", "Errors per bit", "<b>Time: 10<sup>&minus;12</sup> at 10 Gb/s takes ~100 s per point</b>"],
         ["Time interval analyser", "Jitter statistics", "Trigger accuracy"],
         ["Logic analyser", "Digital state", "No analogue detail"],
         ["Thermal camera", "Surface temperature", "Emissivity; not junction temperature"],
         ["Power analyser / shunt", "Current", "Bandwidth versus resolution"]]))
    s.append("""<div class="ms"><b>Bathtub extrapolation exists because direct BER
    measurement does not scale.</b> Confirming 10<sup>&minus;15</sup> by counting errors
    would take days per operating point, which is impossible for a characterisation sweep.
    Instead the eye is scanned at several sampling phases, the error rate is measured where
    it is high enough to be quick, and the Gaussian random-jitter tails are extrapolated to
    the target BER. <b>The extrapolation is only valid if the random component really is
    Gaussian and has been correctly separated from the bounded deterministic component</b>
    &mdash; which is why jitter decomposition is a required capability rather than a
    convenience, and why a reported margin should always name the method.</div>""")
    s.append(tab("Characterisation practices",
        ["Practice", "Reason"],
        [["Sweep, do not spot-check",
          "A single operating point can be unrepresentative or accidentally favourable"],
         ["Confirm the operating point is healthy first",
          "<b>Measurements taken on a broken setup look plausible</b>"],
         ["Obtain the same quantity a second way",
          "An independent estimate catches methodological errors"],
         ["List the trivial explanations and rule each out by measurement",
          "A result that could be an artefact is a hypothesis, not a finding"],
         ["Record conditions with every number",
          "Temperature, voltage, part, instrument, settings"],
         ["Report the condition under which the claim fails",
          "<b>A claim with no stated failure condition is advertising</b>"]]))
    s.append("""<div class="warn"><b>Four measurement failures, each of which produced a
    plausible number that meant nothing.</b> Taking the slope of a pulse at its peak
    &mdash; which is zero by definition &mdash; and reporting it as a sensitivity.
    Measuring residuals at an operating point where BER was already 0.49, so the link
    carried no information. Asking a tool for the longest path in an entire netlist when
    the quantity of interest was the delay around one feedback loop. Reporting a lookup
    table's accuracy at an operating point where the feedback taps were so small that the
    loop was effectively inactive, so the table was never exercised. <b>In every case the
    instrument worked and the number was wrong, because the quantity measured was not the
    quantity intended.</b> The four rules above are written to prevent exactly these.</div>""")
    return "\n".join(s)
