# -*- coding: utf-8 -*-
"""Volume III, Part Y15 -- A complete worked project: RS-KP4 as a sellable block."""
import sys, os, math
sys.path.insert(0, "/home/user/SE/edu")
sys.path.insert(0, "/home/user/SE")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line
import gf, rs


def _f_arch():
    b = []
    stages = [("input\nFIFO", 14), ("syndrome\n&times;2t", 96), ("key equation\n(BM)", 186),
              ("Chien +\nForney", 276), ("correct\n(delay FIFO)", 366)]
    for nm, x in stages:
        w = 74 if x != 366 else 86
        a, bb = nm.split("\n")
        b.append(box(x, 30, w, 34, a, bb, 8))
        if x > 14:
            b.append(arr(x - 8, 47, x, 47))
    b.append(arr(452, 47, 476, 47))
    b.append(line(50, 64, 50, 92, w=0.9))
    b.append(line(50, 92, 408, 92, w=0.9))
    b.append(arr(408, 92, 408, 64))
    b.append(txt(229, 106, "the codeword waits in a FIFO while the syndrome path "
                           "computes the correction", 8, "middle"))
    b.append(txt(229, 124, "latency = FIFO depth = one codeword + the key-equation "
                           "pipeline", 8, "middle", 'font-style="italic"'))
    return svg(500, 134, "".join(b))


def ch_project():
    s = ['<h1 id="y15">Y15. A Complete Worked Project: RS-KP4</h1>']
    s.append("""<p>This part takes one block from a specification through to a delivery
    package, with the numbers computed rather than estimated. It uses the code that is
    already in this repository &mdash; the field arithmetic and the decoder of
    Part&nbsp;X5 &mdash; and it states, at each step, what exists and what does not, so
    the reader can see the difference between a worked example and a finished
    product.</p>""")
    s.append(fig(_f_arch(), "The decoder architecture. The delay FIFO is the block's "
                            "dominant memory and the reason latency is quoted in "
                            "codewords."))

    s.append("<h2>Y15.1 The parameters, and which are still unconfirmed</h2>")
    c = rs.RS(gf.필드(10, 0x409), 544, 514, fcr=0)
    rows = [
        ["Field", "GF(2<sup>10</sup>)", "confirmed by the code length",
         "&mdash;"],
        ["Primitive polynomial", "<code>0x409</code> assumed",
         "<b>NOT confirmed</b>",
         "<b>Fixed by IEEE 802.3 Clause 91, which this repository has not read</b>"],
        ["First consecutive root <code>fcr</code>", "0 assumed", "<b>NOT confirmed</b>",
         "Same clause"],
        ["Symbol bit order", "MSB first assumed", "<b>NOT confirmed</b>", "Same clause"],
        ["<i>n</i>, <i>k</i>", "544, 514", "confirmed &mdash; the code's name",
         "&mdash;"],
        ["<i>t</i>", str(c.t), "derived: (<i>n</i>&minus;<i>k</i>)/2", "&mdash;"],
    ]
    s.append(sweep("The parameter set, with the confidence of each entry",
        ["Parameter", "Value used", "Confidence", "Where it is fixed"], rows,
        "<b>Three of six are assumptions.</b> The model in this repository takes all "
        "three as arguments with the assumption marked, and its tests check "
        "<i>properties</i> that hold whatever the values are &mdash; that up to "
        "<i>t</i> errors are always corrected and that beyond <i>t</i> the decoder does "
        "not silently return the input. <b>When the clause is obtained, only the "
        "defaults change.</b>"))
    s.append("""<div class="warn"><b>This is what it looks like to build honestly on an
    unread specification.</b> The alternative &mdash; pick a polynomial, hard-code it,
    and proceed &mdash; produces a block that works perfectly against itself and fails at
    the first interoperability test, with the cause buried in a constant nobody
    questions. Parameterising costs nothing and the marked confidence costs one column in
    a table. <b>What it buys is that the unread clause remains visible</b> instead of
    dissolving into an assumption, which is precisely the failure Part&nbsp;Y6 is written
    to prevent.</div>""")

    s.append("<h2>Y15.2 Sizing the block from the standard's rate</h2>")
    fb = 53.125e9
    W = 10
    rows = []
    for lanes, clk in ((4, 830e6), (8, 415e6), (16, 208e6), (32, 104e6)):
        sym_per_clk = fb / clk / 1
        rows.append([num(lanes), num(clk / 1e6, 4), num(sym_per_clk, 4),
                     num(math.ceil(sym_per_clk)), num(math.ceil(sym_per_clk) * W),
                     num(544 / math.ceil(sym_per_clk), 4)])
    s.append(sweep("Parallelism required at 53.125&nbsp;GBd, one symbol per 10 bits",
        ["De-serialisation", "Digital clock (MHz)", "Symbols per clock",
         "Symbols processed in parallel", "Datapath width (bits)",
         "Clocks per codeword"], rows,
        "The third column is the block's fundamental parallelism: at 830&nbsp;MHz the "
        "decoder must absorb 64 symbols every cycle. <b>Every stage of the architecture "
        "must be replicated or restructured to that width</b>, and that replication, not "
        "the algorithm, is where the area goes."))
    s.append(ex("Where the area actually goes",
        f"RS(544,514), <i>t</i>&nbsp;=&nbsp;{c.t}, 64 symbols per cycle at 830&nbsp;MHz.",
        "Count the three structures separately: the syndrome computation (parallel, "
        "wide), the key equation (serial, narrow) and the Chien search (parallel, wide). "
        "The asymmetry is the architectural fact.",
        [("Syndromes to compute", num(2 * c.t)),
         ("GF multipliers for syndromes, unparallelised", num(2 * c.t)),
         ("At 64 symbols per cycle", num(2 * c.t * 64)),
         ("Berlekamp&ndash;Massey multipliers (serial, ~2<i>t</i>)", num(2 * c.t)),
         ("BM cycles per codeword", num(2 * c.t)),
         ("Chien: evaluate &sigma; at 64 positions per cycle",
          num(64 * c.t)),
         ("Ratio of wide structures to the key equation",
          num((2 * c.t * 64 + 64 * c.t) / (2 * c.t), 4) + "&times;"),
         ("Delay FIFO", num(544 * 10) + " bits per codeword in flight")],
        "<b>By optimising Berlekamp&ndash;Massey.</b> It is the algorithmically "
        "interesting stage, it is what the literature discusses, and here it is about "
        "one per cent of the multipliers. <b>The syndrome and Chien stages dominate "
        "because they are replicated 64 ways</b> and BM is not. The architectural "
        "leverage is therefore in sharing and folding those wide stages &mdash; the "
        "standard techniques being common-subexpression sharing across the syndrome "
        "constants and a folded Chien search &mdash; and in nothing else. "
        "<b>Compute the replication factor before deciding what to optimise</b>, in any "
        "block."))

    s.append("<h2>Y15.3 What exists in this repository and what does not</h2>")
    s.append(tab("State of the project, stated plainly",
        ["Item", "State", "Where"],
        [["Field arithmetic with verified axioms", "<b>Exists</b>",
          "<code>gf.py</code>, 10 tests"],
         ["Encoder and bounded-distance decoder", "<b>Exists</b>",
          "<code>rs.py</code>, 13 tests including mutation guards"],
         ["Measurement that refuses a zero-error pass", "<b>Exists</b>",
          "<code>rs.측정()</code>"],
         ["Prior-art survey with confidence markers", "<b>Exists</b>",
          "<code>paper/&#49440;&#54665;&#51312;&#49324;/PCS_FEC&#44228;&#52789;_IP.md</code>"],
         ["A syndrome-step RTL block verified against the model", "<b>Exists</b>",
          "<code>edu/agent/blocks/rs_syndrome/</code>"],
         ["Full parallel decoder RTL", "<b>Does not exist</b>", "&mdash;"],
         ["Berlekamp&ndash;Massey RTL", "<b>Does not exist</b>", "&mdash;"],
         ["The three unconfirmed constants", "<b>Still unconfirmed</b>",
          "Needs the IEEE document"],
         ["Concatenated inner code (802.3dj)", "<b>Not started</b>", "&mdash;"],
         ["A named first customer", "<b>None</b>", "&mdash;"]]))
    s.append("""<div class="ms"><b>Listing what does not exist is the point of this
    section.</b> A worked example that presents a partial project as a finished one
    teaches the wrong lesson twice: it misleads about the effort, and it models the
    behaviour &mdash; quiet omission of the incomplete parts &mdash; that this book spends
    two chapters warning against. The honest summary is that this repository contains a
    <i>verified reference model and one verified RTL primitive</i> for a block whose
    full implementation is most of Part&nbsp;Y8's 39-week plan, and that three of its
    parameters await a document that must be purchased.</div>""")
    s.append(prob("Given that state, what are the next three actions, in order?",
        "<b>First, obtain the clause.</b> Three unconfirmed constants block every "
        "downstream claim of interoperability, and no amount of RTL removes that block; "
        "until they are confirmed the project can produce a correct decoder for a code "
        "that may not be the standard's. This is a purchase and a fortnight of reading, "
        "and it is the highest-value action available. <b>Second, build the syndrome "
        "stage at full parallelism and verify it against the model</b>, because the "
        "sizing example above says that stage dominates the area, so the area and "
        "frequency claims &mdash; the numbers a customer asks for first &mdash; are "
        "determined by it. One wide stage, synthesised and timed, converts an estimate "
        "into a measurement. <b>Third, find a customer conversation before writing the "
        "key equation</b>, because everything after the syndrome stage is a large effort "
        "whose requirements (latency budget, code rate set, concatenation) the customer "
        "determines, and guessing them is how the 39 weeks turn into 60. <b>Note that "
        "the technically interesting work is third on this list</b>, which is usually "
        "where it belongs."))
    return "\n".join(s)
