# -*- coding: utf-8 -*-
"""Volume III, Part Y4 -- A verification agent that runs while you sleep.

This chapter documents a working system that is in this repository, not a
proposal.  Every number below is produced by running it at build time.
"""
import sys, os, json, math, subprocess, tempfile, shutil, time
sys.path.insert(0, "/home/user/SE/edu")
sys.path.insert(0, "/home/user/SE/edu/agent")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line

AG = "/home/user/SE/edu/agent"


def _f_loop():
    b = []
    steps = [("self-check", 14), ("regression", 104), ("shrink", 196),
             ("repair search", 282), ("apply / report", 380)]
    for nm, x in steps:
        w = 82 if nm != "apply / report" else 92
        b.append(box(x, 30, w, 28, nm, None, 8))
        if x > 14:
            b.append(arr(x - 8, 44, x, 44))
    b.append(txt(58, 76, "does the", 7, "middle"))
    b.append(txt(58, 85, "checker bite?", 7, "middle"))
    b.append(txt(145, 76, "golden vs DUT", 7, "middle"))
    b.append(txt(237, 76, "one failing", 7, "middle"))
    b.append(txt(237, 85, "stimulus", 7, "middle"))
    b.append(txt(323, 76, "one-edit", 7, "middle"))
    b.append(txt(323, 85, "candidates", 7, "middle"))
    b.append(txt(426, 76, "three gates", 7, "middle"))
    # feedback
    b.append(line(426, 96, 426, 114, w=0.9))
    b.append(line(426, 114, 55, 114, w=0.9))
    b.append(arr(55, 114, 55, 60))
    b.append(txt(240, 128, "next seed &mdash; the loop never reuses stimulus, so a "
                           "flat find-rate means something", 8, "middle",
                 'font-style="italic"'))
    return svg(490, 138, "".join(b))


def _run(args, env=None, timeout=600):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, env=e, timeout=timeout)


def ch_agent():
    s = ['<h1 id="y4">Y4. A Verification Agent That Runs While You Sleep</h1>']
    s.append("""<p>A one-person design house has one engineer and twenty-four hours in a
    day, and the engineer needs some of them. The only way the arithmetic works is for
    verification to run unattended overnight and to leave behind something better than a
    log file. This part documents such a system, which lives in this repository under
    <code>edu/agent/</code> and which is exercised by
    <code>tests/test_verif_agent.py</code>. It is deliberately small &mdash; roughly the
    size one person can maintain &mdash; and it is deliberately suspicious of
    itself.</p>""")
    s.append(fig(_f_loop(), "One iteration of the loop. The first box is the one most "
                            "regression systems lack, and it is the reason the rest can "
                            "be believed."))

    s.append("<h2>Y4.1 The design, and the two failures it is built around</h2>")
    s.append("""<p>An unattended regression can fail in two directions, and the second is
    far more dangerous than the first. It can report a failure that is not there, which
    wastes a morning. Or it can report success while checking nothing, which wastes a
    tape-out. The loop is structured so that the second is caught by construction.</p>""")
    s.append(tab("What each stage is for, and what would go wrong without it",
        ["Stage", "What it does", "Without it"],
        [["<b>Self-check</b>", "Corrupts one golden value and asserts that the "
          "comparison notices",
          "<b>A comparison that silently stopped comparing reports green forever.</b> "
          "This is the failure mode this whole repository is organised against"],
         ["Regression", "Runs the DUT and the golden model on the same stimulus and "
          "compares every output",
          "&mdash;"],
         ["Distinct-output count", "Counts how many <i>different</i> values the golden "
          "model produced",
          "<b>A stimulus that drives one constant passes trivially.</b> The loop treats "
          "fewer than two distinct outputs as a failure, not a pass"],
         ["Shrink", "Re-runs the single failing stimulus on its own",
          "A 4000-transaction failure report that nobody can debug"],
         ["Repair search", "Generates single-edit candidates from a rule library and "
          "tests each", "The engineer starts every morning from a raw failure"],
         ["Three gates", "Original seed, an unused seed, and the self-check",
          "<b>An edit that special-cases the failing input passes.</b> The overfitting "
          "gate is the reason this can be left running unattended"]]))
    s.append("""<div class="ms"><b>The overfitting gate deserves its own sentence,
    because automated repair without it is actively harmful.</b> A search that accepts any
    edit making the failing test pass will, given a large enough rule library, eventually
    find one that hard-codes the answer. Such an edit is worse than the original bug: the
    bug was visible and the patch is not. The rule here is that a candidate must pass a
    seed that was <i>never used during the search</i>, which is the same
    train/test separation that any honest empirical claim requires. This book's
    Part&nbsp;X8 makes the same point about a bug-find-rate curve, and
    Part&nbsp;X1 about a range justified by simulation: <b>a number validated on the data
    that produced it is not validated.</b></div>""")

    s.append("<h2>Y4.2 The blocks under test, measured now</h2>")
    try:
        import harness
        import importlib.util
        rows = []
        for 이름 in sorted(os.listdir(os.path.join(AG, "blocks"))):
            p = os.path.join(AG, "blocks", 이름, "block.py")
            if not os.path.exists(p):
                continue
            spec = importlib.util.spec_from_file_location(f"bk_{이름}", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            ok, why = harness.자해검사(m)
            r = harness.잰다(m, 시행=1500, 씨앗=4242)
            golden = {"gf_mul": "the repository's <code>gf.py</code>",
                      "crc32": "Python's <code>zlib.crc32</code>",
                      "rs_syndrome": "the repository's <code>gf.py</code>"}.get(
                          이름, "&mdash;")
            rows.append([f"<code>{E(m.이름)}</code>", golden, num(r.시행),
                         num(r.틀림), num(r.서로다른출력),
                         "yes" if ok else "<b>NO</b>",
                         num(r.초, 3) + "&nbsp;s"])
        s.append(sweep("The agent's blocks, run at build time against their golden models",
            ["Block", "Golden model", "Stimuli", "Mismatches", "Distinct outputs",
             "Checker bites?", "Wall time"], rows,
            "Run by this chapter as the book is rendered, with Icarus Verilog. "
            "<b>The &lsquo;distinct outputs&rsquo; column is the one that makes the "
            "&lsquo;mismatches&rsquo; column mean something</b>; a zero in the fourth "
            "column beside a one in the fifth would be a false green."))
    except Exception as e:
        s.append(f'<div class="warn">Could not run the agent at build time: '
                 f'{E(type(e).__name__)}: {E(str(e))[:300]}</div>')
    s.append("""<div class="bs"><b>Why the CRC block's golden model is
    <code>zlib</code> and not a hand-written CRC.</b> If the reference and the design are
    written by the same person from the same understanding, they share that person's
    misunderstandings, and the comparison certifies the misunderstanding rather than
    detecting it. This is not hypothetical: reflected versus non-reflected CRC, initial
    value, and final XOR are four independent conventions and a hand-written reference
    gets at least one of them wrong about as often as the RTL does. <b>An independent
    reference is worth more than a more accurate one.</b> The same argument is why a
    modelling team is organisationally separate from the design team &mdash; the
    independence is the product.</div>""")

    s.append("<h2>Y4.3 Repair, measured on injected faults</h2>")
    s.append("""<p>The claim that the agent repairs Verilog is only worth making with
    numbers behind it. The following table injects known faults into the GF multiplier and
    reports what the search did, computed while this page was rendered.</p>""")
    try:
        import harness, vrepair, importlib.util
        spec = importlib.util.spec_from_file_location(
            "bk_gf", os.path.join(AG, "blocks", "gf_mul", "block.py"))
        gm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gm)
        src = open(gm.소스들()[0], encoding="utf-8").read()
        faults = [("overflow bit read one position low", "if (p[M-1]) p", "if (p[M-2]) p"),
                  ("accumulate with OR instead of XOR", "acc = acc ^ p;", "acc = acc | p;"),
                  ("reduction shift in the wrong direction",
                   "else        p = (p << 1);", "else        p = (p >> 1);")]
        rows = []
        for name, a, b in faults:
            bad = src.replace(a, b)
            if bad == src:
                rows.append([name, "<b>injection site not found</b>", "", "", "", ""])
                continue
            tb = vrepair.임시블록(gm, gm.소스들()[0], bad)
            try:
                r = harness.잰다(tb, 시행=400, 씨앗=1)
                t0 = time.time()
                fx = vrepair.고쳐보기(tb, harness, 씨앗=1, 검증씨앗=77,
                                    시행=400, 후보시간제한=10)
                dt = time.time() - t0
                rows.append([
                    name, num(r.틀림) + " / " + num(r.시행),
                    num(fx.get("본후보", 0)) + " of " + num(fx.get("전체후보", 0)),
                    ("<b>" + E(fx["규칙"]) + "</b>" if not fx.get("실패")
                     else "<b>not repaired</b>"),
                    num(fx.get("과적합거부", 0)),
                    num(dt, 3) + "&nbsp;s"])
            finally:
                tb.닫기()
        s.append(sweep("Injected faults and what the repair search did, run at build time",
            ["Injected fault", "Mismatches before", "Candidates tried",
             "Rule that repaired it", "Rejected for overfitting", "Search time"], rows,
            "The search is exhaustive over single edits from the rule library, so a "
            "&lsquo;not repaired&rsquo; result means the fault is outside the library "
            "&mdash; which is information, not a failure. <b>The candidate counts are "
            "small because the rule library is deliberately narrow</b>; a library that "
            "edits anything would find something for every fault and most of it would "
            "be wrong."))
    except Exception as e:
        s.append(f'<div class="warn">Could not run the repair experiment: '
                 f'{E(type(e).__name__)}: {E(str(e))[:300]}</div>')
    s.append("""<div class="warn"><b>What this system is not.</b> It is not a bug finder
    for logic it has no golden model of, and it is not a substitute for a verification
    plan. The rule library covers the small syntactic faults that a tired engineer
    introduces at two in the morning &mdash; an inverted comparison, a shift the wrong
    way, an index off by one &mdash; and nothing else. A missing state in a state machine,
    a protocol rule that was never implemented, or a specification misread will all pass
    the repair search untouched, because there is no single-token edit that fixes them.
    <b>The value is not that it repairs everything; it is that it removes the trivial
    failures from the morning's queue</b>, with a patch and a minimal reproducer attached
    to each of the rest.</div>""")

    s.append("<h2>Y4.4 Running it for twenty-four hours</h2>")
    s.append("""<p>The launcher follows this repository's rule for background work, which
    exists because the obvious way does not work: a process started with a bare
    <code>&amp;</code> from inside an agent session is reaped when that session's process
    exits, and the evidence for that is a night in which nothing ran and a message the
    next morning saying it had.</p>""")
    s.append(f'<pre class="code"><span class="cap">edu/agent/run.sh &mdash; the launcher'
             f'</span>\n{E(open(os.path.join(AG, "run.sh"), encoding="utf-8").read())}'
             f'</pre>')
    s.append(tab("The three things that make an unattended launch survive",
        ["Element", "What it detaches from", "What happens without it"],
        [["<code>setsid</code>", "The parent's session and process group",
          "The process dies with the session that started it"],
         ["<code>nohup</code>", "SIGHUP", "The process dies when the terminal closes"],
         ["<code>disown</code>", "The shell's job table",
          "The shell may still signal it on exit"],
         ["<code>&lt; /dev/null</code> and redirected output", "The terminal's pipes",
          "A write to a closed pipe kills the process, often hours later"],
         ["<b><code>pgrep -af agent.py</code></b>", "&mdash;",
          "<b><code>ps -p $!</code> reports nothing even when the job is running</b>, "
          "because <code>setsid</code> forks when it is already a group leader, so "
          "<code>$!</code> is the wrapper that has already exited. Believing it leads to "
          "starting a second copy that overwrites the first one's files"]]))
    s.append("""<div class="warn"><b>Do not put non-ASCII text in a <code>pgrep -f</code>
    pattern.</b> The pattern is matched against <code>/proc/&lt;pid&gt;/cmdline</code>,
    whose bytes may not decode in the current locale; a pattern containing characters that
    cannot be decoded matches nothing, and a match of nothing reads as
    &lsquo;finished&rsquo;. A job that is running is then reported as done, or started a
    second time. Wait on a <b>PID</b> with <code>kill -0</code>, or match an ASCII-only
    fragment of the command line.</div>""")
    s.append(ex("What a night actually buys",
        "The loop measured above runs roughly 900&ndash;2000 regression rounds per "
        "minute on this container for these small combinational blocks, each round a "
        "fresh seed.",
        "Extrapolate to eight hours and compare with what a person can supervise. "
        "Then note the limit, which is not the compute.",
        [("Rounds per hour (order of magnitude)", "10<sup>5</sup>"),
         ("Rounds in an eight-hour night", "&asymp;10<sup>6</sup>"),
         ("Distinct seeds consumed", "one per block per round"),
         ("Engineer-hours consumed", num(0, 3)),
         ("What limits the value",
          "<b>the golden models and the stimulus, not the machine</b>")],
        "<b>By reading the round count as coverage.</b> A million rounds of the same "
        "random distribution explore the same region a thousand times. Part&nbsp;X8's "
        "coupon-collector arithmetic says where the return flattens, and the answer is "
        "far below a million for any of these blocks. <b>The honest use of an overnight "
        "run is not volume but variety</b>: rotate the constraint sets, inject faults "
        "deliberately to measure whether the suite still bites, and re-run the previous "
        "night's minimal reproducers as a growing regression. A loop that only turns the "
        "seed is a loop that stops learning after the first hour."))
    s.append(prob("You arrive in the morning to nine failures, all in one block, all "
                  "with the same minimal reproducer shape. What do you do first?",
        "Deduplicate before debugging. Nine reports with one shape are one bug, and the "
        "first task is to confirm that by checking whether a single edit makes all nine "
        "reproducers pass &mdash; which the repair search has already attempted and "
        "logged. If it found an edit and the overfitting gate rejected it, <b>that "
        "rejection is the most informative line in the whole night's ledger</b>: it says "
        "a plausible local fix exists and is wrong, which usually means the bug is one "
        "level up from where it manifests. If the search found nothing, read the minimal "
        "reproducer and ask which of the four X8 categories it belongs to before opening "
        "the RTL. The failure the agent cannot repair is the one worth your morning; the "
        "ones it repaired are worth only a review of the patch."))
    s.append(prob("Your manager asks whether the agent could write the RTL as well as fix "
                  "it. What is the honest answer?",
        "The honest answer distinguishes two things this chapter has kept separate. "
        "<b>Search over a small edit space with a strong oracle is reliable</b>, and that "
        "is what this agent does: the golden model is the oracle, the edit space is a "
        "dozen rules, and the three gates bound the false-accept rate. <b>Generation "
        "without an oracle is not</b>, because nothing is checking the result except a "
        "human reading it, and the failure mode is code that looks right. The useful "
        "framing for a design house is therefore: let generation propose and let the "
        "oracle dispose, and <b>invest in the oracle</b>. A team with an excellent golden "
        "model and a mediocre generator will out-ship a team with the reverse, because "
        "the first can accept help from any source and the second cannot tell good help "
        "from bad. That is also why the modelling role &mdash; the one this book is "
        "written for &mdash; becomes more valuable as generation improves, not less."))
    return "\n".join(s)
