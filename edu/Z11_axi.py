# -*- coding: utf-8 -*-
"""Volume III, Part Z11 -- Writing the AXI wrapper a customer will accept."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_wrap():
    b = []
    b.append(f'<rect x="16" y="18" width="372" height="132" fill="none" '
             f'stroke="#123f6d" stroke-width="1.4"/>')
    b.append(txt(202, 14, "what you deliver", 8, "middle"))
    b.append(box(32, 34, 96, 30, "AXI-Lite", "register file", 8))
    b.append(box(32, 78, 96, 30, "AXI-Stream", "sink", 8))
    b.append(box(32, 114, 96, 26, "AXI-Stream", "source", 8))
    b.append(box(164, 60, 100, 56, "your core", "clock-agnostic", 9,
                 fill="#eef7f2"))
    b.append(box(292, 60, 84, 56, "CDC", "if needed", 8))
    b.append(arr(128, 49, 164, 60))
    b.append(arr(128, 93, 164, 82))
    b.append(arr(164, 110, 128, 127))
    b.append(arr(264, 88, 292, 88))
    b.append(txt(202, 166, "The core knows nothing about AXI. The wrapper knows "
                           "nothing about the algorithm.", 9, "middle"))
    b.append(txt(202, 180, "That separation is what lets you sell the same core with "
                           "three different wrappers.", 9, "middle",
                 'font-style="italic"'))
    return svg(410, 190, "".join(b))


def ch_axiwrap():
    s = ['<h1 id="z11">Z11. Writing the AXI Wrapper a Customer Will Accept</h1>']
    s.append("""<p>Almost every block a design house sells is bought as an AXI
    peripheral, and almost every integration complaint is about the wrapper rather than
    the core. This part is the wrapper &mdash; what it must do, what it must not do, and
    the specific mistakes that cost a week at the customer's end.</p>""")
    s.append(fig(_f_wrap(), "The separation that makes a core sellable more than once."))

    s.append("<h2>Z11.1 Keep the protocol out of the core</h2>")
    s.append(derive("Why the boundary pays for itself three times", [
        ("A core that consumes and produces values, with a simple ready/valid or an "
         "enable, has no protocol in it.",
         "It can be tested against the golden model directly &mdash; Part Z1's "
         "arrangement."),
        ("The wrapper translates AXI into that.",
         "And it is the same wrapper for every core you build."),
        ("<b>First payment: verification.</b> The core is verified against the model; "
         "the wrapper is verified against the protocol.",
         "Two small problems instead of one large one, and the protocol half is "
         "reusable."),
        ("<b>Second payment: the customer.</b> Some want AXI-Stream, some AXI4, some "
         "a bare FIFO, some APB for configuration only.",
         "<b>A core with the protocol baked in has to be rewritten for each.</b>"),
        ("<b>Third payment: the standard changes and the core does not.</b>",
         "AMBA revisions, a move to CHI, a customer's proprietary fabric &mdash; all "
         "wrapper work."),
        ("The cost is one extra level of hierarchy and a handful of registers.",
         "<b>Which Part X37's skid-buffer argument says you wanted anyway</b>, because "
         "registering the boundary is what keeps your timing independent of their "
         "floorplan."),
    ]))
    s.append(tab("What belongs on each side of the line",
        ["Belongs in the wrapper", "Belongs in the core"],
        [["AXI channels and their handshakes", "The algorithm"],
         ["Burst handling, ID management, ordering", "Word lengths and pipelining"],
         ["The register file (generated &mdash; Part Z4)", "Nothing about registers "
          "&mdash; it takes parameters and strobes"],
         ["Clock domain crossing, if the customer's is different",
          "One clock; no assumptions about its rate"],
         ["Error responses (SLVERR, DECERR)", "An error <i>flag</i>, not a bus code"],
         ["<b>Back pressure and buffering</b>",
          "<b>A stall input it honours &mdash; nothing more</b>"],
         ["Low-power and isolation (Part X43)", "A clock enable"]]))

    s.append("<h2>Z11.2 The wrapper mistakes that cost a week</h2>")
    rows = [
        ["<b><code>s_ready</code> depends combinationally on <code>s_valid</code></b>",
         "<b>Deadlock or oscillation when the partner does the same</b>",
         "Register one side; a skid buffer costs two entries and one cycle"],
        ["No skid buffer, both directions registered",
         "<b>Throughput halves</b> and functional tests still pass",
         "Part X37's table &mdash; measure transfers per cycle, not correctness"],
        ["Read and write share an internal queue",
         "<b>Deadlock in the customer's system, never in yours</b>",
         "Part X11 &mdash; keep the AXI channels independent all the way in"],
        ["Bursts allowed to cross a 4&nbsp;kB boundary",
         "Protocol violation the interconnect may not check",
         "Split in the wrapper; it is a comparison and an adder"],
        ["<b><code>WSTRB</code> ignored</b>",
         "<b>Neighbouring bytes corrupted on a narrow write</b>",
         "Honour it, or declare the register file 32-bit-only in the guide"],
        ["Write response returned before the write is visible",
         "A driver's read-after-write returns stale data",
         "Define and document the visibility point"],
        ["Reset not synchronised per domain",
         "One boot in a thousand (Part X42)",
         "Two flops per domain; the constraint shipped with the block"],
        ["<b>Register map hand-written into the wrapper</b>",
         "<b>Diverges from the header and the datasheet</b>",
         "<b>Generate it &mdash; Part Z4</b>"],
    ]
    s.append(sweep("Eight wrapper defects, what each looks like, and the fix",
        ["Mistake", "Symptom", "Fix"], rows,
        "<b>Six of the eight pass a functional test.</b> They are found at integration, "
        "at line rate, or in the customer's system &mdash; which is why the release "
        "gate of Part&nbsp;Z3 checks throughput and why the testbench must apply "
        "randomised back pressure rather than accepting everything."))
    s.append(ex("Proving the wrapper does not halve your throughput",
        "An AXI-Stream wrapper around a core that accepts one word per cycle. The "
        "customer will measure sustained throughput with back pressure applied at "
        "random.",
        "State the bound, measure it, and put the measurement in the datasheet &mdash; "
        "the same three steps the agent's throughput check performs.",
        [("Ideal", "1 word/cycle"),
         ("With random back pressure at 50&nbsp;%", "0.5 word/cycle &mdash; expected"),
         ("<b>With a missing skid buffer</b>",
          "<b>0.25 &mdash; and every value is still correct</b>"),
         ("What a value-only regression says", "<b>pass</b>"),
         ("What the throughput check says",
          "<b>cycles &gt; bound &rarr; red</b>"),
         ("Where the bound comes from",
          "<b>measured on the clean block over several seeds</b>"),
         ("This repository's example",
          "crc32_stream: 2.18 clean vs 3.16 broken cycles/byte, bound 2.6")],
        "<b>By declaring a bound from the architecture rather than from a "
        "measurement.</b> The architectural ideal is one word per cycle and no real "
        "testbench achieves it, so a bound set from the ideal never fires and a bound "
        "set by guessing is either useless or a false alarm. <b>Measure the clean block "
        "on several seeds, check the spread is small, and set the bound just above "
        "it</b> &mdash; which in this repository's case caught a mutation that a "
        "value-only suite had missed."))

    s.append("<h2>Z11.3 What ships with the wrapper</h2>")
    s.append(tab("The wrapper's own deliverables",
        ["Item", "Why the customer needs it"],
        [["The SDC constraints for the boundary",
          "<b>Your timing claim is meaningless without them</b> &mdash; Part X14"],
         ["CDC constraints, if the block crosses domains",
          "Their tool will flag the crossing and stop; the waiver must come from you"],
         ["<b>Protocol assertions (SVA) on the AXI interfaces</b>",
          "<b>They can bind them in their environment and see your block behaving</b>"],
         ["A bus functional model or a trivial testbench",
          "So they can run it in ten minutes, which is when they decide"],
         ["The register map in IP-XACT", "Automated integration"],
         ["A reference integration: your block plus a stub master",
          "<b>Removes the whole class of &lsquo;it does not work&rsquo; reports where "
          "the wiring was wrong</b>"]]))
    s.append("""<div class="ms"><b>The reference integration is the item with the best
    return and the one most often left out.</b> It is an hour's work: your block, a
    minimal master that writes the registers and streams some data, and a script that runs
    it. What it removes is the first two days of every customer's evaluation, during
    which they are wiring your block up for the first time and every problem looks like
    your problem. <b>A customer who runs your reference in ten minutes and sees traffic
    move has formed an opinion about your competence before reading the
    datasheet</b>, and that opinion is expensive to change later in either
    direction.</div>""")
    s.append(prob("The customer's interconnect is CHI, not AXI. How much work is that?",
        "Ask first whether it has to be, because the answer is often no. Most CHI "
        "systems provide AXI bridges for peripherals, and a block that does not need "
        "coherence has no reason to speak CHI &mdash; so the first move is to establish "
        "whether the block is a coherent agent or a device behind a bridge, and for a "
        "datapath accelerator it is almost always the latter. <b>If it genuinely must be "
        "a coherent agent</b>, the work is substantial and is <i>not</i> a wrapper "
        "change: CHI is a coherence protocol with a snoop interface, ordering rules and "
        "a state machine, and Part&nbsp;X28's verification argument applies &mdash; the "
        "state space is the kind that needs formal methods, and the effort is comparable "
        "to the core itself. <b>For a one-person house that is a reason to decline or to "
        "scope it as a separate project</b>, not a line item in a wrapper quote. The "
        "middle case worth naming: some blocks need only IO-coherence, where the block's "
        "accesses snoop the host caches but nothing snoops the block. <b>That is an "
        "interconnect feature, not a block feature</b>, and it costs you nothing &mdash; "
        "which is worth knowing so you do not quote for work the customer's fabric "
        "already does."))
    return "\n".join(s)
