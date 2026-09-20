# -*- coding: utf-8 -*-
"""Volume I, Part R -- Cryptographic mathematics, test, and quantum."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def ch_cryptomath():
    s = ['<h1 id="r1">R1. Cryptographic Mathematics</h1>']
    s.append("<h2>R1.1 Number theory for public-key cryptography</h2>")
    s.append(tab("Results and the hardware they imply",
        ["Result", "Statement", "Hardware consequence"],
        [["Fermat's little theorem",
          "<i>a</i><sup><i>p</i>&minus;1</sup> &equiv; 1 (mod <i>p</i>)",
          "Inversion by exponentiation &mdash; avoids extended Euclid"],
         ["Euler's theorem", "<i>a</i><sup>&phi;(<i>n</i>)</sup> &equiv; 1 (mod <i>n</i>)",
          "The basis of RSA"],
         ["<b>Chinese remainder theorem</b>", "Work modulo factors, recombine",
          "<b>RSA private operations run ~4&times; faster</b>"],
         ["Extended Euclid", "Compute inverses", "Needed for key setup"],
         ["<b>Montgomery reduction</b>", "Modular reduction without division",
          "<b>The core of every modular multiplier</b>"],
         ["Barrett reduction", "Reduction by precomputed reciprocal",
          "Alternative; good for fixed small moduli"],
         ["Discrete logarithm hardness", "&mdash;", "Security of Diffie&ndash;Hellman and ECC"],
         ["Elliptic curve group law", "&mdash;", "Point addition and doubling formulas"]]))
    s.append("""<div class="ms"><b>Montgomery multiplication is worth understanding
    because it explains why modular arithmetic is feasible in hardware at all.</b> Naive
    modular reduction requires a division, which is expensive and has data-dependent
    latency. Montgomery's method transforms operands into a residue domain where reduction
    becomes a multiplication and a shift &mdash; both cheap and constant time. The cost is
    a conversion in and out of the domain, which is amortised when many operations are
    performed, exactly as in an exponentiation. <b>The constant-time property is as
    important as the speed</b>: a reduction whose duration depended on the operand would
    leak the secret exponent through timing.</div>""")
    s.append("""<div class="warn"><b>The Chinese remainder theorem speedup for RSA is also
    its most famous vulnerability.</b> Computing modulo <i>p</i> and <i>q</i> separately
    and recombining is about four times faster, but if a fault is injected during one of
    the two branches, the faulty signature and a correct one together reveal a factor of
    the modulus by a single greatest-common-divisor computation &mdash; the entire private
    key, from one fault. The standard countermeasure is to verify the signature before
    releasing it. <b>This is the clearest example in the book of a performance optimisation
    creating a security hole</b>, and of why a countermeasure must be specified alongside
    the optimisation that makes it necessary.</div>""")

    s.append("<h2>R1.2 Post-quantum cryptography</h2>")
    s.append(tab("NIST post-quantum standards",
        ["Standard", "Scheme", "Basis", "Hardware character"],
        [["<b>FIPS 203</b>", "ML-KEM (Kyber)", "Module lattices (MLWE)",
          "<b>NTT over &#8484;<sub>3329</sub></b>; small coefficients"],
         ["<b>FIPS 204</b>", "ML-DSA (Dilithium)", "Module lattices",
          "<b>NTT over &#8484;<sub>8380417</sub></b>; rejection sampling"],
         ["FIPS 205", "SLH-DSA (SPHINCS+)", "Hash-based",
          "<b>Many hash evaluations</b>; large signatures; conservative security"],
         ["(FN-DSA)", "Falcon", "NTRU lattices",
          "Floating-point Gaussian sampling &mdash; awkward in hardware"]]))
    s.append("""<div class="ms"><b>The shared kernel across the lattice schemes is the
    number-theoretic transform, and recognising this is how a design house covers several
    standards with one block.</b> An NTT is an FFT over a finite ring: the same butterfly
    structure, with modular multipliers replacing complex ones and a root of unity
    replacing the twiddle factor. Everything learned about FFT architectures &mdash;
    pipelined versus memory-based, in-place addressing, bit-reversal handling &mdash;
    transfers directly. What is new is modular reduction in the datapath, and for the
    specific small primes used by these standards there are cheap reduction sequences.
    <b>A parameterised NTT block serves ML-KEM, ML-DSA and homomorphic encryption
    alike.</b></div>""")
    s.append("""<div class="warn"><b>Rejection sampling makes ML-DSA's timing
    data-dependent, and that is a specification problem.</b> Signature generation retries
    until the candidate satisfies a bound, so the number of iterations varies. A naive
    implementation therefore has variable latency &mdash; awkward for a pipeline, and a
    potential timing side channel. Implementations must either run for a fixed number of
    iterations with the result masked, or ensure the timing variation reveals nothing about
    the secret. <b>This is the same fixed-versus-adaptive tension as the SVD sweep count
    and the LDPC iteration limit of earlier chapters</b>, arriving in a new
    domain.</div>""")

    s.append("<h2>R1.3 Symmetric primitives and modes</h2>")
    s.append(tab("Modes of operation and their hardware character",
        ["Mode", "Parallelisable", "Needs", "Note"],
        [["ECB", "Yes", "&mdash;", "<b>Insecure for structured data</b> &mdash; never use"],
         ["CBC", "Decrypt only", "IV", "Encryption is serial &mdash; a throughput limit"],
         ["<b>CTR</b>", "<b>Fully, both directions</b>", "Unique counter",
          "<b>Preferred in hardware</b>; turns a cipher into a keystream generator"],
         ["<b>GCM</b>", "Yes", "GF(2<sup>128</sup>) multiplier",
          "Authenticated encryption; the multiplier is a substantial block"],
         ["XTS", "Yes", "Tweak", "Storage encryption"],
         ["CMAC / GMAC", "&mdash;", "&mdash;", "Authentication only"]]))
    s.append("""<div class="ms"><b>Counter mode is the reason a high-throughput AES core
    is feasible.</b> In CBC each block's encryption depends on the previous ciphertext, so
    the cipher is a serial chain and throughput is bounded by one block per cipher latency.
    In CTR the cipher encrypts a counter, independent of the data, so many blocks can be
    computed in parallel and the cipher becomes a pipelined keystream generator whose
    latency no longer matters. <b>The mode, not the cipher, determines whether the block
    can be pipelined</b> &mdash; which is why a datasheet must state which modes achieve
    full throughput and which do not.</div>""")
    return "\n".join(s)


def ch_test():
    s = ['<h1 id="r2">R2. Manufacturing Test</h1>']
    s.append(tab("Fault models",
        ["Model", "Represents", "Coverage target", "Test method"],
        [["<b>Stuck-at</b>", "A node permanently 0 or 1", "&gt;99%", "Scan + ATPG"],
         ["<b>Transition / delay</b>", "A path too slow", "&gt;90%",
          "At-speed scan (launch-on-capture or launch-on-shift)"],
         ["Path delay", "A specific critical path", "Selected paths", "Targeted patterns"],
         ["Bridging", "Short between nodes", "&mdash;", "Layout-aware ATPG"],
         ["Open", "Broken connection", "&mdash;", "&mdash;"],
         ["IDDQ", "Abnormal quiescent current", "&mdash;",
          "<b>Less effective at advanced nodes</b> &mdash; leakage swamps it"],
         ["Cell-aware", "Defects inside a standard cell", "&mdash;",
          "Requires cell-level fault dictionaries"]]))
    s.append("""<div class="ms"><b>Stuck-at coverage is a proxy, not a goal, and the
    distinction matters commercially.</b> No real defect is exactly a stuck-at fault; the
    model is used because it is tractable and correlates with real defect detection. The
    correlation is imperfect, which is why transition and cell-aware models were added as
    geometries shrank. For an IP vendor the practical obligation is to make the block
    testable &mdash; fully scannable, no uncontrollable clock gating, no internally
    generated asynchronous resets, memories accessible to BIST &mdash; because the
    customer must reach <i>their</i> coverage target on the whole chip, and an untestable
    island drags the total down. <b>Testability is a deliverable property, and it is
    checked long before the customer ever runs the block.</b></div>""")
    s.append(tab("Test economics",
        ["Factor", "Effect", "Lever"],
        [["Tester time", "Directly proportional to cost per part",
          "<b>Test compression</b> (10&ndash;100&times; pattern reduction)"],
         ["Pattern count", "Drives tester time", "ATPG effectiveness"],
         ["Test escapes", "Defective parts shipped", "Higher coverage, better fault models"],
         ["Yield loss (overkill)", "Good parts rejected", "Correct test limits"],
         ["<b>Burn-in</b>", "Screens infant mortality", "Expensive; sometimes replaced by design margin"],
         ["Known-good die", "<b>Essential for chiplets</b>",
          "<b>Test before assembly or lose the whole package</b>"]]))
    s.append("""<div class="ms"><b>Known-good-die testing is what makes chiplets
    economically possible, and its absence is what delayed them.</b> If four dies are
    assembled into one package and any is defective, the whole package is lost &mdash; so
    the compound yield is the product of the individual yields. At 90% each, four dies give
    66%. Testing each die thoroughly before assembly restores the economics, but testing a
    bare die at speed is harder than testing a packaged part. <b>This is why the
    disaggregation trend depended on test technology as much as on interconnect
    standards</b>, and it is a useful reminder that a manufacturing capability can gate an
    architectural trend.</div>""")
    return "\n".join(s)


def ch_quantum():
    s = ['<h1 id="r3">R3. Quantum Computing: What a Hardware Engineer Should Know</h1>']
    s.append("""<p>Quantum computing is unlikely to be an IP engineer's day job, but it
    determines the timeline for post-quantum cryptography and it is generating demand for
    conventional control electronics. This chapter covers only what is decision-relevant.</p>""")
    s.append(tab("Concepts",
        ["Concept", "Meaning", "Consequence"],
        [["Qubit", "Two-level quantum system", "State is a superposition, not a bit"],
         ["Superposition and entanglement", "&mdash;", "Source of the potential speedup"],
         ["<b>Decoherence</b>", "Loss of quantum state to the environment",
          "<b>The central engineering problem</b>"],
         ["Gate fidelity", "Error per operation", "Currently ~10<sup>&minus;3</sup>&ndash;10<sup>&minus;4</sup>"],
         ["<b>Error correction</b>", "Many physical qubits per logical qubit",
          "<b>Overhead of 10<sup>3</sup>&ndash;10<sup>4</sup>&times;</b>"],
         ["Shor's algorithm", "Factoring in polynomial time",
          "<b>Breaks RSA and ECC &mdash; the reason for PQC</b>"],
         ["Grover's algorithm", "Quadratic search speedup",
          "Halves effective symmetric key strength &mdash; AES-256 remains adequate"]]))
    s.append("""<div class="ms"><b>The asymmetry between Shor and Grover is the fact that
    determines the migration plan.</b> Shor breaks public-key cryptography outright, so
    RSA and ECC must be replaced. Grover only square-roots the search space for symmetric
    ciphers and hashes, so doubling the key length restores the margin &mdash; AES-256 and
    SHA-384 are considered adequate. <b>The practical consequence is that the transition is
    about key exchange and signatures, not about bulk encryption</b>, which is why
    FIPS&nbsp;203 and 204 arrived while AES was left alone. An IP portfolio needs new
    asymmetric blocks, not new symmetric ones.</div>""")
    s.append(tab("Conventional electronics needed by quantum systems",
        ["Function", "Requirement", "Nature"],
        [["Qubit control pulses", "Precise microwave shaping",
          "<b>DAC + DSP &mdash; conventional high-speed design</b>"],
         ["Readout", "Low-noise amplification and discrimination", "ADC + classification"],
         ["<b>Real-time feedback</b>", "Error correction within the coherence time",
          "<b>Sub-microsecond latency &mdash; an FPGA or ASIC problem</b>"],
         ["Cryogenic operation", "Operate at 4 K or below", "Cryo-CMOS; extreme power limits"],
         ["Classical control processor", "Sequencing", "Conventional"]]))
    s.append("""<div class="ms"><b>Quantum error correction is a real-time classical
    signal-processing problem, and that is where conventional IP meets the field.</b>
    Syndrome measurements must be decoded and corrections applied faster than the qubits
    decohere &mdash; microseconds, not milliseconds &mdash; for thousands of qubits
    simultaneously. The decoders involved (minimum-weight perfect matching and its
    approximations) are graph algorithms with hard latency budgets, which is precisely the
    kind of problem the rest of this book is about. <b>A designer who can build a
    low-latency decoder for LDPC or surface codes has transferable skills here</b>,
    without needing any quantum physics.</div>""")
    return "\n".join(s)
