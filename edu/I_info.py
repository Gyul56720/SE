# -*- coding: utf-8 -*-
"""Volume I, Part I -- Information theory, algebra, optimisation, discrete maths."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def ch_info():
    s = ['<h1 id="i1">I1. Information Theory</h1>']
    s.append("<h2>I1.1 Entropy and its operational meanings</h2>")
    s.append("""<div class="math">H(X) = &minus;&sum;<sub>x</sub> p(x) log<sub>2</sub> p(x)
    &nbsp;&nbsp;&nbsp; I(X;Y) = H(X) &minus; H(X|Y)</div>""")
    s.append(tab("Information-theoretic quantities and where they bind hardware",
        ["Quantity", "Meaning", "Operational limit it sets"],
        [["Entropy <i>H</i>(<i>X</i>)", "Average information per symbol",
          "<b>Lossless compression cannot go below it</b> &mdash; bounds a codec's ratio"],
         ["Min-entropy <i>H</i><sub>&infin;</sub>",
          "&minus;log<sub>2</sub> max<sub>x</sub> <i>p</i>(<i>x</i>)",
          "<b>The measure NIST SP 800-90B requires</b> for an entropy source; always &le; <i>H</i>"],
         ["Conditional entropy", "Remaining uncertainty given side information",
          "Leakage analysis in side-channel evaluation"],
         ["Mutual information", "Information one variable carries about another",
          "<b>Side-channel leakage metric</b>; also the quantity maximised by capacity"],
         ["Channel capacity <i>C</i>", "max <i>I</i>(<i>X</i>;<i>Y</i>)",
          "No code can exceed it; tells you how far your FEC is from optimal"],
         ["Rate&ndash;distortion <i>R</i>(<i>D</i>)", "Minimum rate for distortion <i>D</i>",
          "<b>Lossy codec bound</b> &mdash; the theoretical floor of a video encoder"],
         ["Kolmogorov complexity", "Shortest program producing the string",
          "Uncomputable; conceptual only"]]))
    s.append("""<div class="ms"><b>Min-entropy is the one an IP engineer must get right,
    and it is not Shannon entropy.</b> A biased source that outputs 0 with probability
    0.9 has Shannon entropy 0.47 bits but min-entropy only
    &minus;log<sub>2</sub>(0.9) = 0.152 bits. Certification uses min-entropy because
    security must hold against the <i>most likely</i> guess, not the average case. A TRNG
    that claims "0.5 bits of entropy per sample" on Shannon grounds and is conditioned on
    that basis will fail validation and, worse, will produce keys with less
    unpredictability than advertised. <b>The conditioning ratio &mdash; how many raw bits
    are compressed into one output bit &mdash; is derived from min-entropy, and it is a
    hardware parameter.</b></div>""")

    s.append("<h2>I1.2 Capacity results that matter in practice</h2>")
    s.append(tab("Capacity expressions",
        ["Channel", "Capacity", "Design meaning"],
        [["AWGN", "<i>B</i> log<sub>2</sub>(1+SNR)",
          "The reference against which every modem is measured"],
         ["Binary symmetric (BSC)", "1 &minus; <i>H</i><sub>b</sub>(<i>p</i>)",
          "Hard-decision decoding loses ~2 dB versus soft"],
         ["Binary erasure (BEC)", "1 &minus; &epsilon;",
          "<b>Erasure decoding doubles RS correction capability</b>"],
         ["MIMO (<i>N<sub>t</sub></i>&times;<i>N<sub>r</sub></i>)",
          "&asymp; min(<i>N<sub>t</sub></i>,<i>N<sub>r</sub></i>) log(1+SNR)",
          "Capacity scales with antennas, not power"],
         ["Fading with CSI", "E[log(1+|<i>h</i>|<sup>2</sup>SNR)]",
          "Motivates adaptive modulation and coding"],
         ["Band-limited with ISI", "water-filling over the channel response",
          "<b>The theoretical justification for OFDM bit loading</b>"]]))
    s.append("""<div class="ms"><b>The soft-versus-hard decision gap is the most
    actionable number here.</b> Passing hard decisions to a decoder discards the
    reliability information the slicer had, and costs roughly 2&nbsp;dB on an AWGN
    channel. In a link budget 2&nbsp;dB is enormous &mdash; it is the difference between
    needing an extra equaliser tap and not. This is why modern FEC interfaces carry LLRs
    rather than bits, why the slicer in an ADC-based receiver reports a multi-bit
    soft value, and why the fixed-point width of that LLR is a system-level parameter
    rather than a local choice. <b>An interface that carries one bit where it could carry
    four has thrown away 2&nbsp;dB before the decoder starts.</b></div>""")

    s.append("<h2>I1.3 Source coding</h2>")
    s.append(tab("Compression methods in hardware",
        ["Method", "Principle", "Hardware character"],
        [["Huffman", "Prefix code by symbol probability",
          "Table lookup; <b>variable-length decode is serial</b>"],
         ["Canonical Huffman", "Ordered code lengths", "Compact tables, faster decode"],
         ["<b>Arithmetic / range</b>", "Interval subdivision",
          "Better ratio; <b>strictly serial</b> &mdash; a throughput bottleneck"],
         ["<b>CABAC</b>", "Context-adaptive binary arithmetic",
          "<b>The critical path of an H.264/HEVC decoder</b>"],
         ["ANS / rANS", "Asymmetric numeral systems",
          "Arithmetic-coding ratio with table-driven speed; used in AV1, Zstd"],
         ["LZ family", "Dictionary matching", "Match search is the expensive part"],
         ["RLE", "Run lengths", "Trivial; still used for coefficient maps"]]))
    s.append("""<div class="warn"><b>Entropy coding is where video decoders stop
    parallelising.</b> Transform, prediction and filtering all parallelise over blocks,
    but arithmetic decoding is inherently sequential: the next symbol's interval depends
    on the current state. This is why real decoders introduce architectural workarounds
    &mdash; slices and tiles that reset the context so they can be decoded independently,
    wavefront parallel processing, or the bypass modes that skip context modelling for
    near-uniform symbols. <b>The bitstream syntax was designed around a hardware
    constraint</b>, which is the clearest possible illustration that standards and
    architectures co-evolve.</div>""")
    return "\n".join(s)


def ch_algebra():
    s = ['<h1 id="i2">I2. Algebraic Structures for Hardware</h1>']
    s.append("<h2>I2.1 Groups, rings, fields</h2>")
    s.append(tab("Structures and the hardware they license",
        ["Structure", "Operations", "Guarantee", "Hardware consequence"],
        [["Group", "one associative op with inverses", "Cancellation",
          "Reversible transforms"],
         ["<b>Ring</b>", "+ and &times;, no division",
          "Closure under both", "<b>Two's-complement <i>W</i>-bit arithmetic is a ring</b> &mdash; "
          "wrap-around is exact, so operation order does not matter"],
         ["Field", "+ &times; and division", "Every non-zero element invertible",
          "GF(2<sup><i>m</i></sup>) arithmetic for codes and crypto"],
         ["Vector space over a field", "&mdash;", "Linearity",
          "<b>Linear codes: encoding and syndrome are matrix products</b>"],
         ["Polynomial ring <i>F</i>[<i>x</i>]/(<i>f</i>)", "&mdash;", "&mdash;",
          "Cyclic codes, NTT, lattice cryptography"]]))
    s.append("""<div class="ms"><b>The ring property of two's-complement arithmetic is the
    formal reason behind a practical rule.</b> Because <i>W</i>-bit two's complement is
    the ring &#8484;/2<sup><i>W</i></sup>&#8484;, addition and multiplication are exact
    modulo 2<sup><i>W</i></sup>, associative and commutative. Intermediate overflow
    therefore cancels exactly, provided the final result is in range, and <b>the order of
    accumulation cannot change the answer</b>. Saturation destroys the ring structure:
    once a value is clamped, information is lost and order matters. This is why a CIC
    filter <i>requires</i> wrap-around and why an LDPC decoder <i>requires</i> saturation
    &mdash; the two blocks rely on opposite algebraic properties. <b>Stating this as
    algebra rather than as folklore makes it possible to decide the question for a new
    block instead of guessing.</b></div>""")

    s.append("<h2>I2.2 Finite fields in detail</h2>")
    s.append(tab("GF(2<sup>m</sup>) implementation choices",
        ["Representation", "Multiplication", "Inversion", "Best for"],
        [["Polynomial basis", "Shift-and-XOR, reduce", "Extended Euclid or Itoh&ndash;Tsujii",
          "General purpose; most codes"],
         ["Normal basis", "More complex", "<b>Squaring is a free cyclic shift</b>",
          "Inversion-heavy workloads (ECC)"],
         ["<b>Log/antilog tables</b>", "Add logs", "Negate the log",
          "<b>Small fields (m &le; 12); the usual RS choice</b>"],
         ["Tower field", "GF(2<sup>8</sup>)&rarr;GF(2<sup>4</sup>)&rarr;GF(2<sup>2</sup>)",
          "Recursive", "<b>Maskable</b> &mdash; the AES DOM S-box"],
         ["Composite field", "&mdash;", "&mdash;", "Area reduction"]]))
    s.append("""<div class="ms"><b>The choice of irreducible polynomial is a
    specification item, not an implementation detail.</b> Two implementations of
    GF(2<sup>10</sup>) using different primitive polynomials produce entirely different
    &mdash; though isomorphic &mdash; arithmetic, and codewords from one will not decode in
    the other. Standards therefore fix the polynomial: AES uses
    <i>x</i><sup>8</sup>+<i>x</i><sup>4</sup>+<i>x</i><sup>3</sup>+<i>x</i>+1, and
    IEEE&nbsp;802.3 Clause&nbsp;91 fixes the field for RS(544,514). <b>A reference model
    that hard-codes a plausible polynomial without checking the standard will interoperate
    with nothing.</b> The defensive practice is to make the polynomial a parameter, assert
    that it is primitive (verify that &alpha; generates all 2<sup><i>m</i></sup>&minus;1
    non-zero elements), and record in the code whether the value has been confirmed
    against the specification text.</div>""")
    s.append(tab("Where finite fields appear",
        ["Application", "Field", "Operation that dominates"],
        [["Reed&ndash;Solomon", "GF(2<sup>8</sup>), GF(2<sup>10</sup>)", "Multiply, invert"],
         ["BCH", "GF(2<sup><i>m</i></sup>)", "Multiply"],
         ["AES", "GF(2<sup>8</sup>)", "Inverse (S-box), &times;2 and &times;3 (MixColumns)"],
         ["AES-GCM", "GF(2<sup>128</sup>)", "Carry-less multiply"],
         ["Elliptic curves", "GF(<i>p</i>) or GF(2<sup><i>m</i></sup>)",
          "Modular multiply (Montgomery)"],
         ["<b>ML-KEM / ML-DSA</b>", "&#8484;<sub><i>q</i></sub>[<i>x</i>]/(<i>x</i><sup><i>n</i></sup>+1)",
          "<b>Number-theoretic transform</b>"],
         ["CRC", "GF(2)[<i>x</i>]", "Polynomial remainder (LFSR)"],
         ["Erasure coding (RAID)", "GF(2<sup>8</sup>)", "Matrix multiply"]]))
    s.append("""<div class="ms"><b>Post-quantum cryptography brings a new arithmetic
    requirement into mainstream silicon.</b> ML-KEM and ML-DSA operate in a polynomial
    ring modulo a small prime (3329 and 8380417 respectively), and their bottleneck is the
    number-theoretic transform &mdash; an FFT over that ring. The hardware looks like an
    FFT but with modular multipliers instead of complex ones, and modular reduction by a
    fixed small prime admits efficient tricks (Montgomery, Barrett, or prime-specific
    shift&ndash;add chains). <b>For a design house, an NTT block parameterised over
    modulus and length is a single kernel serving several standards</b>, in the same way
    that a Cholesky block serves radar, MIMO and beamforming. Finding these shared kernels
    is how a small portfolio covers a large market.</div>""")
    return "\n".join(s)


def ch_opt():
    s = ['<h1 id="i3">I3. Optimisation and Numerical Methods</h1>']
    s.append(tab("Optimisation problems that appear in IP design",
        ["Problem", "Class", "Method", "Where"],
        [["Filter coefficient design", "Convex (minimax)", "Remez, convex solvers",
          "FIR design with quantised coefficients"],
         ["Equaliser tap solution", "Least squares", "Normal equations, QR",
          "MMSE equaliser initialisation"],
         ["Bit allocation", "Integer, convex relaxation", "Water-filling then rounding",
          "OFDM loading, quantisation budgeting"],
         ["<b>Scheduling / binding</b>", "NP-hard",
          "ILP, list scheduling, force-directed", "<b>HLS internals</b>"],
         ["Retiming", "Polynomial", "Leiserson&ndash;Saxe", "Timing optimisation"],
         ["Placement", "NP-hard", "Analytic + partitioning", "Physical design"],
         ["Layer/schedule ordering", "Combinatorial", "Local search, simulated annealing",
          "<b>LDPC layered decoding order</b>"],
         ["Word-length assignment", "Mixed integer", "Heuristic + simulation",
          "Fixed-point conversion"]]))
    s.append("""<div class="warn"><b>The objective function must be the true cost, not a
    convenient proxy.</b> A measured example: optimising an LDPC layer ordering against a
    closed-form stall estimate produced a schedule that a cycle-accurate model scored
    differently &mdash; the formula predicted 108 stall cycles where the true figure was
    80. Because the formula is an upper bound that assumes every potential conflict
    materialises, it ranks schedules incorrectly, and the search converges on the wrong
    one. <b>Build the accurate evaluator before the optimiser</b>; a search is only as good
    as the function it is minimising, and a fast wrong objective is worse than a slow
    right one.</div>""")
    s.append(tab("Numerical methods and their hardware suitability",
        ["Method", "Convergence", "Hardware note"],
        [["Newton&ndash;Raphson", "Quadratic",
          "Needs a multiplier and a good seed; used for reciprocal and rsqrt"],
         ["Goldschmidt", "Quadratic", "Better pipelining than Newton (no dependency chain)"],
         ["CORDIC", "Linear (one bit per iteration)", "<b>Shifts and adds only</b>"],
         ["Polynomial (minimax)", "Fixed degree",
          "<b>Remez-fitted polynomials beat Taylor</b> for equal degree"],
         ["Piecewise polynomial + LUT", "&mdash;", "The usual production answer"],
         ["Iterative refinement", "Doubles accuracy per step",
          "<b>Limited by conditioning</b> &mdash; see A5.2"]]))
    s.append("""<div class="ms"><b>Taylor series should almost never appear in shipped
    hardware.</b> A Taylor expansion minimises error at a single point and degrades away
    from it; a minimax (Remez) polynomial of the same degree distributes error evenly and
    typically achieves the same worst-case accuracy with one or two fewer terms. Since
    each term is a multiply&ndash;add, that is a direct area and latency saving. The
    standard production recipe is: reduce the argument to a small interval using the
    number's exponent, evaluate a low-degree minimax polynomial on that interval, then
    reconstruct. <b>Knowing that the textbook series is the wrong tool is a small piece of
    knowledge with a consistently measurable payoff.</b></div>""")
    return "\n".join(s)


def ch_discrete():
    s = ['<h1 id="i4">I4. Discrete Mathematics and Graphs in Hardware</h1>']
    s.append(tab("Graph problems in the design flow",
        ["Problem", "Where it appears", "Complexity", "Practical method"],
        [["Topological sort", "Netlist evaluation, scheduling", "Linear", "Exact"],
         ["Longest path", "<b>Static timing analysis</b>", "Linear on a DAG",
          "Exact &mdash; this is what STA computes"],
         ["Cycle detection", "Combinational loop check", "Linear", "Exact"],
         ["Min-cut / max-flow", "Partitioning, retiming",
          "Polynomial", "Exact"],
         ["Graph colouring", "Register allocation, channel assignment", "NP-hard", "Heuristic"],
         ["Clique / independent set", "Binding in HLS", "NP-hard", "Heuristic"],
         ["Shortest path", "Routing", "Polynomial", "A*, maze routing"],
         ["Steiner tree", "Multi-pin net routing", "NP-hard", "Heuristic"],
         ["Isomorphism", "<b>LVS (layout vs schematic)</b>", "Unknown class", "Practical algorithms"]]))
    s.append("""<div class="ms"><b>Recognising that a design task is a known graph problem
    is worth more than knowing an algorithm for it.</b> Static timing analysis is longest
    path on a DAG &mdash; which is why combinational loops must be forbidden: they make the
    problem ill-posed, not merely difficult. Retiming is a min-cost flow problem, which is
    why it is exactly solvable while placement (a quadratic assignment problem) is not.
    <b>The tractability boundary explains the tool landscape</b>: tasks on the polynomial
    side have exact tools that engineers trust, and tasks on the NP-hard side have
    heuristics whose results engineers must inspect. A designer who knows which side a
    problem lies on knows whether to argue with the tool.</div>""")
    s.append(tab("Boolean algebra and representations",
        ["Representation", "Property", "Use"],
        [["Truth table", "Exponential size", "Small functions, LUT mapping"],
         ["SOP / POS", "Two-level", "PLA, simple synthesis"],
         ["<b>BDD</b>", "Canonical for a fixed variable order",
          "<b>Equivalence checking</b>; order-sensitive size"],
         ["AIG (And-Inverter Graph)", "Compact, not canonical",
          "<b>Modern synthesis and formal engines</b>"],
         ["<b>CNF + SAT</b>", "&mdash;", "<b>Bounded model checking, equivalence</b>"],
         ["SMT", "Theories beyond Boolean", "Word-level formal verification"]]))
    s.append("""<div class="ms"><b>The shift from BDDs to SAT reshaped formal
    verification.</b> BDDs are canonical, which makes equivalence a pointer comparison,
    but their size explodes for arithmetic functions such as multipliers and is acutely
    sensitive to variable ordering. Modern SAT solvers, with conflict-driven clause
    learning, handle far larger instances without canonicity. The practical consequence
    for an IP engineer is that <b>formal property checking is now feasible on real control
    logic</b> &mdash; arbiters, FIFOs, protocol adapters, FSM reachability &mdash; where a
    decade ago it was a specialist activity. It remains infeasible on deep datapaths, so
    the division of labour is: formal for control, simulation with a golden model for
    datapath. <b>Knowing which side of that line a block falls on is how a verification
    plan is written.</b></div>""")
    return "\n".join(s)
