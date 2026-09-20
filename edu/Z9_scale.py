# -*- coding: utf-8 -*-
"""Volume III, Part Z9 -- Scaling the agent to a block that is actually big."""
import sys, os, math
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def ch_scale():
    s = ['<h1 id="z9">Z9. Scaling the Agent to a Block That Is Actually Big</h1>']
    s.append("""<p>The blocks this book's agent verifies are small &mdash; tens to
    hundreds of lines. A sellable block is thousands. This part is about what changes,
    because several things that work at the small scale stop working, and knowing which
    ones in advance is the difference between a method and a demonstration.</p>""")

    s.append("<h2>Z9.1 What breaks as the block grows</h2>")
    rows = [
        ["Regression runtime", "0.03&nbsp;s", "minutes", "<b>Fine</b> &mdash; it runs "
         "at night", "Use Verilator for the bulk run; keep Icarus for X-propagation"],
        ["<b>Mutation pass</b>", "15&nbsp;s", "<b>hours to days</b>",
         "<b>Breaks</b> &mdash; mutants &times; seeds &times; runtime is a triple "
         "product",
         "<b>Sample the mutants; run the full set weekly</b>"],
        ["Repair search", "8 candidates", "thousands",
         "<b>Breaks</b> &mdash; and most edits are irrelevant to the failure",
         "<b>Restrict candidates to the cone of the failing output</b>"],
        ["Minimal reproducer", "one stimulus line", "a sequence",
         "Breaks &mdash; shrinking a sequence is a different algorithm",
         "Delta-debugging over the transaction sequence"],
        ["Golden model runtime", "microseconds", "comparable to the RTL",
         "Can break", "Model in C++ and link it, or compare at checkpoints"],
        ["Stimulus generation", "random in a loop", "constrained, layered",
         "<b>Breaks</b> &mdash; random reaches nothing interesting",
         "Constraint solving, sequences, and directed corners"],
        ["Distinct-output check", "trivially satisfied", "still trivially satisfied",
         "Holds &mdash; but becomes weak",
         "<b>Replace with functional coverage bins</b>"],
    ]
    s.append(sweep("Each mechanism at both scales",
        ["Mechanism", "At 30 lines", "At 3000 lines", "Holds?", "What replaces it"],
        rows,
        "<b>Three of seven break, and they break for the same reason</b>: the work is "
        "a product of several quantities that each grow with the design. The "
        "replacements are all standard verification practice &mdash; the agent's "
        "structure does not change, only the components inside it."))
    s.append(ex("When the mutation pass stops fitting in a night",
        "Mutants scale roughly with lines; each mutant is run on <i>k</i> seeds; each "
        "run takes time proportional to the design.",
        "Compute the triple product at three sizes and find where twelve hours runs "
        "out.",
        [("30 lines: mutants &times; seeds &times; run",
          "8 &times; 1 &times; 0.03&nbsp;s = " + num(8 * 0.03, 3, "s")),
         ("300 lines", "80 &times; 2 &times; 0.3&nbsp;s = " + num(80 * 2 * 0.3, 4, "s")),
         ("3000 lines", "800 &times; 2 &times; 3&nbsp;s = "
          + num(800 * 2 * 3 / 3600, 4, "h")),
         ("30&#8239;000 lines", "8000 &times; 2 &times; 30&nbsp;s = "
          + num(8000 * 2 * 30 / 3600, 4, "h")),
         ("Hours available per night", num(12)),
         ("<b>Where it stops fitting</b>", "<b>around 3000&ndash;10&#8239;000 lines</b>"),
         ("The fix", "<b>sample mutants nightly, full set weekly</b>"),
         ("Sampling 10&nbsp;% nightly at 30k lines", num(8000 * 2 * 30 / 10 / 3600, 4,
                                                          "h"))],
        "<b>By treating the mutation score as something run once at release.</b> "
        "Sampled nightly it is a <i>trend</i>, and the trend is what detects "
        "Part&nbsp;Z6's first failure mode &mdash; the oracle standing still while the "
        "design grows. A single number at release cannot detect that, and by then it is "
        "too late to act on it anyway."))

    s.append("<h2>Z9.2 Shrinking a sequence, not a value</h2>")
    s.append(derive("Delta debugging, and why it is worth implementing", [
        ("A sequential failure is a <i>sequence</i> of transactions, not one input.",
         "So the current shrink &mdash; replay the one failing stimulus &mdash; does "
         "not apply."),
        ("Naive minimisation removes one transaction at a time and re-runs: "
         "<i>O</i>(<i>n</i><sup>2</sup>) runs for length <i>n</i>.",
         "At <i>n</i> = 10&#8239;000 and one second a run, that is weeks."),
        ("<b>Delta debugging halves instead</b>: try the first half, then the second, "
         "then quarters, keeping any subset that still fails.",
         "<i>O</i>(<i>n</i> log <i>n</i>) in the worst case and far better in "
         "practice, because failures usually depend on a few transactions."),
        ("The result is a <i>1-minimal</i> sequence: removing any single transaction "
         "makes it pass.",
         "<b>Which is usually two or three transactions out of ten thousand</b>, and "
         "that is a debuggable report."),
        ("It needs only a predicate: does this sequence still fail?",
         "<b>Which the harness already provides.</b> That is why it is cheap to add "
         "&mdash; the expensive part, the oracle, already exists."),
    ]))
    rows = []
    for n in (100, 1000, 10000, 100000):
        naive = n * n
        dd = n * math.log2(n) * 2
        rows.append([num(n), num(int(naive)), num(int(dd)),
                     num(naive / dd, 4),
                     num(dd / 3600, 4) + " h at 1 s/run"])
    s.append(sweep("Shrinking a failing sequence: one-at-a-time against delta debugging",
        ["Transactions", "Naive runs", "Delta-debug runs (bound)", "Speed-up",
         "Delta-debug time"], rows,
        "Worst-case bounds; in practice delta debugging does far better because it "
        "finds the small dependent subset early. <b>The naive column is why nobody "
        "shrinks long sequences by hand</b>, and the third column is why the agent "
        "should."))

    s.append("<h2>Z9.3 Constrained stimulus: where random stops working</h2>")
    s.append(tab("Stimulus layers, and what each reaches",
        ["Layer", "Reaches", "Cost", "When you need it"],
        [["Uniform random", "The bulk of the state space", "free",
          "Always &mdash; the first 90&nbsp;% of coverage (Part X8)"],
         ["<b>Weighted random</b>", "Rare values, boundaries",
          "A distribution per field",
          "<b>As soon as any field has a rare-but-legal value</b>"],
         ["Constrained random", "Only legal combinations", "A solver",
          "When illegal stimulus wastes the night"],
         ["<b>Sequences</b>", "Protocol states that need a history",
          "A sequence library",
          "<b>The moment the block has state</b> &mdash; which is immediately"],
         ["Directed corners", "What random never reaches",
          "One test each; you write them",
          "Part X8's argument: some bins have probability 10<sup>&minus;9</sup>"],
         ["Replay of past failures", "Everything previously found",
          "<b>Almost nothing &mdash; keep the minimal reproducers</b>",
          "<b>Every night. This is the cheapest coverage in existence</b>"]]))
    s.append("""<div class="ms"><b>The last row is the one to build first, and it is
    routinely skipped.</b> Every failure the agent has ever found, reduced to its minimal
    reproducer, is a test that costs nothing to re-run and that is known to have caught a
    real bug once. A growing file of them is a regression suite assembled for free from
    work already done, and it is the only part of the stimulus that is guaranteed to be
    relevant to <i>this</i> design rather than to a designer's idea of it. <b>This
    repository's agent writes the minimal reproducer into its ledger; turning that ledger
    into a replay set is a few lines and should be the first thing added when a block
    gets big.</b></div>""")
    s.append(prob("At what size should you stop using one agent and split the block?",
        "The question is better posed as: at what size does the <i>oracle</i> stop being "
        "a single comparison? The agent's structure is indifferent to size; what fails "
        "is the golden model's granularity. While one model consumes the block's inputs "
        "and produces its outputs, one comparison suffices however large the block is. "
        "<b>The break comes when a failure's distance from its cause becomes too "
        "large</b> &mdash; an error injected in a pipeline's first stage that manifests "
        "as a wrong packet ten thousand cycles later, where the minimal reproducer is "
        "still ten thousand transactions and the repair search has no cone to restrict "
        "to. At that point split the <i>comparison</i>, not the block: add internal "
        "checkpoints where the model and the RTL can be compared &mdash; after the "
        "syndrome stage, after the key equation, after Chien &mdash; each with its own "
        "small oracle. <b>This is step-and-compare from Part&nbsp;X19 applied to a "
        "datapath</b>, and it converts one hard debugging problem into several easy "
        "ones. The cost is that the internal interfaces become part of the verification "
        "contract and cannot be changed freely, which is a real constraint and is "
        "usually worth it."))
    return "\n".join(s)
