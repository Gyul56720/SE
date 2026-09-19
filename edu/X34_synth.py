# -*- coding: utf-8 -*-
"""Volume I, Part X34 -- Logic synthesis: what the tool is actually doing."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_synth():
    s = ['<h1 id="x34">X34. Logic Synthesis: What the Tool Is Actually Doing</h1>']
    s.append("""<p>Synthesis is the step an IP designer has least visibility into and
    most dependence on. Its behaviour is not arbitrary: it is a sequence of well-defined
    transformations with known strengths, and knowing them turns &lsquo;the tool did
    something odd&rsquo; into a specific diagnosis.</p>""")

    s.append("<h2>X34.1 The pipeline, stage by stage</h2>")
    s.append(tab("What each synthesis stage does and what it cannot do",
        ["Stage", "Input &rarr; output", "Optimises", "Cannot"],
        [["Elaboration", "RTL &rarr; generic netlist",
          "Nothing &mdash; it interprets the language",
          "<b>Fix a coding style that infers a latch</b>"],
         ["Datapath extraction", "Operators &rarr; architectures",
          "Picks adder and multiplier structures from a library",
          "Restructure an algorithm you wrote out by hand as gates"],
         ["<b>Technology-independent optimisation</b>",
          "Generic netlist &rarr; smaller generic netlist",
          "<b>Factoring, common subexpressions, constant propagation, redundancy "
          "removal</b>", "Know anything about delay in picoseconds"],
         ["<b>Technology mapping</b>", "Generic &rarr; library cells",
          "<b>Covers the network with cells at minimum cost &mdash; solvable optimally "
          "on a tree</b>", "Change the network's structure much"],
         ["Timing-driven restructuring", "Netlist &rarr; netlist",
          "Balances the critical path, duplicates, remaps",
          "Buy more than a limited amount &mdash; see Part&nbsp;X2"],
         ["Sizing and buffering", "Netlist &rarr; sized netlist",
          "<b>Convex, near-optimal (Part&nbsp;X26)</b>",
          "Fix a structural problem"]]))
    s.append("""<div class="ms"><b>Technology mapping is optimal on trees and heuristic
    on graphs, and that single fact explains most of what a synthesis tool does well.</b>
    The classic formulation covers a Boolean network with library cells at minimum cost.
    If the network is a tree, dynamic programming over the nodes gives a provably optimal
    cover in linear time. Real networks are DAGs with reconvergent fanout, so the tool
    partitions them into trees at multiple-fanout points, maps each optimally, and accepts
    that the partition itself was a heuristic choice. <b>The practical consequence is that
    logic with heavy reconvergence maps worse than logic without it</b>, and that
    restructuring an expression to reduce fanout &mdash; which looks cosmetic in RTL
    &mdash; can measurably change the result.</div>""")
    rows = []
    for depth in (2, 4, 6, 8, 10, 12):
        n_tree = 2 ** depth - 1
        rows.append([num(depth), num(n_tree), num(depth), num(n_tree * 4),
                     num(depth * 2 + 1)])
    s.append(sweep("A balanced tree of two-input gates: the structure mapping likes",
        ["Depth", "Gates", "Logic levels", "DP table entries (4 cells/node)",
         "Gate delays at 2 per level"], rows,
        "Dynamic-programming mapping visits each node once per candidate cell, so it is "
        "linear in gates times library size. <b>This is why mapping a million-gate "
        "design takes minutes</b> even though the underlying covering problem is "
        "NP-hard on general graphs."))

    s.append("<h2>X34.2 What your RTL controls, and what it does not</h2>")
    s.append(tab("RTL constructs and what the tool does with them",
        ["You write", "The tool produces", "You control it by"],
        [["<code>a + b</code>", "An adder chosen from an architecture library",
          "<b>The timing constraint &mdash; not by writing the adder yourself</b>"],
         ["<code>a * b</code>", "Booth or array multiplier, possibly shared",
          "Constraints, and <code>set_dont_use</code> if the choice is wrong"],
         ["<code>case</code> (full)", "A multiplexer tree", "Ordering and priority "
          "annotations"],
         ["<code>case</code> (incomplete, no default)",
          "<b>A latch &mdash; almost never what you meant</b>",
          "<b>Write the default; lint for it</b>"],
         ["<code>if</code> chain", "<b>Priority logic &mdash; deep and slow</b>",
          "Use <code>case</code> when the conditions are mutually exclusive"],
         ["A for loop", "Unrolled combinational logic",
          "The loop bound; there is no hardware loop"],
         ["<code>x &lt;= y</code> in a clocked block", "A flip-flop", "&mdash;"],
         ["Division by a variable", "<b>A large slow divider</b>",
          "Do not; see Part&nbsp;X9"],
         ["Division by a constant", "Shifts and adds",
          "Nothing needed &mdash; the tool does this well"]]))
    s.append(ex("The cost of an if-chain that should have been a case",
        "A 16-way priority <code>if/else if</code> chain versus a 16-way "
        "<code>case</code>, each selecting between 16 values.",
        "Count the logic levels. A priority chain is a serial selection; a case is a "
        "balanced tree, because the tool knows the conditions are mutually exclusive.",
        [("Priority chain: multiplexers in series", num(16)),
         ("Delay at ~2 gate levels per 2:1 mux", num(32) + " gate levels"),
         ("Case: mux tree depth", num(int(math.log2(16)))),
         ("Delay", num(8) + " gate levels"),
         ("Ratio", num(4, 3) + "&times;"),
         ("At 25&nbsp;ps per gate level",
          num(32 * 25, 4) + "&nbsp;ps vs " + num(8 * 25, 4) + "&nbsp;ps"),
         ("Period this costs at 1&nbsp;GHz", "<b>60&nbsp;% of it, for nothing</b>")],
        "<b>By assuming the tool will notice the conditions are exclusive.</b> "
        "Sometimes it does, and it cannot in general &mdash; proving exclusivity is a "
        "Boolean problem it does not always attempt. Writing <code>case</code>, or "
        "annotating the chain as parallel, tells it directly. <b>This is the single "
        "highest-value RTL coding habit for timing</b>, and it costs nothing; a priority "
        "structure should appear only where priority is actually meant, and then the "
        "depth is a deliberate cost rather than an accident."))

    s.append("<h2>X34.3 Retiming: moving registers without changing behaviour</h2>")
    s.append(derive("Why retiming is a graph problem with an exact answer", [
        ("Model the circuit as a graph: nodes are combinational blocks with delay, "
         "edges carry a register count.",
         "The standard retiming model."),
        ("Retiming assigns each node an integer <i>r<sub>v</sub></i>: move "
         "<i>r<sub>v</sub></i> registers from its outputs to its inputs.",
         "Registers on edge (<i>u</i>,<i>v</i>) become "
         "<i>w</i> + <i>r<sub>v</sub></i> &minus; <i>r<sub>u</sub></i>."),
        ("Legality requires every edge to keep a non-negative count: "
         "<i>r<sub>u</sub></i> &minus; <i>r<sub>v</sub></i> &le; <i>w</i>.",
         "<b>A system of difference constraints</b> &mdash; exactly the structure "
         "Part&nbsp;X26 identified as solvable."),
        ("Achieving period <i>P</i> adds more difference constraints between node "
         "pairs.",
         "Derived from the longest combinational path between them."),
        ("So &lsquo;is period <i>P</i> achievable by retiming?&rsquo; is a "
         "negative-cycle test, and binary search over <i>P</i> finds the optimum.",
         "<b>Polynomial, exact, and implemented in every synthesis tool.</b>"),
        ("What it cannot do: change the number of registers on any cycle.",
         "<b>The latency around a feedback loop is invariant under retiming</b>, which "
         "is why retiming cannot fix a loop that is too long &mdash; Part&nbsp;X4's DFE "
         "problem is exactly this, and the answer there was unrolling, which changes the "
         "graph."),
    ]))
    s.append("""<div class="warn"><b>Retiming is exact and is nevertheless often turned
    off, for reasons worth knowing.</b> It renames and moves registers, which breaks the
    structural correspondence equivalence checking depends on (Part&nbsp;X33), so
    verification becomes sequential equivalence checking &mdash; a much harder problem
    that may not complete. It also destroys the correspondence between RTL signal names
    and netlist nodes, which makes debug and ECOs painful, and it can interact badly with
    scan insertion and with clock gating. <b>The common compromise is to retime within
    a clearly delimited pipeline and to verify that block by simulation against its
    pre-retiming version</b>, rather than enabling it design-wide.</div>""")
    s.append(prob("Synthesis reports your block at 620&nbsp;MHz against a 700&nbsp;MHz "
                  "target. List what you would try, in order of cost.",
        "Cheapest first, because the early items often suffice. <b>Check the constraints "
        "before the design</b>: an over-constrained input delay, a missing "
        "multicycle path, or a clock defined without its uncertainty will each produce a "
        "believable-looking failure that no RTL change fixes. <b>Read the critical path "
        "and classify it</b> &mdash; if it crosses a whole datapath it is structural, if "
        "it is a long priority chain it is X34.2, if it starts or ends at a boundary it "
        "is a constraint issue, and each has a different fix. <b>Try the free "
        "restructuring</b>: turn an if-chain into a case, split a wide comparison, move a "
        "constant multiplication to a shift-add, precompute something that depends only "
        "on slowly changing inputs (Part&nbsp;X9's rule). <b>Then pipeline</b> &mdash; "
        "one more stage, which costs latency and a verification change and is usually "
        "decisive. <b>Then re-architect</b>: parallel slices at a lower rate, which is "
        "Part&nbsp;X7's energy argument arriving as a timing fix. <b>What not to do "
        "first is instantiate gates by hand</b>; it is slow, it does not port, and the "
        "tool is better at it than you are except in the rare case where you know "
        "something it cannot &mdash; and then you should be telling it, through a "
        "constraint, rather than bypassing it."))
    return "\n".join(s)
