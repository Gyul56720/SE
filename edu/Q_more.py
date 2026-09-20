# -*- coding: utf-8 -*-
"""Volume I, Part Q -- Performance modelling, compilers/HLS, embedded software, EMC."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def ch_queue():
    s = ['<h1 id="q1">Q1. Performance Modelling and Queueing</h1>']
    s.append("""<p>Functional correctness is verified against a golden model; performance
    is predicted by a different kind of model entirely. Confusing the two is a common and
    expensive mistake, because a functionally perfect block can still fail its throughput
    requirement in a system.</p>""")
    s.append(tab("Model types and what each answers",
        ["Model", "Question answered", "Cost", "Fidelity"],
        [["Analytical (closed form)", "Rough sizing, bounds", "Minutes", "Low but instant"],
         ["<b>Spreadsheet / static</b>", "Bandwidth and utilisation budgets", "Hours",
          "Adequate for first-order decisions"],
         ["<b>Queueing model</b>", "Latency under load, buffer sizing", "Days",
          "Good when arrivals are stochastic"],
         ["Trace-driven simulation", "Behaviour on real workloads", "Days", "High"],
         ["<b>Cycle-approximate (SystemC TLM)</b>", "System behaviour before RTL exists",
          "Weeks", "Good"],
         ["Cycle-accurate", "Exact cycle counts", "Weeks&ndash;months", "Highest"],
         ["RTL simulation", "Ground truth", "&mdash;", "Exact but far too slow for system studies"]]))
    s.append("""<div class="ms"><b>The practical value of the middle rows is that they
    exist before RTL does.</b> An architecture decision &mdash; how deep a buffer, how many
    outstanding transactions, whether to double the datapath width &mdash; must be made
    months before there is anything to simulate. A cycle-approximate SystemC model built
    from the specification answers it in days, and being wrong by 10% is usually
    irrelevant when the alternatives differ by a factor of two. <b>Insisting on
    cycle-accurate fidelity for an architectural question delays the decision until it is
    too late to act on.</b></div>""")
    s.append(tab("Queueing results worth knowing",
        ["Result", "Statement", "Use"],
        [["<b>Little's law</b>", "<i>L</i> = &lambda;<i>W</i>",
          "<b>Occupancy = arrival rate &times; latency</b> &mdash; sizes any buffer"],
         ["M/M/1 latency", "<i>W</i> = 1/(&mu;&minus;&lambda;)",
          "<b>Latency diverges as utilisation &rarr; 1</b>"],
         ["M/M/1 occupancy", "&rho;/(1&minus;&rho;)",
          "At 90% utilisation the mean queue is 9"],
         ["M/D/1", "Deterministic service", "Half the waiting time of M/M/1"],
         ["Erlang B", "Blocking probability", "Sizing a finite resource pool"],
         ["Burstiness", "&mdash;", "<b>Real traffic is burstier than Poisson</b> &mdash; "
          "Poisson results are optimistic"]]))
    s.append("""<div class="ms"><b>Little's law is the single most useful formula in
    system design and it requires no assumptions about distributions.</b> To sustain
    10&nbsp;GB/s with a 500&nbsp;ns round trip, the system must keep
    10&times;10<sup>9</sup>&times;500&times;10<sup>&minus;9</sup>&nbsp;=&nbsp;5&nbsp;kB in
    flight; if the interface supports 32 outstanding 64-byte requests, that is 2&nbsp;kB
    and the link will run at 40% of its rate no matter how fast it is. <b>This is the
    quantitative form of the PCIe tag-capacity argument in Chapter P2</b>, and the same
    calculation sizes DMA descriptor rings, memory controller queues and cache
    miss-status registers. Learning to apply it in thirty seconds is worth more than any
    simulator.</div>""")
    s.append("""<div class="warn"><b>Designing for average load is designing to fail.</b>
    The M/M/1 result shows latency rising hyperbolically with utilisation: at 50% the
    queue is 1, at 90% it is 9, at 99% it is 99. Systems provisioned at their average
    demand spend a substantial fraction of their time near saturation, where latency is
    dominated by queueing rather than service. <b>Buffer sizing must be driven by the
    tail of the arrival distribution, not its mean</b>, and a performance specification
    that quotes only average throughput is incomplete.</div>""")
    return "\n".join(s)


def ch_hls():
    s = ['<h1 id="q2">Q2. Compilers and High-Level Synthesis Internals</h1>']
    s.append("""<p>HLS is often treated as a black box. Knowing what it does internally
    makes the difference between fighting the tool and directing it, and the internal
    steps are the same scheduling and binding problems that appear elsewhere in design.</p>""")
    s.append(tab("The HLS pipeline",
        ["Step", "Function", "What the designer controls"],
        [["Front end", "Parse to an intermediate representation", "Language subset used"],
         ["Optimisation", "Constant folding, loop transforms, inlining",
          "Code structure; pragmas"],
         ["<b>Scheduling</b>", "Assign operations to clock cycles",
          "<b>Target II and latency constraints; dependences</b>"],
         ["<b>Allocation</b>", "Decide how many of each resource",
          "Resource constraints, binding directives"],
         ["<b>Binding</b>", "Map operations to specific units, values to registers",
          "Storage directives"],
         ["Interface synthesis", "Turn arguments into ports/protocols", "Interface pragmas"],
         ["RTL generation", "Emit Verilog/VHDL", "&mdash;"]]))
    s.append("""<div class="ms"><b>Scheduling is a constrained optimisation problem and
    that explains the tool's behaviour.</b> Given a dependence graph and resource limits,
    the scheduler minimises latency or the initiation interval. Because the problem is
    NP-hard in general, tools use heuristics (list scheduling, modulo scheduling for
    pipelines, occasionally ILP for small regions). Two consequences follow. First, a
    small change in the source can produce a disproportionate change in the schedule,
    because the heuristic follows a different path &mdash; which is why HLS results can be
    unstable. Second, <b>the tool cannot schedule around a dependence it cannot
    disprove</b>, so telling it the truth about aliasing is the highest-leverage thing a
    designer does. That is what a dependence directive is: not an optimisation hint, but a
    fact the tool could not derive.</div>""")
    s.append(tab("Directive families and what they actually do",
        ["Family", "Examples", "Nature", "Risk of misuse"],
        [["<b>Scheduling</b>", "pipeline, unroll, inline, loop_flatten, loop_merge",
          "<b>Requests</b> &mdash; the tool may not achieve them",
          "Silent failure to meet the target; check the report"],
         ["<b>Structural</b>", "array_partition, bind_storage, bind_op, dataflow, stream",
          "<b>Change what is built</b>", "Area explosion"],
         ["<b>Assertions</b>", "dependence, loop_tripcount",
          "<b>Facts the tool trusts</b>",
          "<b>A false assertion produces silently wrong hardware</b>"],
         ["Interface", "interface, axis, m_axi, s_axilite", "Define ports", "Protocol mismatch"]]))
    s.append("""<div class="warn"><b>The third family is categorically different from the
    other two and should be reviewed differently.</b> A scheduling directive that cannot be
    satisfied produces a worse result and a report message. A structural directive produces
    a bigger design. A false dependence assertion produces hardware that computes the wrong
    answer, with no message and no simulation failure &mdash; because the C semantics are
    unaffected. <b>Every dependence directive is therefore a proof obligation</b>: the
    reviewer must be able to state why the asserted independence holds for every legal
    parameter value. Treating it as an optimisation switch is how silent bugs enter.</div>""")
    s.append(tab("What HLS is good and bad at",
        ["Suited", "Reason", "Unsuited", "Reason"],
        [["Loop-dominated datapaths", "Regular dependence structure",
          "Cycle-exact interface protocols", "The tool owns the schedule"],
         ["Design-space exploration", "One source, many points",
          "Control-dominated logic", "Irregular; RTL is clearer"],
         ["Filters, transforms, crypto rounds", "Well-structured loops",
          "Blocks needing precise latency", "Latency is an output, not an input"],
         ["Algorithm-level changes", "Edit the C, not the RTL",
          "Deep pipelines with feedback", "The iteration bound still applies"]]))
    return "\n".join(s)


def ch_embedded():
    s = ['<h1 id="q3">Q3. Embedded Software Around the Hardware</h1>']
    s.append(tab("Software layers that touch an IP block",
        ["Layer", "Concern", "What the hardware must provide"],
        [["Boot ROM", "Bring the system up", "Deterministic reset state"],
         ["<b>Device driver</b>", "Register access, interrupts, DMA",
          "<b>A clean register map and a defined initialisation sequence</b>"],
         ["RTOS / kernel", "Scheduling, memory management",
          "Interrupt latency guarantees; cache coherence behaviour"],
         ["Middleware", "Protocol stacks", "&mdash;"],
         ["Application", "&mdash;", "&mdash;"],
         ["Firmware in the block", "Local control", "Instruction memory, debug access"]]))
    s.append("""<div class="ms"><b>Cache coherence with a DMA-capable block is the
    interaction that produces the most confusing bugs.</b> If a block writes to memory by
    DMA while the CPU has that region cached, the CPU may read stale data; if the CPU
    writes and the data sits in a write-back cache, the block may read stale data. On a
    coherent interconnect the hardware resolves this; on a non-coherent one the driver must
    invalidate before reading and clean before writing, and getting the order wrong
    produces intermittent corruption that looks like an IP defect. <b>An IP datasheet must
    state whether its transactions are coherent</b>, and the example driver should
    demonstrate the required maintenance operations if they are not.</div>""")
    s.append(tab("Real-time considerations",
        ["Concept", "Meaning", "Hardware implication"],
        [["Interrupt latency", "Event to first instruction of the handler",
          "Interrupt controller design; cache and TLB state"],
         ["<b>Worst-case execution time</b>", "Upper bound, not average",
          "<b>Caches and branch prediction make it hard to bound</b>"],
         ["Priority inversion", "Low-priority task blocks a high-priority one",
          "Priority inheritance in locks"],
         ["Jitter", "Variation in response time", "Deterministic arbitration helps"],
         ["Scratchpad versus cache", "&mdash;",
          "<b>Scratchpads give predictability; caches give average speed</b>"]]))
    s.append("""<div class="ms"><b>The tension between average performance and worst-case
    predictability runs through the whole field.</b> Caches, branch predictors,
    out-of-order execution and adaptive arbitration all improve the average and widen the
    distribution. Hard real-time systems therefore often disable or avoid them, accepting
    lower throughput for a bound that can be certified. <b>An accelerator with
    deterministic latency is a feature in automotive and industrial markets even if it is
    slower</b>, which is a positioning fact worth knowing before designing for peak
    numbers.</div>""")
    return "\n".join(s)


def ch_emc():
    s = ['<h1 id="q4">Q4. Electromagnetic Compatibility</h1>']
    s.append("""<p>A product must not emit excessive interference and must tolerate what
    it receives. Both are system properties, but several of the levers are inside the
    digital design.</p>""")
    s.append(tab("Emission mechanisms and mitigations",
        ["Mechanism", "Source", "Mitigation", "Where decided"],
        [["Differential-mode radiation", "Current loops on the board",
          "Reduce loop area; ground planes", "Board"],
         ["<b>Common-mode radiation</b>", "Cables driven by common-mode voltage",
          "<b>Balanced differential signalling; common-mode chokes</b>",
          "I/O design and board"],
         ["Harmonics of clocks", "Fast edges with periodic content",
          "<b>Spread-spectrum clocking; slew-rate control</b>",
          "<b>Clock generator and I/O cells &mdash; a chip-level choice</b>"],
         ["Simultaneous switching", "Many outputs toggling together",
          "Stagger switching; use differential I/O", "<b>RTL and I/O planning</b>"],
         ["Power supply coupling", "d<i>I</i>/d<i>t</i>", "Decoupling; ramped enables", "Chip and board"]]))
    s.append("""<div class="ms"><b>Spread-spectrum clocking is a direct trade of jitter for
    emissions.</b> Modulating the clock frequency by a fraction of a percent spreads each
    harmonic's energy across a band, lowering the peak that a regulatory measurement
    reports, without reducing total energy. The cost is added low-frequency jitter, which
    a receiver's CDR must track &mdash; which is why standards that permit SSC also specify
    a maximum modulation rate and depth, and why a CDR's loop bandwidth must be high enough
    to follow it. <b>An interface IP that does not support SSC cannot be used in a product
    that needs it to pass emissions testing</b>, so it is a specification item, not an
    optional extra.</div>""")
    s.append(tab("Immunity concerns",
        ["Threat", "Standard", "Design response"],
        [["ESD", "IEC 61000-4-2, HBM/CDM",
          "On-chip protection structures; careful I/O design"],
         ["Radiated immunity", "IEC 61000-4-3", "Shielding; filtering"],
         ["Fast transients / surge", "IEC 61000-4-4/5", "Board-level protection"],
         ["Supply dips", "IEC 61000-4-11", "Brown-out detection and clean reset"],
         ["<b>Latch-up</b>", "&mdash;",
          "<b>Guard rings; substrate contacts</b> &mdash; a layout obligation"]]))
    s.append("""<div class="warn"><b>ESD and latch-up are the two failure modes that
    destroy parts rather than merely disturb them.</b> An ESD event can be several kilovolts
    and must be shunted by protection structures before it reaches a gate oxide; latch-up
    is a parasitic thyristor in the CMOS structure that, once triggered, conducts until
    power is removed and often destroys the die. Both are addressed in layout and I/O
    design rather than in RTL, but both constrain what a digital designer may do &mdash;
    notably the rules about powering domains in a particular order and about driving
    signals into unpowered domains. <b>An IP with multiple power domains must specify the
    legal power-up and power-down sequences</b>, and a violation of them is a hardware
    destruction risk, not a functional one.</div>""")
    return "\n".join(s)
