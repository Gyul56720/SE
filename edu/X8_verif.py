# -*- coding: utf-8 -*-
"""Volume I, Part X8 -- The mathematics of verification, worked.

Verification is usually taught as a methodology.  Underneath it there is
arithmetic -- coupon collection, coverage saturation, bug discovery curves, the
cost of a late escape -- and that arithmetic is what decides how long a
regression must run and when it is rational to stop.  A modelling engineer who
can do it is the one whose schedule estimates turn out to be right.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_verifmath():
    s = ['<h1 id="x8">X8. The Mathematics of Verification, Worked</h1>']
    s.append("""<p>Three questions decide a verification plan: how long must random
    stimulus run to reach a coverage target, how many bugs remain when the discovery rate
    flattens, and what a bug costs at each stage. All three have arithmetic answers. None
    of them is a substitute for judgement, but a plan that contradicts the arithmetic
    needs a reason.</p>""")

    s.append("<h2>X8.1 Coverage closure is a coupon-collector problem</h2>")
    s.append(derive("How long random stimulus takes to hit every bin", [
        ("Suppose there are <i>n</i> coverage bins, each hit with equal probability "
         "1/<i>n</i> by an independent random transaction.",
         "The idealisation. Real bins are neither equiprobable nor independent, and "
         "X8.2 measures what that does."),
        ("After the <i>k</i>th distinct bin is hit, the probability that the next "
         "transaction hits a new bin is (<i>n</i>&minus;<i>k</i>)/<i>n</i>.",
         "Uniformity."),
        ("So the expected wait for the next new bin is <i>n</i>/(<i>n</i>&minus;<i>k</i>).",
         "Mean of a geometric distribution."),
        ("Total expected transactions = <i>n</i> &Sigma;<sub><i>k</i>=1..<i>n</i></sub> "
         "1/<i>k</i> = <i>nH<sub>n</sub></i> &asymp; <i>n</i>(ln <i>n</i> + 0.577).",
         "Sum the waits; <i>H<sub>n</sub></i> is the harmonic number."),
        ("<b>For 90&nbsp;% of the bins, the sum truncates and the cost is only "
         "<i>n</i>&nbsp;ln&nbsp;10 &asymp; 2.3<i>n</i>.</b>",
         "&Sigma; from 1 to 0.9<i>n</i> of 1/(<i>n</i>&minus;<i>k</i>). <b>This is the "
         "whole shape of every coverage curve you have ever seen</b>: cheap to 90&nbsp;%, "
         "expensive to 100&nbsp;%."),
    ]))
    rows = []
    for n in (100, 1000, 10000, 100000):
        H = sum(1.0 / k for k in range(1, n + 1))
        rows.append([num(n), num(int(n * math.log(10))), num(int(n * math.log(100))),
                     num(int(n * H)), num(n * H / (n * math.log(10)), 3)])
    s.append(sweep("Expected random transactions to reach a coverage target, "
                   "equiprobable bins",
        ["Bins <i>n</i>", "To 90&nbsp;%", "To 99&nbsp;%", "To 100&nbsp;%",
         "Cost of the last 10&nbsp;% as a multiple of the first 90&nbsp;%"], rows,
        "The last column is roughly constant at about four, independent of <i>n</i>. "
        "<b>The final ten per cent of coverage costs three times what the first ninety "
        "did</b>, every time, and that is before the bins turn out to be unequal."))
    s.append(plot(list(range(1, 100)),
                  [("expected transactions / n",
                    [sum(1.0 / (1000 - k) for k in range(0, int(10 * p)))
                     for p in range(1, 100)])],
                  "coverage target (% of 1000 bins)", "transactions / n",
                  "The coupon-collector curve for 1000 bins. It is not that the last "
                  "bins are harder to hit by design; they are harder to hit because "
                  "there are fewer of them left to hit by accident."))
    s.append(ex("Sizing a regression from a coverage model",
        "A block has 8000 coverage bins. One simulation runs 40&#8239;000 transactions "
        "and takes 6 minutes. The target is 99&nbsp;% coverage. 200 simulations can run "
        "in parallel.",
        "Convert the bin count to a transaction count with the coupon-collector "
        "estimate, then to simulations, then to wall-clock time.",
        [("Transactions to 99&nbsp;%", num(int(8000 * math.log(100)))),
         ("Simulations needed", num(math.ceil(8000 * math.log(100) / 40000))),
         ("Serial machine-time",
          num(math.ceil(8000 * math.log(100) / 40000) * 6 / 60, 3, "hours")),
         ("Wall clock on 200 in parallel", "&lt; 1 run &mdash; the pool is not the limit"),
         ("Transactions to 100&nbsp;% (harmonic sum)",
          num(int(8000 * sum(1.0 / k for k in range(1, 8001))))),
         ("Simulations for 100&nbsp;%",
          num(math.ceil(8000 * sum(1.0 / k for k in range(1, 8001)) / 40000)))],
        "<b>By concluding that random stimulus will therefore close coverage.</b> The "
        "model assumes every bin is reachable by random stimulus with equal probability. "
        "In practice a handful of bins require a specific sequence &mdash; a FIFO full "
        "while a retry is in flight and a parity error arrives &mdash; whose random "
        "probability is not 1/<i>n</i> but 10<sup>&minus;9</sup>. <b>Those bins never "
        "close randomly and no amount of compute changes that</b>; they close with "
        "directed tests or constrained scenarios. The arithmetic above tells you how much "
        "compute to buy for the easy 99&nbsp;%, and identifying the remaining bins as "
        "requiring direction is the actual verification engineering."))
    # unequal bins
    rng = np.random.default_rng(9)
    rows = []
    for skew in (0.0, 0.5, 1.0, 1.5, 2.0):
        n = 1000
        w = np.exp(-skew * np.arange(n) / n)
        w = w / w.sum()
        hits = np.zeros(n, dtype=bool)
        cnt = 0
        step = 2000
        while hits.mean() < 0.99 and cnt < 20_000_000:
            idx = rng.choice(n, size=step, p=w)
            hits[idx] = True
            cnt += step
        rows.append([num(skew, 3), num(float(w.max() / w.min()), 3), num(cnt),
                     num(cnt / (n * math.log(100)), 3)])
    s.append(sweep("Measured transactions to 99&nbsp;% coverage of 1000 bins as the bin "
                   "probabilities are made unequal",
        ["Skew parameter", "Most likely : least likely bin", "Transactions measured",
         "Multiple of the equiprobable estimate"], rows,
        "An exponential weighting with the stated skew, measured by simulation with "
        "seed&nbsp;9. Even a 7:1 spread between the most and least likely bin multiplies "
        "the cost noticeably; real constraint solvers produce far larger spreads than "
        "that, which is why <b>coverage convergence is slower than any model predicts "
        "and why the remedy is to reshape the constraints, not to buy machines.</b>"))

    s.append("<h2>X8.2 Bug discovery curves and when to stop</h2>")
    s.append("""<p>Bugs are found at a rate that decays roughly exponentially with effort,
    because the easy ones go first. Fitting that decay gives an estimate of how many
    remain &mdash; an estimate that is crude, defensible, and far better than the
    alternative, which is a feeling.</p>""")
    rows = []
    N0, lam = 240.0, 0.18
    for wk in (2, 4, 6, 8, 10, 12, 16, 20):
        found = N0 * (1 - math.exp(-lam * wk))
        rate = N0 * lam * math.exp(-lam * wk)
        rows.append([num(wk), num(int(found)), num(rate, 3),
                     num(int(N0 - found)), num((N0 - found) / N0 * 100, 3)])
    s.append(sweep("An exponential bug-discovery model: 240 latent bugs, decay constant "
                   "0.18 per week",
        ["Week", "Cumulative found", "Bugs found this week", "Estimated remaining",
         "Remaining (%)"], rows,
        "The parameters are illustrative; the <i>method</i> is not. Fit the two "
        "parameters to your own weekly find-rate data and the extrapolation is a real "
        "estimate with a real confidence interval."))
    s.append(plot([2, 4, 6, 8, 10, 12, 16, 20],
                  [("cumulative found",
                    [N0 * (1 - math.exp(-lam * w)) for w in (2, 4, 6, 8, 10, 12, 16, 20)]),
                   ("remaining",
                    [N0 * math.exp(-lam * w) for w in (2, 4, 6, 8, 10, 12, 16, 20)])],
                  "week", "bugs",
                  "The two curves sum to a constant by construction. The decision to "
                  "tape out is the decision that the lower curve is acceptable."))
    s.append("""<div class="warn"><b>The find-rate falling is ambiguous and this is where
    projects deceive themselves.</b> A falling rate means either that the bugs are running
    out or that the <i>testing</i> is running out &mdash; the same tests re-run on the
    same stimulus find nothing new whether or not bugs remain. The two are distinguished
    by a measurement, not by an argument: <b>introduce new stimulus or a new checker and
    see whether the rate recovers</b>. Mutation testing does this systematically by
    injecting known faults and asking what fraction the existing suite catches; a suite
    that catches 60&nbsp;% of injected faults is telling you your find-rate curve has
    flattened for the wrong reason. This repository runs exactly such a hunt against its
    own checks.</div>""")
    rows = []
    for stage, cost, mult in [("Specification review", 1, "&mdash;"),
                              ("Modelling / C++ reference", 3, "3&times;"),
                              ("Block-level simulation", 10, "10&times;"),
                              ("Chip-level simulation", 40, "40&times;"),
                              ("Emulation / FPGA prototype", 100, "100&times;"),
                              ("First silicon bring-up", 1000, "1000&times;"),
                              ("Customer escape", 10000, "10&#8239;000&times;")]:
        rows.append([stage, num(cost), mult,
                     num(cost * 240 * 0.02, 3)])
    s.append(sweep("Relative cost of finding one bug at each stage, and the cost of "
                   "letting 2&nbsp;% of 240 bugs reach that stage",
        ["Stage found", "Relative cost", "vs. spec review", "Cost of 2&nbsp;% escaping "
         "to here (relative units)"], rows,
        "The multipliers are the industry's rule of thumb and vary by an order of "
        "magnitude between sources; the <b>shape</b> is what is robust. It is the reason "
        "a modelling team that catches specification ambiguities pays for itself many "
        "times over, and the reason design houses invest in the left-hand rows."))
    s.append(ex("Is another month of verification worth it?",
        "At week 12 the model above estimates 28 bugs remaining. A month of verification "
        "costs 4 engineer-months. Each bug that reaches silicon costs, on average, "
        "1&nbsp;engineer-month of debug; a respin costs 40 engineer-months plus three "
        "months of schedule, and the probability of a respin is roughly the probability "
        "that at least one remaining bug is functional-critical, estimated at 5&nbsp;% "
        "per remaining bug.",
        "Compute the expected cost of stopping now against the expected cost of "
        "continuing, using the discovery model to say how many bugs the extra month "
        "removes.",
        [("Bugs remaining at week 12", num(int(N0 * math.exp(-lam * 12)))),
         ("Bugs remaining at week 16", num(int(N0 * math.exp(-lam * 16)))),
         ("Bugs removed by the extra month",
          num(int(N0 * math.exp(-lam * 12) - N0 * math.exp(-lam * 16)))),
         ("P(no respin) if we stop now",
          num(0.95 ** (N0 * math.exp(-lam * 12)), 3)),
         ("P(no respin) if we continue",
          num(0.95 ** (N0 * math.exp(-lam * 16)), 3)),
         ("Expected respin cost now (engineer-months)",
          num((1 - 0.95 ** (N0 * math.exp(-lam * 12))) * 40, 4)),
         ("Expected respin cost after one more month",
          num((1 - 0.95 ** (N0 * math.exp(-lam * 16))) * 40, 4)),
         ("Saving from the extra month",
          num((0.95 ** (N0 * math.exp(-lam * 16)) -
               0.95 ** (N0 * math.exp(-lam * 12))) * 40, 4)),
         ("Cost of the extra month", num(4, 3)),
         ("Verdict",
          "<b>continue</b>" if (0.95 ** (N0 * math.exp(-lam * 16)) -
                                0.95 ** (N0 * math.exp(-lam * 12))) * 40 > 4
          else "stop")],
        "<b>By treating the model's parameters as known.</b> The decay constant is fitted "
        "from noisy weekly counts and its uncertainty propagates into the remaining-bug "
        "estimate, which sits inside an exponent. The right use of this calculation is "
        "not to produce a verdict but to find out <i>which assumption the verdict is "
        "sensitive to</i>: here it is the 5&nbsp;% criticality figure, and that figure "
        "can be improved by classifying the bugs already found, which is free. "
        "<b>Do the sensitivity analysis and go and measure the sensitive term.</b>"))
    s.append(prob("Your regression has 100&nbsp;% code coverage and 98&nbsp;% functional "
                  "coverage, and has found no new bug in three weeks. A reviewer asks "
                  "for evidence that the suite would catch a bug if one existed. What do "
                  "you provide?",
        "Code coverage is the weakest of the three and answering with it is the mistake: "
        "it shows lines executed, not behaviour checked, and a testbench with the checkers "
        "disabled reaches 100&nbsp;%. The evidence a reviewer should accept is <b>fault "
        "injection</b>: take the design, introduce a set of realistic mutations &mdash; "
        "invert a comparison, drop a reset term, change a FIFO threshold by one, delete a "
        "wait state &mdash; and report the fraction the existing suite catches, with the "
        "escapes listed and explained. A suite that catches 95&nbsp;% of mutations has "
        "made a falsifiable claim about itself. Supplement it with <b>checker coverage</b> "
        "(did each assertion ever fire in a passing run? an assertion that never even "
        "evaluated its antecedent is not checking anything) and with the <b>bug-find-rate "
        "recovery test</b> above: add genuinely new stimulus and see whether the rate "
        "moves. <b>Every one of these is a measurement of the testbench rather than of "
        "the design</b>, which is precisely what was asked for."))
    s.append(prob("Formal verification proves a property over all inputs. Why does a "
                  "project still simulate?",
        "Three reasons, in decreasing order of how often they bite. <b>Capacity</b>: "
        "proofs complete on control logic, arbiters, FIFOs and protocol interfaces, and "
        "commonly do not on a datapath with wide multipliers or on a whole subsystem; "
        "what comes back is a bounded proof, which is a very good simulation and not a "
        "proof. <b>Specification</b>: a formal tool proves the properties you wrote. A "
        "missing property is an unproven behaviour, and there is no coverage metric for "
        "&lsquo;properties I did not think of&rsquo; &mdash; though mutation coverage of "
        "the property set comes closest. <b>Environment</b>: proofs need constraints to "
        "exclude illegal inputs, and an over-constraint silently removes the case that "
        "would have failed &mdash; the formal equivalent of a false-green, and the one "
        "that has ended more than one post-silicon investigation. The two techniques are "
        "complementary in a specific way worth remembering: <b>formal is strong where "
        "state space is deep and narrow, simulation is strong where it is shallow and "
        "wide.</b>"))
    return "\n".join(s)
