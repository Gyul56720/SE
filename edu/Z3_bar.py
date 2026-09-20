# -*- coding: utf-8 -*-
"""Volume III, Part Z3 -- The quality bar: what 'sellable' means as numbers."""
import sys, os, subprocess
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def ch_bar():
    s = ['<h1 id="z3">Z3. The Quality Bar: What &lsquo;Sellable&rsquo; Means as '
         'Numbers</h1>']
    s.append("""<p>&lsquo;Industry level&rsquo; is not a feeling. A customer's technical
    evaluation is a list of questions with numerical answers, and a block either has them
    or does not. This part is that list, with the acceptance criterion for each and the
    command that produces it. <b>A block that passes every row is sellable; one that
    passes most of them is a prototype.</b></p>""")

    s.append("<h2>Z3.1 The gate list</h2>")
    rows = [
        ["<b>Functional agreement</b>",
         "Zero mismatches against an independent golden model, on many seeds",
         "<code>agent: 잰다() 틀림 == 0</code>, &ge; 20 seeds",
         "<b>Non-negotiable</b>"],
        ["<b>The checker bites</b>",
         "Corrupting a golden value makes the comparison fail",
         "<code>자해검사() == True</code> every run",
         "<b>Without it the row above is meaningless</b>"],
        ["<b>Stimulus is non-degenerate</b>",
         "The golden model produced many distinct outputs",
         "<code>서로다른출력 &ge; 2</code>, in practice &gt; 20",
         "A constant stimulus passes any design"],
        ["<b>Mutation score</b>", "Injected defects are caught",
         "<code>mutscore.py</code> &ge; 90&nbsp;%, every escape judged in writing",
         "<b>The number a knowledgeable buyer asks for</b>"],
        ["<b>Throughput</b>", "Cycles per unit of work within a stated bound",
         "<code>성능한계()</code> declared and met",
         "A value-only suite cannot see a block getting slower"],
        ["Code and toggle coverage", "Every line and every bit exercised",
         "Verilator or a coverage-capable simulator",
         "Weakest of the metrics; necessary, not sufficient"],
        ["<b>Lint clean</b>", "No inferred latches, no width mismatches, no "
         "incomplete sensitivity",
         "<code>verilator --lint-only -Wall</code>, zero warnings or a written waiver",
         "<b>The customer will run this and judge you by it</b>"],
        ["<b>Synthesises</b>", "To a gate netlist, with reported area and frequency",
         "<code>yosys</code> plus a timing run, scripts shipped",
         "An unsynthesisable block is not a product"],
        ["CDC analysed", "Every crossing identified, structured and constrained",
         "A CDC tool, or a documented manual analysis with the constraints",
         "<b>The commonest integration failure</b>"],
        ["<b>Reset verified</b>", "Random initialisation, many seeds; de-assertion "
         "synchronised per domain",
         "Regression with randomised initial state",
         "<b>The commonest silicon failure</b>"],
        ["Register map generated", "RTL, header, docs and IP-XACT from one source",
         "<code>house/regmap.py --전부</code>",
         "Hand-maintained copies diverge"],
        ["<b>Documentation</b>", "Datasheet, integration guide, known issues, release "
         "notes", "They exist and match the code",
         "<b>Support cost is inversely proportional to this</b>"],
        ["Reproducibility", "A clean checkout reproduces every number",
         "<code>scripts/precheck.sh</code> from HEAD, not the working directory",
         "<b>A missing file passes locally and fails for the customer</b>"],
    ]
    s.append(sweep("The gates a sellable block passes",
        ["Gate", "What it asserts", "How it is measured", "Why"], rows,
        "<b>Nine of the thirteen are runnable by the agent, unattended.</b> The four "
        "that are not &mdash; judging escapes, CDC analysis, documentation, and "
        "deciding what the block should do &mdash; are the ones this volume says "
        "belong to you."))
    s.append("""<div class="warn"><b>The bar is not &lsquo;no known bugs&rsquo;; it is
    &lsquo;here is the evidence, and here is what is not covered&rsquo;.</b> Every real IP
    block ships with limitations, and Part&nbsp;Y5 argues that naming them is what
    distinguishes a professional supplier. The gate list above is what converts that from
    a posture into a document: each row either passes, or fails with a stated reason and a
    workaround. <b>A customer can evaluate that. They cannot evaluate an
    assurance.</b></div>""")

    s.append("<h2>Z3.2 Running the whole bar in one command</h2>")
    s.append("""<p>A gate that requires remembering to run it is a gate that will be
    skipped in the week it matters. The repository's own discipline applies: one command,
    from a clean checkout, that runs everything and refuses to report green on anything it
    could not check.</p>""")
    s.append(f'<pre class="code"><span class="cap">edu/house/release.sh &mdash; the '
             f'release gate</span>\n'
             + E("""bash edu/house/release.sh <블록이름>

  1. 깨끗한 판을 꺼낸다          -- 작업 디렉터리를 안 본다
  2. 자해검사                    -- 비교가 무는가
  3. 회귀 (씨앗 20개)            -- 값과 순서
  4. 성능                        -- 선언된 한계 안인가
  5. 변이 점수                   -- 몇 %, 탈출은 몇 개
  6. lint  (verilator -Wall)
  7. 합성  (yosys)               -- 면적과 셀 수
  8. 레지스터 맵 생성물          -- 컴파일되는가
  9. 문서가 있는가               -- 데이터시트·통합가이드·알려진문제
 10. 보고서를 낸다               -- 통과/실패와 **못 잰 것**을 같이

**못 잰 것을 초록이라고 하지 않는다.**  도구가 없으면 '없어서 못 쟀다' 로 낸다.""")
             + '</pre>')
    s.append(ex("What the gate costs to run",
        "Five blocks, the regression at 20 seeds each, a mutation pass, lint and "
        "synthesis.",
        "Estimate from the measured per-step times in this book's own runs.",
        [("Regression, 600 stimuli", num(0.03, 3, "s") + " per seed per block"),
         ("20 seeds &times; 5 blocks", num(20 * 5 * 0.03, 4, "s")),
         ("Self-check", num(5 * 0.03, 4, "s")),
         ("Mutation pass, 5 blocks", "&asymp;" + num(60, 3, "s")),
         ("Lint", "seconds"),
         ("Synthesis", "seconds to minutes per block"),
         ("<b>Whole gate</b>", "<b>a few minutes</b>"),
         ("How often it should run", "<b>every push, and nightly</b>")],
        "<b>By assuming the gate is expensive and running it at release.</b> At a few "
        "minutes it is cheap enough to run on every push, and a gate that runs on every "
        "push finds the regression on the commit that caused it rather than three weeks "
        "later. The expensive parts &mdash; a full mutation pass over a large block, a "
        "long synthesis &mdash; belong in the nightly run, which costs nothing at all "
        "because nobody is waiting."))

    s.append("<h2>Z3.3 What the numbers should look like</h2>")
    rows = [
        ["Mismatches", "0", "0", "Any non-zero is a stop"],
        ["Self-check", "passes", "passes", "A failure invalidates the run"],
        ["Distinct outputs", "&gt; 20", "&gt; 20", "Low means the stimulus degenerated"],
        ["<b>Mutation score</b>", "&ge; 90&nbsp;%", "<b>&ge; 95&nbsp;%</b>",
         "Escapes all judged and recorded"],
        ["Escapes unjudged", "0", "0", "<b>An unjudged escape is an unexamined hole</b>"],
        ["Lint warnings", "0", "0", "Or a written waiver per warning"],
        ["Coverage (line)", "&gt; 95&nbsp;%", "&gt; 99&nbsp;%",
         "Unreached lines explained"],
        ["Throughput margin", "&gt; 10&nbsp;%", "&gt; 20&nbsp;%",
         "Against the declared bound"],
        ["Documented registers", "100&nbsp;%", "100&nbsp;%", "Generated, not typed"],
        ["Known issues listed", "yes", "yes", "<b>Absence is not a clean sheet</b>"],
    ]
    s.append(sweep("Acceptance thresholds: internal and at release",
        ["Metric", "Internal (keep working)", "Release", "Note"], rows,
        "<b>Two columns because they serve different purposes.</b> The internal column "
        "is what you refuse to go home below; the release column is what a customer's "
        "evaluation will find. Setting the internal bar lower than the release bar is "
        "how a release becomes a scramble."))
    s.append(prob("A customer's technical evaluation asks for your verification plan. "
                  "What do you send?",
        "Not a narrative. Send four things, and their existence is most of the answer. "
        "<b>The gate list of Z3.1 with each row's current value</b> &mdash; this is a "
        "table of facts and it is what they are actually trying to establish. <b>The "
        "mutation report, escapes included</b>, because it is the one artefact that "
        "demonstrates the suite bites rather than merely runs, and very few suppliers "
        "have one; including the escapes with their judgements is more convincing than a "
        "higher score without them. <b>The known-issue list</b>, dated, with "
        "workarounds. <b>And the command they can run themselves</b> on the delivered "
        "package to reproduce every number. <b>The fourth is the one that converts the "
        "first three from claims into evidence</b>, and it is the reason the release "
        "gate must run from a clean checkout rather than from your working directory "
        "&mdash; if it only works on your machine, they will find that out, and it will "
        "cost more than the bug it hides."))
    return "\n".join(s)
