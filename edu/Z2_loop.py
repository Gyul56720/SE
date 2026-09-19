# -*- coding: utf-8 -*-
"""Volume III, Part Z2 -- The daily and weekly loop."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

AG = "/home/user/SE/edu/agent"


def _f_day():
    b = []
    slots = [("morning", "read the ledger,", "triage, decide", 14),
             ("midday", "model, RTL,", "architecture", 122),
             ("afternoon", "strengthen the", "oracle", 230),
             ("evening", "launch the agent,", "go home", 338)]
    for nm, a, c, x in slots:
        b.append(box(x, 26, 96, 44, a, c, 8))
        b.append(txt(x + 48, 18, nm, 8, "middle", 'font-weight="bold"'))
        if x > 14:
            b.append(arr(x - 10, 48, x, 48))
    b.append(line(434, 48, 452, 48, w=0.9))
    b.append(line(452, 48, 452, 92, w=0.9))
    b.append(line(452, 92, 8, 92, w=0.9))
    b.append(arr(8, 92, 8, 56))
    b.append(txt(230, 108, "The agent works the interval you are not there.", 9,
                 "middle"))
    b.append(txt(230, 122, "Your afternoon decides what it is able to find that night.",
                 9, "middle", 'font-style="italic"'))
    return svg(470, 132, "".join(b))


def ch_loop():
    s = ['<h1 id="z2">Z2. The Daily and Weekly Loop</h1>']
    s.append("""<p>A two-member team has an unusual property: one member works when the
    other does not. That makes the shape of the day the main scheduling decision, and
    getting it right is worth more than working longer.</p>""")
    s.append(fig(_f_day(), "One day."))

    s.append("<h2>Z2.1 The day</h2>")
    s.append(tab("Four slots, and what each is for",
        ["When", "You do", "Why then", "What it must not become"],
        [["<b>Morning</b>",
          "Read the night's ledger. Triage: real failure, equivalent mutant, "
          "infrastructure noise. Apply or reject the proposed patches.",
          "<b>The information is freshest and the decisions unblock the rest of the "
          "day</b>",
          "Debugging. Triage decides <i>what</i> to debug; the debugging happens "
          "midday"],
         ["<b>Midday</b>",
          "The work that needs an unbroken stretch: the golden model, architecture, "
          "RTL, the hard bug from triage.",
          "It is the only slot long enough",
          "Email, or fiddling with the flow"],
         ["<b>Afternoon</b>",
          "Strengthen the oracle: one more property, one more corner in the stimulus, "
          "one measured bound, one lint rule.",
          "<b>This is what decides what the agent can catch tonight</b>",
          "Optional. It is the compounding part and it is always the first thing "
          "sacrificed"],
         ["<b>Evening</b>",
          "Launch the run and stop. Check it is alive, not that it is finished.",
          "The agent has the night",
          "Watching it. If you are watching, the ledger is not good enough"]]))
    s.append(f'<pre class="code"><span class="cap">The evening command, and the morning '
             f'one</span>\n'
             + E("""# 저녁 -- 밤새 돌린다 (setsid/nohup/disown; 확인은 pgrep)
bash edu/agent/run.sh 12

# 아침 -- 무엇이 있었나
bash edu/agent/status.sh
python3 edu/agent/mutscore.py            # 주 1회면 충분하다

# 밤새 빨간불이 났다면: 최소 사례와 제안된 편집이 원장에 있다
grep '빨간불' edu/agent/ledger/regress.jsonl | tail -5""") + '</pre>')
    s.append("""<div class="warn"><b>The failure mode of this loop is that the afternoon
    slot disappears.</b> It is the only slot with no immediate consequence &mdash; skip it
    and tonight's run still happens, this week's deliverable still moves &mdash; so it is
    the one that gets spent on whatever is urgent. Three weeks later the agent is finding
    nothing, not because the design is clean but because the oracle stopped growing while
    the design kept growing. <b>The measurable symptom is a flat mutation score against a
    rising line count</b>, and it is worth plotting: if the design grew 30&nbsp;% and the
    mutant count did not, the suite is covering a smaller fraction of it than it
    was.</div>""")

    s.append("<h2>Z2.2 The week</h2>")
    rows = [
        ["Monday", "Plan against the deliverable list; pick this week's one thing",
         "A week with two goals finishes neither"],
        ["Tuesday&ndash;Thursday", "The daily loop",
         "&mdash;"],
        ["Friday morning", "<b>Mutation score across every block; read every escape</b>",
         "<b>Weekly is the right cadence &mdash; daily is noise, monthly is too late "
         "to act on</b>"],
        ["Friday afternoon", "Documentation for what changed this week",
         "<b>Written now it takes twenty minutes; written at release it takes "
         "days and is wrong</b>"],
        ["Friday, last thing", "Tag, and run the full gate from a clean checkout",
         "A green working directory is not a green repository &mdash; the commit may "
         "be missing a file"],
    ]
    s.append(sweep("The week",
        ["When", "What", "Why"], rows,
        "The Friday items are the ones that make a release possible without a "
        "release scramble. <b>Both are cheap weekly and expensive in a batch</b>, which "
        "is the general shape of everything in this chapter."))
    s.append(ex("What a night is actually worth",
        "The agent runs 12 hours. Each block's regression takes about 0.02&nbsp;s of "
        "simulation per 600 stimuli, and a full mutation pass over five blocks takes "
        "about a minute.",
        "Count what the night can cover, then note what limits it &mdash; which is not "
        "the machine.",
        [("Regression rounds per hour (order)", "10<sup>5</sup>"),
         ("Distinct seeds consumed in 12 hours", "&asymp;10<sup>6</sup>"),
         ("Mutation passes possible in one night", "hundreds"),
         ("Engineer-hours consumed", num(0, 3)),
         ("What actually limits the value",
          "<b>the stimulus distribution and the golden model</b>"),
         ("Marginal value of the 500th mutation pass", "<b>zero</b>"),
         ("Marginal value of one new checker", "<b>large and permanent</b>")],
        "<b>By measuring the night in rounds.</b> A million rounds of the same "
        "distribution explore the same region a thousand times &mdash; Part&nbsp;X8's "
        "coupon-collector arithmetic says the return flattens far below that. "
        "<b>The honest use of the night is variety, not volume</b>: rotate the "
        "constraint sets, replay every previous minimal reproducer as a growing "
        "regression, and run the mutation pass. A loop that only turns the seed stops "
        "learning within the first hour and then keeps the machine warm until "
        "morning."))

    s.append("<h2>Z2.3 Triage: what to do with each thing in the ledger</h2>")
    s.append(tab("The morning decision table",
        ["Ledger says", "You do", "Time"],
        [["<code>초록</code> on every block", "Nothing. Read the mutation trend instead",
          "1 min"],
         ["<b><code>자해검사</code> failed</b>",
          "<b>Stop. The night's results mean nothing.</b> Fix the harness first",
          "Highest priority &mdash; a broken checker is worse than a broken design"],
         ["<code>자극이 DUT 를 안 건드렸다</code>",
          "The stimulus degenerated &mdash; a constraint is over-tight or a parameter "
          "is wrong", "10 min"],
         ["<b><code>빨간불 -- 수리 적용됨</code></b>",
          "<b>Read the patch.</b> It passed three gates; it still has to be right for "
          "the right reason", "5 min per patch"],
         ["<code>빨간불 -- 수리 후보 있음 (적용 안 함)</code>",
          "The agent found an edit and was not allowed to apply it. Decide",
          "5 min"],
         ["<b><code>빨간불 -- 수리 실패</code></b>",
          "<b>This is the real work.</b> The minimal reproducer is in the ledger; "
          "it is outside the repair library, which usually means it is structural",
          "The morning's budget goes here"],
         ["<code>적용했다가 되돌림</code>",
          "The edit passed the first seeds and failed after application &mdash; look "
          "at why, it is usually an interacting change", "15 min"],
         ["An escape in the mutation report",
          "Equivalent mutant, or a hole in the stimulus. <b>Write down which, and the "
          "reason</b>", "5 min each, weekly"]]))
    s.append("""<div class="ms"><b>Record the verdict on every escape, permanently.</b>
    An escape you have judged to be an equivalent mutant will reappear in every run
    forever, and re-deciding it each week is both wasted time and an invitation to stop
    reading the list. Keep a file of judged escapes with the reason &mdash; &lsquo;extra
    loop iteration reads an out-of-range bit, which is <code>x</code>, so the branch is
    never taken&rsquo; &mdash; and have the report mark them as known. <b>What must not
    happen is suppressing them silently</b>: a suppressed escape whose reasoning was
    wrong is a permanent blind spot, and the file is the thing that lets a reviewer, or
    you in six months, check the reasoning.</div>""")
    s.append(prob("The agent applied a patch overnight and the regression is green. Do "
                  "you trust it?",
        "Trust the <i>evidence</i> and check the <i>reason</i>, which are different "
        "things. The evidence is strong: the edit passed the original seed, passed a "
        "seed never used during the search (the overfitting gate), and passed the "
        "self-check confirming the comparison still bites. That rules out the classic "
        "automated-repair failure of special-casing the failing input. <b>What it does "
        "not establish is that the edit is the change a human would have made.</b> An "
        "edit that makes the symptom go away by tightening a condition can be correct on "
        "every stimulus the suite has and wrong in a case the suite does not reach "
        "&mdash; and if the suite reached that case, the bug would have been caught "
        "before the patch. So: <b>read the diff, and ask what the original defect "
        "was.</b> If you can state the defect in one sentence, keep the patch. If you "
        "cannot, the patch is masking something and the right response is to extend the "
        "stimulus until the failure is understood. <b>Five minutes per patch, and it is "
        "the five minutes that keeps the arrangement honest.</b>"))
    return "\n".join(s)
