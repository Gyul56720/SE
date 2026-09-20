# -*- coding: utf-8 -*-
"""Volume I, Part X33 -- Boolean reasoning: BDDs, SAT and equivalence checking."""
import sys, math, itertools
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_boolreason():
    s = ['<h1 id="x33">X33. Boolean Reasoning: BDDs, SAT and Equivalence Checking</h1>']
    s.append("""<p>Three tools an IP designer uses every week &mdash; logic equivalence
    checking, formal property verification and automatic test pattern generation &mdash;
    are the same engine underneath: a decision procedure for Boolean formulas. Knowing
    what that engine can and cannot do explains why one proof finishes in seconds and
    another never finishes, which is otherwise the most frustrating thing about these
    tools.</p>""")

    s.append("<h2>X33.1 Representations, and why the choice is everything</h2>")
    s.append(tab("Ways to represent a Boolean function",
        ["Representation", "Size", "Equivalence check", "Where it is used"],
        [["Truth table", "2<sup><i>n</i></sup> always", "Trivial",
          "Small cells; library characterisation"],
         ["Sum of products", "Can be exponential", "Hard",
          "Two-level minimisation, PLAs"],
         ["<b>BDD (reduced, ordered)</b>", "<b>Canonical &mdash; and variable-order "
          "dependent</b>", "<b>Pointer comparison</b>",
          "Symbolic model checking; some equivalence checking"],
         ["AIG (and-inverter graph)", "Linear in the circuit", "Needs a solver",
          "<b>The working representation of every modern synthesis and verification "
          "tool</b>"],
         ["CNF for SAT", "Linear via Tseitin encoding", "<b>NP-complete, and fast in "
          "practice</b>", "Formal verification, ATPG, equivalence"]]))
    s.append("""<div class="ms"><b>Canonicity is the property that makes BDDs both
    magical and fragile.</b> Two functions are equal if and only if their reduced ordered
    BDDs are the identical graph, so equivalence is a pointer comparison rather than a
    search. The price is that the size depends catastrophically on the variable order: the
    same function can be linear under one order and exponential under another, and finding
    the best order is itself NP-hard. The canonical example is a multiplier, whose BDD is
    exponential under <i>every</i> order &mdash; which is exactly why BDD-based equivalence
    checking fails on datapaths and why modern tools use AIGs plus SAT instead. <b>When a
    tool reports that it is &lsquo;building BDDs&rsquo; and then runs out of memory, this
    is what happened</b>, and the remedy is a different engine rather than a bigger
    machine.</div>""")
    # measure BDD-like blowup with a simple ordered decision diagram
    def bdd_nodes(fn, n, order):
        """Count nodes of a reduced ordered decision diagram, by memoising subfunctions."""
        from functools import lru_cache
        table = {}

        def build(level, assign):
            if level == n:
                return ("L", fn(assign))
            v = order[level]
            a0 = dict(assign); a0[v] = 0
            a1 = dict(assign); a1[v] = 1
            lo = build(level + 1, a0)
            hi = build(level + 1, a1)
            if lo == hi:
                return lo
            key = (v, lo, hi)
            if key not in table:
                table[key] = key
            return table[key]
        build(0, {})
        return len(table)

    rows = []
    for n in (4, 8, 12, 16):
        # f = x0 y0 + x1 y1 + ... (the classic good/bad ordering example)
        half = n // 2
        def f(a, half=half):
            return int(any(a[i] and a[half + i] for i in range(half)))
        good = [j for i in range(half) for j in (i, half + i)]
        bad = list(range(n))
        rows.append([num(n), num(half),
                     num(bdd_nodes(f, n, good)), num(bdd_nodes(f, n, bad)),
                     num(bdd_nodes(f, n, bad) / max(bdd_nodes(f, n, good), 1), 4)])
    s.append(sweep("Measured decision-diagram size for "
                   "<i>x</i><sub>0</sub><i>y</i><sub>0</sub> + "
                   "<i>x</i><sub>1</sub><i>y</i><sub>1</sub> + &hellip; under two "
                   "variable orders",
        ["Variables", "Product terms", "Interleaved order (nodes)",
         "Separated order (nodes)", "Ratio"], rows,
        "Built by exhaustive construction with subfunction sharing, which is what "
        "reduction does. <b>The interleaved column is exactly <i>n</i>; the separated "
        "column is 2<sup><i>n</i>/2+1</sup>&minus;2.</b> Linear against exponential, on "
        "the same function with the same tool. The ratio is modest at these sizes "
        "because the exponent is small &mdash; at 40 variables it is a factor of "
        "52&#8239;000 &mdash; (2<sup>21</sup>&minus;2)/40 &mdash; which is the "
        "difference between a second and a week. "
        "This is the whole of BDD practice in one table."))

    s.append("<h2>X33.2 Why SAT is fast even though it is NP-complete</h2>")
    s.append(derive("What a modern SAT solver actually does", [
        ("Convert the circuit to CNF by Tseitin encoding: one variable per gate, a few "
         "clauses per gate.",
         "<b>Linear in circuit size</b> &mdash; no blow-up here, unlike naive "
         "expansion."),
        ("Search by assigning variables, propagating implications, and backtracking on "
         "conflict.",
         "DPLL. The naive version is hopeless."),
        ("<b>On conflict, derive a new clause that explains it (clause learning) and "
         "add it.</b>",
         "<b>This is the single change that made SAT practical.</b> The learned clause "
         "prunes an entire region of the search space, not just the current branch."),
        ("Backjump non-chronologically to the level the conflict actually came from.",
         "Rather than undoing one decision at a time."),
        ("Restart periodically, keeping the learned clauses.",
         "Escapes a bad region of the search while retaining what was learned."),
        ("<b>Result: industrial instances with millions of variables solve in "
         "seconds</b>, while small random instances at the hardness threshold do not.",
         "<b>Structure, not size, decides.</b> Circuits have enormous structure; that "
         "is why circuit problems are the easy case and why a tool's runtime is "
         "unpredictable in the specific way engineers observe."),
    ]))
    s.append(ex("Why equivalence checking succeeds where simulation cannot",
        "Comparing a 64-bit multiplier's RTL against its gate netlist.",
        "Compare the exhaustive-simulation cost with what an equivalence checker does "
        "instead.",
        [("Input space", "2<sup>128</sup>"),
         ("Vectors per second, simulated", "10<sup>7</sup>"),
         ("Time to simulate exhaustively",
          "&gt;10<sup>23</sup> years"),
         ("What an equivalence checker does",
          "<b>proves the two are equal for all inputs</b>"),
         ("How", "structural matching of internal points, then SAT on each cone"),
         ("Why it works", "<b>the two designs share almost all their internal "
          "structure</b>"),
         ("When it fails", "after retiming, resource sharing, or a datapath rewrite "
          "&mdash; the structure no longer matches")],
        "<b>By assuming equivalence checking always works.</b> It works because it finds "
        "internal equivalence points and cuts the problem into small cones; a "
        "transformation that destroys that correspondence &mdash; retiming across "
        "register boundaries, sequential optimisation, a multiplier architecture change "
        "&mdash; leaves the tool with one enormous cone and it fails. <b>The practical "
        "consequence is a rule for the synthesis flow</b>: turn on transformations that "
        "break equivalence checking only when you are prepared to verify the result "
        "another way, and know which ones they are before the schedule depends on "
        "them."))
    rows = []
    for name, cones, size in (("Control logic", 50000, 40), ("Datapath adders", 2000, 200),
                              ("Multiplier (structural match)", 500, 2000),
                              ("Multiplier (after rewrite)", 1, 500000)):
        rows.append([name, num(cones), num(size), num(cones * size),
                     "easy" if size < 5000 else "<b>the hard case</b>"])
    s.append(sweep("Why cone size, not design size, decides an equivalence check",
        ["Situation", "Cones", "Typical cone size (gates)", "Total gates",
         "Difficulty"], rows,
        "Illustrative structure counts. <b>The last row has the same total size and is "
        "the one that does not finish</b>, because the work per cone grows far faster "
        "than linearly."))

    s.append("<h2>X33.3 Model checking: proving something about all time</h2>")
    s.append(derive("Bounded model checking, and what &lsquo;bounded&rsquo; costs", [
        ("Unroll the design's transition relation <i>k</i> times.",
         "Copy the combinational logic <i>k</i> times, chaining state."),
        ("Assert the initial state and the negation of the property.",
         "If satisfiable, the assignment is a counterexample trace of length "
         "&le; <i>k</i>."),
        ("Hand the whole thing to SAT.",
         "<b>A bug of depth &le; <i>k</i> is found; a bug of depth <i>k</i>+1 is "
         "not.</b>"),
        ("So BMC is a very good bug hunter and <b>not a proof</b>.",
         "This is the distinction that matters when reading a tool's report: "
         "&lsquo;proven to depth 40&rsquo; is not &lsquo;proven&rsquo;."),
        ("A full proof needs induction, interpolation or IC3/PDR, which find an "
         "inductive invariant.",
         "<b>These do give unbounded proofs</b>, and they are what a tool means by "
         "&lsquo;proven&rsquo; without a depth."),
        ("The bound needed for confidence is the design's <i>diameter</i> &mdash; how "
         "many cycles to reach any reachable state.",
         "Usually unknown, and for a design with a large counter it is astronomically "
         "large. <b>Which is why counters are abstracted before proving anything around "
         "them.</b>"),
    ]))
    s.append("""<div class="warn"><b>The three ways a formal proof lies to you, in order
    of frequency.</b> <b>Over-constraint</b>: an assumption excludes the input that would
    have failed, so the property is proven about a machine that is not yours. This is the
    formal equivalent of a disabled checker and is by far the commonest; the defence is to
    check that the constraints are satisfiable together with interesting behaviour, which
    good tools report as &lsquo;assumption coverage&rsquo;. <b>Vacuity</b>: the property's
    antecedent never occurs, so it holds trivially &mdash; &lsquo;if a grant is given
    without a request&hellip;&rsquo; proven because no grant is ever modelled. <b>A
    bounded result read as a proof</b>, as above. <b>All three report green</b>, which is
    why this book's rule applies with full force here: a proof whose assumptions have not
    themselves been checked is an unexamined green light.</div>""")
    s.append(prob("Where should a design house spend its formal effort, given that it "
                  "cannot afford to prove everything?",
        "On the properties whose failure is catastrophic and whose state space is deep "
        "and narrow, which is where formal has the advantage over simulation. In "
        "practice that means, in order: <b>arbiters and any structure that can "
        "starve</b>, because starvation is a liveness property and simulation can never "
        "prove its absence; <b>FIFOs, credit counters and flow control</b>, where "
        "overflow and underflow are provable and the bugs appear only at full rate; "
        "<b>protocol interfaces</b>, where a vendor-supplied assertion set exists and "
        "proving compliance at the boundary is worth more than any amount of "
        "traffic; <b>clock-domain crossing structures</b>, where the interesting cases "
        "are timing-related and simulation is blind to them; and <b>security "
        "properties</b>, where the question is whether information can flow between two "
        "places and the answer must hold for all inputs. <b>What not to spend it on: "
        "datapath equivalence at the algorithm level</b> &mdash; a bit-exact reference "
        "model plus random simulation gets there faster &mdash; <b>and anything with a "
        "large counter in the cone</b>, until the counter has been abstracted."))
    return "\n".join(s)
