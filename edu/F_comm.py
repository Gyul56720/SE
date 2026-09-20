# -*- coding: utf-8 -*-
"""Volume I, Part F -- Communications links and error control coding."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line, poly


def _f_rx():
    b = []
    blk = [("AFE\nCTLE", 20, 78), ("ADC\n32-way", 112, 78), ("FFE", 204, 62),
           ("DFE", 280, 62), ("Slicer", 356, 66), ("FEC", 436, 62), ("PCS", 512, 62)]
    for n, x, w in blk:
        b.append(box(x, 36, w, 40, n.replace("\n", " "), None, 9))
        if x > 20: b.append(arr(x-14, 56, x, 56))
    b += [arr(0, 56, 20, 56), arr(578, 56, 605, 56)]
    b.append(box(190, 105, 175, 26, "sign-sign LMS adaptation", None, 8, "#eef7f2"))
    b += [arr(278, 105, 240, 76), arr(300, 105, 320, 76)]
    b.append(box(100, 105, 80, 26, "MM CDR", None, 8, "#f4eefa"))
    b += [arr(140, 105, 145, 76)]
    b.append(txt(300, 160, "Everything right of the ADC is digital IP a design house can sell",
                 9, "middle", 'font-style="italic"'))
    b.append(txt(300, 177, "Everything left of it is a hard macro tied to the process node",
                 9, "middle", 'font-style="italic"'))
    return svg(615, 190, "".join(b))


def ch_link():
    s = ['<h1 id="f1">F1. The Wireline Link, End to End</h1>']
    s.append(fig(_f_rx(), "A modern ADC-DSP receiver. The PMA/PCS boundary is also the "
                          "boundary of what can be sold as soft IP."))
    s.append("<h2>F1.1 Why the architecture looks like this</h2>")
    s.append("""<p>The structure above is not arbitrary; each block exists because a
    specific physical limit made the previous approach fail. Following that chain is the
    fastest way to understand the field.</p>""")
    s.append(tab("The forcing chain",
        ["Limit encountered", "Response", "New problem created"],
        [["Channel loss rises as &radic;<i>f</i> (skin effect)",
          "Equalise",
          "Analogue boost amplifies noise as well as signal"],
         ["CTLE alone cannot open the eye at 30 dB loss",
          "Add DFE (subtracts decided symbols, no noise gain)",
          "<b>DFE feedback must close within 1 UI</b>"],
         ["1 UI = 17.86 ps at 56 GBd; latch + summer + wire + setup &gt; 23 ps",
          "Speculate (unroll) and parallelise (sub-rate)",
          "Area grows; still not enough alone"],
         ["Baud rate cannot be raised further &mdash; the channel will not pass it",
          "<b>PAM4</b>: two bits per symbol at the same baud rate",
          "9.54 dB SNR penalty"],
         ["PAM4 raw BER is ~10<sup>&minus;4</sup>, far from 10<sup>&minus;15</sup>",
          "<b>Forward error correction (RS-FEC KP4)</b>",
          "Latency, and FEC becomes mandatory in the standard"],
         ["Analogue equalisation cannot be adapted precisely enough",
          "<b>Sample first with a fast ADC, equalise digitally</b>",
          "Time-interleaved ADC mismatch; huge digital block"],
         ["200 Gb/s per lane: even KP4 is not enough",
          "<b>Concatenated FEC</b> (outer RS-KP4 + inner Hamming)",
          "More latency; more complex decoder"]]))
    s.append("""<div class="ms"><b>This table is the single most useful thing to
    memorise about high-speed links</b>, because it lets you derive the architecture
    rather than recall it, and it identifies where a newcomer can contribute. Notice that
    the last four rows are all <i>digital</i> responses to <i>analogue</i> limits. That
    migration &mdash; from analogue equalisation to digital &mdash; is why a digital IP
    house can participate in SerDes at all, and it is still in progress.</div>""")

    s.append("<h2>F1.2 Timing budget arithmetic</h2>")
    s.append(tab("DFE first-tap loop budget at 56 GBd (1 UI = 17.86 ps)",
        ["Element", "Delay", "Comment"],
        [["Slicer (latch) clock-to-Q", "12 ps", "Regeneration plus output drive"],
         ["Summer", "8 ps", "Analogue summing node settling"],
         ["Wiring", "6 ps", "Layout-dependent; often underestimated"],
         ["Setup at next slicer", "5 ps", "&mdash;"],
         ["<b>Total loop</b>", "<b>31.0 ps</b>", "&mdash;"],
         ["<b>Available</b>", "<b>17.86 ps</b>", "1 UI"],
         ["<b>Margin</b>", "<b>&minus;13.14 ps</b>", "<b>Infeasible</b>"],
         ["Latch + wire + setup alone", "23 ps", "<b>Still exceeds 1 UI</b>"]]))
    s.append("""<div class="warn">The last row is decisive and is often missed.
    Unrolling removes the <i>summer</i> from the loop by pre-computing both hypotheses,
    but the latch, the wiring and the setup time remain &mdash; and they already exceed
    one UI. <b>Therefore no amount of speculation alone reaches 56 GBd; sub-rate
    parallelism is mandatory.</b> Stating this as a measured budget rather than an
    opinion is what turns an architecture argument into an engineering conclusion, and it
    is exactly the kind of analysis a modelling engineer is expected to produce before any
    RTL exists.</div>""")

    s.append("<h2>F1.3 Equaliser taxonomy</h2>")
    s.append(tab("Equalisers compared",
        ["Type", "Location", "Removes", "Noise effect", "Constraint"],
        [["TX FFE (de-emphasis)", "Transmitter", "Pre- and post-cursor",
          "None (pre-distortion)", "Reduces transmitted amplitude"],
         ["CTLE", "RX analogue", "Broad high-frequency loss",
          "<b>Amplifies noise</b>", "Limited number of poles/zeros"],
         ["RX FFE", "RX digital", "Pre- and post-cursor",
          "<b>Amplifies noise</b>", "Needs ADC; tap count &times; rate"],
         ["<b>DFE</b>", "RX digital", "<b>Post-cursor only</b>",
          "<b>None</b> (uses decisions)",
          "1 UI loop; <b>error propagation</b>"],
         ["MLSE / Viterbi", "RX digital", "Optimal sequence detection",
          "None", "Complexity grows as <i>M</i><sup><i>L</i></sup>"],
         ["Nonlinear (Volterra, NN)", "RX digital", "Nonlinear channel effects",
          "&mdash;", "Training, complexity; an active research area"]]))
    s.append("""<div class="ms"><b>Error propagation</b> is the price of the DFE's
    noise-free subtraction. A wrong decision is fed back and corrupts the next few
    symbols, so errors arrive in bursts rather than independently. Two consequences
    follow, and both are design decisions rather than analysis details. First, the raw
    BER is worse than an independent-error model predicts, so a link budget built on
    Q-function arithmetic alone is optimistic. Second &mdash; and more usefully &mdash;
    <b>bursty errors are exactly what a symbol-oriented code like Reed&ndash;Solomon
    handles well</b>, because several wrong bits inside one symbol still count as one
    symbol error. The choice of RS over a binary code at the FEC layer is therefore
    partly a consequence of the DFE at the equaliser layer. <b>Layers that look
    independent in a block diagram are coupled through their error statistics.</b></div>""")

    s.append("<h2>F1.4 Clock and data recovery</h2>")
    s.append(tab("CDR phase detectors",
        ["Detector", "Samples needed", "Characteristic", "Used with"],
        [["Alexander (bang-bang)", "Data + edge (2&times;)", "Binary output; nonlinear",
          "Classic NRZ links"],
         ["Hogge", "Data + edge", "Linear output", "Lower jitter, more complex"],
         ["Gardner", "2&times; oversampling", "Modulation-independent", "Wireless, some wireline"],
         ["<b>Mueller&ndash;Müller</b>", "<b>Baud-rate only</b>",
          "Uses ISI structure; needs equalised signal",
          "<b>ADC-DSP receivers</b> &mdash; no 2&times; sampling needed"],
         ["Oversampling / majority", "3&ndash;8&times;", "Simple, robust, low rate",
          "Low-speed links, FPGA"]]))
    s.append("""<div class="ms"><b>Why Mueller&ndash;Müller won in ADC-based receivers.</b>
    At 56 GBd, sampling at 2&times; the baud rate means 112 GS/s &mdash; roughly doubling
    the ADC's power and area, which are already the dominant cost. MM extracts a timing
    error from baud-rate samples alone by exploiting the asymmetry of the equalised pulse
    response: it drives the sampling phase to the point where the first pre-cursor and
    first post-cursor are equal. The subtlety is that <b>MM's lock point depends on the
    equaliser</b>, so CDR and equaliser adaptation interact; a modelling engineer who
    simulates them independently will not see the interaction, and joint convergence
    failures are a classic late-stage surprise. <b>Model the loops together or state
    explicitly that you have not.</b></div>""")
    return "\n".join(s)


def ch_fec():
    s = ['<h1 id="f2">F2. Error Control Coding</h1>']
    s.append("<h2>F2.1 The coding landscape</h2>")
    s.append(tab("Codes by structure and application",
        ["Family", "Alphabet", "Decoding", "Strength", "Typical use"],
        [["Parity / SECDED", "binary", "syndrome", "1-bit correct, 2-bit detect",
          "<b>Memory ECC</b>, register files"],
         ["Hamming / extended", "binary", "syndrome", "&mdash;", "Inner code in concatenation"],
         ["BCH", "binary", "BM + Chien", "<i>t</i> bit errors", "Flash, optical"],
         ["<b>Reed&ndash;Solomon</b>", "GF(2<sup><i>m</i></sup>)",
          "syndrome&rarr;BM&rarr;Chien&rarr;Forney", "<i>t</i> <b>symbol</b> errors &mdash; burst tolerant",
          "<b>Ethernet KP4</b>, storage, DVB"],
         ["Convolutional", "binary", "<b>Viterbi</b> (ML)", "Random errors", "Legacy wireless, satellite"],
         ["Turbo", "binary", "iterative BCJR", "Near capacity", "3G/4G"],
         ["<b>LDPC</b>", "binary", "belief propagation (min-sum)", "Near capacity",
          "<b>5G NR data</b>, Wi-Fi, 802.3ca, NAND"],
         ["Polar", "binary", "SC / SC-List", "Provably capacity-achieving", "5G control"],
         ["Fountain (LT, Raptor)", "binary", "BP", "Rateless", "Broadcast, storage"],
         ["<b>Concatenated</b>", "mixed", "inner then outer",
          "Burst + random", "<b>802.3dj 224G</b>, deep space"]]))
    s.append("""<div class="ms"><b>Choosing a code is choosing an error model.</b> A
    binary code assumes errors are independent bit flips; a symbol code assumes they
    cluster. Getting this wrong is expensive in both directions &mdash; a strong binary
    code performs poorly on bursts, and an RS code wastes redundancy on isolated bit
    errors. The correct procedure is to <b>measure the error statistics of the actual
    slicer output</b>, including DFE error propagation and any burst noise, and choose
    accordingly. In concatenated schemes the division of labour is explicit: the inner
    code cleans up random errors and the outer code mops up the bursts that the inner
    decoder's own failures produce. <b>The inner decoder's failure mode is the outer
    decoder's input distribution</b> &mdash; a subtlety that must be in the system
    model.</div>""")

    s.append("<h2>F2.2 Reed&ndash;Solomon in detail</h2>")
    s.append(tab("RS decoder pipeline",
        ["Stage", "Computation", "Parallelism", "Hardware character"],
        [["Syndrome", "<i>S<sub>i</sub></i> = <i>r</i>(&alpha;<sup>fcr+<i>i</i></sup>), <i>i</i>=0&hellip;2<i>t</i>&minus;1",
          "<b>Fully parallel</b> (2<i>t</i> independent evaluations)",
          "2<i>t</i> constant-multiplier accumulators"],
         ["Key equation (BM)", "Find &sigma;(<i>x</i>)",
          "<b>Sequential</b> &mdash; 2<i>t</i> dependent iterations",
          "<b>This is the critical path</b>"],
         ["Chien search", "Roots of &sigma;(<i>x</i>)", "Parallel over positions",
          "<i>n</i>/<i>P</i> cycles"],
         ["Forney", "<i>e<sub>j</sub></i> = &omega;/&sigma;&prime; evaluated at roots",
          "Parallel", "Needs GF inversion (ROM or Itoh&ndash;Tsujii)"],
         ["Correction", "XOR into the buffer", "Parallel", "Requires the codeword buffered"]]))
    s.append("""<div class="ms"><b>The Berlekamp&ndash;Massey iteration is the same kind
    of obstacle as the DFE loop and the OOO wakeup loop.</b> Each iteration depends on the
    previous discrepancy, so it cannot be pipelined away. The standard remedies mirror
    those in the other two cases: <i>inversionless</i> BM removes the GF inversion from
    the loop (replacing it with an extra multiplication), and <i>reformulated</i> BM
    restructures the recurrence so that fewer operations sit inside it. A design house
    that recognises this pattern can move an engineer from a SerDes project to an FEC
    project and expect them to be productive quickly, because the underlying problem is
    identical.</div>""")
    s.append(tab("RS decoder behaviour that must appear in the datasheet",
        ["Condition", "Behaviour", "Why it must be documented"],
        [["&le; <i>t</i> symbol errors", "<b>Always corrected</b>", "The guarantee being sold"],
         ["&gt; <i>t</i> errors", "Detected <b>or</b> mis-corrected",
          "<b>Not all are detected.</b> Claiming otherwise is false"],
         ["Mis-correction probability", "Roughly <i>n</i><sup><i>t</i></sup>/(<i>t</i>! 2<sup><i>m</i>(<i>n</i>&minus;<i>k</i>&minus;<i>t</i>)</sup>)",
          "Customers at 10<sup>&minus;15</sup> FLR need this number"],
         ["Erasure decoding", "Corrects up to <i>n</i>&minus;<i>k</i> erasures",
          "If the receiver can flag unreliable symbols, capacity doubles"],
         ["Latency", "Fixed, = pipeline depth", "Real-time systems need the number"]]))
    s.append("""<div class="warn"><b>&ldquo;All errors beyond <i>t</i> are detected&rdquo;
    is a false statement that appears in datasheets.</b> A received word with more than
    <i>t</i> errors may land within distance <i>t</i> of a <i>different</i> valid
    codeword, in which case the decoder confidently produces the wrong answer. A measured
    illustration on a small code, RS(15,9) with <i>t</i>&nbsp;=&nbsp;3: injecting exactly
    four symbol errors 120 times gave <b>117 detected failures and 3 mis-corrections</b>
    &mdash; never a correct recovery, but not always a detection either. An honest
    specification states the mis-correction probability; a verification plan must
    distinguish the three outcomes (corrected / detected / mis-corrected) rather than
    counting pass and fail.</div>""")

    s.append("<h2>F2.3 LDPC</h2>")
    s.append(tab("LDPC decoding choices",
        ["Choice", "Options", "Effect"],
        [["Message form", "Probability vs <b>log-likelihood ratio</b>",
          "LLR turns products into sums &mdash; essential in hardware"],
         ["Check-node update", "Sum-product (tanh) vs <b>min-sum</b>",
          "Min-sum loses ~0.5 dB, removes transcendental functions"],
         ["Correction", "Normalised or offset min-sum", "Recovers most of the loss for one constant"],
         ["Schedule", "Flooding vs <b>layered</b>",
          "Layered halves the iteration count; creates pipeline hazards"],
         ["Parallelism", "Fully parallel / row / block",
          "Quasi-cyclic structure enables block parallelism"],
         ["Early termination", "Syndrome check per iteration",
          "<b>Large average power saving</b>; worst-case latency unchanged"]]))
    s.append("""<div class="warn"><b>LDPC's fixed-point rule is the opposite of the
    CIC's.</b> An LLR's sign carries the hard decision. If an LLR wraps in two's
    complement, a strong belief in &ldquo;0&rdquo; becomes a strong belief in
    &ldquo;1&rdquo;, and the decoder does not merely lose precision &mdash; it is actively
    misled, and iteration amplifies the damage. Measured on a 5G NR base-graph decoder,
    reducing the message width by three bits gave BLER&nbsp;0.250 with saturation and
    <b>1.000 &mdash; complete failure &mdash; with wrap-around</b>. Meanwhile the CIC
    filter of Chapter E1 <i>requires</i> wrap-around to function. <b>There is no global
    "correct" overflow policy; it is a per-block property that must be stated in the
    specification and enforced by tests.</b></div>""")
    s.append("""<div class="ms"><b>Layered scheduling and pipeline hazards.</b> In a
    layered decoder, layer <i>j</i> may need a variable node that layer <i>i</i> is still
    updating, forcing a stall whose length depends on the pipeline depth <i>D</i> and on
    the layer ordering. It is tempting to optimise the ordering against a closed-form
    stall count, but that formula is only an <b>upper bound</b>: it assumes every
    potential conflict costs a full stall. A measured comparison on 5G NR base graph 1 at
    <i>D</i>&nbsp;=&nbsp;4 gave the formula 108 stall cycles while a cycle-accurate model
    and the RTL both gave <b>80</b> &mdash; the difference between a 70.1% and a 62.0%
    efficiency loss. <b>Optimising a schedule against the wrong objective function finds
    the wrong schedule.</b> Build the cycle-accurate model first; it is a day of work and
    it changes the answer.</div>""")
    return "\n".join(s)
