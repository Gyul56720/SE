# -*- coding: utf-8 -*-
"""Volume III, Part Z8 -- The money: a one-person house's actual arithmetic."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def ch_money():
    s = ['<h1 id="z8">Z8. The Money</h1>']
    s.append("""<p>Part&nbsp;Y5 covers licensing structures. This part is narrower and
    more uncomfortable: what a one-person house's first three years look like as numbers,
    where the money actually goes, and which of the failure modes are arithmetic rather
    than bad luck.</p>""")

    s.append("<h2>Z8.1 The cost base</h2>")
    rows = [
        ["Your living cost", "$40k&ndash;$120k / yr", "The dominant term. Everything "
         "else is noise beside it"],
        ["<b>Standards membership and documents</b>", "$0&ndash;$50k / yr",
         "<b>Zero for open standards, five figures for some bodies &mdash; and this "
         "is a gate, not a preference</b> (Part Z5)"],
        ["EDA tools", "$0&ndash;$50k / yr",
         "<b>$0 is viable for soft IP</b> (Part Y14); the line appears only if you "
         "must sign off"],
        ["Compute", "$0&ndash;$3k / yr", "<b>Genuinely small.</b> The agent runs on "
         "one machine overnight"],
        ["FPGA bench", "$500&ndash;$5k one-off", "Part Z7"],
        ["Legal (contract templates, one review)", "$2k&ndash;$10k one-off",
         "<b>Do not skip the indemnity review</b> &mdash; Part Y5"],
        ["Accounting, insurance, entity", "$1k&ndash;$5k / yr", "Jurisdiction dependent"],
        ["Conferences and plugfests", "$2k&ndash;$10k / yr",
         "<b>The highest-return line per dollar</b> for a house nobody has heard of"],
    ]
    s.append(sweep("Where the money goes in year one",
        ["Item", "Order of cost", "Note"], rows,
        "<b>Ranges, not quotations</b> &mdash; they vary by country, body and year, and "
        "this repository has not obtained current price lists. The shape is what "
        "transfers: <b>your time is the cost base and almost everything else is "
        "optional or small</b>, with the two exceptions in bold."))
    s.append("""<div class="ms"><b>Read the tools line against the standards line.</b> The
    received wisdom is that EDA licences are what keep individuals out of chip design. For
    <i>soft IP</i> that is no longer true &mdash; Part&nbsp;Y14 measures a complete
    model-to-synthesis flow at zero &mdash; and the barrier has moved to a less discussed
    place: <b>the specification</b>. A protocol block you cannot legally read the standard
    for cannot be built at any price, and some bodies' membership is a five-figure annual
    commitment before a line of RTL exists. <b>That is the real gate, and it is why
    Part&nbsp;Z5 weights &lsquo;specification obtainable&rsquo; at 3</b> and why the
    post-quantum candidate scores so well: NIST published everything.</div>""")

    s.append("<h2>Z8.2 Three years, three scenarios</h2>")
    def 시나리오(이름, 서비스, 라이선스, 건수, 비용):
        수입 = [서비스[i] + 라이선스 * 건수[i] for i in range(3)]
        누적 = []
        c = 0
        for i in range(3):
            c += 수입[i] - 비용
            누적.append(c)
        return [이름] + [num(수입[i] / 1000, 4) for i in range(3)] + \
               [num(누적[-1] / 1000, 4),
                "<b>생존</b>" if 누적[-1] > 0 and min(누적) > -60000 else
                ("아슬" if 누적[-1] > 0 else "<b>못 버틴다</b>")]
    비용 = 120000
    rows = [
        시나리오("서비스만 (계약 검증·모델링)", [90000, 130000, 150000], 0, [0, 0, 0], 비용),
        시나리오("서비스 + 블록 하나", [70000, 60000, 40000], 80000, [0, 1, 2], 비용),
        시나리오("블록만, 고객 없이 시작", [0, 0, 0], 80000, [0, 1, 3], 비용),
        시나리오("블록 가족 (둘째가 싸다)", [60000, 40000, 20000], 80000, [0, 2, 4], 비용),
    ]
    s.append(sweep("Three years at a $120k/yr cost base, revenue in thousands",
        ["Path", "Year 1", "Year 2", "Year 3", "Cumulative", "Verdict"], rows,
        "<b>Illustrative numbers, computed from the stated assumptions</b> &mdash; not "
        "a forecast and not anyone's actual results. The purpose is the ranking, which "
        "is robust to changing the inputs: <b>the row that starts with no revenue is "
        "the row that does not survive</b>, and it is the row most first-time houses "
        "choose because it is the most technically satisfying."))
    s.append(ex("How long the runway has to be",
        "You have savings <i>S</i>, a cost base of $120k/yr, and the first licence "
        "revenue lands in month <i>M</i>.",
        "Compute the required savings for several values of <i>M</i>, and note what "
        "determines <i>M</i>.",
        [("Cost per month", num(10000, 5, "USD")),
         ("First revenue at month 12", num(120000, 6, "USD") + " needed"),
         ("At month 18", num(180000, 6, "USD")),
         ("At month 24", num(240000, 6, "USD")),
         ("Part Y8's block takes", "39 weeks &asymp; 9 months to <b>build</b>"),
         ("Then evaluation, negotiation, integration",
          "<b>3&ndash;9 months more before money moves</b>"),
         ("So realistic <i>M</i> without services", "<b>18&ndash;24</b>"),
         ("With services from month 1", "<b>M does not matter</b>")],
        "<b>By budgeting the build and not the sale.</b> The nine months are the part "
        "you control and the least of it; a customer's evaluation, legal review and "
        "purchase cycle is measured in quarters and does not start until the block "
        "exists. <b>That gap is why Part&nbsp;Y8 recommends services first</b>, and the "
        "recommendation is not about risk appetite &mdash; it is that the alternative "
        "requires two years of savings, and the failure mode is running out three weeks "
        "before the first sale, at which point the asset is worth nothing to you."))

    s.append("<h2>Z8.3 Pricing the first block</h2>")
    s.append(tab("Four ways to set the first price, and what each signals",
        ["Approach", "Number", "What the customer reads"],
        [["Cost plus margin", "Part Y5's arithmetic",
          "<b>Nothing &mdash; they cannot see your cost</b>"],
         ["<b>Fraction of their alternative</b>",
          "<b>What it would cost them to build it</b>",
          "<b>The only argument that lands.</b> Their engineer-year is the comparison"],
         ["Market comparable", "What incumbents charge",
          "Credible if you can name the comparables; weak if you cannot"],
         ["Below cost for a reference", "Low, explicitly one-off",
          "<b>Rational once</b>, and only with a written reference commitment in "
          "exchange"]]))
    s.append("""<div class="warn"><b>Do not discount to win the first deal without getting
    something back for it.</b> The discount is defensible &mdash; a first customer takes a
    real risk on an unproven supplier and a public reference is worth more to you than the
    margin. What is not defensible is giving it away quietly: the price becomes the
    anchor for every subsequent negotiation, the customer's procurement remembers it, and
    you have bought nothing. <b>Trade it explicitly</b>: a named reference, a quotable
    result, an introduction, or a commitment to the second block in the family at full
    price. Write the exchange into the contract, because a verbal promise of a reference
    does not survive a change of contact.</div>""")
    s.append(prob("A customer asks for source code escrow, unlimited indemnity, and a "
                  "five-year support commitment. Which do you agree to?",
        "<b>Escrow: yes</b>, and budget the annual fee. It is a reasonable request from "
        "anyone betting a product on a one-person supplier, and refusing it confirms "
        "exactly the risk they are worried about. Keep the deposit current &mdash; a "
        "stale escrow is worse than none, because it creates false comfort. "
        "<b>Unlimited indemnity: no</b>, and this is the one to hold. Cap it at fees "
        "received, which is standard and which a competent counterparty will accept; "
        "uncapped IP indemnity can exceed the value of everything you own, and no price "
        "compensates for that because the loss is unbounded. If they will not move, the "
        "deal is not worth doing at any price. <b>Five-year support: yes, with the "
        "scope defined.</b> Define what an update is &mdash; bug fixes in the delivered "
        "version, yes; a new revision of the standard, no, that is a new product &mdash; "
        "define a response time you can actually meet alone including holidays, and "
        "price the years beyond the first separately. <b>The general rule is that the "
        "ones to resist are the unbounded ones</b>, not the expensive ones; expensive is "
        "a number you can put in the quote, unbounded is not."))
    return "\n".join(s)
