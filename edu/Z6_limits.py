# -*- coding: utf-8 -*-
"""Volume III, Part Z6 -- What the agent cannot do, and how to work inside that."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def ch_limits():
    s = ['<h1 id="z6">Z6. What the Agent Cannot Do</h1>']
    s.append("""<p>A tool's limits are more useful than its features, because the limits
    decide where your attention has to go. This part states the agent's honestly, each
    with the evidence from this repository's own use of it, and then says what to do
    about each one.</p>""")

    s.append("<h2>Z6.1 The limits, named</h2>")
    s.append(tab("What the agent does not do, and why not",
        ["Limit", "Why", "What you do instead"],
        [["<b>It cannot decide what the block should do</b>",
          "No oracle exists for a specification reading",
          "You read the standard. This is the asset"],
         ["<b>It cannot write the golden model</b>",
          "<b>The model <i>is</i> the oracle; a machine-written oracle checked by the "
          "same machine proves nothing</b>",
          "You write it, from the standard, before the RTL"],
         ["It cannot architect",
          "Architecture is a judgement against cost, and the cost model is yours",
          "Parts X1, X2, X6, X13 give the arithmetic; you apply it"],
         ["<b>Its repairs are single-token edits from a narrow library</b>",
          "A wider library finds something for every failure and most of it is wrong",
          "Structural bugs come to you with a minimal reproducer &mdash; which is the "
          "valuable part"],
         ["<b>It cannot judge an equivalent mutant</b>",
          "Behavioural equivalence is undecidable in general",
          "You judge each escape once and record the reason"],
         ["It does not know what the stimulus is missing",
          "It measures what the stimulus reaches, not what it should reach",
          "<b>The mutation escapes point at the holes &mdash; read them</b>"],
         ["It cannot verify timing, area or power",
          "Those need a library and a flow, not a comparison",
          "The release gate runs lint and synthesis; sign-off is the customer's"],
         ["<b>It cannot talk to a customer</b>", "&mdash;",
          "Part Y5. This is most of whether the business works"]]))
    s.append("""<div class="warn"><b>The limit that does the most damage when forgotten is
    the second.</b> Under deadline it is very tempting to have the machine write the
    reference too &mdash; it is faster, it looks like the same kind of work, and the
    result will agree with the RTL. It will agree because both came from the same
    reading, which is the one thing the reference exists to be independent of. <b>Every
    disagreement you delete this way is a check you cannot get back</b>, and nobody will
    remember six months later which checks were deleted or why. Part&nbsp;Y11 states the
    rule for a human team; it does not change when one member is a machine.</div>""")

    s.append("<h2>Z6.2 What happened when the limits were tested</h2>")
    s.append(tab("This repository's own record",
        ["What the agent did", "What it could not do", "Who closed the gap"],
        [["Found the ID-register bug on the first run",
          "It could not say the generator's <i>design</i> was incomplete",
          "A human decided RO fields should default to constants"],
         ["Found the RC/penable bug after the stimulus was extended",
          "<b>It could not find it before</b> &mdash; the stimulus never reached the "
          "logic",
          "The mutation escapes pointed at the hole; a human read them"],
         ["<b>Scored the register file at 58.3&nbsp;%</b>",
          "It could not say <i>why</i> the five escapes shared a cause",
          "A human read three lines and saw <code>hw_set</code> tied to zero"],
         ["Repaired three injected Verilog faults exactly",
          "None of the three was a structural bug",
          "&mdash; the library is deliberately narrow"],
         ["Caught a throughput-only regression once the bound existed",
          "<b>It could not invent the bound</b>",
          "A human measured the clean block and chose 2.6 cycles/byte"],
         ["Ran all night, every night, for free", "&mdash;",
          "<b>This is the part that is genuinely free, and it is not the valuable "
          "part</b>"]]))
    s.append("""<div class="ms"><b>Read the last two rows together.</b> The compute is
    free and the bound is not; the agent contributed the checking and a human contributed
    the number being checked against. Every one of the agent's real finds in this
    repository traces back to a human decision about what to compare, what to drive, or
    what bound to declare. <b>That is not a complaint about the agent &mdash; it is the
    investment thesis.</b> An hour spent on the oracle is repaid every night
    indefinitely; an hour spent running the agent is repaid once and would have happened
    anyway.</div>""")

    s.append("<h2>Z6.3 The failure modes of working with it</h2>")
    s.append(tab("How a two-member team goes wrong",
        ["Failure", "How it looks", "The early symptom"],
        [["<b>The oracle stops growing</b>",
          "The agent finds nothing and everyone is pleased",
          "<b>Flat mutant count against a rising line count</b> &mdash; plot it"],
         ["Patches accumulate unread",
          "Green regressions, RTL nobody can explain",
          "A patch whose original defect you cannot state in one sentence"],
         ["Escapes suppressed rather than judged",
          "The score rises and the blind spots stay",
          "A suppression file with no reasons in it"],
         ["<b>Triage becomes debugging</b>",
          "The morning consumes the day; the afternoon slot disappears",
          "Part Z2's first symptom, and the commonest"],
         ["Stimulus tuned until it passes",
          "A constraint narrowed to make a failure go away",
          "<b>Distinct-output count falling</b> &mdash; the gate checks it for this "
          "reason"],
         ["Believing the mutation score is the goal",
          "Mutants chosen because they are easy to catch",
          "The library stops growing while the score stays at 100&nbsp;%"]]))
    s.append(ex("Detecting the first failure mode before it costs a month",
        "Plot, weekly: lines of DUT code, number of mutants generated, mutation score, "
        "and distinct outputs in the regression.",
        "Each pair of series answers a question that neither answers alone.",
        [("Lines rising, mutants flat", "<b>the suite covers a shrinking fraction</b>"),
         ("Mutants rising, score flat", "healthy &mdash; new code is being checked"),
         ("Score rising, escapes flat at zero", "healthy"),
         ("Score 100&nbsp;%, mutants flat for weeks",
          "<b>the library has stopped growing, not the design</b>"),
         ("Distinct outputs falling", "<b>the stimulus is narrowing</b>"),
         ("Everything flat", "you are not working on this block &mdash; fine, if "
          "deliberate")],
        "<b>By watching the score alone.</b> A mutation score is a ratio, and a ratio "
        "hides both of its terms: 100&nbsp;% of eight mutants on a block that has grown "
        "to four thousand lines is a much weaker statement than 90&nbsp;% of two hundred. "
        "<b>Plot the numerator and the denominator</b>, which costs nothing because the "
        "agent already records both, and the failure mode announces itself weeks before "
        "it matters."))
    s.append(prob("Should the agent be allowed to apply its own patches unattended?",
        "Yes for a narrow class, and the class is worth defining precisely rather than "
        "deciding by feel. <b>Allow it when all four hold</b>: the edit is a single "
        "token from the declared library; it passed a seed never used during the search; "
        "the self-check confirms the comparison still bites; and the block is one whose "
        "golden model you trust because it is independent. <b>Refuse it otherwise</b>, "
        "and in particular refuse it on any block whose reference model you wrote by "
        "reading the RTL &mdash; there the whole gate structure rests on nothing. Two "
        "practical additions make the yes safe. Keep the default as report-only "
        "(`--적용` is opt-in, which is how this repository ships it), so an unattended "
        "night cannot silently change the design. And require that every applied patch "
        "be reviewed in the morning with the one question of Part&nbsp;Z2: <i>what was "
        "the original defect?</i> <b>If you cannot state it, the patch is masking "
        "something</b>, and the right response is to extend the stimulus rather than to "
        "keep the patch."))
    return "\n".join(s)
