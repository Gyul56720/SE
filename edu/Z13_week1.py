# -*- coding: utf-8 -*-
"""Volume III, Part Z13 -- Week one: what to do on Monday morning."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def ch_week1():
    s = ['<h1 id="z13">Z13. Week One</h1>']
    s.append("""<p>This book is long and the first Monday is short. This part is what to
    do in the first five days if the aim is a two-member team producing sellable IP, in
    an order that leaves something working at the end of each one. Everything it names
    exists in this repository and can be copied.</p>""")

    s.append("<h2>Z13.1 The five days</h2>")
    rows = [
        ["<b>Monday</b>", "Get the flow running",
         "Install iverilog, verilator, yosys, Python. Clone this repository. "
         "Run <code>bash edu/house/release.sh gf_mul</code> and watch it pass.",
         "<b>You now have a working gate on somebody else's block</b>, which is the "
         "fastest way to see what one looks like"],
        ["<b>Tuesday</b>", "Make it your block",
         "Copy <code>edu/agent/blocks/gf_mul</code>. Replace the RTL with the smallest "
         "thing you actually want to build. Write <code>block.py</code>'s "
         "<code>자극()</code> against a golden model you did not write.",
         "<b>The golden model must be independent</b> &mdash; a library, a reference "
         "implementation, the standard's vectors"],
        ["<b>Wednesday</b>", "Make the checks bite",
         "Run <code>mutscore.py</code>. Read every escape. Fix the stimulus until the "
         "score is above 90&nbsp;% with every remaining escape judged in writing.",
         "<b>This is the day that teaches the most</b>, and it is the day this "
         "repository's register file went from 58&nbsp;% to 100&nbsp;% and surfaced "
         "two real bugs"],
        ["<b>Thursday</b>", "Declare a bound",
         "Measure the clean block's cycles over several seeds. Declare "
         "<code>성능한계()</code> just above the spread. Break the block so it is only "
         "slower and confirm the gate catches it.",
         "<b>A value-only suite cannot see a block getting slower</b>"],
        ["<b>Friday</b>", "Write the three documents and run the gate",
         "Datasheet, integration guide, known issues &mdash; short, with the numbers "
         "you measured this week and their conditions. Then "
         "<code>release.sh</code> and read what it says.",
         "<b>It will say you cannot sell it yet, and it will say exactly why</b>"],
    ]
    s.append(sweep("Week one",
        ["Day", "Goal", "What you do", "Why this and not something else"], rows,
        "<b>No architecture, no algorithm, no big block.</b> The week builds the "
        "apparatus; the apparatus is what makes every later week cheap. A week spent "
        "the other way round produces a nicer block and no way to know whether it "
        "works."))
    s.append("""<div class="warn"><b>The instinct is to start with the interesting
    block.</b> It is the reason to be doing this at all, and it is the wrong first week:
    a large block with no gate is a large block you cannot make claims about, and the
    gate is far easier to build against something trivial. <b>The 30-line GF multiplier
    in this repository exists for exactly that reason</b> &mdash; it is small enough that
    every part of the apparatus can be seen working, and the apparatus transfers
    unchanged to a block a hundred times larger.</div>""")

    s.append("<h2>Z13.2 What each day leaves behind</h2>")
    s.append(tab("The artefacts, and what each proves",
        ["After", "You have", "You can say"],
        [["Monday", "A green gate on a known-good block",
          "&lsquo;my flow works&rsquo; &mdash; which you could not say before"],
         ["Tuesday", "Your RTL compared against an independent model",
          "&lsquo;it agrees with <i>X</i> on <i>n</i> cases&rsquo;"],
         ["<b>Wednesday</b>", "<b>A mutation score with judged escapes</b>",
          "<b>&lsquo;the suite catches <i>k</i>&nbsp;% of injected defects, and here "
          "are the ones it does not and why&rsquo;</b>"],
         ["Thursday", "A measured throughput bound that fires",
          "&lsquo;it sustains <i>x</i>, and the gate proves it has not regressed&rsquo;"],
         ["Friday", "Three documents and a gate report",
          "<b>&lsquo;here is what is done, here is what is not&rsquo;</b>"]]))
    s.append(ex("What the first week costs and what it saves",
        "Five days building apparatus instead of five days building the block.",
        "Count what the apparatus does over the following months, using this book's own "
        "measurements.",
        [("Cost", num(5) + " days"),
         ("Nightly regression thereafter", "<b>free</b>"),
         ("Bugs the mutation score surfaced here in one afternoon", num(2)),
         ("Where those bugs would otherwise have been found",
          "<b>the customer's driver</b>"),
         ("Cost of a bug found by a customer (Part X8)",
          "<b>10<sup>3</sup>&ndash;10<sup>4</sup>&times; a specification-stage fix</b>"),
         ("Break-even", "<b>the first real bug</b>"),
         ("Additional return", "every block after this one starts on Tuesday")],
        "<b>By counting the week as lost time.</b> It is the only week whose output is "
        "reusable without modification across every block the house will ever build, and "
        "the ratio in the fifth row means it pays for itself the first time the gate "
        "catches something. <b>The honest caution is that it does not <i>feel</i> like "
        "progress</b>, which is why it is worth deciding in advance to spend it."))

    s.append("<h2>Z13.3 Where to go next in this book</h2>")
    s.append(tab("Reading order after week one",
        ["If you are", "Read", "Because"],
        [["Choosing what to build", "Part Z5, then Part Y6",
          "Scorecard first, then the prior-art discipline that stops you rebuilding "
          "something"],
         ["<b>Writing the golden model</b>", "<b>Parts X1 and Y11</b>",
          "<b>Fixed point is most of the work and independence is the whole point</b>"],
         ["Choosing an architecture", "Parts X2, X6, X13",
          "Timing budget, memory-versus-arithmetic, the roofline"],
         ["Stuck on verification", "Parts X8, X33, Z6",
          "Coverage arithmetic, where formal helps, what the agent cannot do"],
         ["Getting it to close timing", "Parts X2, X14, X34",
          "The budget, the physical consequences, what synthesis can and cannot fix"],
         ["<b>Preparing to sell</b>", "<b>Parts Z3, Z4, Y5, Z12</b>",
          "<b>The bar, the pack, the commercial terms, the documents</b>"],
         ["Talking to a customer", "Parts Y5, Y9, Z8",
          "Scoping, compliance, money"],
         ["Scaling past a toy", "Part Z9", "What breaks and what replaces it"]]))
    s.append(prob("You have read this book and you have a day job. Is any of this "
                  "possible part-time?",
        "The apparatus is, and the block is not &mdash; and separating the two is the "
        "useful answer rather than a discouraging one. <b>The apparatus is compatible "
        "with part-time work</b> because the agent runs when you are not there: an hour "
        "in the evening spent strengthening the oracle is repaid by a night of "
        "unattended checking, which is the one part of this arrangement that does not "
        "scale with your hours. Week one is five evenings rather than five days. "
        "<b>What is not compatible is the customer side</b>: evaluations, plugfests, "
        "support response times and the conversations of Part&nbsp;Z5 all happen during "
        "business hours and cannot be deferred, and Part&nbsp;Z8's arithmetic says the "
        "customer side is what decides whether the business exists. <b>So the honest "
        "part-time plan is to build the apparatus and one small, complete, publishable "
        "block</b> &mdash; which is a portfolio (Part&nbsp;Y13) and an asset and a "
        "genuine thing to point at &mdash; and to treat the transition to selling as a "
        "separate decision that needs the day job to end. <b>Conflating the two is how "
        "people spend two years part-time and arrive with neither.</b>"))
    return "\n".join(s)
