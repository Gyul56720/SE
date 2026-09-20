# -*- coding: utf-8 -*-
"""Volume III, Part Y6 -- From a paper to a block, and back to a paper."""
import sys, math, os, json
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_papers2():
    s = ['<h1 id="y6">Y6. From a Paper to a Block, and Back to a Paper</h1>']
    s.append("""<p>Research papers are the cheapest source of architecture a design house
    has, and the most dangerous, because a paper's incentives are not a product's
    incentives. A paper must be novel; a product must be robust. A paper reports the
    configuration that worked; a product must survive the ones that did not. This part is
    a procedure for extracting value from the literature without inheriting its
    optimism &mdash; and, in its second half, for publishing without committing the same
    offence.</p>""")

    s.append("<h2>Y6.1 Reading a hardware paper in the order that matters</h2>")
    s.append(tab("What to read, in order, and what you are looking for",
        ["Read", "You are asking", "Stop if"],
        [["The results table", "What was actually measured, in what units, against what "
          "baseline",
          "<b>The baseline is the authors' own strawman</b> rather than a published "
          "comparable"],
         ["The methodology section", "Simulated, synthesised, or fabricated? At what "
          "node? Post-layout or post-synthesis?",
          "Post-synthesis numbers compared against someone else's post-layout numbers "
          "&mdash; a 20&ndash;40&nbsp;% difference presented as a contribution"],
         ["The assumptions", "What is held fixed, and is it fixed in your application?",
          "The gain depends on a parameter your customer sets differently"],
         ["The limitations paragraph", "What do the authors admit?",
          "There is not one"],
         ["<b>The related work</b>", "<b>Who else did this, and how does this compare?</b>",
          "It is a list of citations rather than a comparison"],
         ["The algorithm", "Can you implement it from the text alone?",
          "Only now &mdash; <b>reading the algorithm first is how a fortnight "
          "disappears</b>"]]))
    s.append("""<div class="warn"><b>The recurring pattern in hardware papers is the
    unstated operating point.</b> A result is reported at the configuration where the
    proposed technique wins, and the sweep that shows where it loses is absent. This is
    not usually dishonesty; it is page limits and the reviewing process. But it means
    <b>the first thing to do with a promising technique is to reproduce the sweep the
    paper did not print</b>, in your own model, and find the crossover. If the crossover
    is on the wrong side of your customer's operating point, the technique is a
    publication and not a product &mdash; and you have learned that in a week rather than
    a quarter. This repository's own record contains the mirror image of this mistake: a
    headline figure of &lsquo;1/59 the area&rsquo; taken from the most favourable corner
    of a sweep, with the loss condition present elsewhere in the same document.</div>""")
    s.append(ex("Reproducing the missing sweep: a worked reading",
        "A paper claims an unrolled architecture removes a timing bottleneck and reports "
        "a 59&times; area advantage over the standard-cell baseline at one operating "
        "point.",
        "Identify the parameter the advantage depends on, sweep it, and find where the "
        "sign changes. Here the parameter is the number of taps that must be unrolled, "
        "which grows with channel loss; area grows as 2<sup><i>n</i></sup>.",
        [("Claimed advantage at the reported point", num(59, 3) + "&times;"),
         ("Unrolled taps at that point", num(2)),
         ("Area factor at <i>n</i>=2", num(2 ** 2)),
         ("Unrolled taps at a realistic 30&nbsp;dB channel", num(5)),
         ("Area factor at <i>n</i>=5", num(2 ** 5)),
         ("Advantage rescaled", num(59 / (2 ** 5 / 2 ** 2), 3) + "&times;"),
         ("Taps at which the advantage disappears",
          num(2 + math.log2(59), 3))],
        "<b>By quoting the headline and moving on.</b> The arithmetic above takes ten "
        "minutes and changes the conclusion from &lsquo;adopt&rsquo; to &lsquo;adopt for "
        "short channels only&rsquo;, which is a completely different product decision. "
        "The general procedure is: <b>find the exponential, and find where it eats the "
        "constant.</b> Almost every architecture paper contains exactly one such "
        "exponential, and the paper's operating point is chosen just below where it "
        "bites."))

    s.append("<h2>Y6.2 The prior-art search, done so that it means something</h2>")
    s.append("""<p>This book's repository enforces a rule that a prior-art note must be
    committed before the code for a topic. The rule exists because the same failure
    occurred five times: choose a topic, build, measure, write, and only then discover the
    work already existed. The procedure below is what the rule requires.</p>""")
    s.append(tab("A prior-art note that is worth the time it takes",
        ["Section", "Content", "The failure it prevents"],
        [["Closest prior work", "arXiv or DOI, year, and one sentence on what it did",
          "&lsquo;I could not find anything&rsquo;, which is not a finding"],
         ["<b>How we differ</b>", "<b>One paragraph, specific, falsifiable</b>",
          "<b>A difference that evaporates under a reviewer's first question</b>"],
         ["Queries run", "The literal search strings, at least three, with the "
          "databases", "An unrepeatable search"],
         ["<b>Where you have not looked</b>", "Named: patents, a paywalled venue, a "
          "language, an industry body's documents",
          "<b>Treating absence of evidence as evidence of absence</b>"],
         ["Confidence of each citation", "Full text, abstract, listing, or snippet",
          "Citing something you have not read as though you had"],
         ["Possibilities not yet eliminated", "A list",
          "A false sense of completion"]]))
    s.append("""<div class="ms"><b>The confidence marker is the mechanically enforceable
    part and therefore the part worth automating.</b> This repository requires every
    citation in a paper to carry, on the document's face, whether the author read the full
    text, the abstract, a listing entry, or only a search snippet; a gate checks the
    document against a ledger of citations and fails the build if they disagree. What the
    gate <i>cannot</i> check is whether the marker is honest, and the repository's notes
    say so explicitly. <b>That is the correct division: the machine forces the claim to be
    stated, and a human is accountable for its truth.</b> A process that pretends the
    machine can verify reading is worse than one that admits it cannot, because it invites
    everyone to stop looking.</div>""")
    s.append(prob("You find a patent that appears to cover the architecture you were "
                  "about to build. What are the possible responses, and which are "
                  "realistic for a one-person house?",
        "Six responses exist and only some are realistic. <b>Design around</b>: read the "
        "<i>claims</i>, not the abstract &mdash; the claims are the legal scope and are "
        "usually much narrower than the description &mdash; and find an element of the "
        "independent claim you can avoid. This is the normal answer and it is realistic. "
        "<b>Check the status</b>: the patent may have lapsed for unpaid maintenance fees, "
        "may never have been granted in your customers' jurisdictions, or may expire "
        "before your product ships; all are cheap to check and all are common. "
        "<b>License it</b>: realistic only if the holder licenses, which large "
        "semiconductor holders often do not to small parties. <b>Challenge validity</b>: "
        "not realistic &mdash; the cost exceeds a small house's annual revenue. "
        "<b>Ignore it</b>: not an option; wilful infringement carries enhanced damages, "
        "and your customer's legal review will find it anyway. <b>Change topic</b>: often "
        "the correct answer, and the reason the prior-art search comes first. "
        "<b>The meta-point is that the patent is information, not a verdict</b>, and "
        "reading the claims carefully is a skill worth acquiring because it converts a "
        "project-ending discovery into a design constraint about half the time."))

    s.append("<h2>Y6.3 Measuring so that the number survives a reviewer</h2>")
    s.append("""<p>The four rules below are this repository's response to four specific
    measurements that were reported and were wrong. They are stated as a checklist because
    each failure looked, at the time, like a result.</p>""")
    s.append(tab("Four checks before a number is said aloud",
        ["Check", "What went wrong without it", "How to do it"],
        [["<b>Did you measure the quantity you defined?</b>",
          "A tool reported the longest path in the whole netlist; the quantity wanted "
          "was the longest path <i>around a loop</i>. Different number, same units",
          "Isolate the quantity &mdash; cut the loop, build the combinational "
          "equivalent, and measure that"],
         ["<b>Is the operating point healthy?</b>",
          "A residual analysis was run at a point where the bit error rate was 0.49 "
          "&mdash; the link was not working, so every derived number was noise",
          "Sweep first, find a working point, then measure. Report the point"],
         ["<b>Is there an independent cross-check?</b>",
          "A reconstruction double-counted a term; the error was invisible until the "
          "same quantity was computed a second way",
          "Closed form, a second estimator, or a hand calculation &mdash; and print the "
          "difference"],
         ["<b>Have you killed the trivial explanations?</b>",
          "&lsquo;Seven gates, zero mismatch&rsquo; &mdash; because at that operating "
          "point the equalizer taps were near zero and the loop was doing nothing",
          "<b>Write the list of boring reasons the number could look good, then measure "
          "each one away</b>"]]))
    s.append("""<div class="warn"><b>If you cannot do all four, say which one you could
    not do.</b> A number with a stated gap is usable by a reader, who can weigh it. A
    number presented as complete when it is not is a claim the reader cannot calibrate,
    and when it turns out to be wrong it costs more than the information was ever worth.
    This applies with full force inside a company: the colleague reading your slide has no
    way to know which checks you ran unless you say.</div>""")
    s.append(prob("Your simulation shows a 3&times; improvement. What do you do before "
                  "telling anyone?",
        "Assume it is a bug, because at that magnitude it usually is, and spend an hour "
        "trying to prove it. <b>Check the baseline actually runs</b>: the commonest cause "
        "of a large speed-up is a baseline that is mis-configured, unoptimised, or "
        "silently failing, and comparing against a broken baseline is the strawman "
        "failure from Y6.1 committed against yourself. <b>Check the units and the "
        "normalisation</b> &mdash; per operation, per cycle, per joule and per second are "
        "four different claims. <b>Check that both sides did the same work</b>: a fast "
        "path that skips a case the baseline handles is not faster. <b>Compute the "
        "improvement a second way</b>, from first principles, and see whether 3&times; is "
        "even plausible given what changed; if the change removed 20&nbsp;% of the "
        "operations, a 3&times; speed-up needs an explanation beyond the operation count. "
        "<b>Only then look for the mechanism</b>, and when you report it, report the "
        "mechanism rather than the multiplier &mdash; a number with an explanation "
        "survives scrutiny and a number without one does not."))
    s.append(prob("Should a one-person design house publish at all?",
        "Yes, and for reasons that are commercial rather than academic. A publication is "
        "<b>evidence a customer can check</b> before trusting a supplier they have never "
        "heard of, which is the central problem of a new house. It is <b>defensive prior "
        "art</b>: published material cannot later be patented against you, which is cheap "
        "insurance compared with a patent of your own. It <b>forces the four checks "
        "above</b>, because a reviewer will ask, and work that survives review is work "
        "you can quote in a datasheet. And it <b>brings the people</b> &mdash; "
        "collaborators, customers and the occasional acquirer read the literature of "
        "their field. The cost is real: a paper is several weeks, and a rejection is "
        "several more. The pragmatic compromise many small houses take is an arXiv "
        "preprint plus a workshop or industry conference talk, which captures most of the "
        "benefit at a fraction of the cost of a top-tier submission, and <b>which is "
        "perfectly compatible with holding back the implementation details that are "
        "actually the product.</b>"))
    return "\n".join(s)
