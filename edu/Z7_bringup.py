# -*- coding: utf-8 -*-
"""Volume III, Part Z7 -- Solo bring-up: the bench a one-person house needs."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def ch_solobringup():
    s = ['<h1 id="z7">Z7. Solo Bring-Up: The Bench You Actually Need</h1>']
    s.append("""<p>At some point a block has to run on real hardware, because a customer
    will ask whether it has and because simulation does not model the things that break.
    This part is about the smallest bench that answers that honestly, what it costs, and
    what it cannot tell you.</p>""")

    s.append("<h2>Z7.1 What an FPGA prototype proves &mdash; and what it does not</h2>")
    s.append(tab("Claims a prototype supports",
        ["Claim", "Prototype evidence?", "Why"],
        [["The RTL is functionally correct at speed",
          "<b>Strong</b>",
          "Billions of cycles against real traffic &mdash; far beyond simulation"],
         ["It interoperates with a real partner",
          "<b>Strong, and unobtainable any other way</b>",
          "The partner's implementation is the thing you cannot simulate"],
         ["Reset and initialisation work",
          "<b>Strong</b>",
          "Real power-up, real clock start &mdash; Part X42's untestable cases"],
         ["The clock-domain crossings are sound",
          "Weak",
          "Metastability at the FPGA's rates and MTBF is not the ASIC's"],
         ["<b>It meets the ASIC frequency</b>", "<b>No</b>",
          "<b>Different fabric entirely.</b> An FPGA number says nothing about an ASIC "
          "number and quoting it as if it did is the classic misrepresentation"],
         ["The area estimate is right", "No", "LUTs are not gates"],
         ["Power is acceptable", "No", "Unrelated"],
         ["Timing closes at the customer's corners", "No",
          "Their library, their flow, their corners"]]))
    s.append("""<div class="warn"><b>The temptation is to quote the FPGA frequency.</b> It
    is a real number that was really measured, and it is about a different technology.
    A customer's evaluator knows this and will read the substitution as either ignorance
    or misdirection, both of which cost more than the number was worth.
    <b>Quote it as what it is</b>: &lsquo;runs at 200&nbsp;MHz on <i>this</i> part, with
    this build, and here is the project&rsquo;, alongside a separately-labelled synthesis
    estimate with its library named. Part&nbsp;Y14's rule again: the honest smaller claim
    is more persuasive than the unattributed larger one.</div>""")

    s.append("<h2>Z7.2 The bench, itemised</h2>")
    rows = [
        ["FPGA board with the right I/O", "$200&ndash;$3,000",
         "<b>Choose by the interface you must prove</b>, not by logic capacity. "
         "A board without the connector is useless however large its fabric"],
        ["Vendor toolchain", "$0 (free tier) &ndash; $3,000",
         "The free tier covers small and mid parts; check your part is in it "
         "<b>before</b> buying the board"],
        ["<b>Logic analyser, on-chip</b>", "<b>$0 &mdash; bundled</b>",
         "<b>The single most valuable debug tool</b>; budget the block RAM it eats"],
        ["USB protocol analyser / scope", "$300&ndash;$5,000",
         "Only if the interface is external and slow enough to see"],
        ["High-speed scope or BERT", "$20,000+ or rented",
         "<b>Rent by the day, or use the far end's own error counters</b>"],
        ["Partner hardware to interoperate with", "varies",
         "<b>Often the largest real cost and the highest value</b>"],
        ["Bench supplies, cables, adapters", "$200&ndash;$800", "Underestimated"],
    ]
    s.append(sweep("A first bench, with what each item is for",
        ["Item", "Order of cost", "Note"], rows,
        "<b>Ranges, not quotations.</b> The point is the shape: the board and the "
        "partner hardware matter and the instruments mostly do not, because modern "
        "high-speed links carry their own error counters and a rented instrument "
        "answers the rest."))
    s.append(ex("What the prototype has to demonstrate, in order",
        "Part Y7's bring-up sequence, applied to an IP block on an FPGA.",
        "Each step is a claim you will make to a customer. Do them in dependency order "
        "and stop at the first that fails.",
        [("1. Bitstream loads, clock runs", "the board and the build"),
         ("2. <b>ID register reads the right constant</b>",
          "<b>power, clock, reset, bus, decode &mdash; all in one read</b>"),
         ("3. Scratch register writes and reads back", "the write path"),
         ("4. Internal loopback passes traffic", "the datapath, no external risk"),
         ("5. One external transaction", "debuggable; the channel now included"),
         ("6. Line-rate traffic for an hour", "buffering, back pressure, rate matching"),
         ("7. Overnight with error counters read", "<b>the number you quote</b>"),
         ("8. Against a second vendor's part", "<b>interoperability &mdash; the claim "
          "worth the most</b>")],
        "<b>By starting at step 6.</b> Running traffic before the ID register reads is "
        "how a week disappears: every failure has a dozen candidate causes and none of "
        "the cheap tests has been done. Part&nbsp;Y7's information argument applies "
        "exactly &mdash; each early step splits the hypothesis space evenly and costs "
        "minutes, and skipping them does not save the minutes, it spends days."))

    s.append("<h2>Z7.3 Instrumenting for a bench you will be alone at</h2>")
    s.append(tab("What to build into the RTL before the board arrives",
        ["Feature", "Cost", "What it saves"],
        [["<b>ID register with a known constant</b>", "a dozen gates",
          "<b>Six hypotheses in one read</b>"],
         ["Scratch register", "32 flops", "Separates the write path from the function"],
         ["<b>Internal loopback</b>", "a multiplexer",
          "<b>Splits &lsquo;inside the chip&rsquo; from &lsquo;outside&rsquo; &mdash; "
          "the one clean partition</b>"],
         ["Per-stage error counters, saturating", "a counter each",
          "Tells you <i>which</i> stage, not just that something failed"],
         ["Snapshot register on first error", "a register set and a sticky bit",
          "<b>The first failure is the debuggable one; the thousandth is not</b>"],
         ["State register readable", "wires",
          "A stuck state machine names itself"],
         ["Pattern generator and checker", "a small LFSR pair",
          "Removes the host from the loop &mdash; tests at line rate with no software"],
         ["On-chip logic analyser trigger outputs", "a few wires",
          "Lets the bundled analyser trigger on your condition, not on time"]]))
    s.append("""<div class="ms"><b>All eight are cheap, and all eight must exist before
    the board arrives.</b> Adding instrumentation during bring-up means a rebuild, and a
    rebuild on a large FPGA is an hour you spend staring at a progress bar while the
    failure is still unexplained. The habit worth forming is to write the debug features
    in the same sitting as the datapath they observe, when you still remember what could
    go wrong with it. <b>They are also a sales feature</b>: a customer bringing your block
    up in their chip has exactly the same problem you did, and a block that names its own
    failures is materially cheaper for them to integrate &mdash; which is the argument
    Part&nbsp;Y5 makes about support cost, arriving as concrete RTL.</div>""")
    s.append(prob("You have no partner hardware and no budget for it. Can you still "
                  "claim interoperability?",
        "No, and saying so is better than the alternatives. What you <i>can</i> claim, "
        "precisely, is conformance: &lsquo;passes the standard's test vectors&rsquo;, "
        "&lsquo;matches the reference implementation bit for bit on <i>n</i> random "
        "cases&rsquo;, &lsquo;runs at line rate against an open-source implementation of "
        "the far end&rsquo;. That last one is the most useful and the most overlooked "
        "&mdash; for most protocols in this book an open implementation exists, and "
        "running against it is a genuine second implementation even though it is not a "
        "product. <b>Then say what is untested and what it would take.</b> A customer "
        "who reads &lsquo;interoperability not yet demonstrated; we have run against "
        "<i>X</i> and the gap is a plugfest&rsquo; can decide whether to lend you "
        "hardware, which happens more often than a first-time vendor expects, or to "
        "treat it as a risk they price. <b>A customer who reads an interoperability "
        "claim that turns out to mean &lsquo;against ourselves&rsquo; stops reading the "
        "rest of the datasheet.</b>"))
    return "\n".join(s)
