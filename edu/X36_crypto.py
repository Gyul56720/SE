# -*- coding: utf-8 -*-
"""Volume I, Part X36 -- Cryptographic engines: the arithmetic that sizes them."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_cryptoeng():
    s = ['<h1 id="x36">X36. Cryptographic Engines, Sized</h1>']
    s.append("""<p>Crypto IP is one of the most commonly licensed categories, and it is
    unusual in that its correctness is binary, its specifications are published and
    testable, and its cost is dominated by a small number of arithmetic primitives. That
    combination makes it a good first product for a design house and a good subject for
    exact sizing.</p>""")

    s.append("<h2>X36.1 The three primitive families and their costs</h2>")
    s.append(tab("What each family needs from the hardware",
        ["Family", "Examples", "Core operation", "Cost driver", "Typical area"],
        [["<b>Block ciphers</b>", "AES, ChaCha, SM4",
          "Substitution and permutation over a small state",
          "<b>The S-box, replicated</b>", "5&ndash;50 kGE"],
         ["<b>Hashes</b>", "SHA-2, SHA-3, BLAKE",
          "A compression function over a message block",
          "Adders and rotations; long carry chains in SHA-2",
          "10&ndash;30 kGE"],
         ["<b>Public key</b>", "RSA, ECC, Diffie&ndash;Hellman",
          "<b>Modular exponentiation or point multiplication</b>",
          "<b>The modular multiplier &mdash; dominates everything</b>",
          "50&ndash;500 kGE"],
         ["Post-quantum", "ML-KEM (Kyber), ML-DSA (Dilithium)",
          "Polynomial arithmetic in a ring, NTT",
          "<b>NTT butterflies and modular reduction &mdash; Part&nbsp;X6's FFT with "
          "a different field</b>", "50&ndash;200 kGE"],
         ["MAC / AEAD", "GCM, Poly1305, CMAC",
          "Carry-less or modular multiply-accumulate",
          "GF(2<sup>128</sup>) multiplier for GCM", "10&ndash;40 kGE"]]))
    s.append("""<div class="ms"><b>Post-quantum cryptography is an opportunity for
    design houses precisely because it is new.</b> The standards are recent, the hardware
    literature is thin, the incumbent crypto-IP vendors' portfolios were built for RSA and
    ECC, and the core operation &mdash; the number-theoretic transform &mdash; is an FFT
    over a finite field, which means Part&nbsp;X6's entire architectural analysis
    transfers: the same radix choices, the same twiddle-ROM symmetries, the same
    memory-versus-multiplier trade. <b>A team that has built an FFT has most of what an
    NTT needs</b>, with the arithmetic replaced by modular arithmetic, and that is an
    unusually direct path from an existing competence to a new market.</div>""")

    s.append("<h2>X36.2 AES: where the area actually goes</h2>")
    s.append(derive("The S-box is the block", [
        ("AES-128 is ten rounds of SubBytes, ShiftRows, MixColumns, AddRoundKey.",
         "Specification."),
        ("ShiftRows is wiring; AddRoundKey is 128 XORs; MixColumns is a fixed "
         "GF(2<sup>8</sup>) matrix &mdash; shifts and XORs.",
         "<b>All three are nearly free.</b>"),
        ("SubBytes applies a 256-entry nonlinear substitution to each of 16 bytes.",
         "<b>This is the whole cost.</b>"),
        ("As a table it is 16 &times; 2048 bits of ROM or 16 &times; ~700 gates "
         "synthesised.",
         "The naive implementation."),
        ("<b>Or compute it: the S-box is inversion in GF(2<sup>8</sup>) plus an affine "
         "map, and inversion decomposes through GF((2<sup>4</sup>)<sup>2</sup>).</b>",
         "Canright's tower-field construction reduces the S-box to roughly a third of "
         "the table's area, at the cost of more logic depth. <b>The trade is area "
         "against frequency</b>, and which side wins depends entirely on the "
         "throughput requirement."),
        ("A round can use 16 S-boxes (one cycle per round), 4, or 1.",
         "<b>Throughput scales linearly with S-box count and so does area</b>, which "
         "makes AES one of the cleanest area/throughput families to parameterise "
         "&mdash; and therefore a good product, because one design serves many "
         "customers."),
    ]))
    rows = []
    for sboxes, cyc in ((16, 10), (8, 20), (4, 40), (1, 160)):
        thr_1g = 128 / cyc
        rows.append([num(sboxes), num(cyc), num(thr_1g, 4),
                     num(thr_1g * 1e9 / 1e9, 4),
                     num(sboxes * 700 + 2000), num(thr_1g * 1e9 / 1e6 /
                                                   (sboxes * 700 + 2000) * 1e3, 4)])
    s.append(sweep("AES-128 area and throughput against S-box count, at 1&nbsp;GHz",
        ["S-boxes", "Cycles per block", "bits/cycle", "Gbit/s",
         "Approx. gates", "Mbit/s per kGE"], rows,
        "Gate counts are indicative (700&nbsp;GE per table-based S-box plus 2&nbsp;kGE "
        "of state and key schedule). <b>The last column is nearly constant</b>, which is "
        "the signature of a cleanly scalable block: the customer chooses a point on the "
        "line rather than a different design."))
    s.append(ex("Which AES configuration does a 400&nbsp;Gbit/s link need?",
        "MACsec on a 400&nbsp;Gbit/s Ethernet port, AES-GCM, digital logic at "
        "800&nbsp;MHz.",
        "Work out bits per cycle, then how many parallel AES cores that implies, then "
        "check the GCM multiplier alongside it.",
        [("Line rate", num(400, 3, "Gbit/s")),
         ("Clock", num(800, 3, "MHz")),
         ("Bits per cycle required", num(400e9 / 800e6, 4)),
         ("AES block size", num(128)),
         ("Blocks per cycle", num(400e9 / 800e6 / 128, 4)),
         ("Fully unrolled pipelined AES cores needed",
          num(math.ceil(400e9 / 800e6 / 128))),
         ("Pipeline stages each (one per round)", num(10)),
         ("GF(2<sup>128</sup>) multiplies per cycle (GCM)",
          num(math.ceil(400e9 / 800e6 / 128))),
         ("Dominant cost", "<b>the GCM multiplier, not AES</b>")],
        "<b>By sizing AES and forgetting the mode.</b> Counter mode parallelises "
        "perfectly &mdash; each block's keystream is independent &mdash; so AES scales "
        "by replication. The GCM authentication tag is a <i>sequential</i> "
        "multiply-accumulate in GF(2<sup>128</sup>), which does not parallelise "
        "naively; making it keep up requires the standard trick of precomputing powers "
        "of the hash key and processing several blocks at once, which costs several "
        "128-bit carry-less multipliers and their key storage. <b>At high line rates the "
        "authenticator is larger than the cipher</b>, and a datasheet that quotes only "
        "AES throughput has quoted the easy half."))

    s.append("<h2>X36.3 Public key: modular multiplication is the whole problem</h2>")
    s.append(derive("Montgomery multiplication, and why division disappears", [
        ("Modular multiplication needs <i>ab</i> mod <i>n</i>; the reduction is a "
         "division, which is expensive (Part&nbsp;X9).",
         "And it is needed thousands of times per operation."),
        ("Montgomery's idea: work with <i>a</i>&#773; = "
         "<i>aR</i> mod <i>n</i> for <i>R</i> = 2<sup><i>k</i></sup> &gt; <i>n</i>.",
         "A change of representation."),
        ("Then REDC(<i>x</i>) = (<i>x</i> + "
         "(<i>xn</i>&prime; mod <i>R</i>)<i>n</i>)/<i>R</i> reduces using only "
         "multiplications and <b>shifts</b>, because dividing by <i>R</i> is a shift.",
         "<b>The division is gone.</b> <i>n</i>&prime; is precomputed once."),
        ("Conversion in and out costs two extra multiplications, amortised over the "
         "whole exponentiation.",
         "Negligible over thousands of operations."),
        ("So an RSA engine is: a wide multiplier, an adder, a shifter, and a "
         "controller.",
         "<b>And the wide multiplier is 80&ndash;90&nbsp;% of the area</b>, which is "
         "why the literature is about multiplier architectures and not about "
         "protocols."),
    ]))
    rows = []
    for name, bits, ops in (("RSA-2048 (CRT)", 1024, 1024 * 1.5 * 2),
                            ("RSA-4096 (CRT)", 2048, 2048 * 1.5 * 2),
                            ("ECC P-256", 256, 256 * 1.3 * 12),
                            ("ECC P-384", 384, 384 * 1.3 * 12),
                            ("X25519", 255, 255 * 1.3 * 10)):
        for w in (64,):
            words = math.ceil(bits / w)
            cycles = ops * words * words / 4
        rows.append([name, num(bits), num(int(ops)), num(words),
                     num(int(cycles)), num(cycles / 5e8 * 1e3, 4)])
    s.append(sweep("Public-key work, measured in modular multiplications and cycles "
                   "(64-bit multiplier, schoolbook, 500&nbsp;MHz)",
        ["Operation", "Modulus bits", "Modular multiplies", "64-bit words",
         "Cycles (approx.)", "Time (ms)"], rows,
        "The multiplication counts are the standard estimates: square-and-multiply for "
        "RSA with the Chinese remainder theorem halving the modulus, and roughly a "
        "dozen field operations per elliptic-curve point addition. <b>The table explains "
        "the industry's migration</b>: ECC at 256 bits gives comparable security to "
        "RSA at 3072 and costs orders of magnitude less work."))
    s.append("""<div class="warn"><b>A public-key engine that is merely correct is
    dangerous.</b> The classical attacks are not on the mathematics but on the
    implementation: a square-and-multiply loop that branches on key bits leaks the key
    through timing and through power (Part&nbsp;X15), and a Montgomery ladder &mdash;
    which performs the same operations regardless of the bit &mdash; costs perhaps
    30&nbsp;% more work and removes the leak. Likewise a conditional subtraction at the
    end of a reduction is a data-dependent branch, so implementations make it
    unconditional. <b>Constant-time behaviour must be a stated requirement and a verified
    property</b>, not a side effect, and it is one of the few properties where a formal
    argument (no branch or memory access depends on secret data) is both achievable and
    genuinely convincing.</div>""")
    s.append(prob("A customer wants a crypto accelerator supporting &lsquo;all the usual "
                  "algorithms&rsquo;. How do you scope it?",
        "Refuse the phrase and replace it with a table, because the algorithms differ in "
        "cost by two orders of magnitude and &lsquo;all the usual&rsquo; hides that. "
        "Ask for, and write into the specification: <b>which algorithms and which "
        "parameter sets</b> &mdash; AES-128 and AES-256 differ only in rounds, but "
        "adding SHA-3 to a SHA-2 design is a completely separate datapath; <b>which "
        "modes</b>, since GCM costs more than the cipher at high rates; <b>what "
        "throughput for each</b>, separately, because a design sized for line-rate bulk "
        "encryption and one sized for occasional key exchange are different machines; "
        "<b>what attack model</b>, since side-channel countermeasures are a factor of "
        "two to four in area (Part&nbsp;X15) and are pointless if the part is in a locked "
        "rack; and <b>what certification</b>, because FIPS or Common Criteria brings its "
        "own known-answer tests, entropy requirements and documentation, and that cost "
        "exceeds the design cost. <b>The scoping conversation is the deliverable at this "
        "stage</b>, and a vendor who produces this table instead of a quote is "
        "demonstrating exactly the competence the customer is trying to buy."))
    return "\n".join(s)
