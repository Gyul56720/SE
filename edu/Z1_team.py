# -*- coding: utf-8 -*-
"""Volume III, Part Z1 -- The two-member IP team: you and the agent."""
import sys, os, subprocess, importlib.util, time
sys.path.insert(0, "/home/user/SE/edu")
sys.path.insert(0, "/home/user/SE/edu/agent")
sys.path.insert(0, "/home/user/SE/edu/house")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

AG = "/home/user/SE/edu/agent"


def _f_team():
    b = []
    b.append(f'<rect x="12" y="16" width="176" height="150" fill="#eef7f2" '
             f'stroke="#2a7f5f" stroke-width="1.2"/>')
    b.append(txt(100, 34, "you", 10, "middle", 'font-weight="bold"'))
    for i, t in enumerate(["read the specification",
                           "write the golden model",
                           "choose the architecture",
                           "write the RTL",
                           "decide what a disagreement means",
                           "talk to the customer"]):
        b.append(txt(24, 54 + i * 18, "• " + t, 8))
    b.append(f'<rect x="224" y="16" width="176" height="150" fill="#eef2f7" '
             f'stroke="#123f6d" stroke-width="1.2"/>')
    b.append(txt(312, 34, "the agent", 10, "middle", 'font-weight="bold"'))
    for i, t in enumerate(["run the regression, all night",
                           "shrink every failure",
                           "attempt a one-edit repair",
                           "measure the mutation score",
                           "measure throughput",
                           "write the ledger"]):
        b.append(txt(236, 54 + i * 18, "• " + t, 8))
    b.append(arr(190, 70, 222, 70))
    b.append(txt(206, 62, "RTL +", 7, "middle"))
    b.append(txt(206, 84, "model", 7, "middle"))
    b.append(arr(222, 130, 190, 130))
    b.append(txt(206, 122, "failures +", 7, "middle"))
    b.append(txt(206, 144, "patches", 7, "middle"))
    b.append(txt(206, 186, "The division is not by difficulty. It is by whether a "
                           "decision is needed.", 9, "middle"))
    b.append(txt(206, 200, "The agent does what is checkable; you do what is "
                           "judgeable.", 9, "middle", 'font-style="italic"'))
    return svg(420, 210, "".join(b))


def _블록들():
    out = []
    root = os.path.join(AG, "blocks")
    for n in sorted(os.listdir(root)):
        p = os.path.join(root, n, "block.py")
        if not os.path.exists(p):
            continue
        spec = importlib.util.spec_from_file_location(f"z1_{n}", p)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
            out.append(m)
        except Exception:
            pass
    return out


def ch_team():
    s = ['<h1 id="z1">Z1. The Two-Member IP Team: You and the Agent</h1>']
    s.append("""<p>This volume is written for a specific arrangement: one engineer and
    one automated verification agent, producing IP that is good enough to sell. That is a
    smaller team than any company would assign to the job, and it can work &mdash; but
    only if the division of labour is decided deliberately rather than by what happens to
    be convenient. This part sets it out, and every claim about the agent in it is
    measured by running the agent while this page is rendered.</p>""")
    s.append(fig(_f_team(), "The division of labour. Everything on the right is "
                            "mechanically checkable; everything on the left needs a "
                            "judgement."))

    s.append("<h2>Z1.1 The rule that decides who does what</h2>")
    s.append(derive("Why the boundary falls where it does", [
        ("The agent can only act where there is an <b>oracle</b> &mdash; something that "
         "says right or wrong without a human.",
         "A golden model, a standard's test vectors, a compiler, a timing report."),
        ("Where an oracle exists, the agent's work is <i>search plus check</i>, and "
         "search with a good oracle is reliable and improves with compute.",
         "This is the regression, the shrink, the repair attempt and the mutation "
         "score."),
        ("Where no oracle exists, any output must be read by a human, and the failure "
         "mode is work that looks right.",
         "<b>Which is the expensive kind of failure</b>, because it is found late."),
        ("<b>So: the agent owns everything downstream of a model; you own the model "
         "and everything upstream of it.</b>",
         "Reading the specification, deciding what the block should do, deciding which "
         "side of a disagreement is wrong &mdash; none of these has an oracle."),
        ("The corollary is where to invest: <b>make the oracle better and the agent "
         "gets better for free.</b>",
         "A stronger golden model, a wider stimulus, a throughput bound, a lint rule "
         "&mdash; each one extends the region the agent can work in, permanently."),
    ]))
    s.append(tab("Task by task, and why",
        ["Task", "Who", "Because"],
        [["Read the standard, resolve ambiguities", "<b>You</b>",
          "No oracle; and the ambiguities are what you will be asked about"],
         ["Write the bit-accurate golden model", "<b>You</b>",
          "<b>It <i>is</i> the oracle.</b> Writing it is how you find out what the "
          "specification actually says"],
         ["Choose the architecture, the word lengths, the parallelism", "<b>You</b>",
          "Judgement against cost; Parts X1&ndash;X2 give the arithmetic"],
         ["Write the RTL", "<b>You</b>",
          "For now. The agent repairs small defects; it does not architect"],
         ["Run the regression on every seed, all night", "Agent",
          "Pure search against an oracle"],
         ["Reduce a failure to one stimulus", "Agent",
          "Mechanical, and it is the difference between a debuggable and an "
          "undebuggable report"],
         ["Attempt a single-edit repair", "Agent",
          "Bounded search; three gates bound the false-accept rate"],
         ["<b>Measure the mutation score</b>", "<b>Agent</b>",
          "<b>The number that says whether the suite bites &mdash; and the escapes "
          "say where the stimulus is thin</b>"],
         ["Measure throughput against a stated bound", "Agent",
          "A value-only regression cannot see a block getting slower"],
         ["Decide whether an escape is an equivalent mutant", "<b>You</b>",
          "A machine cannot decide behavioural equivalence in general"],
         ["Decide which side of a disagreement is wrong", "<b>You</b>",
          "Only the specification settles it, and only you have read it"],
         ["Talk to the customer, price the work, scope it", "<b>You</b>",
          "Part&nbsp;Y5"]]))
    s.append("""<div class="warn"><b>The temptation to let the agent write the model is
    the one thing that destroys the arrangement.</b> If the model and the RTL come from
    the same process, they share its misunderstandings and their agreement proves nothing
    &mdash; this is the independence argument of Part&nbsp;Y11, and it does not change
    because one of the two authors is a machine. The agent may write <i>stimulus</i>, may
    write <i>checkers derived from the model</i>, and may repair RTL; it must not be the
    source of the reference. <b>Your reading of the specification is the asset the
    business is built on</b>, and it is the one part that cannot be delegated.</div>""")

    s.append("<h2>Z1.2 What the agent actually does, measured now</h2>")
    try:
        import harness, mutscore
        blocks = _블록들()
        rows = []
        for m in blocks:
            ok, why = harness.자해검사(m, 시행=80)
            r = harness.잰다(m, 시행=600, 씨앗=20260919)
            rows.append([f"<code>{E(m.이름)}</code>",
                         "yes" if ok else "<b>NO</b>",
                         num(r.시행), num(r.틀림), num(r.서로다른출력),
                         "yes" if getattr(m, "성능한계", None) else "&mdash;",
                         num(r.초, 3) + "&nbsp;s"])
        s.append(sweep("The agent's blocks, run while this page was rendered",
            ["Block", "Checker bites?", "Stimuli", "Mismatches", "Distinct outputs",
             "Throughput bound?", "Wall time"], rows,
            "Run with Icarus Verilog at build time. <b>The &lsquo;checker bites&rsquo; "
            "column is produced by deliberately corrupting a golden value and asserting "
            "that the comparison notices</b> &mdash; without it the mismatch column "
            "would be an unexamined green light."))
        rows = []
        for m in blocks:
            sc = mutscore.점수(m, 시행=250, 씨앗들=(1,), 최대변이=40, 시간제한=8)
            rows.append([f"<code>{E(m.이름)}</code>", num(sc["변이수"]),
                         num(sc["잡힘"]), num(sc["점수"] * 100, 4),
                         num(len(sc["탈출"])), num(sc["초"], 3) + "&nbsp;s"])
        s.append(sweep("Mutation score, measured at build time",
            ["Block", "Mutants run", "Caught", "Score (%)", "Escapes", "Time"], rows,
            "Each mutant is a single-token edit to the DUT &mdash; not to the "
            "testbench, and not inside a comment, because mutating either produces "
            "escapes that mean nothing. <b>An escape is a finding, not a defect in the "
            "score</b>: it is either an equivalent mutant or a place the stimulus does "
            "not reach, and both need a human to say which."))
    except Exception as e:
        s.append(f'<div class="warn">Could not run the agent at build time: '
                 f'{E(type(e).__name__)}: {E(str(e))[:300]}</div>')

    s.append("<h2>Z1.3 A worked morning: what the escapes actually told us</h2>")
    s.append("""<p>The mutation score is not a grade; it is a pointer. The following
    happened while this book's own register-file block was being built, and it is the
    clearest illustration in the book of why the number is worth measuring.</p>""")
    s.append(tab("From a score to two real bugs",
        ["Step", "What happened", "What it cost"],
        [["Regression written, all green", "400 APB accesses, no mismatch",
          "&mdash;"],
         ["<b>Mutation score run: 58.3&nbsp;%</b>",
          "Five escapes, all pointing at the same place",
          "20 minutes"],
         ["Escapes read", "<code>r | hw_set</code> &rarr; <code>r ^ hw_set</code> not "
          "caught &mdash; because <code>hw_set</code> was tied to zero, and 0 behaves "
          "identically under both",
          "<b>The W1C and RC paths had never executed</b>"],
         ["Testbench fixed to pulse the hardware inputs",
          "Plus a directed sequence: set three bits, read, clear one, check the other "
          "two survive", "an hour"],
         ["<b>Regression re-run: two failures</b>",
          "<b>Both were real generator bugs</b> &mdash; an ID register that could not "
          "hold a constant, and an RC register cleared during the APB setup phase "
          "because <code>penable</code> was missing from the read term",
          "&mdash;"],
         ["Fixed, re-scored", "<b>100&nbsp;% (13 of 13)</b>",
          "Two bugs that would otherwise have been found by a customer's driver"]]))
    s.append("""<div class="ms"><b>Note what the green regression was worth before the
    mutation score ran.</b> It was not wrong &mdash; those 400 accesses really did match
    &mdash; and it was nearly worthless, because the stimulus never reached the logic that
    was broken. <b>This is the difference between &lsquo;the tests pass&rsquo; and
    &lsquo;the tests would fail if the design were wrong&rsquo;</b>, and only the second
    is evidence. For a one-person house it is also the only affordable substitute for a
    verification team's scepticism: you cannot review your own work with fresh eyes, and
    the mutation score does not need fresh eyes.</div>""")
    s.append(prob("You are one person. How much of the day should go to verification?",
        "More than feels reasonable, and the arithmetic from Part&nbsp;Y1's effort table "
        "says roughly how much: verification and everything downstream of RTL is about "
        "three quarters of the work in a sellable block. But the useful answer for a "
        "day rather than a project is a <b>shape</b>, not a fraction. <b>Verification "
        "infrastructure is built once and runs forever</b>, so it belongs early and its "
        "cost is amortised; <b>the agent runs it while you sleep</b>, so the marginal "
        "cost of <i>running</i> verification is zero and only the marginal cost of "
        "<i>improving</i> it is real. That changes the allocation: spend your hours on "
        "the golden model, the stimulus and the checkers &mdash; the things that decide "
        "what the agent can catch &mdash; and almost none on running or triaging, which "
        "the agent does. <b>A practical daily target is that every session leaves the "
        "oracle stronger than it found it</b>: one more property checked, one more "
        "corner in the stimulus, one more bound measured. That compounds, and it is the "
        "only thing in a one-person house that does."))
    return "\n".join(s)
