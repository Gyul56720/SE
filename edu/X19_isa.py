# -*- coding: utf-8 -*-
"""Volume I, Part X19 -- Processors as IP: what a core vendor actually sells."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E, lines, find
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_cores():
    s = ['<h1 id="x19">X19. Processors as IP, Worked</h1>']
    s.append("""<p>The processor core is the archetype of licensable IP and the block most
    likely to sit beside whatever a design house builds. This part treats it the way the
    rest of the book treats blocks: by the arithmetic that sets its size, its speed and
    its verification cost.</p>""")

    s.append("<h2>X19.1 Where the cycles go</h2>")
    s.append(derive("The performance equation and what each term belongs to", [
        ("Time = instructions &times; cycles per instruction &times; cycle time.",
         "The identity. Its value is that the three terms belong to <i>different "
         "people</i>."),
        ("Instructions: the compiler and the instruction set.",
         "A richer ISA lowers this and usually raises one of the other two."),
        ("CPI: the micro-architecture &mdash; pipeline, caches, branch prediction.",
         "Where a core designer spends their effort."),
        ("Cycle time: the implementation and the process.",
         "Where Part X2's budget applies directly."),
        ("<b>An improvement that lowers one term and raises another by more is a "
         "regression</b>, and this is the standard failure of ISA extensions.",
         "A new instruction that saves two instructions but lengthens the critical path "
         "by 5&nbsp;% has to save 5&nbsp;% of all instructions to break even."),
    ]))
    rows = []
    for name, cpi, mhz, instr in (("Simple 3-stage, in-order", 1.35, 400, 1.00),
                                  ("5-stage, in-order, no cache", 1.20, 600, 1.00),
                                  ("5-stage with I/D caches", 1.45, 900, 1.00),
                                  ("Dual-issue in-order", 0.95, 900, 1.00),
                                  ("Out-of-order, 3-wide", 0.55, 1200, 1.00)):
        perf = mhz / cpi
        rows.append([name, num(cpi, 3), num(mhz), num(perf / 1000, 4),
                     num(perf / (400 / 1.35), 4)])
    s.append(sweep("Illustrative core points: performance is frequency divided by CPI",
        ["Core", "CPI", "MHz", "MIPS (approx.)", "Relative performance"], rows,
        "<b>These are illustrative operating points chosen to show the structure of the "
        "trade, not measured benchmark results for any particular core.</b> Note the "
        "third row: adding caches <i>raises</i> CPI, because a miss costs cycles the "
        "cacheless design never paid &mdash; and still wins, because it raises the "
        "achievable frequency far more."))
    s.append("""<div class="ms"><b>The third row is the most instructive line in this
    chapter.</b> A design without caches has a low, predictable CPI and cannot run fast,
    because every access goes to a memory whose latency sets the cycle time. Adding caches
    introduces misses and therefore raises average CPI, and simultaneously removes the
    slow memory from the critical path, which raises frequency by more. <b>Optimising CPI
    in isolation would have rejected the change.</b> This is the general hazard of
    single-metric optimisation, and it is why architectural decisions are evaluated on
    the product of the three terms and never on one of them.</div>""")
    rows = []
    for miss, pen in ((0.01, 10), (0.02, 10), (0.05, 10), (0.02, 30), (0.02, 100),
                      (0.005, 100)):
        cpi = 1.0 + miss * pen
        rows.append([num(miss * 100, 3), num(pen), num(cpi, 4),
                     num(miss * pen / cpi * 100, 3), num(1 / cpi, 4)])
    s.append(sweep("Memory stall as a fraction of CPI",
        ["Miss rate (%)", "Miss penalty (cycles)", "CPI", "Stall share of CPI (%)",
         "Relative performance"], rows,
        "The last two rows are the same miss penalty at 2&nbsp;% and 0.5&nbsp;% miss "
        "rates. <b>At a 100-cycle penalty a 2&nbsp;% miss rate spends two thirds of "
        "every cycle waiting</b>, which is why a small improvement in hit rate is worth "
        "more than a large improvement in almost anything else &mdash; and why "
        "prefetching, which attacks the penalty rather than the rate, is worth its "
        "complexity."))

    s.append("<h2>X19.2 What a processor IP licence actually contains</h2>")
    s.append(tab("The deliverable, and why a core is expensive",
        ["Item", "Note"],
        [["RTL or a hard macro", "The smallest part of the value"],
         ["<b>The compiler toolchain</b>",
          "<b>A core without a compiler is unusable.</b> GCC and LLVM ports, a "
          "libc, a debugger"],
         ["Instruction-set simulator", "For software development before silicon, and "
          "as the golden model for verification"],
         ["<b>The architectural compliance suite</b>",
          "<b>The thing that makes the core the ISA it claims to be.</b> For RISC-V "
          "this is a formal specification plus a test suite"],
         ["Debug and trace", "A standard debug module; trace if the customer needs it"],
         ["Operating-system ports", "Where applicable &mdash; Linux, an RTOS"],
         ["Verification collateral", "So the customer can re-verify after configuring"],
         ["Configuration tooling", "A core with 30 options has 2<sup>30</sup> "
          "configurations; the tool generates and verifies the chosen one"]]))
    s.append("""<div class="warn"><b>The configuration explosion is the hardest
    verification problem in processor IP and it is worth understanding as arithmetic.</b>
    A core with thirty independent options has more configurations than can ever be
    verified individually. What vendors do instead is to verify a <i>covering set</i>:
    choose configurations so that every option and every interacting pair is exercised at
    least once, which for pairwise coverage needs a number of configurations that grows
    logarithmically rather than exponentially &mdash; typically a few dozen. <b>The claim
    a customer should check is not &lsquo;we verified every configuration&rsquo; but
    &lsquo;here is the covering criterion and here is the set&rsquo;</b>, and a vendor
    who can state the criterion is a different proposition from one who
    cannot.</div>""")
    rows = []
    for n in (5, 10, 20, 30):
        rows.append([num(n), num(2 ** n), num(n), num(n * (n - 1) // 2),
                     num(int(math.ceil(math.log2(n) * 4)) if n > 1 else 1)])
    s.append(sweep("Configuration coverage: exhaustive versus pairwise",
        ["Independent options", "All configurations", "Options to cover singly",
         "Option pairs", "Configurations for pairwise coverage (approx.)"], rows,
        "The pairwise column is an order-of-magnitude estimate from the standard "
        "combinatorial-testing result that pairwise coverage of <i>n</i> binary factors "
        "needs <i>O</i>(log&nbsp;<i>n</i>) tests. <b>The gap between the second and last "
        "columns is the entire practical argument for combinatorial test design.</b>"))

    s.append("<h2>X19.3 Verifying a core against its specification</h2>")
    try:
        n1 = lines("model", "riscv-isa-sim")
        n2 = lines("model", "sail-riscv")
        n3 = lines("model", "riscv-tests")
        n4 = lines("model", "riscv-arch-test")
        s.append(f"""<p>The code appendix of this book contains the machinery a
        processor-verification engineer uses, in its real form: <b>{n2:,} lines</b> of
        the Sail formal specification of RISC-V, <b>{n1:,} lines</b> of the Spike
        instruction-set simulator, and <b>{n3 + n4:,} lines</b> of the architectural
        test suites. Reading them together is the most direct way to see what
        &lsquo;a specification&rsquo; means when it has to be executable.</p>""")
    except Exception as e:
        s.append(f'<div class="warn">RISC-V corpus not indexed: {E(str(e))}</div>')
    s.append(tab("Four ways to verify a core, and what each one catches",
        ["Method", "How", "Catches", "Misses"],
        [["Directed tests", "Hand-written assembly per feature",
          "What you thought of", "What you did not"],
         ["Architectural suite", "The ISA body's own tests",
          "Non-conformance to the ISA", "Micro-architectural bugs the ISA does not "
          "constrain"],
         ["<b>Random instruction generation</b>",
          "Generate legal programs, run on core and on a reference, compare state",
          "<b>Interactions nobody enumerated</b>",
          "Rare sequences; needs enormous volume"],
         ["<b>Step-and-compare (co-simulation)</b>",
          "<b>After every instruction, compare the core's architectural state with the "
          "reference simulator's</b>",
          "<b>The exact instruction where they diverge &mdash; the debug cost collapses</b>",
          "Only what the interface exposes"],
         ["Formal", "Prove properties of the pipeline, the ISA decode, the memory "
          "ordering", "Deep control bugs, over all inputs",
          "Needs the properties written; capacity limits on the datapath"]]))
    s.append("""<div class="ms"><b>Step-and-compare is the technique worth internalising,
    because it generalises far beyond processors.</b> The idea is to compare not the final
    output but the state after every step, against a reference that advances in the same
    steps. The payoff is that the first divergence is the bug, so debug time falls from
    hours of backward reasoning to inspecting one instruction. The requirement is an
    interface that exposes committed state &mdash; in RISC-V cores this is conventionally
    a formal interface emitting, for every retired instruction, its program counter, its
    encoding, and the register and memory it wrote. <b>Designing that interface into a
    block is a small cost that pays for itself the first time something goes
    wrong</b>, and the same pattern applies to any block with a sequential golden model:
    a codec, a protocol engine, a FEC decoder.</div>""")
    s.append(prob("Why can a core pass the full architectural test suite and still be "
                  "broken?",
        "Because the suite tests the <b>architecture</b> and bugs live in the "
        "<b>micro-architecture</b>. The ISA says what the visible state is after an "
        "instruction; it says nothing about what happens when a branch mispredicts while "
        "a load is outstanding and an interrupt arrives. Those interactions are where "
        "pipeline bugs live, and an architectural test that executes instructions in "
        "isolation never creates them. Three further gaps are worth naming. <b>Memory "
        "ordering</b> under concurrency is barely exercised by single-threaded tests and "
        "is the hardest part of a multi-core design to get right; it needs litmus tests "
        "derived from the memory model. <b>Privilege transitions</b> &mdash; traps, "
        "interrupts, nested exceptions, debug entry &mdash; are under-tested everywhere "
        "and are where security bugs concentrate. And <b>performance counters and "
        "debug</b> are architectural state that customers rely on and suites barely "
        "touch. The remedy is the one above: random program generation with "
        "step-and-compare, run for a very long time, with a stimulus generator biased "
        "toward the interactions rather than toward the instructions."))
    return "\n".join(s)
