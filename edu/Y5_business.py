# -*- coding: utf-8 -*-
"""Volume III, Part Y5 -- The commercial mechanics of selling an IP block."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_business2():
    s = ['<h1 id="y5">Y5. The Commercial Mechanics of Selling an IP Block</h1>']
    s.append("""<p>A design house that cannot price, license and support its work does not
    have a business, it has a hobby with good documentation. This part gives the
    arithmetic of the commercial side with the same seriousness as the technical parts,
    because the failure modes are just as specific and rather less discussed.</p>""")

    s.append("<h2>Y5.1 The three revenue models and when each applies</h2>")
    s.append(tab("How semiconductor IP is actually sold",
        ["Model", "Customer pays", "Suits", "Risk to you", "Risk to them"],
        [["<b>Licence + royalty</b>", "A licence fee, then a per-unit royalty",
          "High volume, standard function",
          "<b>Royalty depends on their success and their honesty</b> &mdash; audit "
          "rights matter",
          "Ongoing cost; they will try to convert it to a buyout"],
         ["Paid-up / perpetual licence", "One fee, unlimited units",
          "Customers who cannot tolerate per-unit accounting",
          "You capture none of their upside", "Large up-front commitment"],
         ["<b>Services / NRE</b>", "Engineering time",
          "<b>Where a one-person house should start</b>",
          "No leverage &mdash; you are paid once for each hour",
          "Low; they own the result"],
         ["Subscription", "Annual fee for access and updates",
          "Rapidly changing standards", "Churn", "Dependence on your survival"],
         ["Open core + support", "Support and customisation",
          "Building reputation from nothing", "Hard to monetise", "Very low"]]))
    s.append(ex("When a royalty beats a buyout, from the customer's side",
        "A block licensed at $150&#8239;000 plus $0.20 per unit, or $600&#8239;000 "
        "paid up. The customer's forecast is 1&nbsp;million units over three years, but "
        "forecasts in this market are routinely out by 3&times; in both directions.",
        "Compute the break-even volume, then compute what each party's exposure is "
        "above and below it. The break-even is arithmetic; the interesting part is the "
        "asymmetry around it.",
        [("Break-even volume", num(int((600000 - 150000) / 0.20))),
         ("Royalty model cost at 1M units", num(150000 + 1e6 * 0.20, 5, "USD")),
         ("Buyout cost", num(600000, 5, "USD")),
         ("Royalty cost at 0.3M units (forecast &divide; 3)",
          num(150000 + 0.3e6 * 0.20, 5, "USD")),
         ("Royalty cost at 3M units", num(150000 + 3e6 * 0.20, 5, "USD")),
         ("Your revenue at 3M units under buyout", num(600000, 5, "USD")),
         ("Your revenue at 3M units under royalty",
          num(150000 + 3e6 * 0.20, 5, "USD"))],
        "<b>By negotiating the break-even and not the distribution.</b> Both parties can "
        "compute 2.25&nbsp;million units; what decides the deal is who is more confident "
        "and who can bear the downside. A one-person house with no cash reserve should "
        "prefer the larger up-front fee even at a worse expected value, because "
        "<b>surviving to the next contract dominates expected value when a single bad "
        "quarter ends the business</b>. The standard compromise is a royalty with a "
        "cap and a floor, which bounds both parties' exposure and is easier to agree "
        "than either extreme."))

    s.append("<h2>Y5.2 What a customer actually receives</h2>")
    s.append(tab("The delivery package, item by item",
        ["Item", "Form", "Why it is not optional"],
        [["RTL", "Encrypted or plain SystemVerilog",
          "The product &mdash; but the smallest part of the package"],
         ["Testbench and tests", "UVM or equivalent, runnable",
          "<b>The customer must be able to re-verify after editing</b>; without it "
          "your block becomes untouchable and therefore unusable"],
         ["Reference model", "C or C++, bit-accurate",
          "Their system model needs it; also it is what makes your claims checkable"],
         ["Synthesis scripts and constraints", "SDC plus a script",
          "Timing closure in <i>their</i> flow is where integrations fail"],
         ["Lint and CDC waivers", "Files with justifications",
          "Their sign-off will run these tools; unexplained violations stop the project"],
         ["<b>IP-XACT / integration metadata</b>", "<b>XML</b>",
          "<b>Automated integration; increasingly a purchase requirement</b>"],
         ["Register map", "Generated from one source",
          "Hand-maintained duplicates diverge, and the divergence is discovered by "
          "software at the worst time"],
         ["Documentation", "Datasheet, integration guide, release notes",
          "Support cost is inversely proportional to documentation quality"],
         ["Known-issue list", "A document",
          "<b>Omitting it does not remove the issues, it removes your credibility "
          "when they are found</b>"]]))
    s.append("""<div class="ms"><b>The known-issue list is the item that distinguishes a
    professional supplier, and it is counter-intuitive to first-time vendors.</b> Every
    block has limitations: a configuration that was never verified, a corner that fails a
    lint rule for a defensible reason, a performance figure that holds only above a
    certain clock ratio. A customer who finds these themselves concludes you did not know;
    a customer who reads them in your release notes concludes you did. <b>The second
    customer calls you when they have a problem instead of calling your competitor.</b>
    Write the list, keep it honest, and put dates and workarounds beside each
    entry.</div>""")

    s.append("<h2>Y5.3 Support: the cost nobody budgets</h2>")
    rows = []
    for n_cust, q_per in ((1, 40), (3, 30), (5, 25), (10, 20), (20, 18)):
        q = n_cust * q_per
        hrs = q * 1.5
        rows.append([num(n_cust), num(q_per), num(q), num(hrs),
                     num(hrs / 1800 * 100, 3), num(hrs / 8 / 5, 3)])
    s.append(sweep("Support load against customer count, at 1.5 engineer-hours per query",
        ["Customers", "Queries per customer per year", "Queries per year",
         "Engineer-hours", "% of a person-year (1800 h)", "Working weeks"], rows,
        "Queries per customer fall with experience because the documentation improves "
        "and the frequent questions get answered in it. <b>At twenty customers support "
        "is a full-time job</b>, which for a one-person house means either hiring, "
        "raising prices to slow growth, or investing hard in documentation and "
        "self-service &mdash; and the third is the only one available immediately."))
    s.append(ex("Pricing that accounts for support",
        "You expect 8 customers over three years for a block that took 44 weeks to "
        "build. Target: recover the build and support and earn a living. Your cost of "
        "living plus overhead is $120&#8239;000 a year.",
        "Total the engineering, add the support from the table above, and divide. "
        "Then compare with what the market will bear, because the two are independent "
        "numbers and the smaller one wins.",
        [("Build effort", num(44, 3) + " weeks"),
         ("Support over 3 years at 8 customers",
          num(8 * 22 * 1.5 * 3 / 40, 3) + " weeks"),
         ("Total effort", num(44 + 8 * 22 * 1.5 * 3 / 40, 4) + " weeks"),
         ("Cost at $120k/year", num((44 + 8 * 22 * 1.5 * 3 / 40) / 52 * 120000, 5, "USD")),
         ("Break-even price per customer",
          num((44 + 8 * 22 * 1.5 * 3 / 40) / 52 * 120000 / 8, 5, "USD")),
         ("With a 40&nbsp;% margin",
          num((44 + 8 * 22 * 1.5 * 3 / 40) / 52 * 120000 / 8 / 0.6, 5, "USD")),
         ("If only 3 customers materialise",
          num((44 + 3 * 22 * 1.5 * 3 / 40) / 52 * 120000 / 3 / 0.6, 5, "USD"))],
        "<b>By pricing from cost and ignoring the market.</b> The last row is the real "
        "risk: with three customers instead of eight, the price that covers cost is "
        "more than double, and there is no reason a customer will pay it. The standard "
        "mitigations are to <b>start with services revenue</b>, which is paid whether "
        "or not the block sells; to <b>sell the first block below cost to a reference "
        "customer</b> in exchange for a public reference, which is worth more than the "
        "margin; and to <b>build blocks whose adjacent variants share most of the "
        "effort</b>, so the second customer in a family costs a fraction of the "
        "first."))

    s.append("<h2>Y5.4 Legal and quality items that bite a small vendor</h2>")
    s.append(tab("Contractual terms and what each one means in practice",
        ["Term", "What the customer wants", "What you should watch"],
        [["Indemnification", "You cover patent claims against the block",
          "<b>Cap it at fees received.</b> Uncapped indemnity can exceed the company's "
          "value; it is the single most dangerous clause for a small vendor"],
         ["Warranty", "The block conforms to the specification",
          "Define the specification precisely and tie the warranty to it, not to "
          "&lsquo;fitness for purpose&rsquo;"],
         ["Escrow", "Source held by a third party in case you disappear",
          "Reasonable; budget the fee and keep the deposit current"],
         ["Acceptance criteria", "A defined test they run",
          "<b>Insist the criteria be written and runnable before delivery.</b> "
          "Undefined acceptance is an unbounded obligation"],
         ["Exclusivity", "Nobody else gets the block",
          "Price it as the lost market, and time-limit it"],
         ["Support term", "Years of updates",
          "Define what an update is; a new standard revision is a new product"]]))
    s.append("""<div class="warn"><b>Provenance of the source you ship is a hard
    requirement, not a formality.</b> If any part of your block derives from code with a
    copyleft licence, or from a previous employer's work, or from a reference design with
    redistribution limits, a customer's legal review will find it &mdash; they scan for
    this &mdash; and the deal ends there. Keep a per-file record of origin, do not paste
    from sources you cannot name, and be able to produce that record on request. <b>The
    code appendix of this book is an illustration of the standard</b>: every file
    reproduced in it is named with its repository and its line count, and a reader can
    trace any line back to its source.</div>""")
    s.append(prob("A prospective customer asks for a three-month free evaluation with "
                  "full source. How do you respond?",
        "Not with a flat refusal, and not with the source. The request is reasonable in "
        "intent &mdash; they cannot buy what they cannot assess &mdash; and unreasonable "
        "in form, because full source for three months is the product. The standard "
        "structures, in increasing order of what you give away: an <b>evaluation "
        "package</b> of documentation, the datasheet, the register map and simulation "
        "results, which costs you nothing and answers most questions; an <b>encrypted or "
        "obfuscated netlist or FPGA bitstream</b> they can integrate and measure but not "
        "read, which answers the performance question; and a <b>paid evaluation licence</b> "
        "whose fee is credited against the full licence if they proceed, which aligns "
        "both parties and filters out tyre-kickers at no cost to a serious buyer. "
        "<b>The paid evaluation is the one to propose</b>; a customer who will not pay a "
        "small fee to evaluate is very unlikely to pay a large one to license."))
    s.append(prob("Your block has been shipping for a year when a customer reports a bug "
                  "that affects every unit they have built. What do you do, in order?",
        "<b>Reproduce it before saying anything about cause.</b> Ask for the "
        "configuration, the stimulus and the failing condition, and reproduce it in your "
        "own environment; a report is a hypothesis. <b>Then determine the blast radius</b> "
        "&mdash; which configurations, which versions, which other customers &mdash; "
        "because the answer determines whether this is one email or a notification to "
        "everyone. <b>Then notify affected customers before they find it</b>, with what "
        "is known, what is not, and when the next update will come; a vendor who reports "
        "their own bug keeps the account, and one who is caught concealing it does not. "
        "<b>Then fix, with a regression test that would have caught it</b>, and say in "
        "the release notes what that test is. <b>Finally, ask why the verification plan "
        "missed it</b> and fix the plan, not just the code &mdash; Part&nbsp;X8's "
        "mutation argument applies directly: if the suite did not catch this, inject it "
        "and find out what else of the same shape it would miss."))
    return "\n".join(s)
