# -*- coding: utf-8 -*-
"""Volume I, Part X29 -- LDPC and polar codes, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_tanner():
    b = []
    vx = [40, 90, 140, 190, 240]
    cx = [65, 140, 215]
    for x in vx:
        b.append(f'<circle cx="{x}" cy="34" r="9" fill="#fff" stroke="#000" '
                 f'stroke-width="1.1"/>')
    for x in cx:
        b.append(f'<rect x="{x-9}" y="103" width="18" height="18" fill="#eef2f7" '
                 f'stroke="#000" stroke-width="1.1"/>')
    edges = [(0, 0), (1, 0), (2, 0), (1, 1), (2, 1), (3, 1), (2, 2), (3, 2), (4, 2)]
    for v, c in edges:
        b.append(line(vx[v], 43, cx[c], 103, w=0.7))
    b.append(txt(280, 38, "variable nodes", 8))
    b.append(txt(280, 116, "check nodes", 8))
    b.append(txt(150, 148, "Decoding passes messages along the edges. A short cycle in "
                           "this graph", 9, "middle"))
    b.append(txt(150, 162, "makes a message come back as if it were independent "
                           "evidence.", 9, "middle", 'font-style="italic"'))
    return svg(370, 172, "".join(b))


def ch_ldpc():
    s = ['<h1 id="x29">X29. LDPC and Polar Codes, Worked</h1>']
    s.append("""<p>These are the codes that reach within a fraction of a decibel of
    capacity and they are, between them, the error correction of 5G, Wi-Fi, high-speed
    Ethernet and modern storage. Their hardware is dominated by memory and interconnect
    rather than arithmetic, which makes them an unusually good case study in the gap
    between an algorithm's operation count and its silicon.</p>""")
    s.append(fig(_f_tanner(), "A Tanner graph. The code is the graph; the decoder is "
                              "message passing on it."))

    s.append("<h2>X29.1 Belief propagation, and the approximation everyone ships</h2>")
    s.append(derive("From the check equation to the min-sum rule", [
        ("A check node enforces that the XOR of its connected bits is zero.",
         "Parity check."),
        ("The log-likelihood ratio of a XOR of independent bits satisfies "
         "tanh(<i>L</i>/2) = &Pi; tanh(<i>L<sub>i</sub></i>/2).",
         "The standard identity: probabilities of a parity multiply in the tanh "
         "domain."),
        ("So the exact check update is "
         "<i>L</i> = 2&nbsp;tanh<sup>&minus;1</sup>(&Pi; tanh(<i>L<sub>i</sub></i>/2)).",
         "<b>Accurate and unimplementable</b>: a transcendental function per edge, at "
         "hundreds of gigabits per second."),
        ("Because tanh saturates, the product is dominated by its smallest term.",
         "Every factor with large |<i>L</i>| is close to &plusmn;1."),
        ("<b>Min-sum:</b> <i>L</i> &asymp; (&Pi; sgn <i>L<sub>i</sub></i>) &middot; "
         "min |<i>L<sub>i</sub></i>|.",
         "<b>A comparison and a sign product &mdash; no multipliers, no tables.</b>"),
        ("Min-sum overestimates the magnitude, so it is scaled or offset: "
         "&alpha;&middot;min or max(min&nbsp;&minus;&nbsp;&beta;, 0).",
         "<b>One constant recovers most of the loss</b>, and X29.2 measures how much."),
    ]))
    rng = np.random.default_rng(31)

    def make_code(n, dv, dc, seed):
        m = n * dv // dc
        r = np.random.default_rng(seed)
        H = np.zeros((m, n), dtype=np.int8)
        slots = np.repeat(np.arange(n), dv)
        r.shuffle(slots)
        for i, v in enumerate(slots):
            H[i % m, v] ^= 1
        return H

    def decode(H, llr, iters, rule, alpha=1.0, beta=0.0):
        m, n = H.shape
        E = [np.nonzero(H[i])[0] for i in range(m)]
        msg = {}
        for i in range(m):
            for j in E[i]:
                msg[(i, j)] = 0.0
        tot = llr.copy()
        for _ in range(iters):
            for i in range(m):
                vals = [tot[j] - msg[(i, j)] for j in E[i]]
                a = np.abs(vals)
                sg = np.prod(np.sign(vals) + (np.array(vals) == 0))
                for k, j in enumerate(E[i]):
                    others = np.delete(a, k)
                    so = sg * (1 if np.sign(vals[k]) >= 0 else -1)
                    if rule == "minsum":
                        v = so * alpha * float(others.min())
                    else:
                        v = so * max(float(others.min()) - beta, 0.0)
                    msg[(i, j)] = v
            tot = llr.copy()
            for (i, j), v in msg.items():
                tot[j] += v
        return np.sign(tot)

    n, dv, dc = 96, 3, 6
    H = make_code(n, dv, dc, 5)
    rows = []
    for snr_db in (1, 2, 3, 4):
        sigma = 10 ** (-snr_db / 20)
        trials = 60
        errs = {"minsum": 0, "scaled": 0, "offset": 0}
        bits = 0
        for t in range(trials):
            x = np.ones(n)
            y = x + rng.normal(0, sigma, n)
            llr = 2 * y / sigma ** 2
            bits += n
            for name, rule, a, b_ in (("minsum", "minsum", 1.0, 0.0),
                                      ("scaled", "minsum", 0.75, 0.0),
                                      ("offset", "offset", 1.0, 0.5)):
                d = decode(H, llr.copy(), 8, rule, a, b_)
                errs[name] += int(np.sum(d != x))
        rows.append([num(snr_db), num(float(np.mean(np.sign(llr) != 1)), 3),
                     num(errs["minsum"] / bits, 3),
                     num(errs["scaled"] / bits, 3),
                     num(errs["offset"] / bits, 3)])
    s.append(sweep("Measured bit error rate of a (96,&nbsp;<i>d<sub>v</sub></i>=3, "
                   "<i>d<sub>c</sub></i>=6) LDPC code under three check-node rules, "
                   "8 iterations, 60 trials per point",
        ["SNR (dB)", "Uncoded (last trial)", "Plain min-sum",
         "Scaled min-sum (&alpha;=0.75)", "Offset min-sum (&beta;=0.5)"], rows,
        "Decoded by a direct implementation of the message-passing rules, all-ones "
        "codeword. <b>The scaling and offset constants cost one multiplier or one "
        "subtractor in the whole decoder</b> and recover a measurable part of the loss; "
        "this is the cheapest improvement available in an LDPC decoder and it is "
        "universal in shipping designs."))
    s.append("""<div class="ms"><b>Why the all-ones codeword is a legitimate test and
    not a shortcut.</b> For a linear code over a symmetric channel, the error probability
    is independent of the transmitted codeword: the decoder's behaviour depends only on
    the noise realisation relative to the sent word, and the code's symmetry makes every
    word equivalent. So simulating the all-zero (or all-ones, under the sign convention
    used here) word is exact, not approximate, and it removes the encoder from the
    simulation entirely. <b>The condition to check is that the decoder is genuinely
    symmetric</b> &mdash; a quantised implementation with an asymmetric saturation or a
    biased rounding rule is not, and then the shortcut becomes invalid. That is a real
    trap in fixed-point LDPC verification and a good reason to run a full encoder at
    least once against the shortcut.</div>""")

    s.append("<h2>X29.2 Where the hardware cost actually is</h2>")
    rows = []
    for n_, rate, dv_ in ((648, 0.5, 3), (1944, 0.5, 3), (8448, 0.8, 4), (26112, 0.86, 4)):
        m_ = int(n_ * (1 - rate))
        edges = n_ * dv_
        rows.append([num(n_), num(rate, 3), num(m_), num(edges),
                     num(edges * 6 / 8 / 1024, 5), num(edges * 2)])
    s.append(sweep("LDPC decoder memory and interconnect, 6-bit messages",
        ["Block length <i>n</i>", "Rate", "Checks <i>m</i>", "Edges",
         "Message memory (kB)", "Message accesses per iteration"], rows,
        "The edge count sets everything. <b>A decoder is a memory with comparators "
        "attached</b>: the message memory dominates area, and moving those messages "
        "between the variable and check phases dominates power. Arithmetic &mdash; "
        "comparisons and adds &mdash; is almost free by comparison."))
    s.append(tab("Decoder architectures",
        ["Architecture", "Parallelism", "Memory", "Throughput", "Where used"],
        [["Fully parallel", "Every edge has wires", "Registers",
          "<b>Highest</b>", "Short codes; the interconnect is the limit and routing "
          "congestion sets the block length"],
         ["<b>Layered / row-parallel</b>",
          "One block-row of the parity matrix at a time",
          "SRAM banks", "<b>High; roughly halves the iterations needed</b>",
          "<b>The standard for 5G and Wi-Fi quasi-cyclic codes</b>"],
         ["Serial", "One check at a time", "Single memory", "Low",
          "Area-critical, low-rate applications"],
         ["Flooding", "All checks then all variables",
          "Two message arrays", "Moderate",
          "Simple; needs about twice the iterations of layered"]]))
    s.append("""<div class="bs"><b>Why quasi-cyclic codes are the ones that get
    standardised.</b> A quasi-cyclic parity-check matrix is built from circulant blocks
    &mdash; identity matrices shifted by a stored amount. Three consequences follow, and
    all three are hardware consequences rather than coding ones. The matrix is described
    by a small table of shift values instead of a full incidence list, so the code fits in
    a few hundred bytes of ROM. A whole block-row can be processed in parallel with
    perfectly regular addressing, because a circulant is a barrel shifter. And the same
    hardware serves many block lengths by changing the circulant size, which is what lets
    one decoder cover a standard's whole rate and length family. <b>The structure exists
    for the decoder's benefit, at a small cost in threshold performance</b>, and that
    trade is why every modern LDPC standard is quasi-cyclic.</div>""")

    s.append("<h2>X29.3 Polar codes, and why they won the control channel</h2>")
    s.append(derive("Channel polarisation in one page", [
        ("Combine two uses of a channel <i>W</i> as "
         "<i>u</i><sub>1</sub>&oplus;<i>u</i><sub>2</sub> and <i>u</i><sub>2</sub>.",
         "The basic 2&times;2 transform."),
        ("Decoding <i>u</i><sub>1</sub> first sees a <i>worse</i> channel; decoding "
         "<i>u</i><sub>2</sub> given <i>u</i><sub>1</sub> sees a <i>better</i> one.",
         "The mutual information is conserved but redistributed: "
         "<i>I</i>(<i>W</i><sup>&minus;</sup>) + <i>I</i>(<i>W</i><sup>+</sup>) = "
         "2<i>I</i>(<i>W</i>)."),
        ("Recurse <i>n</i> times over 2<sup><i>n</i></sup> uses.",
         "The fraction of synthetic channels that are nearly perfect tends to "
         "<i>I</i>(<i>W</i>) and the rest tend to useless."),
        ("<b>Put information on the good channels and freeze the rest to known "
         "values.</b>",
         "<b>That is the entire code construction</b> &mdash; no search, no "
         "optimisation, and it provably achieves capacity as the length grows."),
        ("Decoding is successive cancellation: decide bits in order, using earlier "
         "decisions.",
         "<b>Inherently serial</b>, which is the hardware problem; latency grows with "
         "block length even though the operation count is <i>N</i>log<i>N</i>."),
        ("Adding a CRC and keeping <i>L</i> candidate paths (SCL) closes most of the "
         "gap to maximum likelihood.",
         "<b>At <i>L</i>&times; the memory and the sorting network</b>, which is what "
         "5G specifies for control channels."),
    ]))
    rows = []
    for N_ in (128, 256, 512, 1024):
        for L in (1, 2, 4, 8):
            lat = 2 * N_ - 2
            rows.append([num(N_), num(L), num(lat), num(L * N_ * 6 / 8, 5),
                         num(int(math.log2(N_)) * L)])
    s.append(sweep("Successive-cancellation list decoding cost",
        ["<i>N</i>", "List size <i>L</i>", "SC latency (cycles, unoptimised)",
         "Path memory (bytes, 6-bit LLR)", "Sorter comparisons per stage"], rows,
        "<b>Latency is the polar decoder's problem and list size is its area "
        "problem.</b> The published architectural work is almost entirely about "
        "shortening the serial schedule &mdash; recognising sub-blocks that can be "
        "decoded in one step rather than bit by bit."))
    s.append(prob("5G uses polar codes for control channels and LDPC for data. Why "
                  "not one code for both?",
        "Because the two channels have opposite requirements and each code is better at "
        "one of them. <b>Control messages are short</b> &mdash; tens of bits &mdash; and "
        "at those lengths LDPC's performance degrades badly, because the Tanner graph "
        "cannot avoid short cycles and the asymptotic analysis that makes LDPC excellent "
        "does not apply. Polar codes with CRC-aided list decoding are close to optimal at "
        "short lengths, and their <b>error detection</b> is excellent, which matters "
        "enormously for control: a mis-decoded control message is worse than a detected "
        "failure, exactly as Part&nbsp;X5 argued for Reed&ndash;Solomon. <b>Data blocks "
        "are long and need throughput</b>, and there LDPC's parallel decoding wins "
        "decisively while polar's serial successive cancellation would set a latency "
        "floor. <b>The standard is not being indecisive; it is applying the right tool at "
        "each length</b>, and the lesson generalises: code choice is dominated by block "
        "length and by whether detection or throughput is the binding requirement."))
    return "\n".join(s)
