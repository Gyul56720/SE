# -*- coding: utf-8 -*-
"""Volume I, Part K -- Wireless systems, protocol stacks, reliability, modern topics."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def _f_ofdm():
    b = []
    blk = [("S/P", 25, 60), ("map", 100, 60), ("IFFT", 175, 66), ("+CP", 256, 58),
           ("P/S", 327, 58), ("DAC/RF", 398, 76)]
    for n, x, w in blk:
        b.append(box(x, 34, w, 38, n, None, 9))
        if x > 25: b.append(arr(x-13, 53, x, 53))
    b += [arr(0, 53, 25, 53), arr(487, 53, 512, 53)]
    b.append(txt(260, 104, "Cyclic prefix ≥ channel delay spread", 9, "middle"))
    b.append(txt(260, 124, "⇒ multipath becomes circular convolution", 9, "middle"))
    b.append(txt(260, 144, "⇒ one complex tap per subcarrier equalises the channel",
                 9, "middle", 'font-weight="bold"'))
    b.append(txt(260, 170, "The CP converts a hard equalisation problem into a division",
                 9, "middle", 'font-style="italic"'))
    return svg(525, 182, "".join(b))


def ch_wireless():
    s = ['<h1 id="k1">K1. Wireless Physical Layers</h1>']
    s.append("<h2>K1.1 OFDM</h2>")
    s.append(fig(_f_ofdm(), "OFDM transmitter. The cyclic prefix is the trick that makes "
                            "frequency-domain equalisation valid."))
    s.append("""<div class="ms"><b>Why the cyclic prefix works, stated precisely.</b>
    A linear convolution with the channel is not diagonalised by the DFT; a <i>circular</i>
    convolution is. Prepending the last <i>N<sub>cp</sub></i> samples of the symbol makes
    the channel's linear convolution look circular to the receiver, provided
    <i>N<sub>cp</sub></i> exceeds the channel's delay spread. The channel matrix then
    becomes diagonal in the DFT basis, so equalisation reduces to dividing each subcarrier
    by one complex number. <b>An <i>N</i>-tap time-domain equalisation problem has been
    exchanged for <i>N<sub>cp</sub></i>/<i>N</i> of lost throughput.</b> That trade is the
    entire justification for OFDM, and it explains why the CP length in every standard is
    tied to the expected delay spread of its deployment environment.</div>""")
    s.append(tab("OFDM impairments and their remedies",
        ["Impairment", "Effect", "Remedy", "Where implemented"],
        [["<b>PAPR</b>", "Sum of subcarriers has a high peak",
          "Clipping, tone reservation, SLM; or use SC-FDMA uplink",
          "Digital pre-distortion; amplifier back-off"],
         ["Carrier frequency offset", "<b>Destroys subcarrier orthogonality (ICI)</b>",
          "Estimate from preamble/pilots, correct before FFT", "Digital"],
         ["Sampling clock offset", "Progressive phase rotation", "Track with pilots", "Digital"],
         ["Phase noise", "Common phase error + ICI",
          "Estimate CPE from pilots", "Digital"],
         ["I/Q imbalance", "Mirror-image interference",
          "Estimate and compensate", "Digital"],
         ["Doppler", "Time-varying channel within a symbol",
          "Shorter symbols, or per-symbol tracking", "Design-level"]]))
    s.append("""<div class="ms"><b>Frequency offset is the impairment that must be fixed
    first and fixed well.</b> A residual offset destroys orthogonality and produces
    inter-carrier interference that no subsequent equaliser can undo, because the
    subcarriers are no longer separable. The tolerance is roughly 1% of the subcarrier
    spacing for negligible loss; in 5G NR with 30&nbsp;kHz spacing that is 300&nbsp;Hz
    &mdash; at 3.5&nbsp;GHz carrier, under 0.1&nbsp;ppm. <b>This single requirement sets
    the crystal specification for the whole device</b>, which is a good illustration of a
    digital-layer requirement propagating down to a bill-of-materials cost.</div>""")

    s.append("<h2>K1.2 MIMO</h2>")
    s.append(tab("MIMO techniques",
        ["Technique", "Objective", "Requirement", "Processing"],
        [["Spatial multiplexing", "Throughput", "Rich scattering",
          "<b>Matrix inversion or successive cancellation per subcarrier</b>"],
         ["Space&ndash;time coding", "Diversity", "None", "Simple combining (Alamouti)"],
         ["Beamforming", "SNR, interference", "<b>Channel knowledge at the TX</b>",
          "Weight computation"],
         ["Massive MIMO", "Both", "Many antennas, reciprocity",
          "Large matrix operations; <b>Cholesky/QR territory</b>"],
         ["MU-MIMO", "Multi-user capacity", "Multi-user CSI", "Precoding (ZF, MMSE, dirty paper)"]]))
    s.append(tab("MIMO detection algorithms",
        ["Detector", "Complexity", "Performance", "Hardware"],
        [["Zero forcing", "One matrix inverse", "Noise enhancement",
          "<b>Cholesky on <i>H</i><sup>H</sup><i>H</i></b>"],
         ["MMSE", "One matrix inverse", "Better at low SNR", "Same, with a regularising term"],
         ["<b>V-BLAST / SIC</b>", "Iterative", "Better", "Ordering + repeated inversion"],
         ["Sphere decoding", "Variable", "Near-ML", "<b>Data-dependent latency</b> &mdash; awkward"],
         ["<b>K-best</b>", "Fixed", "Near-ML", "<b>Fixed latency &mdash; preferred in hardware</b>"],
         ["Belief propagation", "Iterative", "Good", "Fits with LDPC decoding"]]))
    s.append("""<div class="ms"><b>K-best beats sphere decoding in hardware for a reason
    that has nothing to do with performance.</b> Sphere decoding prunes a search tree
    adaptively, so its runtime depends on the channel and the noise realisation; a
    pipelined receiver with a fixed symbol rate cannot accommodate variable latency without
    buffering for the worst case, which negates the saving. K-best keeps a fixed number of
    candidates at every level, giving constant throughput and latency at slightly worse
    error performance. <b>Determinism is worth more than average-case efficiency in a
    streaming datapath</b>, and this principle recurs in FEC (fixed iteration counts),
    in SVD (fixed sweep counts), and in CFAR (fixed window sizes).</div>""")
    return "\n".join(s)


def ch_protocol():
    s = ['<h1 id="k2">K2. Protocol Stacks as Hardware</h1>']
    s.append(tab("Ethernet layering and what each layer does",
        ["Layer", "Function", "Hardware", "Clause (802.3)"],
        [["MAC", "Framing, addressing, CRC, flow control", "Digital", "4, 31"],
         ["<b>RS-FEC</b>", "Reed&ndash;Solomon KP4/KR4", "<b>Digital &mdash; soft IP</b>",
          "<b>91, 161</b>"],
         ["<b>PCS</b>", "64b/66b or 256b/257b coding, scrambling, lane distribution, "
          "alignment markers, gearbox", "<b>Digital &mdash; soft IP</b>", "49, 82, 119"],
         ["PMA", "Serialisation, clock recovery, equalisation",
          "<b>Analogue/mixed &mdash; hard macro</b>", "&mdash;"],
         ["PMD", "Electrical or optical interface", "Analogue", "&mdash;"],
         ["AN / LT", "Auto-negotiation, link training", "Digital + control", "73, 72"]]))
    s.append("""<div class="ms"><b>The PCS/PMA boundary is the commercial boundary of the
    whole industry.</b> Vendors describe their products in exactly these terms &mdash;
    "hardened PMA with a soft PCS layer" &mdash; because the PMA is tied to a process node
    and must be delivered as a hard macro, while the PCS is process-independent RTL. For
    a digital design house this boundary defines what is reachable: everything from the
    PCS upward. It is also where the open-source landscape is thinnest &mdash; 10G BASE-R
    PCS exists in open form, but 100G-and-above multi-lane PCS and RS-FEC do not &mdash;
    which makes it a reasonable place to look for an entry product.</div>""")
    s.append(tab("64b/66b coding: what each piece is for",
        ["Element", "Purpose", "Failure if omitted"],
        [["2-bit sync header", "Distinguishes data from control blocks",
          "Receiver cannot find block boundaries"],
         ["<b>Self-synchronising scrambler</b> (x<sup>58</sup>+x<sup>39</sup>+1)",
          "DC balance and transition density",
          "<b>Baseline wander through AC coupling; CDR loses lock</b>"],
         ["Block type field", "Encodes control block layout", "&mdash;"],
         ["Block lock state machine", "Finds the header position", "No synchronisation"],
         ["BER monitor", "Counts invalid sync headers", "No link quality signal"],
         ["Gearbox", "Maps 66 bits onto a 64-bit datapath",
          "<b>Rate mismatch</b> &mdash; 66 does not divide the bus width"]]))
    s.append("""<div class="ms"><b>The gearbox is the piece newcomers underestimate.</b>
    A 66-bit block does not fit a 64-bit datapath, so the PCS must repack a 66-bit stream
    into 64-bit words, which realigns every block by two bits and returns to alignment
    only after 32 blocks. The resulting barrel shifter and control state machine are a
    surprisingly large fraction of the PCS. Multi-lane 100G+ adds alignment markers,
    lane deskew and reordering on top. <b>The "simple" coding layer is mostly plumbing,
    and the plumbing is where the engineering effort goes</b> &mdash; a pattern
    that recurs in every protocol block.</div>""")
    s.append(tab("PCIe layering",
        ["Layer", "Function", "Notes"],
        [["Transaction (TLP)", "Read/write/completion semantics, ordering rules",
          "<b>Ordering rules are subtle and a frequent source of bugs</b>"],
         ["Data link (DLLP)", "Sequence numbers, ACK/NAK, credit flow control",
          "Replay buffer sizing matters"],
         ["Physical logical", "Encoding (8b/10b, 128b/130b, FLIT), scrambling, lane management",
          "&mdash;"],
         ["Physical electrical", "SerDes", "Hard macro"],
         ["LTSSM", "Link training state machine",
          "<b>Large, intricate FSM &mdash; a classic formal-verification target</b>"]]))
    s.append(tab("DDR memory interface",
        ["Element", "Function", "Difficulty"],
        [["Command scheduling", "Bank, row, column timing", "Performance-critical"],
         ["<b>Training</b>", "Write levelling, read gate, per-bit deskew",
          "<b>Runs at boot; a mix of hardware and firmware</b>"],
         ["PHY", "DLL/PLL, DQS strobing", "Hard macro"],
         ["ECC", "SECDED or chipkill", "Latency and bandwidth cost"],
         ["Refresh", "Periodic; blocks access", "Real-time guarantee impact"],
         ["<b>Rowhammer mitigation</b>", "Track and refresh victims", "Security requirement"]]))
    return "\n".join(s)


def ch_reliability():
    s = ['<h1 id="k3">K3. Reliability, Safety and Yield</h1>']
    s.append(tab("Wear-out mechanisms",
        ["Mechanism", "Physics", "Accelerated by", "Design response"],
        [["<b>NBTI / PBTI</b>", "Interface trap generation under gate bias",
          "Voltage, temperature, duty cycle", "Timing guard band; adaptive body bias"],
         ["<b>HCI</b>", "Hot carriers damage the oxide", "Switching activity, high field",
          "Reduce voltage; limit slew"],
         ["<b>TDDB</b>", "Oxide breakdown", "Field, temperature",
          "Thickness rules; Weibull statistics"],
         ["<b>Electromigration</b>", "Momentum transfer moves metal atoms",
          "Current density, temperature", "Wire width rules, via arrays"],
         ["Stress migration", "Thermo-mechanical stress", "Thermal cycling", "Layout rules"],
         ["Soft errors", "Particle strikes", "Altitude, neutron flux", "<b>ECC, TMR, scrubbing</b>"]]))
    s.append("""<div class="ms"><b>Wear-out is a timing constraint, not an afterthought.</b>
    NBTI shifts |<i>V<sub>TH</sub></i>| over the device lifetime, so a path that just met
    timing on day one may fail after five years. Sign-off therefore uses an aged library
    or an explicit derate &mdash; commonly 5&ndash;10%. For an IP vendor this matters in a
    specific way: <b>a frequency claim is implicitly a claim about a lifetime</b>, and the
    two must be quoted together. "500 MHz" at fresh silicon and "500 MHz over ten years at
    125&nbsp;&deg;C" are different products.</div>""")
    s.append(tab("Functional safety (ISO 26262) concepts",
        ["Concept", "Meaning", "Hardware implication"],
        [["ASIL A&ndash;D", "Risk classification", "D is the most stringent"],
         ["<b>SPFM</b>", "Single-point fault metric", "&ge;99% for ASIL D"],
         ["<b>LFM</b>", "Latent fault metric", "&ge;90% for ASIL D"],
         ["<b>PMHF</b>", "Probabilistic metric for random hardware failures",
          "&lt;10 FIT for ASIL D"],
         ["Safety mechanism", "Detects or controls a fault",
          "ECC, lockstep, watchdogs, BIST"],
         ["Diagnostic coverage", "Fraction of faults detected", "Drives the metrics"],
         ["<b>Lockstep</b>", "Duplicate cores compared cycle by cycle",
          "Delayed lockstep avoids common-cause failures"],
         ["FMEDA", "Failure mode and diagnostic analysis",
          "<b>A required deliverable for safety IP</b>"]]))
    s.append("""<div class="warn"><b>Safety certification changes the deliverable list, not
    just the design.</b> An ASIL-D block must ship with an FMEDA showing computed SPFM,
    LFM and PMHF, a safety manual stating the assumptions of use, and evidence of a
    qualified development process. A technically excellent block without these documents
    cannot be used in a safety application at any price. <b>For a small design house this
    is the clearest example of a market that is closed not by engineering capability but
    by process obligations</b>, and it should be entered deliberately or not at all.</div>""")
    s.append(tab("Yield",
        ["Concept", "Expression", "Meaning"],
        [["Defect density <i>D</i><sub>0</sub>", "defects/cm<sup>2</sup>", "Process maturity"],
         ["Poisson yield", "<i>Y</i> = e<sup>&minus;<i>AD</i><sub>0</sub></sup>", "Pessimistic for large dies"],
         ["Negative binomial", "<i>Y</i> = (1+<i>AD</i><sub>0</sub>/&alpha;)<sup>&minus;&alpha;</sup>",
          "Accounts for defect clustering"],
         ["<b>Die area effect</b>", "&mdash;",
          "<b>Yield falls steeply with area</b> &mdash; the economic driver behind chiplets"],
         ["Repair / redundancy", "&mdash;", "Spare rows and columns in memories raise yield"],
         ["Parametric yield", "&mdash;", "Devices that work but miss specification"]]))
    return "\n".join(s)


def ch_modern():
    s = ['<h1 id="k4">K4. Current Research Directions</h1>']
    s.append("""<p>This chapter surveys the areas where current literature is active, so
    that a reader who has absorbed the preceding chapters can approach a recent paper
    knowing what problem it is addressing and which established constraint it is trying to
    relax.</p>""")
    s.append(tab("Active areas and the constraint each attacks",
        ["Area", "Constraint attacked", "Approach", "Open problem"],
        [["<b>Post-quantum cryptography</b>", "Shor's algorithm breaks RSA/ECC",
          "Lattice (ML-KEM/ML-DSA), hash-based (SLH-DSA)",
          "Large keys; NTT throughput; <b>side-channel protection of lattice arithmetic</b>"],
         ["<b>In-memory computing</b>", "Von Neumann data movement energy",
          "Analogue MAC in memory arrays (RRAM, SRAM)",
          "ADC overhead often cancels the saving; device variability"],
         ["<b>Approximate computing</b>", "Exactness is expensive",
          "Truncated multipliers, stochastic computing, voltage overscaling",
          "<b>Error bounds must be guaranteed, not measured</b>"],
         ["<b>Chiplets / UCIe</b>", "Reticle limit and yield vs die area",
          "Disaggregation with standard die-to-die links",
          "Test, thermal, known-good-die"],
         ["<b>Nonlinear equalisation</b>", "Linear equalisers fail on nonlinear channels",
          "Volterra series, neural equalisers",
          "Power and latency; <b>verification of a learned block</b>"],
         ["<b>Concatenated FEC for 224G</b>", "KP4 alone insufficient at 200G/lane",
          "Outer RS-KP4 + inner Hamming(128,120)", "Latency budget; decoder complexity"],
         ["<b>Formal at scale</b>", "Simulation cannot cover state space",
          "Word-level model checking, SMT", "Datapath equivalence remains hard"],
         ["<b>ML for EDA</b>", "Heuristics in placement/routing",
          "Learned cost models, RL for scheduling",
          "<b>Reproducibility and trust in sign-off</b>"],
         ["<b>Open PDK / open EDA</b>", "Tool licence cost as a barrier",
          "SkyWater/IHP PDKs, OpenROAD, Yosys",
          "Analogue and advanced-node support"],
         ["Cryogenic and superconducting", "CMOS energy floor", "SFQ logic, cryo-CMOS",
          "Infrastructure; interface to room temperature"]]))
    s.append("""<div class="ms"><b>How to read a paper in any of these areas.</b> Each row
    names a constraint from earlier chapters. In-memory computing attacks the roofline's
    memory-bound region (J2); approximate computing attacks the fixed-point
    accuracy&ndash;area trade (A3, C1); neural equalisation attacks the linear-model
    assumption behind every equaliser in F1; chiplets attack the yield-versus-area
    relation in K3. <b>Identifying which constraint a paper is relaxing, and what it pays
    for the relaxation, is a faster route to understanding than reading the method
    first</b> &mdash; and it immediately tells you whether the result transfers to your
    own problem, because you know which assumption it depends on.</div>""")
    s.append("""<div class="warn"><b>A caution that applies to all of these areas.</b>
    Reported gains are measured at an operating point the authors chose. Before accepting
    a claim, locate three things: the baseline (is it a strong implementation or a
    straw man?), the operating conditions (process, voltage, data set, channel), and the
    point at which the advantage disappears. A result quoted without the crossover point
    is a data point, not a design rule &mdash; and in an IP business, mistaking one for
    the other is how a year is lost.</div>""")
    return "\n".join(s)
