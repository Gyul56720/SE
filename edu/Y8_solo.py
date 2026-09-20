# -*- coding: utf-8 -*-
"""Volume III, Part Y8 -- The one-person path from model to sellable product."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_flow():
    b = []
    rows = [("Specification", 12), ("C/C++ golden model", 12), ("Architecture study", 12),
            ("RTL", 12), ("Verification", 12), ("Synthesis and STA", 12),
            ("FPGA prototype", 12), ("Package and document", 12)]
    y = 12
    for nm, _ in rows:
        b.append(box(120, y, 190, 22, nm, None, 9))
        y += 28
    # feedback arrows
    b.append(line(316, 34, 344, 34, w=0.9))
    b.append(line(344, 34, 344, 146, w=0.9))
    b.append(arr(344, 146, 316, 146))
    b.append(txt(352, 92, "measure", 8))
    b.append(txt(352, 103, "then fix", 8))
    b.append(txt(352, 114, "the spec", 8))
    b.append(line(114, 62, 86, 62, w=0.9, dash="4,3"))
    b.append(line(86, 62, 86, 174, w=0.9, dash="4,3"))
    b.append(arr(86, 174, 114, 174))
    b.append(txt(20, 112, "golden model", 8))
    b.append(txt(20, 123, "is the", 8))
    b.append(txt(20, 134, "reference", 8))
    b.append(txt(20, 145, "for every", 8))
    b.append(txt(20, 156, "stage below", 8))
    return svg(400, 250, "".join(b))


def ch_solo():
    s = ['<h1 id="y8">Y8. The One-Person Path from Model to Product</h1>']
    s.append("""<p>The three-team structure of a large company &mdash; design, modelling,
    verification &mdash; exists because independence catches bugs. A single engineer
    cannot have organisational independence, so it has to be manufactured by process: the
    golden model is written before the RTL, from the specification rather than from the
    design, and it is never modified to agree with the RTL. This part is the procedure,
    with the realistic schedule and the places it goes wrong.</p>""")
    s.append(fig(_f_flow(), "The solo flow. The dashed line is the one that matters: the "
                            "golden model is the reference for every stage below it, "
                            "which is what replaces organisational independence."))

    s.append("<h2>Y8.1 The rule that replaces a second engineer</h2>")
    s.append(tab("How to be your own independent checker",
        ["Rule", "Why", "What breaks without it"],
        [["<b>Write the model before the RTL</b>",
          "The model then encodes your reading of the specification, not your design",
          "The model inherits the design's misunderstanding and certifies it"],
         ["<b>Never edit the model to match the RTL</b>",
          "A disagreement is information; resolving it by editing destroys the "
          "information",
          "<b>The commonest single failure of solo verification</b> &mdash; and it feels "
          "productive while you do it"],
         ["Resolve every disagreement by returning to the specification",
          "One of the two is wrong and the text says which",
          "You pick the one that is less work to change"],
         ["Use a third source where one exists", "zlib, a reference implementation, a "
          "vendor model, published vectors", "Two of your own artefacts agreeing proves "
          "only that you are consistent"],
         ["Write the test before the fix",
          "Otherwise the fix is unverified and may be wrong",
          "Regressions reappear"],
         ["Record why each parameter has its value",
          "You will not remember in six months, and a customer will ask",
          "Undocumented constants become unchangeable"]]))
    s.append("""<div class="warn"><b>&lsquo;I will fix the model later&rsquo; is the
    moment a solo project loses its verification.</b> When the RTL and the model disagree
    and the deadline is close, editing the model makes the test pass in minutes and
    investigating takes hours. Every such edit removes one independent check permanently,
    and they are not recoverable later because nobody remembers which ones were principled.
    The practical defence is mechanical: <b>keep the model in a separate commit history
    and require a written reason in the commit message for any change to it after the RTL
    exists.</b> The friction is the point.</div>""")

    s.append("<h2>Y8.2 A realistic schedule, with the failure points marked</h2>")
    stages = [("Specification study and requirements", 3, "Under-reading the standard; "
               "the parameters you assume are the ones that fail interoperability"),
              ("Golden model in C++ or Python", 3,
               "Modelling what you intend to build rather than what the spec says"),
              ("Architecture study and word lengths", 2,
               "Choosing uniform word lengths &mdash; Part&nbsp;X1's sweep exists for this"),
              ("RTL, first pass", 5, "Writing before the architecture is settled"),
              ("Testbench and checkers", 4,
               "Checkers that cannot fail; <b>run mutation testing here</b>"),
              ("Random and directed regression", 5,
               "Believing a flat find rate; Part&nbsp;X8's recovery test"),
              ("Lint, CDC, synthesis", 2,
               "Discovering a CDC problem that needs an architecture change"),
              ("Timing closure at target", 2,
               "Finding that the target was never achievable &mdash; check in week 2, "
               "not week 24"),
              ("FPGA prototype and bring-up", 4,
               "No loopback or ID register &mdash; Part&nbsp;Y7"),
              ("Documentation and packaging", 3,
               "Leaving it to the end, when the details are forgotten"),
              ("Buffer for the unforeseen", 6,
               "<b>Omitting it</b>")]
    rows = []
    cum = 0
    for nm, w, risk in stages:
        cum += w
        rows.append([nm, num(w), num(cum), risk])
    s.append(sweep("A 39-week single-engineer plan for a medium protocol block",
        ["Stage", "Weeks", "Cumulative", "Where it goes wrong"], rows,
        "The buffer is 15&nbsp;% of the total and it is the row most often deleted by "
        "someone who wants the number smaller. <b>A plan without a buffer is not an "
        "optimistic plan, it is a plan that has already failed</b>, because the "
        "unforeseen is the only certainty in the list."))
    s.append(ex("What the schedule implies about what you can build",
        "39 weeks for one block, a working year of 46 weeks, and a need to spend some "
        "of it selling and supporting.",
        "Compute how many blocks a single engineer can produce and what that means for "
        "the product strategy.",
        [("Weeks per block", num(39)),
         ("Working weeks per year", num(46)),
         ("Weeks available for sales and support", num(46 - 39)),
         ("Blocks per year", num(46 / 39, 3)),
         ("Blocks in three years, ignoring support growth", num(3 * 46 / 39, 3)),
         ("With support at 20&nbsp;% from year two", num((46 * 3 - 46 * 0.2 * 2) / 39, 3)),
         ("Implication",
          "<b>a family of related blocks, not unrelated ones</b>")],
        "<b>By planning a catalogue.</b> At roughly one block a year, a catalogue of "
        "unrelated blocks takes a decade and each one is supported alone. The strategy "
        "that fits the arithmetic is a <b>family</b>: one architecture parameterised "
        "across a range &mdash; the same FEC core at three code rates, the same MAC at "
        "three line rates &mdash; where the second member costs perhaps a quarter of the "
        "first and shares its verification environment, its documentation structure and "
        "its support material. <b>Choose the first block for the family it opens, not "
        "for its own merits.</b>"))

    s.append("<h2>Y8.3 What to build first</h2>")
    s.append(tab("Criteria for a first block, weighted for a house with no reputation",
        ["Criterion", "Why it matters more than it looks", "Good sign"],
        [["<b>A specification you can obtain</b>",
          "A block you cannot legally read the standard for cannot be built",
          "Open standard, or a membership you can afford"],
         ["<b>A checkable golden model</b>",
          "Without an independent reference, solo verification is much weaker",
          "Published test vectors, or an open reference implementation"],
         ["Soft, not hard", "A hard macro needs analogue skills and foundry access",
          "The block is RTL from end to end"],
         ["<b>Changing standard</b>", "<b>Incumbents' blocks go stale; a new revision "
          "resets the field</b>", "A draft is in ballot now"],
         ["Few credible suppliers", "You can win",
          "Searching finds two vendors, not twenty"],
         ["Adjacent to a family", "Second and third members are cheap",
          "The same core serves several rates or profiles"],
         ["A customer you can name", "Speculative IP is how houses die",
          "Someone has said they would evaluate it"]]))
    s.append("""<div class="ms"><b>Applying these criteria is what selected this book's
    own subject.</b> The PCS and FEC sublayer of a high-speed Ethernet link scores on
    every row: the sublayer is soft RTL between two hard boundaries; Reed&ndash;Solomon
    has an independent reference in any number of open implementations and a golden model
    that can be verified by its algebraic properties rather than by sample values; the
    802.3dj revision is in progress, which resets the incumbents; the supplier list is
    short; and the family extends naturally across code rates and generations. <b>The row
    that is not yet satisfied is the last one</b>, and this book says so rather than
    quietly omitting it &mdash; a named first customer is the thing that converts the
    other six rows from an argument into a business.</div>""")
    s.append(prob("You have 39 weeks and no income. What is the order of operations that "
                  "keeps you solvent?",
        "Invert the order the technical plan suggests. <b>Sell services first</b>: "
        "contract verification, modelling or integration work pays weekly and, crucially, "
        "puts you in front of the customers who will later buy the block &mdash; the "
        "conversations are the market research. <b>Build the golden model and the "
        "architecture study in the gaps</b>, because they are the parts that need "
        "thinking rather than long uninterrupted stretches, and because they are what you "
        "show a prospective customer to prove you understand the problem. <b>Do the RTL "
        "and verification in a funded block</b> &mdash; ideally funded by a customer who "
        "wants the first instance and will accept that you retain the rights, which is a "
        "negotiation worth having explicitly and early. <b>Do not build speculatively for "
        "39 weeks on savings</b>: the failure mode is not that the block is bad, it is "
        "that you run out of runway three weeks before the first sale, and at that point "
        "the asset is worth nothing to you and a great deal to whoever buys it from the "
        "liquidator."))
    return "\n".join(s)
