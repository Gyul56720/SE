# -*- coding: utf-8 -*-
"""Volume III, Part Y9 -- Standards, compliance and interoperability."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_compliance():
    s = ['<h1 id="y9">Y9. Standards, Compliance and Interoperability</h1>']
    s.append("""<p>A protocol block is worth what it can be shown to interoperate with.
    That showing is a separate activity from verification, with its own vocabulary, its
    own costs and its own failure modes, and it is the part of the work that first-time
    vendors most consistently under-budget. This part lays it out.</p>""")

    s.append("<h2>Y9.1 Three different things called &lsquo;testing&rsquo;</h2>")
    s.append(tab("What each activity proves and what it does not",
        ["Activity", "Question answered", "Who runs it", "What it misses"],
        [["<b>Verification</b>", "Does the block do what I specified?",
          "You", "<b>Whether your reading of the standard is right</b>"],
         ["<b>Conformance</b>", "Does the block do what the standard says?",
          "You, or a test house, against a published test suite",
          "Whether real partners interoperate &mdash; conformant implementations can "
          "still fail together"],
         ["<b>Interoperability</b>", "Does it work with this specific partner?",
          "A plugfest, or a lab with partner equipment",
          "Partners not present; the next revision"],
         ["Certification", "Will the body let me use the logo?",
          "An accredited laboratory",
          "Everything above &mdash; it is a process outcome, not a technical one"]]))
    s.append("""<div class="warn"><b>Two conformant implementations can fail to
    interoperate, and the reason is structural rather than anyone's fault.</b> Standards
    contain optional features, permitted ranges and ambiguous sentences. If your block
    implements an option and the partner does not, both conform and neither works with the
    other unless the negotiation that selects it is itself implemented correctly on both
    sides &mdash; and negotiation code is under-tested everywhere, because testing it
    requires a partner that behaves differently from you. <b>The practical consequence is
    that the negotiation and fallback paths deserve more verification effort than the
    steady-state datapath</b>, which is the opposite of where effort naturally goes.
    In every protocol in this book, the bugs found at plugfests are concentrated in link
    training, capability exchange and error recovery.</div>""")

    s.append("<h2>Y9.2 The cost of a standard, itemised</h2>")
    rows = [
        ["The specification document", "$0&ndash;$5,000 per document",
         "Some are free (IETF); most industry standards are not"],
        ["Body membership", "$5,000&ndash;$50,000+ per year",
         "Often required to obtain drafts, to attend, or to use the name"],
        ["Test suite or test equipment", "$10,000&ndash;$200,000+",
         "Protocol analysers and compliance fixtures; rentable"],
        ["Plugfest attendance", "$2,000&ndash;$10,000 per event plus travel",
         "<b>The highest-value line in this table per dollar</b>"],
        ["Accredited laboratory testing", "$10,000&ndash;$100,000 per campaign",
         "Where a logo is required"],
        ["Engineering time to fix what it finds", "4&ndash;12 weeks",
         "<b>The line that is always omitted from the budget</b>"],
    ]
    s.append(sweep("What conformance costs before any revenue arrives",
        ["Item", "Order of magnitude", "Note"], rows,
        "<b>Ranges, not quotations</b> &mdash; the actual figures depend on the body and "
        "the year, and this repository has not obtained current price lists. The purpose "
        "of the table is to prevent the commonest planning error, which is budgeting zero "
        "for all six rows."))
    s.append(ex("Whether to certify at all",
        "A block that could be sold with or without a logo. Certification costs "
        "$60&#8239;000 and eight weeks. Without it you expect 4 customers over three "
        "years at $80&#8239;000; with it you expect 7, and you can charge "
        "$95&#8239;000 because the logo removes a risk from the buyer's evaluation.",
        "Compute both revenues net of cost and time. Then note the factor the "
        "arithmetic does not contain.",
        [("Revenue without certification", num(4 * 80000, 5, "USD")),
         ("Revenue with certification", num(7 * 95000, 5, "USD")),
         ("Certification cost", num(60000, 5, "USD")),
         ("Eight weeks of engineering at $120k/yr",
          num(8 / 52 * 120000, 5, "USD")),
         ("Net with certification",
          num(7 * 95000 - 60000 - 8 / 52 * 120000, 5, "USD")),
         ("Net without", num(4 * 80000, 5, "USD")),
         ("Difference", num(7 * 95000 - 60000 - 8 / 52 * 120000 - 4 * 80000, 5, "USD"))],
        "<b>By treating the customer counts as data.</b> They are forecasts, and the "
        "forecast with certification is the one you have least evidence for, since it is "
        "the counterfactual. The robust way to use this calculation is not to trust its "
        "output but to find the break-even customer count and ask whether it is "
        "plausible: here certification pays if it brings even one additional customer at "
        "the higher price. <b>Framed that way the decision is usually easy</b>, and the "
        "arithmetic has done its job by converting an argument about strategy into a "
        "question about one number."))

    s.append("<h2>Y9.3 Getting value from a plugfest</h2>")
    s.append(tab("Before, during and after",
        ["Phase", "Do", "Do not"],
        [["Weeks before", "Test against every partner implementation you can obtain, "
          "including open-source ones; exercise every negotiation path",
          "Arrive to discover a problem you could have found at home"],
         ["Bring", "Two of everything, a logic analyser or protocol analyser, a way to "
          "rebuild and reload on site, and a colleague if possible",
          "Rely on borrowing; the other vendors are busy"],
         ["Instrument", "Counters, snapshot registers, and a way to capture the first "
          "failing exchange",
          "Debug by re-running and watching"],
         ["<b>Record</b>", "<b>Every partner, every configuration, every result &mdash; "
          "including the ones that worked</b>",
          "Remember it afterwards; you will not"],
         ["When something fails", "Determine which side deviates from the text before "
          "discussing it",
          "Assert that the partner is wrong &mdash; roughly half the time it is you"],
         ["After", "Turn every failure into a regression test; publish an "
          "interoperability list",
          "Fix the symptom and move on"]]))
    s.append("""<div class="ms"><b>The interoperability list is a sales document as much
    as an engineering one.</b> &lsquo;Tested against these seven implementations, at these
    configurations, on these dates&rsquo; answers the question a buyer cannot otherwise
    answer about a supplier they do not know, and it answers it with something checkable.
    It also has a defensive function: when a customer reports an interoperability failure
    with an eighth partner, the list makes it immediately clear that this is new
    territory rather than a regression, which changes the conversation entirely. <b>Keep
    it current and date every row</b>; a list without dates is read as a list of claims
    rather than of tests.</div>""")
    s.append(prob("A partner at a plugfest insists your implementation is wrong. You "
                  "believe theirs is. How do you proceed?",
        "Stop arguing and go to the text, together. Find the clause, read it aloud, and "
        "establish what each implementation does at that point in the exchange with a "
        "capture rather than with an assertion. Three outcomes follow and all three are "
        "useful. <b>The text is clear and you are wrong</b>: fix it, and you have "
        "discovered a real bug cheaply. <b>The text is clear and they are wrong</b>: show "
        "them, courteously, and consider whether to interoperate with their behaviour "
        "anyway &mdash; if they ship in volume, your customers will meet them, and a "
        "conformant block that fails against a popular partner is a commercial problem "
        "whoever is right. <b>The text is ambiguous</b>: this is the most valuable "
        "outcome, because it means everyone has the problem. Raise it with the working "
        "group; a clarification with your name on it is reputation, and it is one of the "
        "few ways a small house becomes visible to the people who buy. <b>In all three "
        "cases the conduct matters more than the verdict</b>: plugfests are small worlds "
        "and the engineer across the table is a future customer, partner or employer."))
    s.append(prob("Why should a soft-IP vendor care about compliance at all, when the "
                  "customer's chip is what gets certified?",
        "Because the customer's certification failure becomes your problem regardless of "
        "whose name is on the certificate. Practically, three things follow. <b>Your "
        "block must be testable in their chip</b>: the compliance tests require modes "
        "&mdash; loopback, pattern generation, error injection, counter read-out &mdash; "
        "that must exist in the RTL and be reachable from their software, and adding them "
        "late is expensive. <b>You must supply the evidence they will be asked for</b>: "
        "which clauses your block implements, which options, which are the customer's "
        "responsibility. And <b>you should have run what you can run yourself</b>, "
        "because a block that has never seen a compliance suite will fail one, and it is "
        "far cheaper to fail it in your lab than in theirs. <b>A vendor who arrives with "
        "a clause-by-clause implementation statement and their own test results is "
        "selling a lower-risk product</b>, and that is precisely what the premium in "
        "protocol IP is paid for."))
    return "\n".join(s)
