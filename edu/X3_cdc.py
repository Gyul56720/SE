# -*- coding: utf-8 -*-
"""Volume I, Part X3 -- Metastability, synchronisers and CDC, worked.

The MTBF formula is quoted constantly and computed rarely.  It is an exponential
in a quantity the designer controls, which means intuition about it is unreliable
and arithmetic about it is decisive.  This part computes it.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

YEAR = 365.25 * 24 * 3600


def _f_sync():
    b = []
    b += [txt(16, 30, "async", 9), arr(16, 40, 56, 40)]
    for i, x in enumerate((56, 128, 200)):
        b += [box(x, 26, 54, 30, f"FF{i+1}", None, 9)]
        if i:
            b += [arr(x - 18, 41, x, 41)]
        b += [line(x + 27, 56, x + 27, 78, w=0.8)]
    b += [arr(254, 41, 294, 41), txt(300, 44, "sync", 9)]
    b += [line(56, 78, 254, 78, w=0.9), txt(155, 92, "clk", 9, "middle")]
    b += [txt(83, 20, "may go", 7, "middle"), txt(83, 12, "metastable", 7, "middle")]
    b += [txt(155, 20, "resolves during", 7, "middle"), txt(155, 12, "one full cycle", 7, "middle")]
    b += [txt(227, 20, "usually clean", 7, "middle")]
    b += [txt(170, 116, "Each added stage multiplies the MTBF by "
                        "e<tspan baseline-shift='super' font-size='6'>T/&tau;</tspan> "
                        "&mdash; the gain is exponential, not linear.",
              9, "middle", 'font-style="italic"')]
    return svg(350, 128, "".join(b))


def lmtbf(T, tau, T0, fc, fd):
    """log10 of the mean time between synchroniser failures, in seconds.

    Computed in the log domain deliberately.  The exponent T/tau reaches several
    hundred for an ordinary 100 MHz two-flop synchroniser, and a direct
    exponential overflows IEEE double long before the design space is
    exhausted -- which is itself worth noticing: the quantity being chosen
    routinely spans hundreds of decades, so intuition calibrated on linear
    quantities is useless here.
    """
    return T / tau / math.log(10) - math.log10(T0 * fc * fd)


def dec(x):
    """Render a log10 value as a readable power of ten."""
    return f"10<sup>{x:.1f}</sup>"


YEARLOG = math.log10(YEAR)


def ch_cdc():
    s = ['<h1 id="x3">X3. Metastability and Clock-Domain Crossing, Worked</h1>']
    s.append("""<p>A flip-flop sampled while its input is changing may enter a
    metastable state whose resolution time is unbounded. &lsquo;Unbounded&rsquo; is the
    word that matters: there is no settling time that guarantees correctness, only a
    settling time that makes failure rare enough. Designing a synchroniser therefore means
    choosing a number of years, which is a much more concrete decision than it first
    sounds.</p>""")
    s.append(fig(_f_sync(), "A two-flop synchroniser. The second flop's job is not to "
                            "clean up the signal &mdash; it is to give the first flop a "
                            "whole clock period in which to resolve."))

    s.append("<h2>X3.1 The MTBF expression and what each symbol is</h2>")
    s.append(derive("Where the exponential comes from", [
        ("A metastable flop's output separates from the balance point exponentially: "
         "&Delta;<i>V</i>(<i>t</i>) = &Delta;<i>V</i><sub>0</sub> "
         "e<sup><i>t</i>/&tau;</sup>.",
         "Small-signal analysis of the cross-coupled pair: the loop has a positive real "
         "pole, and &tau; is its inverse."),
        ("Resolution by time <i>t</i> requires &Delta;<i>V</i><sub>0</sub> larger than "
         "some &Delta;<i>V</i><sub>min</sub>e<sup>&minus;<i>t</i>/&tau;</sup>.",
         "Invert the exponential."),
        ("&Delta;<i>V</i><sub>0</sub> is proportional to how far the data edge was from "
         "the sampling point, and that offset is uniformly distributed.",
         "Asynchronous input: no phase relationship, so all offsets equally likely."),
        ("So P(unresolved after <i>t</i>) &prop; e<sup>&minus;<i>t</i>/&tau;</sup>, "
         "with a constant <i>T</i><sub>0</sub> carrying the aperture width.",
         "Uniform measure times an exponentially shrinking target window."),
        ("Failures occur at rate <i>f</i><sub>clk</sub><i>f</i><sub>data</sub>"
         "<i>T</i><sub>0</sub>e<sup>&minus;<i>t</i><sub>r</sub>/&tau;</sup>.",
         "Each clock edge is a trial; each data edge supplies an opportunity."),
        ("<b>MTBF = e<sup><i>t</i><sub>r</sub>/&tau;</sup> &frasl; "
         "(<i>T</i><sub>0</sub> <i>f</i><sub>clk</sub> <i>f</i><sub>data</sub>)</b>",
         "Reciprocal of the rate. <b>&tau; and <i>T</i><sub>0</sub> are library "
         "measurements</b>, not universal constants; ask the vendor for them."),
    ]))
    tau, T0 = 20e-12, 10e-12
    rows = []
    for st in (1, 2, 3, 4):
        for f in (100e6, 500e6, 1e9):
            Tclk = 1 / f
            tr = st * Tclk - 0.12e-9      # resolution time available, less cq+su
            m = lmtbf(tr, tau, T0, f, f / 10)
            rows.append([st, num(f / 1e6, 3), num(tr * 1e12, 4),
                         dec(m), dec(m - YEARLOG)])
    s.append(sweep("MTBF against synchroniser depth and frequency "
                   "(&tau;&nbsp;=&nbsp;20&nbsp;ps, <i>T</i><sub>0</sub>&nbsp;=&nbsp;"
                   "10&nbsp;ps, data toggling at <i>f</i>/10)",
        ["Stages", "<i>f</i><sub>clk</sub> (MHz)", "Resolution time (ps)",
         "MTBF (s)", "MTBF (years)"], rows,
        "The third column is linear in the number of stages and the fourth is "
        "exponential in the third. That is the whole design space."))
    s.append(plot([1, 2, 3, 4],
                  [(f"{int(f/1e6)} MHz",
                    [lmtbf(st / f - 0.12e-9, tau, T0, f, f / 10) - YEARLOG
                     for st in (1, 2, 3, 4)])
                   for f in (100e6, 500e6, 1e9)],
                  "synchroniser stages", "log10 MTBF (years)",
                  "MTBF in years, log scale, against depth. A straight line on this axis "
                  "is the exponential: each stage adds the same number of decades, and "
                  "that number shrinks as the period shrinks."))
    s.append(ex("Choosing the depth for a 1&nbsp;GHz interface",
        "&tau;&nbsp;=&nbsp;20&nbsp;ps, <i>T</i><sub>0</sub>&nbsp;=&nbsp;10&nbsp;ps, "
        "<i>f</i><sub>clk</sub>&nbsp;=&nbsp;1&nbsp;GHz, data edges at 100&nbsp;MHz. "
        "Setup plus clock-to-Q consume 120&nbsp;ps of each period.",
        "Compute MTBF for two and three stages, then compare against a target. A "
        "reasonable target for a part shipping in volume is <i>not</i> &lsquo;longer "
        "than the product's life&rsquo; &mdash; it is longer than the product's life "
        "multiplied by the number of units in the field.",
        [("Resolution time, 2 stages", num((2e-9 - 0.12e-9) * 1e12, 4, "ps")),
         ("MTBF, 2 stages",
          dec(lmtbf(2e-9 - 0.12e-9, tau, T0, 1e9, 1e8) - YEARLOG) + " years"),
         ("MTBF, 3 stages",
          dec(lmtbf(3e-9 - 0.12e-9, tau, T0, 1e9, 1e8) - YEARLOG) + " years"),
         ("2-stage MTBF across a 10-million-unit fleet",
          dec(lmtbf(2e-9 - 0.12e-9, tau, T0, 1e9, 1e8) - YEARLOG - 7) + " years"),
         ("Same, but with &tau; doubled at the cold/low-V corner",
          dec(lmtbf(2e-9 - 0.12e-9, 2 * tau, T0, 1e9, 1e8) - YEARLOG - 7) + " years")],
        "<b>By evaluating the MTBF for one chip.</b> The failure rate is additive over "
        "units, so a fleet of ten million divides the MTBF by ten million. A synchroniser "
        "that is comfortable in the lab can produce a field return every few weeks. The "
        "second common error is to use &tau; from a different library, or from a "
        "conference slide: &tau; varies by a factor of several between libraries and "
        "corners, and it sits in an exponent."))
    s.append("""<div class="warn"><b>&tau; degrades at low voltage and cold, and the
    degradation is exponential in effect.</b> A synchroniser characterised at nominal may
    have a &tau; 1.5&ndash;2&times; larger at the low-voltage corner; with
    <i>t</i><sub>r</sub>/&tau; halved, an MTBF of 10<sup>9</sup> years becomes
    10<sup>4</sup>. <b>Evaluate the MTBF at the worst corner for &tau;, not the typical
    one</b> &mdash; and note that this is a corner the timing tool does not analyse for
    you, because the synchroniser path is one you told it to ignore.</div>""")

    s.append("<h2>X3.2 A synchroniser is not a CDC solution</h2>")
    s.append("""<p>Two flops make <i>one bit</i> safe. They do nothing for the problem
    that actually causes CDC bugs, which is that several bits crossing together may be
    sampled on different edges and produce a value that never existed in the source
    domain.</p>""")
    rng = np.random.default_rng(5)
    trials = 200000
    rows = []
    for nb in (1, 2, 4, 8, 16):
        # a counter incrementing; sample each bit with independent +-1 cycle skew
        v = rng.integers(0, 1 << nb, trials)
        nxt = (v + 1) % (1 << nb)
        pick = rng.integers(0, 2, (trials, nb))
        bits_old = ((v[:, None] >> np.arange(nb)) & 1)
        bits_new = ((nxt[:, None] >> np.arange(nb)) & 1)
        mixed = np.where(pick == 1, bits_new, bits_old)
        val = (mixed * (1 << np.arange(nb))).sum(1)
        bad = float(np.mean((val != v) & (val != nxt)))
        # gray
        g, gn = v ^ (v >> 1), nxt ^ (nxt >> 1)
        gb_o = ((g[:, None] >> np.arange(nb)) & 1)
        gb_n = ((gn[:, None] >> np.arange(nb)) & 1)
        gm = np.where(pick == 1, gb_n, gb_o)
        gval = (gm * (1 << np.arange(nb))).sum(1)
        gbad = float(np.mean((gval != g) & (gval != gn)))
        rows.append([nb, num(bad, 3), num(gbad, 3),
                     num(int(bad * trials)), num(int(gbad * trials))])
    s.append(sweep("Measured probability that a multi-bit crossing yields a value that "
                   "existed in neither the old nor the new state, binary vs. Gray coding",
        ["Bits", "P(bogus), binary", "P(bogus), Gray", "Bogus samples, binary",
         "Bogus samples, Gray"], rows,
        "200&#8239;000 trials per row, each bit independently taking the old or the new "
        "value. Gray coding makes the bogus count exactly zero, because consecutive Gray "
        "codes differ in one bit and a single bit can only be old or new."))
    s.append(ex("Why Gray code is not optional in an asynchronous FIFO",
        "An 8-bit write pointer crossing into the read domain, incrementing every "
        "cycle at 500&nbsp;MHz.",
        "Take the measured binary bogus probability from the row above and turn it into "
        "a rate. Then ask what a bogus pointer does.",
        [("P(bogus sample), 8 bits binary, measured above", rows[3][1]),
         ("Crossings per second", num(5e8)),
         ("Bogus pointer values per second (order of magnitude)",
          "10<sup>7</sup>&ndash;10<sup>8</sup>"),
         ("Consequence of one bogus write pointer",
          "reader sees a wrong depth &mdash; underflow or overflow"),
         ("Consequence with Gray coding", "none: the value is old or new, both safe")],
        "<b>By assuming the synchroniser flops fix it.</b> They do &mdash; per bit. The "
        "failure is a <i>composition</i> failure across bits, and no amount of depth on "
        "individual bits addresses it. The other frequent error is to Gray-code the "
        "pointer and then do arithmetic on it in the destination domain before converting "
        "back to binary; Gray codes do not add, and a comparison of Gray values is not a "
        "comparison of the numbers they encode except in the specific equality test that "
        "the standard FIFO empty/full logic uses."))
    s.append(tab("CDC schemes and what each is actually for",
        ["Scheme", "Carries", "Throughput", "Latency", "Fails if"],
        [["Two-flop synchroniser", "one bit, slowly changing",
          "&lt; 1 per 2 destination cycles", "2&ndash;3 destination cycles",
          "The bit changes faster than it is sampled (<b>pulse loss</b>)"],
         ["Pulse / toggle synchroniser", "an event",
          "1 per 3&ndash;4 cycles", "3&ndash;4 cycles",
          "Events arrive closer together than that"],
         ["<b>Gray-coded async FIFO</b>", "<b>a data stream</b>",
          "<b>1 word per cycle</b>", "2&ndash;4 cycles each way",
          "Depth is wrong for the rate mismatch &mdash; a <i>performance</i> failure, "
          "not a correctness one"],
         ["Handshake (req/ack)", "a word, safely", "1 per ~5 cycles round trip",
          "high", "Nothing, but it is slow; used for configuration, not data"],
         ["MUX recirculation / data hold", "a bus with a synchronised enable",
          "1 per enable", "2&ndash;3 cycles",
          "The enable and the data are not guaranteed stable together"],
         ["Common clock, no crossing at all", "everything", "&mdash;", "0",
          "<b>Consider this first.</b> Many crossings exist only because nobody "
          "questioned the clock plan"]]))
    s.append("""<div class="ms"><b>The pulse-loss trap, stated precisely.</b> A
    synchroniser samples; it does not detect edges. If the source asserts a signal for one
    source-clock cycle and the destination clock is slower, the destination may simply
    never see it. The rule is that a level crossing into a slower domain must be held for
    at least one full destination period plus the source's own uncertainty &mdash; in
    practice three destination cycles is the usual specification. When the ratio is not
    known at design time, because the customer sets both frequencies, <b>a level crossing
    is unimplementable and the crossing must be a toggle or a handshake.</b> This is a
    frequent finding in IP integration: the block worked at the vendor's ratio and fails
    at the customer's.</div>""")
    s.append(prob("A configuration register is written in a 100&nbsp;MHz APB domain and "
                  "read by a 1&nbsp;GHz datapath. The 32 bits change together. What is "
                  "the correct structure, and what is wrong with synchronising each bit?",
        "Synchronising each bit independently is wrong for the reason measured above: "
        "the datapath can observe a mixture of old and new fields. The standard structure "
        "is <b>data hold with a synchronised enable</b>: the APB domain writes the 32 "
        "bits into a holding register and then toggles a single control bit; that one bit "
        "crosses through a two-flop synchroniser; the datapath samples the 32 bits only "
        "when it sees the toggle. The data bits themselves never need synchronisers "
        "because they are guaranteed stable for several destination cycles before and "
        "after the sampling point &mdash; a guarantee that must be <b>written into the "
        "constraint file as a <code>set_max_delay -datapath_only</code></b>, or the tool "
        "will either flag it or, worse, silently optimise the holding register away."))
    s.append(prob("A reviewer says &lsquo;add a third flop, it is nearly free&rsquo;. "
                  "When is that the wrong advice?",
        "When the crossing's problem is not metastability. A third flop buys MTBF and "
        "costs one cycle of latency; if the observed bug is pulse loss, bus coherency or "
        "a missing constraint, the third flop changes nothing except the latency, and it "
        "can make a <i>reconvergence</i> problem worse by lengthening one path relative "
        "to another. <b>Establish which of the four CDC failure modes you have before "
        "reaching for depth</b>: metastability, pulse loss, incoherent multi-bit "
        "sampling, and reconvergence of separately synchronised signals. Only the first "
        "is helped by more stages."))
    return "\n".join(s)
