# -*- coding: utf-8 -*-
"""Volume III, Part Y11 -- The modelling engineer's working day."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_tri():
    b = []
    b.append(box(140, 14, 128, 34, "Architecture", "what and why", 9))
    b.append(box(24, 110, 118, 34, "Design (RTL)", "how, in gates", 9))
    b.append(box(266, 110, 118, 34, "Verification", "does it agree?", 9))
    b.append(box(140, 66, 128, 30, "Modelling", "the reference", 9, fill="#eef7f2"))
    b.append(arr(204, 48, 204, 66))
    b.append(arr(160, 96, 100, 110))
    b.append(arr(248, 96, 320, 110))
    b.append(line(142, 127, 266, 127, w=0.9, dash="4,3"))
    b.append(txt(204, 142, "compare", 8, "middle"))
    b.append(txt(204, 170, "A bug is a disagreement between the model and the design.",
                 9, "middle"))
    b.append(txt(204, 185, "Which one is wrong is a separate question, answered by "
                           "the specification.", 9, "middle", 'font-style="italic"'))
    return svg(410, 195, "".join(b))


def ch_modelling():
    s = ['<h1 id="y11">Y11. The Modelling Engineer&rsquo;s Working Day</h1>']
    s.append("""<p>This book was written for someone joining a modelling team. This part
    describes the job concretely: what is produced, how it is judged, what the first
    ninety days look like, and the specific habits that distinguish a modelling engineer
    whose work is trusted from one whose work is checked.</p>""")
    s.append(fig(_f_tri(), "The three roles and the place of the model. The dashed line "
                           "is the comparison that defines a bug."))

    s.append("<h2>Y11.1 What a modelling engineer produces</h2>")
    s.append(tab("The deliverables, in the order they are usually needed",
        ["Deliverable", "Form", "Judged by"],
        [["Algorithm study", "Python or MATLAB, plots, a written recommendation",
          "Whether the architecture chosen from it survives implementation"],
         ["<b>Bit-accurate reference model</b>", "<b>C or C++, callable from the "
          "testbench</b>",
          "<b>Whether it agrees with the RTL, and whether it is right when it does "
          "not</b>"],
         ["Word-length study", "A sweep and a recommendation per node",
          "Area saved against the metric held"],
         ["Performance model", "A cycle-approximate or cycle-accurate model",
          "Whether the predicted throughput matches silicon"],
         ["Test vectors", "Stimulus and expected output",
          "Coverage of the corners the RTL must handle"],
         ["The specification's numbers", "Tables in the micro-architecture document",
          "Whether anyone has to re-derive them later"]]))
    s.append("""<div class="ms"><b>The bit-accurate model is the deliverable the role is
    named for, and its value rests entirely on one property: independence.</b> It must
    encode the <i>specification's</i> behaviour, not the design's. A model written by
    reading the RTL is a paraphrase, and a paraphrase agrees with the original for exactly
    the wrong reason. The practical discipline is to write it from the standard or the
    algorithm description before the RTL exists, and to resist the pressure &mdash; which
    is constant and comes from everyone &mdash; to &lsquo;just make the model match&rsquo;
    when the two disagree near a deadline. <b>Every time you make the model match, you
    delete a check that cannot be recovered</b>, and nobody will remember later which
    checks were deleted.</div>""")

    s.append("<h2>Y11.2 Fixed point is most of the work</h2>")
    s.append("""<p>The floating-point algorithm is usually short. Turning it into
    something implementable is not, and that conversion is where a modelling engineer
    spends most of their time. Part&nbsp;X1 gives the arithmetic; this is the
    workflow.</p>""")
    rows = [
        ["1", "Floating-point reference", "Does the algorithm work at all?",
         "A plot against the metric"],
        ["2", "Range analysis", "What does each node hold?",
         "Integer bits per node, with the basis stated"],
        ["3", "Quantised model with parameterised word lengths",
         "How does the metric degrade?", "A sweep, as in Part&nbsp;X1"],
        ["4", "Word-length optimisation", "What is the cheapest point that passes?",
         "A vector of word lengths and the cost model used"],
        ["5", "<b>Bit-exact model</b>",
         "<b>Exactly what the RTL must produce, every bit</b>",
         "<b>The reference the testbench compares against</b>"],
        ["6", "Corner vectors", "What must the RTL handle that random stimulus will "
         "not reach?", "A directed vector set"],
    ]
    s.append(sweep("The six models, and what each one answers",
        ["Stage", "Model", "Question", "Output"], rows,
        "<b>These are six models, not one model in six states.</b> Keeping them "
        "separate means the floating-point reference remains available to answer "
        "&lsquo;is the algorithm wrong or is the quantisation wrong?&rsquo; &mdash; a "
        "question that arises constantly and is unanswerable once the models have been "
        "merged."))
    s.append(ex("A disagreement, diagnosed properly",
        "The RTL and the bit-exact model differ on 3 samples in 100&#8239;000, always "
        "by one LSB, always when the input is near full scale.",
        "Do not guess. Use the model hierarchy: compare the bit-exact model against "
        "the quantised model, and the quantised against floating point, on the same "
        "three inputs. The stage where the discrepancy appears names the cause.",
        [("Differing samples", num(3) + " / 100,000"),
         ("Magnitude", "1 LSB"),
         ("Correlated with", "near-full-scale input"),
         ("First hypothesis", "rounding at a saturation boundary"),
         ("Test", "compare rounding mode at the saturating node in both"),
         ("Second hypothesis", "the RTL saturates before rounding, the model after"),
         ("Which is right?", "<b>whichever the specification says &mdash; check</b>")],
        "<b>By deciding which is right from which is easier to change.</b> The order of "
        "rounding and saturation is a real specification question with a real answer, "
        "and getting it wrong produces a block that differs from every other "
        "implementation by one LSB at full scale &mdash; which will be found by a "
        "customer comparing against a competitor. <b>One-LSB disagreements are the ones "
        "most often waved away and most often genuine</b>; the discipline is that a "
        "disagreement is closed by a citation to the specification, not by a judgement "
        "about magnitude."))

    s.append("<h2>Y11.3 The first ninety days</h2>")
    rows = [
        ["Week 1&ndash;2", "Build and run the existing models and the regression",
         "You cannot contribute to a flow you cannot run. Fix the first thing that "
         "does not build &mdash; it is a real contribution and it teaches the flow"],
        ["Week 2&ndash;4", "Read the specification of the block you will model, and "
         "the existing model beside it",
         "Note every place the model differs from your reading; some are your "
         "misunderstanding and some are bugs"],
        ["Week 4&ndash;6", "Take a small, complete piece &mdash; one function, one "
         "corner case, one test",
         "<b>Complete and small beats large and partial</b>; the goal is a closed loop "
         "through review and merge"],
        ["Week 6&ndash;10", "Own a module's model end to end",
         "Including its verification against the RTL and its documentation"],
        ["Week 10&ndash;13", "Find something the process misses and fix it",
         "A missing check, an unreproducible result, a manual step. <b>This is what "
         "distinguishes you</b>"],
    ]
    s.append(sweep("A first quarter that builds credibility",
        ["When", "What", "Why this and not something more impressive"], rows,
        "The pattern is deliberate: <b>run before reading, read before writing, small "
        "before large, and process improvement last</b> &mdash; because a process "
        "criticism from someone who has not yet shipped anything through the process is "
        "ignored, and the same criticism after ten weeks is acted on."))
    s.append("""<div class="warn"><b>The failure mode of a new modelling engineer is
    silent disagreement.</b> You read the specification, you believe the existing model is
    wrong, and you say nothing because you assume the experienced people have a reason.
    Sometimes they do, and hearing it is how you learn. Sometimes they do not, and the bug
    ships. <b>The correct move is neither silence nor an accusation: it is a question with
    the clause number attached.</b> &lsquo;Clause 7.3.2 says the rounding happens before
    saturation and I read the model as doing the reverse &mdash; what am I missing?&rsquo;
    costs nothing if you are wrong and is extremely valuable if you are right. Engineers
    who ask this way get answers; engineers who assert get arguments.</div>""")
    s.append(prob("You are asked to model a block whose specification is an internal "
                  "document written by an architect who has left. What do you do?",
        "Treat the gap as the first deliverable. <b>Write down what the document does "
        "not determine</b> &mdash; every place where two readings are possible, every "
        "constant with no stated basis, every behaviour on an illegal input &mdash; and "
        "circulate that list. It is immediately useful to everyone and it is the "
        "cheapest thing you can produce in week one. <b>Then resolve the list by evidence "
        "in this order</b>: existing RTL or a previous generation, since what shipped is "
        "a fact; test vectors or captured data, which settle behaviour without settling "
        "intent; the people who integrated against it, who know what they relied on; and "
        "finally a decision recorded as a decision, with your name and the date, for the "
        "items nothing resolves. <b>What you must not do is make the choices silently "
        "inside the model.</b> A model containing twenty undocumented decisions is not a "
        "reference; it is a second design, and when it disagrees with the RTL nobody will "
        "be able to say which is right."))
    s.append(prob("Your model and the RTL agree perfectly on the first day of "
                  "integration. Is that good news?",
        "It is news that needs checking before it is good. Perfect agreement on day one "
        "has three explanations and only one of them is happy. <b>The comparison may not "
        "be running</b> &mdash; a checker that is disabled, a stimulus that never reaches "
        "the block, a comparison of two constants; this is the first thing to rule out, "
        "and the way to rule it out is to <b>break something deliberately and confirm the "
        "comparison notices</b>, which is the same self-check the agent in Part&nbsp;Y4 "
        "performs every round. <b>The model may have been written from the RTL</b>, in "
        "which case agreement is tautological. <b>Or the block may genuinely be simple "
        "and correct</b>, which does happen. Establishing which costs half an hour and is "
        "the single highest-value half hour in an integration, because everything "
        "downstream rests on the answer."))
    return "\n".join(s)
