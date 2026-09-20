# -*- coding: utf-8 -*-
"""Volume III, Part Z10 -- The RS-KP4 decoder, planned block by block."""
import sys, os, math
sys.path.insert(0, "/home/user/SE/edu")
sys.path.insert(0, "/home/user/SE")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line
import gf, rs


def ch_rsplan():
    c = rs.RS(gf.필드(10, 0x409), 544, 514, fcr=0)
    s = ['<h1 id="z10">Z10. The RS-KP4 Decoder, Planned Block by Block</h1>']
    s.append("""<p>Part&nbsp;Y15 states where this project stands. This part is the plan
    that would finish it: each sub-block, what its golden model is, how the agent verifies
    it, what its gate looks like, and how long it takes. It is written so that it can be
    executed rather than admired.</p>""")

    s.append("<h2>Z10.1 The decomposition</h2>")
    rows = [
        ["<b>Syndrome</b>", f"{2*c.t} accumulators, 64 symbols/cycle",
         "<code>rs.신드롬()</code>", "<b>Exists as a one-step block</b>; widen it",
         "3 weeks", "<b>Dominates area</b> &mdash; Part Y15's count"],
        ["Key equation (BM)", "Serial, 2<i>t</i> iterations",
         "<code>rs._BM()</code>", "New", "4 weeks",
         "Small area, fixed latency"],
        ["Chien search", f"Evaluate &sigma; at 544 positions, 64/cycle",
         "<code>rs._치엔()</code>", "New", "3 weeks",
         "Second-largest block"],
        ["Forney", "Magnitudes from &sigma; and &omega;",
         "<code>rs._포니()</code>", "New", "2 weeks",
         "Needs a field inverse &mdash; table or Itoh&ndash;Tsujii"],
        ["Delay FIFO", "One codeword in flight",
         "trivial", "New", "1 week",
         f"{544*10:,} bits &mdash; the block's main memory"],
        ["<b>Re-check after correction</b>", "Recompute syndromes on the corrected word",
         "<code>rs.복호()</code> does this", "New", "1 week",
         "<b>Turns silent miscorrection into a flag</b> &mdash; Part X5"],
        ["Top level, AXI-Stream", "Handshake, packet boundaries, back pressure",
         "the Python decoder end to end", "New", "3 weeks",
         "Part X37's rules"],
    ]
    s.append(sweep("Sub-blocks, each with its own oracle and its own gate",
        ["Sub-block", "What it is", "Golden model", "State", "Effort", "Note"], rows,
        "<b>Every golden model already exists</b>, in this repository's "
        "<code>rs.py</code>, verified by 13 tests including mutation guards. That is "
        "the unusual part of this plan and the reason it is credible: the hardest "
        "thing to get right is already done and already checked."))
    총 = 3 + 4 + 3 + 2 + 1 + 1 + 3
    s.append(f"""<div class="ms"><b>Total {총} weeks of RTL, against Part&nbsp;Y8's
    39-week plan for a sellable block.</b> The difference is everything downstream: the
    verification environment, the release gate, the documentation, the packaging, the
    synthesis and timing runs, and the buffer. <b>The RTL is about a third</b>, which
    matches Part&nbsp;Y1's effort table for MIPI and is the ratio a first-time vendor
    most consistently gets wrong.</div>""")

    s.append("<h2>Z10.2 How each sub-block is verified, concretely</h2>")
    s.append(f"""<p>Each sub-block becomes an agent block in exactly the form
    Part&nbsp;Z1 describes: a DUT file, a testbench, and a <code>block.py</code> whose
    <code>자극()</code> drives it and whose golden values come from
    <code>rs.py</code>. The pattern is already demonstrated by
    <code>blocks/rs_syndrome</code>.</p>""")
    s.append(tab("The verification plan per sub-block",
        ["Sub-block", "Stimulus that must be in the set", "Why"],
        [["Syndrome", f"Zero errors; 1 error; exactly <i>t</i>={c.t}; <i>t</i>+1; "
          "all-zero codeword; all-ones",
          "<b>Zero errors must not pass as success</b> &mdash; <code>rs.측정()</code> "
          "refuses to report a pass from a zero-error trial"],
         ["Key equation", "Every error count 0&hellip;<i>t</i>+2; degenerate "
          "syndromes", "The iteration count is data independent, so the corners are "
          "about degree, not timing"],
         ["Chien", "Roots at position 0, at 543, adjacent roots, repeated roots",
          "<b>Repeated roots mean the locator is wrong</b> &mdash; the decoder must "
          "flag, not correct"],
         ["Forney", "Error magnitudes at the field's extremes; a zero denominator",
          "Part X5's decoder returns failure on a zero denominator; the RTL must too"],
         ["<b>Top level</b>", "<b>Back-to-back codewords with no gap; a stall in the "
          "middle of a codeword; reset mid-codeword</b>",
          "<b>Part X37 and Part X42 &mdash; the integration failures</b>"]]))
    s.append(ex("What the agent can check that a human review cannot",
        f"RS(544,514) over GF(2^10), <i>t</i>={c.t}. The decoder must correct every "
        f"pattern of up to {c.t} symbol errors and must not silently miscorrect beyond.",
        "Count the patterns. Then note which of the two properties is checkable by "
        "sampling and which is not.",
        [("Error positions of weight " + str(c.t),
          "C(544," + str(c.t) + ") &asymp; 10<sup>29</sup>"),
         ("Magnitudes per position", num(1023)),
         ("Total patterns", "astronomically many"),
         ("<b>What sampling establishes</b>",
          "<b>a bound on the failure rate, not correctness</b>"),
         ("What the algebra guarantees",
          "<b>all</b> patterns of weight &le; <i>t</i>, by the code's minimum distance"),
         ("So the RTL must be checked against", "<b>the model, not the space</b>"),
         ("And the model against", "<b>the algebra</b> &mdash; which "
          "<code>tests/test_rs.py</code> does by property, not by sample")],
        "<b>By trying to verify the RTL directly against the specification's "
        "guarantee.</b> The guarantee is over a space nobody can enumerate; what is "
        "checkable is agreement with a model whose own correctness rests on properties "
        "that <i>are</i> checkable. <b>This two-level structure is why the golden model "
        "must be verified by properties rather than by vectors</b> &mdash; and it is "
        "exactly what this repository's <code>test_rs.py</code> does when it breaks the "
        "syndrome computation and asserts the measurement notices."))

    s.append("<h2>Z10.3 The three unconfirmed constants, and the plan around them</h2>")
    s.append(tab("What is not known, and what it blocks",
        ["Unknown", "Fixed by", "Blocks", "Work that proceeds anyway"],
        [["<b>Field polynomial</b>", "IEEE 802.3 Clause 91",
          "<b>Interoperability</b> &mdash; not correctness",
          "<b>Everything.</b> It is a parameter; the RTL takes it as one"],
         ["First consecutive root <code>fcr</code>", "Same clause",
          "Interoperability", "Same &mdash; a parameter"],
         ["Symbol bit order", "Same clause", "The byte/symbol packing at the boundary",
          "The core; only the top-level packer depends on it"]]))
    s.append("""<div class="warn"><b>Parameterising is not a substitute for reading the
    clause, and the plan should not pretend otherwise.</b> A parameterised decoder is
    correct for whatever parameters it is given and interoperable with nothing until the
    parameters are right. What parameterising buys is that <i>the unknown stays
    visible</i> &mdash; a hard-coded constant dissolves into an assumption nobody
    questions, and Part&nbsp;Y15's scorecard would quietly lose its most important row.
    <b>The first item in the plan remains: obtain the document.</b> Everything else is
    work that can proceed in parallel, and none of it is work that can substitute.</div>""")
    s.append(prob("Sixteen weeks of RTL and the specification is still unobtainable. "
                  "Do you build it anyway?",
        "Build the parts that are parameter-independent and stop before the parts that "
        "are not, and be explicit with yourself about which is which. The field "
        "arithmetic, the Berlekamp&ndash;Massey iteration, the Chien search structure "
        "and the Forney computation are all <i>generic</i> &mdash; they are correct for "
        "any primitive polynomial and any first root, and building them is not "
        "speculative. The top-level packing, the interoperability claim and the datasheet "
        "are parameter-dependent and should not be written. <b>What you must not do is "
        "pick a plausible value and proceed as though it were confirmed</b>, because "
        "that converts a known unknown into an unknown one, and the failure surfaces at "
        "a plugfest in front of the people you most want to impress. "
        "<b>The strategic answer, though, is to reconsider the product.</b> "
        "Part&nbsp;Z5's scorecard weights specification availability at 3 precisely so "
        "that this situation is visible before sixteen weeks are spent, and its winner "
        "&mdash; a post-quantum core whose standard, reference implementation and test "
        "vectors are all public &mdash; exists because that row was weighted honestly. "
        "A block you cannot obtain the specification for is not a cheaper project; it is "
        "a different one."))
    return "\n".join(s)
