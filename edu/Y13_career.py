# -*- coding: utf-8 -*-
"""Volume III, Part Y13 -- Getting hired, and what to build to get hired."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def ch_career2():
    s = ['<h1 id="y13">Y13. Getting Hired into a Modelling Team</h1>']
    s.append("""<p>This part is about the interview and the portfolio, treated as an
    engineering problem: what does the hiring side actually need to learn about you, and
    what evidence answers it fastest? The answer is unusually concrete for this kind of
    advice, because modelling work produces artefacts that can be shown.</p>""")

    s.append("<h2>Y13.1 What the interviewer is trying to find out</h2>")
    s.append(tab("The four questions behind a modelling interview",
        ["The question", "How it is usually asked", "What actually answers it"],
        [["<b>Can you write a correct model?</b>",
          "A coding exercise, often a fixed-point or protocol task",
          "Code that handles the corners and says which it handles"],
         ["<b>Do you know why the model exists?</b>",
          "&lsquo;How would you verify this block?&rsquo;",
          "<b>An answer that mentions independence and what a disagreement means</b>"],
         ["<b>Do you understand the hardware?</b>",
          "&lsquo;Why is this architecture like this?&rsquo;",
          "Reasoning from timing, area or bandwidth &mdash; numbers, not adjectives"],
         ["<b>Will you say when something is wrong?</b>",
          "&lsquo;Tell me about a time&hellip;&rsquo;, or a deliberately flawed premise "
          "in a question",
          "<b>Noticing the flaw and saying so, politely, is the whole test</b>"]]))
    s.append("""<div class="ms"><b>The fourth question is weighted more heavily than
    candidates expect, and it is the one this book's discipline speaks to directly.</b> A
    modelling engineer's value is that they are an independent check. An engineer who
    defers to the design team's reading of the specification is not performing the
    function they were hired for, however good their code is. Interviewers probe this
    deliberately &mdash; a question with a wrong assumption embedded, a requirement that
    contradicts an earlier one &mdash; and the answer they want is neither silence nor
    combativeness but the thing this book keeps recommending: <b>name the discrepancy,
    cite the source, and ask.</b></div>""")

    s.append("<h2>Y13.2 A portfolio that is evidence rather than assertion</h2>")
    rows = [
        ["A bit-accurate model of a standard block", "RS or BCH decoder, a CIC "
         "decimator, a 64b/66b PCS",
         "<b>Shows you can read a specification and produce something checkable</b>"],
        ["Its test suite, with mutation results",
         "&lsquo;These 14 injected faults; the suite catches 13; here is the escape and "
         "why&rsquo;",
         "<b>Almost nobody does this, and it is the single most convincing artefact</b>"],
        ["A word-length study", "A sweep, a cost model, a chosen point with a reason",
         "Shows you understand the actual daily work"],
        ["An RTL block compared against the model",
         "Even a small one, with the comparison automated",
         "Shows you have closed the loop end to end"],
        ["A written page on a bug you found",
         "Symptom, hypotheses, the measurement that discriminated, the fix",
         "<b>Demonstrates method, which is what is being hired</b>"],
        ["A contribution to an open project", "A fix, a test, a documentation "
         "improvement in a real codebase",
         "Independent evidence that someone reviewed and merged your work"],
    ]
    s.append(sweep("Portfolio items, ordered by what they prove per hour of effort",
        ["Item", "Concretely", "What it proves"], rows,
        "<b>Depth beats breadth here.</b> One block modelled properly, with its "
        "verification and its written reasoning, is worth more than six half-finished "
        "repositories &mdash; because the thing being assessed is whether you finish and "
        "whether you check, and only a finished, checked thing can show that."))
    s.append(ex("Where the hours go, and what each hour buys",
        "120 available hours over three months, to be spent on a portfolio.",
        "Allocate against the four interview questions, weighting by how much evidence "
        "each hour produces.",
        [("Model of one standard block", num(40) + " h"),
         ("Test suite with mutation measurement", num(30) + " h"),
         ("Small RTL implementation and comparison", num(25) + " h"),
         ("Written documentation and a bug write-up", num(15) + " h"),
         ("Polish, README, reproducibility", num(10) + " h"),
         ("Total", num(120) + " h"),
         ("Questions from Y13.1 this evidences", "<b>all four</b>")],
        "<b>By spending all 120 hours on the model.</b> A beautiful model with no test "
        "suite answers one of the four questions; the same model with 30 hours moved "
        "into verification answers three. The most common portfolio failure is an "
        "imbalance in exactly this direction, because modelling is the enjoyable part. "
        "<b>The hours spent proving the model is right are the hours that "
        "differentiate</b>, precisely because they are the ones most candidates skip."))

    s.append("<h2>Y13.3 Interview questions you should expect, and how to think about them</h2>")
    s.append(tab("Common questions and the shape of a good answer",
        ["Question", "What they want to hear"],
        [["&lsquo;How do you know your model is right?&rsquo;",
          "Independence of source; a third-party reference where one exists; "
          "property-based checks rather than sample values; <b>fault injection to prove "
          "the checks bite</b>"],
         ["&lsquo;The RTL and your model disagree. What now?&rsquo;",
          "Reproduce minimally, then go to the specification. <b>Do not edit the model "
          "to match</b>, and say so"],
         ["&lsquo;How many bits does this filter need?&rsquo;",
          "&lsquo;Against what metric?&rsquo; &mdash; then range, then sweep, then the "
          "knee. <b>Asking for the metric first is most of the answer</b>"],
         ["&lsquo;Why not just use floating point?&rsquo;",
          "Area, power and determinism; then the accumulation and associativity "
          "arguments from Part X9"],
         ["&lsquo;Our coverage is 100&nbsp;%. Are we done?&rsquo;",
          "<b>Code coverage measures execution, not checking.</b> Offer mutation score "
          "and checker coverage as the evidence that would settle it"],
         ["&lsquo;Tell me about a hard bug.&rsquo;",
          "The method, not the heroics: hypotheses, the measurement that discriminated, "
          "what you changed in the process afterwards"]]))
    s.append("""<div class="warn"><b>One answer to avoid: &lsquo;I would add more
    tests.&rsquo;</b> It is the reflex response to every verification question and it is
    almost never the best one, because it does not say <i>which</i> tests or how you would
    know they were enough. The answers that distinguish a candidate name a measurement:
    mutation score, checker coverage, a comparison against an independent reference, a
    property that holds for all inputs rather than a vector that holds for one. <b>Every
    one of those is something this book has computed somewhere</b>, and being able to say
    &lsquo;I would measure X and here is what X would tell us&rsquo; is the difference
    between sounding careful and being useful.</div>""")
    s.append(prob("You are asked to estimate something you do not know &mdash; how many "
                  "gates a block needs, how long a task takes. What do you do?",
        "Estimate out loud, from decomposition, and say what would sharpen it. The "
        "interviewer is not testing recall of a number; they are watching whether you can "
        "bound an unknown, which is most of engineering judgement. A good answer names "
        "the decomposition (&lsquo;the multiplier array is about <i>n</i>&sup2; full "
        "adders, a full adder is about six gates, so&hellip;&rsquo;), states the "
        "assumption that matters most, gives a range rather than a point, and ends with "
        "the measurement that would collapse the range. <b>Refusing to estimate is the "
        "worst answer</b> and a confident unqualified number is the second worst; the "
        "habit being looked for is the one Part&nbsp;X1 applies to word lengths and "
        "Part&nbsp;Y8 to schedules &mdash; a bound, its basis, and what would improve "
        "it."))
    s.append(prob("You have no industry experience and no degree from a famous "
                  "university. What actually compensates?",
        "Artefacts, and one specific kind of them. A repository containing a model, its "
        "test suite, a mutation measurement of that suite, and a written page explaining "
        "a bug it caught is evidence that nobody can produce without having done the "
        "work &mdash; and it is checkable in ten minutes by the person deciding whether "
        "to interview you. Two things amplify it. <b>Contributions to a real open project "
        "carry an independent review signal</b>: someone with no reason to flatter you "
        "merged your change. And <b>a written explanation of something difficult</b> "
        "&mdash; a blog post deriving a result, a clear note on a standard's "
        "ambiguity &mdash; demonstrates the communication half of the job, which is half "
        "of it. What does not compensate is a list of technologies; every candidate has "
        "one, and it distinguishes nobody. <b>Build one thing completely and write down "
        "how you know it works.</b>"))
    return "\n".join(s)
