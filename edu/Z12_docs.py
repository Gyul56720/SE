# -*- coding: utf-8 -*-
"""Volume III, Part Z12 -- Writing the documents, with the templates."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num

HOUSE = "/home/user/SE/edu/house"


def ch_docs():
    s = ['<h1 id="z12">Z12. Writing the Documents</h1>']
    s.append("""<p>Documentation is where a one-person house is at its biggest
    disadvantage and, unusually, where it can be at its best: a document written by the
    person who made the decisions is better than one written by a technical writer
    three months later. This part is the structure, the rules, and what this repository's
    own documents look like.</p>""")

    s.append("<h2>Z12.1 Three documents, three readers</h2>")
    s.append(tab("Who reads each one, and what they are deciding",
        ["Document", "Reader", "The decision they are making", "Fails when"],
        [["<b>Datasheet</b>", "An evaluator, before buying",
          "<b>Does this block do what we need, at the rate we need?</b>",
          "Numbers without conditions; claims without evidence"],
         ["<b>Integration guide</b>", "An engineer, after buying",
          "<b>How do I wire this in without calling them?</b>",
          "It documents the block and not the <i>integration</i>"],
         ["<b>Known issues</b>", "Both",
          "<b>Can I trust this supplier?</b>",
          "<b>It is absent, or it says &lsquo;none&rsquo;</b>"]]))
    s.append("""<div class="ms"><b>The known-issue list is read as a character reference
    and should be written as one.</b> An evaluator has seen datasheets before and knows
    every block has limitations; what varies is whether the supplier says so. A list with
    eight dated entries, each with impact, workaround and status, says that someone has
    thought about the failure modes and is willing to be held to them. An absent list says
    either that nobody looked or that somebody decided not to tell you, and the evaluator
    cannot tell which &mdash; so they assume the worse one. <b>This is the cheapest
    credibility available to a supplier nobody has heard of</b>, and it costs an
    afternoon.</div>""")

    s.append("<h2>Z12.2 The rules that make the numbers usable</h2>")
    rows = [
        ["<b>Every number carries its conditions</b>",
         "&lsquo;2.18 cycles/byte, random back pressure, seeds 1/7/99&rsquo;",
         "&lsquo;1 byte per cycle&rsquo;",
         "<b>A number without conditions cannot be reproduced or disputed</b>"],
        ["Name the tool, the library and the version",
         "&lsquo;208 cells, yosys 0.33, open library&rsquo;",
         "&lsquo;~2 kGE&rsquo;",
         "Part Y14 &mdash; the honest smaller claim beats the unattributed larger one"],
        ["<b>Say what was not measured</b>",
         "&lsquo;Area in your process: not measured. Scripts included&rsquo;",
         "Silence",
         "<b>Silence is read as a claim</b>"],
        ["Separate measured from derived",
         "&lsquo;measured 2.18; bound set at 2.6&rsquo;",
         "&lsquo;2.6 cycles/byte&rsquo;",
         "A bound and a measurement are different facts"],
        ["Give the reproduction command",
         "<code>bash edu/house/release.sh crc32_stream</code>",
         "&mdash;",
         "<b>This is what turns claims into evidence</b>"],
        ["Date everything",
         "&lsquo;2026-09-19, v1.0&rsquo;", "undated",
         "An undated known-issue list is a list of excuses"],
    ]
    s.append(sweep("Six rules, each with the version that fails it",
        ["Rule", "Good", "Bad", "Why"], rows,
        "<b>All six are about the reader's ability to check you</b>, which is the only "
        "thing that distinguishes a datasheet from marketing. A vendor who makes "
        "checking easy is making a bet that the numbers hold, and evaluators read that "
        "bet correctly."))
    try:
        rows = []
        for f, who in (("DATASHEET.md", "evaluator"),
                       ("INTEGRATION.md", "integrator"),
                       ("KNOWN_ISSUES.md", "both")):
            p = os.path.join(HOUSE, f)
            t = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
            rows.append([f"<code>{f}</code>", who, num(len(t.splitlines())),
                         num(t.count("|")), num(t.count("실측") + t.count("잰 ")),
                         "yes" if "KNOWN_ISSUES" in t or f == "KNOWN_ISSUES.md"
                         else "&mdash;"])
        s.append(sweep("This repository's own documents, counted at build time",
            ["File", "Reader", "Lines", "Table cells", "Measured-value mentions",
             "Links to the issue list"], rows,
            "<b>Counted by reading the files as this page rendered.</b> The "
            "measured-value column is the one to watch: a datasheet whose count is "
            "zero is a list of intentions."))
    except Exception as e:
        s.append(f'<div class="warn">{E(str(e))[:200]}</div>')

    s.append("<h2>Z12.3 The datasheet, section by section</h2>")
    s.append(tab("What each section must answer",
        ["Section", "The question", "The commonest omission"],
        [["1. What it is", "Does this solve my problem?",
          "Naming the standard but not the profile or the options"],
         ["2. Interface", "Can I connect it?",
          "<b>The handshake rules</b> &mdash; which side may depend on which"],
         ["3. Performance", "Is it fast enough?",
          "<b>The conditions the number was measured under</b>"],
         ["4. Area and frequency", "Does it fit?",
          "Either silence, or an FPGA number presented as an ASIC one"],
         ["5. Verification", "Can I trust it?",
          "<b>Evidence that the tests bite</b> &mdash; the mutation score"],
         ["6. Configuration", "Can I tune it?",
          "Parameters listed without their legal ranges or their interactions"],
         ["7. Known issues", "What will bite me?", "The whole section"],
         ["8. Deliverables", "What do I get?",
          "Whether the testbench and scripts are included"]]))
    s.append(ex("How long the documents take if written weekly",
        "A 39-week block. Documentation written at the end, versus twenty minutes at "
        "the end of each week.",
        "Compare the totals, and then the quality, which is the part that does not "
        "appear in the total.",
        [("Written at the end", "1&ndash;2 weeks solid"),
         ("Written weekly", num(39 * 20 / 60, 4) + " hours total"),
         ("Ratio", "<b>about 3&times; cheaper</b>"),
         ("And the quality difference",
          "<b>weekly notes record <i>why</i>; end-of-project notes record <i>what</i></b>"),
         ("What is lost by waiting",
          "the reason a constant has its value, the corner that forced a structure, "
          "the thing that nearly went wrong"),
         ("Who needs the why", "<b>the customer's integrator, and you in a year</b>")],
        "<b>By treating documentation as transcription.</b> It is not &mdash; it is the "
        "record of decisions, and decisions are only recoverable while they are fresh. "
        "The three-times cost difference is real and is the smaller of the two effects; "
        "the larger one is that a document written at the end cannot contain the "
        "information that makes it worth reading. <b>Part&nbsp;Z2 puts this in the "
        "Friday slot for exactly this reason</b>, and it is the slot that disappears "
        "first."))
    s.append(prob("Your block has 40 configuration parameters. How do you document "
                  "them without writing 40 pages?",
        "Generate the list and write prose only about the interactions, because the "
        "list is mechanical and the interactions are not. <b>Generated</b>: name, type, "
        "legal range, default, and what it affects &mdash; from the same source that "
        "produces the RTL parameters, exactly as Part&nbsp;Z4's register map is "
        "generated. That is a table nobody writes and nobody can get out of sync. "
        "<b>Written by hand</b>: the three or four <i>combinations</i> that matter "
        "&mdash; which parameters must move together, which ones are ignored when "
        "another is set, which ones change the area or the latency and by roughly how "
        "much. <b>And a short list of the two or three configurations you have actually "
        "verified and synthesised</b>, named, with their numbers. That last item is the "
        "honest core of it: 40 independent parameters is 2<sup>40</sup> configurations "
        "and you have verified a handful, so say which handful and state the covering "
        "argument for the rest (Part&nbsp;X19's pairwise criterion is the standard one). "
        "<b>A customer choosing an unverified combination should know that is what they "
        "are doing</b>, and a supplier who tells them is worth more than one who implies "
        "all 2<sup>40</sup> were tested."))
    return "\n".join(s)
