# -*- coding: utf-8 -*-
"""Volume I, Part D -- Computer architecture for IP engineers."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, snip, lines, E
from figs import svg, box, txt, arr, line


def _f_pipe():
    b = []
    st = ["IF", "ID", "EX", "MEM", "WB"]
    for i, n in enumerate(st):
        b.append(box(30 + i*104, 35, 88, 36, n, None, 10))
        if i: b.append(arr(30+i*104-16, 53, 30+i*104, 53))
    b.append(txt(275, 100, "Throughput 1 instr/cycle; latency 5 cycles", 9, "middle"))
    b.append(box(140, 125, 300, 28, "hazards: structural · data · control", None, 9, "#fbf2f2"))
    b.append(txt(275, 180, "Forwarding removes most data hazards; load-use needs one stall",
                 9, "middle", 'font-style="italic"'))
    b.append(txt(275, 197, "Control hazards cost the branch penalty × misprediction rate",
                 9, "middle", 'font-style="italic"'))
    return svg(560, 210, "".join(b))


def _f_mem():
    b = []
    rows = [("Register file", 1, "~1 KB"), ("L1 cache", 4, "32–64 KB"),
            ("L2 cache", 14, "256 KB–1 MB"), ("L3 / LLC", 45, "8–64 MB"),
            ("DRAM", 200, "GB"), ("NVMe / SSD", 100000, "TB")]
    y = 32
    for name, cyc, size in rows:
        import math
        w = int(26 * math.log10(cyc) + 30)
        b.append(f'<rect x="170" y="{y}" width="{w}" height="24" fill="#123f6d" opacity="0.75"/>')
        b.append(txt(164, y+17, name, 9, "end"))
        b.append(txt(176+w, y+17, f"~{cyc} cycles   ({size})", 9))
        y += 32
    b.append(txt(300, y+22, "Each level is roughly an order of magnitude slower and larger",
                 9, "middle", 'font-style="italic"'))
    return svg(600, y+34, "".join(b))


def ch_isa():
    s = ['<h1 id="d1">D1. Instruction Set Architecture</h1>']
    s.append("""<p>An ISA is a contract between hardware and software. For a modelling
    engineer it is the <i>specification document</i> in the most literal sense: the
    reference model <b>is</b> the ISA, written executably.</p>""")
    s.append(tab("ISA design axes",
        ["Axis", "Options", "Consequence for hardware"],
        [["Operand model", "Stack / accumulator / register&ndash;memory / <b>load&ndash;store</b>",
          "Load&ndash;store simplifies pipelining; every RISC uses it"],
         ["Instruction length", "Fixed / <b>variable</b> / compressed",
          "Fixed simplifies fetch; compressed (RVC, Thumb) saves 25&ndash;30% code size "
          "at the cost of alignment logic"],
         ["Addressing modes", "Few / many",
          "Many modes need an address generation unit; few modes need more instructions"],
         ["Condition handling", "Flags / compare-and-branch",
          "<b>Flags create a serialising dependency</b>; RISC-V deliberately has none"],
         ["Delay slots", "Present (classic MIPS) / absent",
          "Delay slots expose the pipeline in the ISA &mdash; a design mistake later reversed"],
         ["Register count", "8 / 16 / <b>32</b> / more",
          "More registers reduce spills but widen every instruction field"],
         ["Exceptions", "Precise / imprecise",
          "<b>Precise exceptions constrain the whole microarchitecture</b>"]]))
    s.append("""<div class="ms"><b>Delay slots are the canonical example of leaking
    microarchitecture into architecture.</b> MIPS exposed its single branch-delay slot so
    that the compiler could fill it, saving a stall in a five-stage pipeline. When later
    implementations had deeper pipelines and branch prediction, the delay slot became
    useless baggage that every implementation still had to honour. <b>The lesson for IP
    design generalises: a specification that encodes today's implementation constrains
    tomorrow's.</b> When writing a block's interface, ask which parts describe
    <i>what</i> and which describe <i>how</i>, and expose only the former.</div>""")
    s.append("""<div class="ms"><b>Precise exceptions</b> mean that when an exception is
    taken, all instructions before it have completed and none after it has had any
    effect. This is what makes an ISS a valid reference: the model can execute one
    instruction at a time and still describe a machine that executes many concurrently.
    Achieving it in an out-of-order machine requires a reorder buffer and speculative
    state, which is a large fraction of such a core's complexity. <b>The entire
    step-and-compare verification methodology rests on precise exceptions</b>; without
    them there would be no well-defined point at which model and RTL should agree.</div>""")

    s.append("<h2>D1.2 RISC-V as a case study</h2>")
    s.append(tab("RISC-V structure",
        ["Element", "Content", "Modelling note"],
        [["Base integer", "RV32I / RV64I &mdash; ~40 instructions",
          "Small enough to model exhaustively"],
         ["M", "Multiply/divide", "Division by zero is <b>defined</b>, not trapping"],
         ["A", "Atomics (LR/SC, AMO)", "<b>Requires a memory consistency model</b>"],
         ["F/D/Q", "Floating point", "IEEE 754; needs SoftFloat, not host arithmetic"],
         ["C", "Compressed 16-bit", "Alignment: instructions may straddle a word"],
         ["V", "Vector", "Vector-length agnostic &mdash; a model must track <code>vl</code>, <code>vtype</code>"],
         ["B, Zk, Zc&hellip;", "Bit manipulation, crypto, code size", "&mdash;"],
         ["Privileged", "M/S/U modes, CSRs, PMP, virtual memory",
          "<b>Where most model bugs live</b>: exception priority and CSR side effects"]]))
    s.append("""<div class="warn"><b>Exception priority is the most common source of
    reference-model defects in a CPU project.</b> One instruction can simultaneously
    satisfy the conditions for several exceptions &mdash; misaligned address, page fault,
    access fault, breakpoint. The specification gives a strict priority order. A model
    that implements a different order is correct on almost every test and wrong on a
    narrow class of inputs that constrained-random stimulus may take weeks to find. The
    remedy is not more random testing but <b>directed tests derived from the priority
    table itself</b>: enumerate the table, construct one case per row, and check. This is
    a half-day of work that reliably finds bugs a month of random testing misses.</div>""")
    return "\n".join(s)


def ch_pipeline():
    s = ['<h1 id="d2">D2. Pipelining, Hazards and Speculation</h1>']
    s.append(fig(_f_pipe(), "The classic five-stage pipeline and its three hazard classes."))
    s.append(tab("Hazards and remedies",
        ["Hazard", "Cause", "Remedy", "Residual cost"],
        [["Structural", "Two instructions need the same resource",
          "Duplicate the resource, or stall", "Area"],
         ["Data RAW", "Read after write", "<b>Forwarding</b> from EX/MEM",
          "Load-use still costs one cycle"],
         ["Data WAR / WAW", "Anti- and output dependencies",
          "<b>Register renaming</b>", "Only in out-of-order designs"],
         ["Control", "Branch outcome unknown at fetch",
          "<b>Prediction</b> + speculative execution",
          "Misprediction penalty &times; rate"],
         ["Memory ordering", "Loads and stores to the same address",
          "Store buffer with forwarding, memory disambiguation", "Complexity"]]))
    s.append(tab("Branch prediction",
        ["Predictor", "Mechanism", "Typical accuracy"],
        [["Static (backward taken)", "Loop heuristic", "~65%"],
         ["Bimodal", "2-bit saturating counter per PC", "~85%"],
         ["<b>gshare</b>", "Global history XOR PC indexes the table", "~93%"],
         ["Tournament", "Choose between local and global predictors", "~95%"],
         ["<b>TAGE</b>", "Multiple history lengths with tags", "&gt;97%"],
         ["Perceptron", "Linear classifier over history", "&gt;97%"],
         ["Return address stack", "Dedicated stack for call/return", "&gt;99% for returns"]]))
    s.append("""<div class="ms"><b>Why a misprediction is expensive and getting more
    so.</b> The penalty is the pipeline depth from fetch to resolve. In a 5-stage machine
    that is 2&ndash;3 cycles; in a 15-stage out-of-order machine it is 15&ndash;20, and
    the machine may have to discard dozens of in-flight instructions. With a 5% miss rate
    and a 15-cycle penalty, branches alone cost 0.75 cycles per branch &mdash; often more
    than every other stall combined. This is why predictor research continues to be
    worthwhile and why deep pipelines have diminishing returns. <b>For an accelerator IP
    designer the lesson is the opposite and liberating: a fixed-function datapath has no
    branches, so none of this cost exists.</b> Quantifying that difference &mdash; "your
    software loop spends 0.75 cycles per iteration on branch misprediction alone" &mdash;
    is one of the strongest arguments an accelerator vendor has.</div>""")

    s.append("<h2>D2.2 Out-of-order execution</h2>")
    s.append(tab("Out-of-order machinery",
        ["Structure", "Purpose", "Scaling limit"],
        [["Register renaming (RAT)", "Removes WAR/WAW", "Physical register file size"],
         ["Reservation stations / issue queue", "Hold instructions until operands ready",
          "<b>Wakeup&ndash;select loop is the critical path</b>"],
         ["Reorder buffer (ROB)", "In-order commit &rarr; precise exceptions",
          "Entries scale with memory latency"],
         ["Load/store queue", "Memory disambiguation", "Associative search cost"],
         ["Scoreboard", "Simpler alternative (no renaming)", "Stalls on WAR/WAW"]]))
    s.append("""<div class="ms">The <b>wakeup&ndash;select loop</b> &mdash; broadcasting a
    result tag, waking dependent instructions, selecting which to issue &mdash; must
    complete in one cycle for back-to-back dependent execution. It is a broadcast across
    the whole issue queue, so its delay grows with queue size and with issue width. This
    single loop, not transistor speed, is why issue widths have plateaued around 4&ndash;8
    and why further performance has come from more cores rather than wider ones. <b>It is
    the same phenomenon as the DFE feedback loop and the Viterbi ACS loop: a recurrence
    whose latency cannot be pipelined away.</b> Recognising the pattern across domains is
    exactly the transferable skill this book aims to build.</div>""")
    return "\n".join(s)


def ch_memory():
    s = ['<h1 id="d3">D3. Memory Hierarchy and Coherence</h1>']
    s.append(fig(_f_mem(), "The memory hierarchy. Each level trades capacity against "
                           "latency by roughly an order of magnitude."))
    s.append(tab("Cache design parameters",
        ["Parameter", "Effect", "Trade"],
        [["Block size", "Exploits spatial locality",
          "Too large wastes bandwidth and causes false sharing"],
         ["Associativity", "Reduces conflict misses",
          "More comparators, longer hit time; 4&ndash;8 way is the usual optimum"],
         ["Capacity", "Reduces capacity misses", "Area, leakage, hit latency"],
         ["Write policy", "Write-through vs <b>write-back</b>",
          "Write-back reduces bandwidth; needs dirty bits and coherence"],
         ["Allocation", "Write-allocate vs not", "Depends on write locality"],
         ["Replacement", "LRU / pseudo-LRU / random",
          "True LRU is expensive beyond 4-way; pseudo-LRU is within 1%"],
         ["Inclusion", "Inclusive / exclusive / NINE", "Affects snoop filtering"]]))
    s.append("""<div class="bs">Misses classify as <b>compulsory</b> (first reference),
    <b>capacity</b> (working set exceeds the cache), <b>conflict</b> (limited
    associativity), and in multiprocessors <b>coherence</b> (invalidated by another
    core). The classification is useful because each class has a different remedy:
    prefetching for compulsory, larger cache for capacity, higher associativity or
    better indexing for conflict, and data layout changes for coherence.</div>""")
    s.append(tab("Coherence protocols",
        ["Protocol", "States", "Note"],
        [["MSI", "Modified, Shared, Invalid", "Minimal"],
         ["<b>MESI</b>", "+ Exclusive", "Avoids a bus transaction on read&ndash;modify"],
         ["MOESI", "+ Owned", "Allows dirty sharing; saves writebacks"],
         ["Directory-based", "&mdash;",
          "<b>Scales beyond a bus</b>; required for many-core"],
         ["Snoop filter", "&mdash;", "Reduces useless snoops in large systems"]]))
    s.append("""<div class="ms"><b>Memory consistency is not coherence.</b> Coherence
    concerns a single address &mdash; all cores must see one order of writes to it.
    Consistency concerns the relative order of operations to <i>different</i> addresses.
    A machine can be perfectly coherent and still reorder a store to A before a store to
    B as observed by another core. The consistency model (sequential, TSO, release, RVWMO)
    specifies what reorderings are allowed and which fences prevent them. <b>For a
    modelling engineer this is the hardest specification to capture</b>, because the
    reference model is inherently sequential while the hardware is not: a simple
    step-and-compare against an ISS <i>cannot</i> verify a weak memory model. The correct
    approach is <b>litmus tests</b> &mdash; short multi-threaded programs with
    enumerated permitted outcomes &mdash; checked against the architecture's formal memory
    model. Knowing that a different verification technique is required, and why, is the
    point.</div>""")
    s.append(tab("DRAM characteristics that leak into system design",
        ["Property", "Meaning", "Design response"],
        [["Row buffer", "A row must be activated before access",
          "Exploit row locality; schedule for open rows"],
         ["t<sub>RCD</sub>, t<sub>RP</sub>, t<sub>RAS</sub>", "Activate/precharge timings",
          "Memory controller scheduling"],
         ["Refresh", "Every ~32&ndash;64 ms", "Blocks access; matters for real-time guarantees"],
         ["Bank/rank parallelism", "Independent banks", "Interleave addresses to exploit it"],
         ["Burst length", "Minimum transfer granularity",
          "<b>A 4-byte read still fetches 32&ndash;64 bytes</b>"],
         ["<b>Rowhammer</b>", "Repeated activation disturbs neighbours",
          "A <b>security</b> problem solved by refresh management &mdash; a DRAM controller feature"]]))
    return "\n".join(s)
