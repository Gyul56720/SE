# -*- coding: utf-8 -*-
"""Volume I, Part X26 -- Optimisation, the tool behind every EDA algorithm."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_opt2():
    s = ['<h1 id="x26">X26. Optimisation, the Tool Behind Every EDA Algorithm</h1>']
    s.append("""<p>Placement, routing, scheduling, word-length allocation, retiming,
    technology mapping and gate sizing are all optimisation problems, and knowing which
    <i>class</i> a problem belongs to tells you immediately whether a tool can solve it
    exactly, approximately, or not at all. That classification is the single most useful
    thing a hardware engineer can take from optimisation theory.</p>""")

    s.append("<h2>X26.1 The classification that matters</h2>")
    s.append(tab("Problem classes and what each means for a tool",
        ["Class", "Solvable?", "Scale", "Examples in this book"],
        [["<b>Convex (LP, QP, SOCP, SDP)</b>",
          "<b>Yes, to global optimality, reliably</b>",
          "10<sup>5</sup>&ndash;10<sup>6</sup> variables",
          "<b>Gate sizing via geometric programming</b>; filter design with quantised "
          "constraints; buffer insertion"],
         ["Integer linear (ILP)", "Exactly, but exponentially in the worst case",
          "10<sup>3</sup>&ndash;10<sup>4</sup> for structured problems",
          "Scheduling in HLS; technology mapping; test-pattern compaction"],
         ["Submodular", "Greedy gives 1&minus;1/e of optimal &mdash; provably",
          "Large", "Sensor or test-point placement; coverage maximisation"],
         ["<b>Graph-structured (shortest path, max flow, matching)</b>",
          "<b>Yes, polynomial</b>", "10<sup>6</sup>+",
          "<b>Maze routing, retiming, clock skew scheduling, partitioning bounds</b>"],
         ["General non-convex", "Local optima only", "&mdash;",
          "Placement, analogue sizing, neural-network training"],
         ["NP-hard with no structure", "Heuristics",
          "&mdash;", "Placement and routing as a whole"]]))
    s.append("""<div class="ms"><b>The reason gate sizing is solved and placement is
    not.</b> Gate delay as a function of sizes is a <i>posynomial</i> &mdash; a sum of
    terms with positive coefficients and real exponents &mdash; and minimising a
    posynomial subject to posynomial constraints is a geometric program, which becomes
    convex under a logarithmic change of variables. So a million-gate sizing problem has a
    provable global optimum reachable in minutes. Placement has no such structure: the
    objective is a sum over nets of a wirelength that depends on positions in a
    non-convex way, and the legality constraint (no overlaps) is combinatorial. <b>When a
    tool vendor says their sizer is optimal and their placer is good, both statements are
    precise</b>, and knowing why tells you which one to argue with.</div>""")
    rows = []
    for n in (10, 100, 1000, 10000, 100000):
        rows.append([num(n), num(n ** 3 / 1e9, 4), num(n * math.log2(n) / 1e6, 4),
                     num(2 ** min(n, 40) if n <= 40 else float("inf"), 2)
                     if n <= 40 else "&gt;10<sup>12</sup>",
                     num(n * n / 1e6, 4)])
    s.append(sweep("Why complexity class decides the tool, in seconds at "
                   "10<sup>9</sup> operations per second",
        ["Problem size <i>n</i>", "<i>n</i><sup>3</sup> (s)",
         "<i>n</i>&nbsp;log&nbsp;<i>n</i> (ms)", "2<sup><i>n</i></sup>",
         "<i>n</i><sup>2</sup> (ms)"], rows,
        "<b>The exponential column is the reason exact methods are confined to "
        "subproblems.</b> An ILP over a hundred variables may solve in seconds because "
        "its structure prunes the tree; the same ILP over a hundred thousand will not "
        "solve before the product is obsolete, and no faster computer changes that."))

    s.append("<h2>X26.2 Convexity, and how to recognise it in your own problem</h2>")
    s.append(derive("What convexity buys, and why", [
        ("A set is convex if the segment between any two of its points stays inside.",
         "Definition."),
        ("A function is convex if its epigraph is a convex set &mdash; equivalently, if "
         "the chord lies above the curve.",
         "Definition."),
        ("<b>For a convex problem, every local minimum is global.</b>",
         "Suppose a local minimum <i>x</i> and a better point <i>y</i>; the segment "
         "from <i>x</i> to <i>y</i> is feasible and the function along it lies below "
         "the chord, so points arbitrarily close to <i>x</i> beat it, contradicting "
         "local minimality."),
        ("So a descent method cannot get stuck, and a duality gap of zero gives a "
         "<i>certificate</i> of optimality.",
         "<b>The certificate is the practical payoff</b>: you can prove to a customer "
         "that no better answer exists, rather than saying the tool stopped."),
        ("Convexity is preserved by non-negative sums, pointwise maxima, and "
         "composition with affine maps.",
         "<b>These three rules are how you recognise convexity in practice</b> &mdash; "
         "build the objective from convex pieces and it is convex by construction."),
    ]))
    s.append(ex("Recognising a convex problem in word-length allocation",
        "Minimise total multiplier area &Sigma;<i>w<sub>i</sub></i><sup>2</sup> subject "
        "to a noise constraint &Sigma;<i>g<sub>i</sub></i>"
        "4<sup>&minus;<i>w<sub>i</sub></i></sup> &le; &epsilon;, where "
        "<i>g<sub>i</sub></i> &gt; 0 are measured noise gains from Part&nbsp;X1's sweep.",
        "Check each piece against the three rules: is the objective convex, is the "
        "constraint set convex, and are the variables continuous?",
        [("Objective &Sigma;<i>w</i><sup>2</sup>", "convex (sum of convex)"),
         ("4<sup>&minus;<i>w</i></sup>", "convex (exponential of an affine map)"),
         ("<i>g<sub>i</sub></i> &gt; 0 weighting", "preserves convexity"),
         ("Constraint set", "convex sublevel set of a convex function"),
         ("Relaxed problem", "<b>convex &mdash; solvable exactly</b>"),
         ("The catch", "<b><i>w<sub>i</sub></i> must be integers</b>"),
         ("Practical route",
          "solve the relaxation, then round and repair &mdash; and the relaxation's "
          "value is a <b>lower bound</b> on the integer optimum")],
        "<b>By throwing away the relaxation once you have rounded.</b> The relaxed "
        "solution's cost is a bound, so it tells you how much the rounding cost and "
        "therefore whether it is worth searching harder. A greedy word-length search "
        "that reports &lsquo;we found 148&nbsp;kGE&rsquo; says nothing; one that reports "
        "&lsquo;148&nbsp;kGE against a lower bound of 141&rsquo; says the search is "
        "within five per cent and can stop. <b>Bounds turn an open-ended search into a "
        "finished task</b>, which is worth more than the few per cent themselves."))
    # measure a relaxation gap
    rng = np.random.default_rng(29)
    rows = []
    for n in (4, 8, 16, 32):
        g = rng.uniform(0.2, 4.0, n)
        eps = 1e-4
        # continuous optimum by Lagrange: w_i = log4(g_i * lambda)
        def cost(ws):
            return float(np.sum(ws ** 2))
        def noise(ws):
            return float(np.sum(g * 4.0 ** (-ws)))
        lo, hi = 1e-6, 1e12
        for _ in range(200):
            lam = math.sqrt(lo * hi)
            w = np.maximum(0.0, np.log(g * lam) / math.log(4))
            if noise(w) > eps:
                lo = lam
            else:
                hi = lam
        wc = np.maximum(0.0, np.log(g * math.sqrt(lo * hi)) / math.log(4))
        wi = np.ceil(wc)
        rows.append([num(n), num(cost(wc), 5), num(cost(wi), 5),
                     num((cost(wi) - cost(wc)) / cost(wc) * 100, 4),
                     num(noise(wi) / eps, 4)])
    s.append(sweep("Measured relaxation gap for word-length allocation: continuous "
                   "optimum, rounded up, and the slack that rounding wastes",
        ["Nodes", "Continuous cost (lower bound)", "Integer cost", "Gap (%)",
         "Noise used / budget"], rows,
        "Solved by bisection on the Lagrange multiplier, which is exact for this "
        "separable convex problem. <b>The last column shows the rounding buying "
        "unwanted margin</b> &mdash; noise well under budget &mdash; which is the "
        "signal that a repair step (reduce the node with the best cost-per-noise "
        "trade until the budget is met) will recover most of the gap."))

    s.append("<h2>X26.3 Graph problems: the ones that are actually solved</h2>")
    s.append(tab("Graph algorithms an IP designer meets",
        ["Problem", "Algorithm", "Complexity", "Where"],
        [["Shortest path", "Dijkstra, Bellman&ndash;Ford",
          "<i>O</i>(<i>E</i> log <i>V</i>)",
          "Maze routing; <b>timing analysis is longest path on a DAG</b>"],
         ["<b>Longest path on a DAG</b>", "<b>Topological order then relax</b>",
          "<b><i>O</i>(<i>V</i>+<i>E</i>)</b>",
          "<b>Static timing analysis &mdash; this is the whole algorithm</b>"],
         ["Negative cycle detection", "Bellman&ndash;Ford",
          "<i>O</i>(<i>VE</i>)",
          "<b>Clock skew scheduling feasibility; retiming</b>"],
         ["Maximum flow / min cut", "Push-relabel",
          "<i>O</i>(<i>V</i><sup>3</sup>)", "Partitioning, FPGA packing"],
         ["Maximum matching", "Hopcroft&ndash;Karp",
          "<i>O</i>(<i>E</i>&radic;<i>V</i>)", "Resource binding in HLS; scan chain "
          "stitching"],
         ["Graph colouring", "Heuristic (NP-hard)", "&mdash;",
          "Register allocation; via-layer assignment"],
         ["Strongly connected components", "Tarjan", "<i>O</i>(<i>V</i>+<i>E</i>)",
          "<b>Finding the combinational loops a synthesis tool complains about</b>"]]))
    s.append("""<div class="bs"><b>Static timing analysis is longest-path on a directed
    acyclic graph, and saying so demystifies it.</b> Nodes are pins, edges are cell and
    net delays, and the arrival time at a node is the maximum over incoming edges of
    (arrival at the source plus edge delay) &mdash; computed once in topological order, in
    time linear in the design. That is why STA runs on a hundred million gates in minutes
    while simulation of the same design takes days: <b>STA never enumerates paths, it
    propagates a single number per node.</b> It also explains the tool's two famous
    characteristics. Timing is <i>pessimistic</i>, because the maximum is taken without
    checking whether the path is functionally sensitisable &mdash; hence false paths. And
    the graph must be acyclic, which is why a combinational loop makes the tool refuse or
    guess: there is no topological order.</div>""")
    rows = []
    for v, e in ((1e4, 3e4), (1e5, 3e5), (1e6, 3e6), (1e7, 3e7), (1e8, 3e8)):
        sta = (v + e) / 1e8
        paths = "exponential"
        rows.append([num(int(v)), num(int(e)), num(sta, 4),
                     num(sta * 12 * 3 / 60, 4), paths])
    s.append(sweep("Why STA scales and path enumeration does not "
                   "(10<sup>8</sup> graph operations per second)",
        ["Pins", "Edges", "One STA pass (s)",
         "Full MMMC sign-off, 36 corners (min)", "Enumerating all paths"], rows,
        "The linear-time propagation is what makes sign-off possible at all. "
        "<b>The corner count of Part&nbsp;X2, multiplied by this, is the real "
        "sign-off cost</b>, and it is why corner pruning is worth arguing about."))
    s.append(prob("Clock skew scheduling is posed as: choose a delay for each flop's "
                  "clock so every setup and hold constraint is met. Why is this "
                  "solvable exactly, when placement is not?",
        "Because every constraint has the form <i>t<sub>j</sub></i>&nbsp;&minus;&nbsp;"
        "<i>t<sub>i</sub></i>&nbsp;&le;&nbsp;<i>c<sub>ij</sub></i> &mdash; a "
        "<b>difference constraint</b> &mdash; where the <i>t</i> are the clock arrival "
        "times and the constants come from the setup and hold inequalities of "
        "Part&nbsp;X2. A system of difference constraints is exactly a shortest-path "
        "problem on a constraint graph: it is feasible if and only if the graph has no "
        "negative cycle, and Bellman&ndash;Ford both decides that and produces a "
        "solution, in polynomial time. <b>The structure, not the size, is what makes it "
        "tractable</b>, and the negative cycle is even interpretable &mdash; it is a loop "
        "of flops whose combined constraints cannot be satisfied at this period, which "
        "tells you precisely which part of the design sets the frequency. Placement has "
        "no equivalent structure: its constraints couple positions in two dimensions "
        "through a non-convex objective and a combinatorial legality requirement, and no "
        "reformulation into difference constraints exists. <b>Recognising a problem as a "
        "system of difference constraints is worth doing deliberately</b>; it turns "
        "several apparently hard scheduling questions in hardware design into "
        "Bellman&ndash;Ford."))
    return "\n".join(s)
