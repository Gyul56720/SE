# -*- coding: utf-8 -*-
"""Volume I, Part X11 -- Interconnect: arbitration, flow control, deadlock."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_noc2():
    s = ['<h1 id="x11">X11. Interconnect: Arbitration, Flow Control and Deadlock</h1>']
    s.append("""<p>An IP block that talks to anything talks through an interconnect, and
    the interconnect's properties leak into the block's specification whether or not the
    specification mentions them. The three that leak hardest are how bandwidth is shared,
    how back-pressure propagates, and whether the system can lock up. All three are
    computable and the third is provable.</p>""")

    s.append("<h2>X11.1 Credit-based flow control: sizing the buffer</h2>")
    s.append(derive("Why the buffer must cover the round trip", [
        ("The sender may transmit only while it holds credits; each transmission "
         "consumes one.",
         "Definition of credit-based flow control."),
        ("A credit is returned when the receiver frees a buffer entry; the return takes "
         "<i>t</i><sub>ret</sub> to arrive.",
         "Physical delay: the return path is wires and pipeline stages like any other."),
        ("For the sender never to stall while the receiver is draining, credits must "
         "outlast the round trip.",
         "Otherwise there is an interval in which the sender has no credit and the "
         "receiver has space."),
        ("<b><i>N</i><sub>buf</sub> &ge; <i>B</i> &middot; RTT</b>, where <i>B</i> is "
         "the peak rate and RTT is forward latency plus return latency.",
         "The bandwidth&ndash;delay product. <b>It is the same formula as a TCP window "
         "and for exactly the same reason.</b>"),
        ("Any shortfall shows up as a throughput loss of "
         "<i>N</i><sub>buf</sub>/(<i>B</i>&middot;RTT), not as a functional failure.",
         "Which is why an undersized buffer is found in performance bring-up rather than "
         "in verification &mdash; late, and by the customer."),
    ]))
    rows = []
    for fwd, ret in ((1, 1), (2, 2), (4, 4), (8, 8), (16, 16)):
        rtt = fwd + ret
        for w in (1,):
            rows.append([num(fwd), num(ret), num(rtt), num(rtt),
                         num(rtt * 32 / 8), num(1 / rtt, 3)])
    s.append(sweep("Credit buffer needed against pipeline depth, one flit per cycle",
        ["Forward stages", "Return stages", "Round trip (cycles)",
         "Minimum credits", "Buffer bytes at 32&nbsp;B/flit",
         "Throughput if only one credit is provided"], rows,
        "The last column is what an under-provisioned link actually delivers: one flit "
        "per round trip. A four-deep pipeline with one credit runs at an eighth of the "
        "wire's rate, and nothing in the design is broken."))
    s.append(ex("A block on a pipelined AXI interconnect",
        "A DMA engine issues read bursts across an interconnect with 6 cycles of "
        "forward latency and 6 of response, at 500&nbsp;MHz, 128-bit data, and must "
        "sustain 6&nbsp;GB/s.",
        "Convert the required bandwidth into outstanding transactions via the "
        "bandwidth&ndash;delay product, then check it against the interface's ID width, "
        "which is what actually limits outstanding transactions on AXI.",
        [("Bytes per beat", num(16)),
         ("Beats per second required", num(6e9 / 16, 4)),
         ("Cycles per second", num(5e8)),
         ("Beats per cycle required", num(6e9 / 16 / 5e8, 3)),
         ("Round-trip latency", num(12) + " cycles"),
         ("Outstanding beats needed", num(math.ceil(6e9 / 16 / 5e8 * 12))),
         ("If bursts are 16 beats: outstanding bursts needed",
          num(math.ceil(6e9 / 16 / 5e8 * 12 / 16))),
         ("Read data buffer required",
          num(math.ceil(6e9 / 16 / 5e8 * 12) * 16) + "&nbsp;B")],
        "<b>By sizing the buffer for the burst and not for the round trip.</b> A common "
        "specification says &lsquo;one burst of read data&rsquo;, which permits exactly "
        "one outstanding burst and throttles the engine to burst-length divided by "
        "round-trip &mdash; here about a quarter of the wire rate. The second frequent "
        "error is to size for the <i>average</i> latency: the interconnect's latency has "
        "a tail whenever another master is active, and a buffer sized for the mean stalls "
        "whenever the tail occurs. <b>Size for the latency at the load you will actually "
        "run at</b>, and state that load in the datasheet, because a customer whose "
        "system is busier than your bench will not reach your quoted bandwidth."))

    s.append("<h2>X11.2 Arbitration: fairness has a precise meaning and a cost</h2>")
    rng = np.random.default_rng(13)
    n_m = 4
    rates = np.array([0.5, 0.2, 0.15, 0.1])
    T = 200000
    req = rng.random((T, n_m)) < rates
    def run(policy):
        gr = np.zeros(n_m, int)
        wait = [[] for _ in range(n_m)]
        pend = np.zeros(n_m, int)
        age = np.zeros(n_m, int)
        rr = 0
        for t in range(T):
            pend |= req[t]
            age += (pend > 0)
            act = np.nonzero(pend)[0]
            if act.size == 0:
                continue
            if policy == "fixed":
                w = act[0]
            elif policy == "rr":
                order = [(rr + i) % n_m for i in range(n_m)]
                w = next(i for i in order if pend[i])
                rr = (w + 1) % n_m
            else:      # oldest-first
                w = act[int(np.argmax(age[act]))]
            wait[w].append(age[w])
            pend[w] = 0
            age[w] = 0
        return gr, wait
    rows = []
    for name, pol in (("Fixed priority", "fixed"), ("Round robin", "rr"),
                      ("Oldest first (LRG)", "age")):
        _, wait = run(pol)
        cells = [name]
        for i in range(n_m):
            w = wait[i]
            cells.append(f"{np.mean(w):.1f} / {np.max(w) if w else 0}" if w else "&mdash;")
        rows.append(cells)
    s.append(sweep("Measured mean / maximum wait in cycles, four masters offering "
                   "0.5, 0.2, 0.15 and 0.1 requests per cycle, 200&#8239;000 cycles",
        ["Policy", "M0 (busiest)", "M1", "M2", "M3 (quietest)"], rows,
        "Simulated with seed 13. Fixed priority starves the low-priority masters when "
        "the high-priority one is busy &mdash; read M3's maximum. Round robin bounds "
        "everyone's wait; oldest-first minimises the maximum further at the cost of an "
        "age counter per requester."))
    s.append(tab("Arbitration policies and what each guarantees",
        ["Policy", "Guarantees", "Cost", "Fails at"],
        [["Fixed priority", "Lowest latency for the top requester",
          "A priority encoder &mdash; cheapest", "<b>Starvation</b>: no bound for the "
          "bottom requester"],
         ["<b>Round robin</b>", "<b>Bounded wait of <i>n</i>&minus;1 grants</b>",
          "A rotating pointer", "Does not respect differing bandwidth needs"],
         ["Weighted round robin", "Bandwidth in proportion to weights",
          "Per-requester counters", "Latency for a low-weight but urgent requester"],
         ["Deficit round robin", "Bandwidth proportion with variable-size requests",
          "A deficit counter per requester",
          "&mdash; this is the standard answer for packets"],
         ["Oldest first", "Minimises maximum wait",
          "Age counters and a comparison tree &mdash; <b>the tree is the timing "
          "problem</b>", "Scaling: the comparison is <i>O</i>(log <i>n</i>) deep and wide"],
         ["Lottery / randomised", "Proportional in expectation",
          "An LFSR", "No <b>bound</b>, only an expectation &mdash; unacceptable for "
          "real-time"]]))
    s.append("""<div class="ms"><b>Quality of service is not a policy, it is two
    different requirements that must be separated before a policy can be chosen.</b> A
    display controller needs <i>guaranteed bandwidth</i> and tolerates latency, because it
    has a line buffer; a CPU fetching a cache miss needs <i>low latency</i> and consumes
    little bandwidth. One arbiter cannot serve both well with a single knob, which is why
    real interconnects separate them: a bandwidth regulator (a token bucket or a deficit
    counter) enforces the first, and a priority class enforces the second, with the
    regulator demoting a requester that exceeds its allocation so that its priority cannot
    starve anyone. <b>When writing an IP block's requirements, state which of the two you
    need</b>; &lsquo;high performance&rsquo; is not an interconnect requirement and cannot
    be designed against.</div>""")

    s.append("<h2>X11.3 Deadlock: a property of the dependency graph</h2>")
    s.append(derive("The four conditions, and which one hardware removes", [
        ("Mutual exclusion: a resource is held by one holder at a time.",
         "True of every buffer; not removable."),
        ("Hold and wait: a holder may request another resource while holding one.",
         "True of any pipelined request; removing it means allocating everything at "
         "once, which wastes buffers."),
        ("No pre-emption: a buffer cannot be taken back.",
         "Removable &mdash; by <b>dropping and retrying</b>, which is what a network "
         "does and what an on-chip fabric usually cannot afford."),
        ("<b>Circular wait</b>: the wait-for graph contains a cycle.",
         "<b>This is the one hardware removes.</b> Break every cycle and deadlock is "
         "impossible regardless of the other three."),
        ("Virtual channels break cycles by splitting one physical buffer into several "
         "logically independent ones with an ordering between them.",
         "A message may only move from a lower-numbered channel to a higher one, so the "
         "dependency graph becomes acyclic by construction."),
        ("Dimension-ordered routing breaks cycles in a mesh by forbidding a turn.",
         "X then Y: the turns that would close a cycle are simply not permitted. "
         "<b>Cheap, and it costs path diversity</b>, which costs throughput under "
         "adversarial traffic."),
    ]))
    s.append("""<div class="warn"><b>The most common on-chip deadlock has nothing to do
    with routing.</b> It is a read response that cannot make progress because the response
    buffer is full of responses waiting behind a write that cannot complete because the
    write channel is blocked by a request from the same master. Protocol specifications
    address this with ordering rules &mdash; AXI's requirement that read and write
    channels be independent, and that a slave must not make a read response depend on a
    future write &mdash; and <b>those rules are routinely broken by IP blocks that share
    one internal queue between the two channels.</b> If your block merges AXI's read and
    write paths into a single ordered structure anywhere, you have created this deadlock,
    and it will appear in a customer's system and not in yours.</div>""")
    s.append(prob("A bridge accepts an AXI write and must issue a read to fetch the rest "
                  "of a partially written cache line, then complete the write. Why is "
                  "this a deadlock hazard, and what are the fixes?",
        "It creates a dependency from the write channel to the read channel. If the read "
        "travels through the same interconnect and that interconnect is congested with "
        "writes &mdash; including this one, which is holding a slot &mdash; the read "
        "cannot be issued and the write cannot retire. The wait-for graph has a cycle. "
        "Three fixes, in increasing order of cost and decreasing order of fragility. "
        "<b>Reserve resources before accepting</b>: do not accept the write until a read "
        "slot and a line buffer are already allocated, so the bridge never holds and "
        "waits. <b>Use a separate virtual or physical channel</b> for the fetch, so the "
        "read's path cannot be blocked by writes. <b>Buffer the entire write</b> and "
        "acknowledge it immediately, converting the dependency into a local one &mdash; "
        "which costs a full line of storage per outstanding write and changes the "
        "coherence behaviour. Whichever is chosen, <b>the argument must be written down "
        "as an acyclicity claim about the dependency graph</b>, because it is not "
        "something a simulation will refute reliably: deadlocks appear only under "
        "specific congestion, and the bench that would produce it is rarely the bench "
        "that is written."))

    s.append("<h2>X11.4 Topology and the wire budget</h2>")
    rows = []
    for n in (4, 8, 16, 32, 64):
        mesh = (num(int(2 * (math.sqrt(n) - 1)))
                if int(math.sqrt(n)) ** 2 == n else "&mdash;")
        cube = (num(int(math.log2(n)))
                if 2 ** int(math.log2(n)) == n else "&mdash;")
        rows.append([num(n), num(n * (n - 1) // 2), num(n - 1), mesh, cube,
                     num(n // 2)])
    s.append(sweep("Topologies: links and worst-case hop count",
        ["Nodes", "Full crossbar links", "Ring: worst hops",
         "2-D mesh: worst hops", "Hypercube: worst hops", "Ring links"], rows,
        "The crossbar column is the reason crossbars stop at modest radix: the link "
        "count is quadratic and each link is a full-width bus. Beyond about 16 ports a "
        "hierarchy of smaller crossbars wins on area even though it adds hops."))
    s.append(ex("Bisection bandwidth decides, not link count",
        "A 16-node system, 128-bit links at 1&nbsp;GHz. Compare a ring, a 4&times;4 "
        "mesh and a full crossbar under uniform random traffic, where on average half "
        "the traffic crosses the bisection.",
        "Compute the bisection bandwidth &mdash; the bandwidth across the worst cut "
        "that divides the network in half &mdash; and compare with the offered load. "
        "Bisection, not aggregate link bandwidth, is what limits uniform traffic.",
        [("Per-link bandwidth", num(128 / 8 * 1e9 / 1e9, 3) + "&nbsp;GB/s"),
         ("Ring: links crossing the bisection", num(2)),
         ("Ring bisection bandwidth", num(2 * 16, 3) + "&nbsp;GB/s"),
         ("4&times;4 mesh: links crossing", num(4)),
         ("Mesh bisection bandwidth", num(4 * 16, 3) + "&nbsp;GB/s"),
         ("Crossbar bisection bandwidth", num(8 * 16, 3) + "&nbsp;GB/s"),
         ("Offered load if each node sends 8&nbsp;GB/s, half crossing",
          num(16 * 8 / 2, 3) + "&nbsp;GB/s"),
         ("Ring sufficient?", "<b>no</b>"),
         ("Mesh sufficient?", "<b>no</b>"),
         ("Crossbar sufficient?", "yes")],
        "<b>By quoting aggregate bandwidth.</b> The ring in this example has 16 links "
        "and 256&nbsp;GB/s of aggregate link bandwidth, which sounds ample and is "
        "irrelevant: uniform traffic is limited by the two links at the cut. The "
        "corollary is that <b>topology should be chosen from the traffic pattern</b>. "
        "If the real traffic is nearest-neighbour, the ring's bisection never binds and "
        "it is the right answer; if it is all-to-all, only the bisection matters. "
        "An interconnect specified without a traffic model has not been specified."))
    return "\n".join(s)
