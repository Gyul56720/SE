# -*- coding: utf-8 -*-
"""Volume I, Part X14 -- Physical design as the digital designer sees it."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_physdes2():
    s = ['<h1 id="x14">X14. Physical Design as the RTL Designer Sees It</h1>']
    s.append("""<p>A soft-IP vendor does not run place-and-route on the customer's chip,
    but the vendor's RTL determines whether that run succeeds. This part covers the
    physical facts that propagate back into RTL decisions, with the arithmetic that makes
    them checkable.</p>""")

    s.append("<h2>X14.1 Wire delay does not scale, and that changes architecture</h2>")
    s.append(derive("Why a long wire gets relatively slower every generation", [
        ("A wire's distributed RC delay is 0.38<i>rcL</i><sup>2</sup> for resistance "
         "<i>r</i> and capacitance <i>c</i> per unit length.",
         "Elmore delay of a distributed line. <b>Quadratic in length</b> &mdash; the "
         "single most important fact in this chapter."),
        ("Scaling reduces wire cross-section, so <i>r</i> rises roughly as "
         "1/<i>S</i><sup>2</sup> while <i>c</i> stays roughly constant.",
         "Thinner and narrower conductor, same dielectric spacing ratio."),
        ("A wire of <i>fixed physical length</i> therefore gets slower as the process "
         "shrinks.",
         "While gates get faster. <b>The ratio moves against the wire every "
         "generation.</b>"),
        ("Buffering breaks the quadratic: <i>k</i> equal segments give "
         "<i>k</i>&middot;(<i>L</i>/<i>k</i>)<sup>2</sup> = <i>L</i><sup>2</sup>/<i>k</i> "
         "plus <i>k</i> buffer delays.",
         "Optimise over <i>k</i> and the delay becomes <b>linear</b> in <i>L</i>."),
        ("So a long wire costs area and power, and it costs a fixed delay per "
         "millimetre that no amount of cleverness removes.",
         "<b>Which makes distance an architectural quantity.</b> A design whose blocks "
         "must exchange data every cycle across a chip is not implementable at high "
         "frequency, however good the RTL."),
    ]))
    rows = []
    r_per_mm, c_per_mm = 250.0, 200e-15      # ohm/mm, F/mm (intermediate metal, indicative)
    for L in (0.1, 0.5, 1.0, 2.0, 5.0, 10.0):
        unbuf = 0.38 * r_per_mm * L * c_per_mm * L * 1e12
        k = max(1, int(round(L / 0.4)))
        buf = (0.38 * r_per_mm * (L / k) * c_per_mm * (L / k) * k) * 1e12 + k * 20e-12 * 1e12
        rows.append([num(L, 3), num(unbuf, 4), num(k), num(buf, 4),
                     num(buf / L, 4), num(unbuf / max(buf, 1e-9), 3)])
    s.append(sweep("Wire delay with and without optimal buffering "
                   "(250&nbsp;&Omega;/mm, 200&nbsp;fF/mm, 20&nbsp;ps buffers)",
        ["Length (mm)", "Unbuffered delay (ps)", "Buffers", "Buffered delay (ps)",
         "ps per mm", "Speed-up"], rows,
        "The constants are indicative of an intermediate metal layer in a mature node "
        "and are not from a specific PDK. <b>The shape is what matters</b>: the "
        "unbuffered column is quadratic, the buffered column is linear, and the "
        "per-millimetre figure is roughly constant &mdash; which is why architects "
        "budget in millimetres."))
    s.append(ex("How far can a signal travel in one cycle?",
        "A 1&nbsp;GHz design in the process above. Allow half the period for wire and "
        "half for logic and flop overhead.",
        "Divide the available wire time by the per-millimetre delay from the table.",
        [("Period", num(1000, 4, "ps")),
         ("Wire budget", num(500, 3, "ps")),
         ("Delay per mm, buffered", num(float(rows[3][4]), 4, "ps/mm")),
         ("Reachable distance in one cycle",
          num(500 / float(rows[3][4]), 3, "mm")),
         ("At 3&nbsp;GHz", num(500 / 3 / float(rows[3][4]), 3, "mm")),
         ("Typical die edge", num(10, 3, "mm"))],
        "<b>By assuming any module can talk to any module in one cycle.</b> At "
        "3&nbsp;GHz a signal crosses a fraction of a large die per cycle, so a "
        "chip-spanning bus is physically impossible at that frequency and the "
        "architecture must be pipelined, hierarchical, or both. <b>This is the physical "
        "origin of networks-on-chip</b>: not a preference for packets, but the "
        "observation that a global broadcast wire no longer exists. For an IP vendor the "
        "practical consequence is to keep the block's internal critical paths local and "
        "to <b>register every boundary signal</b>, so the customer's floorplanner has "
        "somewhere to put the pipeline stages the distance demands."))

    s.append("<h2>X14.2 What synthesis can and cannot fix</h2>")
    s.append(tab("Where a problem must be solved",
        ["Problem", "Can synthesis fix it?", "Who must"],
        [["Slow gate on the critical path", "<b>Yes</b> &mdash; upsizing, Vt swap",
          "The tool"],
         ["Badly structured arithmetic", "Usually &mdash; it re-implements operators",
          "The tool, if the RTL uses <code>+</code> and <code>*</code> rather than "
          "hand-built structures"],
         ["<b>Too many logic levels between flops</b>", "<b>No</b>",
          "<b>The RTL &mdash; add a pipeline stage</b>"],
         ["High fan-out net", "Partly &mdash; it buffers",
          "The RTL, if the fan-out is architectural (a global enable)"],
         ["Congestion from a crossbar", "No", "The architecture &mdash; reduce the "
          "radix or add a stage"],
         ["Clock domain crossing", "No &mdash; and it may <i>break</i> one by "
          "optimising away a synchroniser",
          "<b>The RTL, plus constraints marking the crossing</b>"],
         ["Latch inferred from an incomplete case", "It will report it",
          "<b>The RTL &mdash; always</b>"],
         ["Multi-cycle path", "No", "The constraint file, with justification"]]))
    s.append("""<div class="warn"><b>Synthesis can delete your synchroniser.</b> The two
    flops of a synchroniser are functionally redundant to a tool that believes the input
    is a normal signal: it may merge them, retime through them, or move one across a
    boundary, any of which destroys the resolution time the MTBF calculation of
    Part&nbsp;X3 depends on. The defences are to mark the flops with a synthesis attribute
    that forbids merging and retiming, to place them in a module the tool is told not to
    ungroup, and <b>to check the gate-level netlist that they are still there</b> &mdash;
    a check that can be automated and belongs in the sign-off list. A design that relies on
    the tool's good behaviour here has an MTBF nobody has verified.</div>""")

    s.append("<h2>X14.3 Utilisation, congestion and the numbers that predict trouble</h2>")
    rows = []
    for util in (50, 60, 70, 75, 80, 85, 90):
        # heuristic: routing difficulty rises sharply above ~75%
        diff = 1.0 / max(1e-6, (1.0 - util / 100.0)) ** 1.5
        rows.append([num(util), num(diff, 4), num(diff / (1 / 0.5 ** 1.5), 3),
                     "comfortable" if util <= 70 else
                     ("tight" if util <= 80 else "<b>expect congestion</b>")])
    s.append(sweep("Relative routing difficulty against placement utilisation "
                   "(heuristic model)",
        ["Utilisation (%)", "Relative difficulty", "vs. 50&nbsp;%", "Practical verdict"],
        rows,
        "The model is a heuristic, not a PDK number: difficulty grows as "
        "(1&minus;<i>u</i>)<sup>&minus;1.5</sup>. <b>Its only job is to make the shape "
        "visible</b> &mdash; the cost is mild to 70&nbsp;% and then rises very fast, "
        "which is why floorplans target 65&ndash;75&nbsp;% and why &lsquo;we will just "
        "raise utilisation&rsquo; is rarely the answer to an area problem."))
    s.append("""<div class="ms"><b>Congestion is caused by pin density and connectivity,
    not by cell area, and this distinction decides what an RTL designer can do about
    it.</b> A block that is 60&nbsp;% utilised can be unroutable if its cells are small
    and richly connected &mdash; a crossbar, a large multiplexer tree, a register file
    read network &mdash; because the routing demand per unit area is set by nets crossing
    a boundary, not by transistors under it. The RTL-level remedies are therefore about
    <i>connectivity</i>: reduce the radix of a switch and add a stage; replace a
    fully-connected structure with a hierarchical one; move a wide mux into a memory where
    the decoder is dense and local; and <b>avoid the one-hot broadcast structures that
    look cheap in gate count and are expensive in tracks.</b> An area report will not show
    any of this; a congestion map will.</div>""")
    s.append(prob("Your block meets timing standalone at 800&nbsp;MHz but the customer "
                  "reports it fails at 600&nbsp;MHz in their chip. Name four causes, in "
                  "the order you would check them.",
        "<b>1. Different constraints.</b> Your standalone run may have used ideal clocks, "
        "no input/output delay, or a different corner set. Ask for their SDC and compare "
        "it with yours line by line; this is the cause more often than the other three "
        "together. <b>2. Boundary paths.</b> Standalone runs frequently constrain inputs "
        "and outputs generously; in the chip your block's inputs arrive late and its "
        "outputs must arrive early. This is why registering every boundary is worth the "
        "latency &mdash; it makes your timing independent of their floorplan. "
        "<b>3. Physical context.</b> In their chip your block may be stretched around a "
        "macro, sit far from its clock source, or share power rails with a noisy "
        "neighbour, all of which add delay your standalone run did not model. "
        "<b>4. A different library or corner.</b> Same process, different vendor library "
        "or different Vt mix, and your critical path is no longer their critical path. "
        "<b>The general lesson for a vendor is to ship the constraints and the "
        "conditions with the frequency claim</b>; a frequency without them is not a "
        "specification, and this exact conversation is why."))
    s.append(prob("Why do IP vendors quote area in gate equivalents rather than "
                  "square micrometres?",
        "Because square micrometres are meaningless without naming the process, the "
        "library and the utilisation, and a vendor who names all three has effectively "
        "told a competitor which foundry and library they used. A gate equivalent &mdash; "
        "conventionally the area of a two-input NAND in the same library &mdash; is a "
        "ratio, so it survives the translation between processes approximately, and it "
        "lets a customer scale to their own library by multiplying by their NAND area. "
        "<b>The approximation is worse than it looks</b>, because the ratio of flop area "
        "to NAND area and of SRAM bit-cell area to NAND area both vary between libraries, "
        "so a flop-heavy block converts less accurately than a logic-heavy one. The "
        "honest datasheet therefore gives <b>gate equivalents, flop count and memory bits "
        "separately</b>, which lets the customer do the conversion properly, and costs "
        "the vendor nothing."))
    return "\n".join(s)
