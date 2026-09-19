# -*- coding: utf-8 -*-
"""Volume I, Part X37 -- Bus protocols: ordering, outstanding transactions, exclusives."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_axi():
    b = []
    ch = [("AW  address write", 16), ("W   write data", 44), ("B   write response", 72),
          ("AR  address read", 108), ("R   read data", 136)]
    for nm, y in ch:
        b.append(f'<rect x="96" y="{y-12}" width="180" height="20" fill="#eef2f7" '
                 f'stroke="#123f6d" stroke-width="0.8"/>')
        b.append(txt(186, y + 2, nm, 8, "middle"))
    b.append(box(16, 44, 66, 66, "master", None, 9))
    b.append(box(290, 44, 66, 66, "slave", None, 9))
    for y in (16, 44, 108):
        b.append(arr(82, y, 96, y)); b.append(arr(276, y, 290, y))
    for y in (72, 136):
        b.append(arr(290, y, 276, y)); b.append(arr(96, y, 82, y))
    b.append(txt(186, 166, "Five independent channels, each with its own handshake.",
                 9, "middle"))
    b.append(txt(186, 180, "Independence is the source of both the throughput and the "
                           "deadlocks.", 9, "middle", 'font-style="italic"'))
    return svg(380, 190, "".join(b))


def ch_bus():
    s = ['<h1 id="x37">X37. Bus Protocols: Ordering, Outstanding Transactions and '
         'Exclusives</h1>']
    s.append("""<p>Almost every block a design house sells attaches to an AMBA interface,
    and almost every integration problem is a protocol misunderstanding rather than a
    functional bug. The protocol's subtle points are few and they recur; this part works
    through them.</p>""")
    s.append(fig(_f_axi(), "The five AXI channels."))

    s.append("<h2>X37.1 The handshake, and the one rule that is always broken</h2>")
    s.append(derive("VALID/READY, and why VALID may not wait", [
        ("A transfer occurs on a rising edge when VALID and READY are both high.",
         "The basic handshake, shared by AXI, AXI-Stream, TileLink and CHI."),
        ("<b>Once VALID is asserted it must stay asserted until the transfer "
         "occurs</b>, and the payload must not change.",
         "Otherwise the receiver cannot rely on what it sampled."),
        ("<b>VALID must not depend combinationally on READY.</b>",
         "<b>This is the rule that is broken.</b> If each side waits for the other, the "
         "two combinational paths form a loop and the interface deadlocks or oscillates "
         "&mdash; and a testbench with a permanently-ready receiver never exposes it."),
        ("READY <i>may</i> depend combinationally on VALID.",
         "The asymmetry is deliberate: it lets a receiver accept in the same cycle, "
         "which is where the throughput comes from."),
        ("A registered-output, registered-ready skid buffer breaks any timing path "
         "across the interface at the cost of one cycle and two entries of storage.",
         "<b>The standard remedy, and the right default for an IP boundary</b> "
         "&mdash; Part&nbsp;X14's advice to register every boundary, in protocol "
         "form."),
    ]))
    s.append("""<div class="warn"><b>The testbench that hides this bug is the default
    one.</b> A driver that holds READY high permanently, or a monitor that never applies
    back-pressure, will never create the condition in which a combinational
    VALID-from-READY dependency matters. <b>Randomised back-pressure is not an
    optional refinement of an interface testbench; it is the only way the interface is
    tested at all.</b> The same applies to the master side: a stimulus that never delays
    VALID does not test the slave's ability to wait. Both are one line of constrained
    randomisation and both routinely go missing.</div>""")
    rows = []
    for name, lat, thr in (("Combinational pass-through", 0, 1.0),
                           ("Register slice, forward only", 1, 1.0),
                           ("Register slice, both directions (skid)", 1, 1.0),
                           ("Naive register on both, no skid", 1, 0.5),
                           ("Two-deep FIFO", 2, 1.0)):
        rows.append([name, num(lat), num(thr, 3),
                     "<b>none</b>" if lat == 0 else "broken",
                     "<b>yes</b>" if thr == 1.0 else "<b>halved</b>"])
    s.append(sweep("Interface buffering options and what each costs",
        ["Structure", "Added latency (cycles)", "Throughput (transfers/cycle)",
         "Timing path across the boundary", "Full rate?"], rows,
        "<b>The fourth row is the trap</b>: registering both VALID and READY without a "
        "skid buffer halves the throughput, because the master cannot present a new "
        "value until it has seen the registered READY. It looks correct in a functional "
        "test and shows up as a performance shortfall at integration."))

    s.append("<h2>X37.2 Ordering: what the protocol guarantees and what it does not</h2>")
    s.append(tab("AXI ordering rules, and the integration failures each one causes",
        ["Rule", "What it means", "The bug it causes when forgotten"],
        [["<b>Same ID, same direction &rarr; ordered</b>",
          "Responses come back in order for one ID",
          "A slave that reorders within an ID breaks masters that rely on it"],
         ["<b>Different IDs &rarr; no order guarantee</b>",
          "Responses may interleave arbitrarily",
          "<b>A master that assumes order across IDs corrupts data</b>"],
         ["Reads and writes are <b>not</b> ordered relative to each other",
          "A read issued after a write may complete first",
          "<b>Read-after-write hazards in a customer's driver</b>; needs an explicit "
          "barrier or a completion wait"],
         ["Write response means accepted, not visible",
          "B arrives when the slave takes responsibility",
          "Assuming data is observable by another master &mdash; it may not be"],
         ["Bursts must not cross 4&nbsp;kB boundaries",
          "A page-crossing burst is illegal",
          "<b>A DMA that ignores it produces a protocol violation the interconnect "
          "may not check</b>"],
         ["Narrow transfers use strobes",
          "WSTRB selects lanes", "A slave ignoring WSTRB corrupts neighbouring bytes"]]))
    s.append(ex("How many IDs does a master need?",
        "A DMA engine with 8&nbsp;GB/s of read bandwidth, a 400&nbsp;ns round trip, "
        "512-byte bursts, on a 256-bit interface at 1&nbsp;GHz.",
        "Bandwidth&ndash;delay product decides outstanding bursts; whether they need "
        "distinct IDs depends on whether the engine can accept out-of-order data.",
        [("Bytes in flight needed", num(8e9 * 400e-9 / 1024, 4, "kB")),
         ("Outstanding bursts", num(math.ceil(8e9 * 400e-9 / 512))),
         ("If all use one ID", "<b>responses are ordered &mdash; simple, but one slow "
          "slave blocks everything behind it</b>"),
         ("If each uses a distinct ID", "reordering allowed &mdash; needs a reorder "
          "buffer"),
         ("Reorder buffer size", num(8e9 * 400e-9 / 1024, 4, "kB")),
         ("ID bits needed", num(math.ceil(math.log2(math.ceil(8e9 * 400e-9 / 512))))),
         ("Recommended", "<b>a few IDs, grouped by destination</b>")],
        "<b>By choosing one extreme.</b> A single ID gives head-of-line blocking: a "
        "request to slow memory stalls every completed request behind it, and the "
        "measured bandwidth collapses when the traffic is mixed. Distinct IDs everywhere "
        "give full reordering freedom and cost a reorder buffer of the full "
        "bandwidth&ndash;delay product plus the logic to fill it. <b>The usual answer is "
        "a small number of IDs partitioned by destination</b> &mdash; one per memory "
        "region or per outstanding stream &mdash; which removes head-of-line blocking "
        "between unrelated traffic while keeping ordering, and therefore simplicity, "
        "within a stream."))

    s.append("<h2>X37.3 Exclusive access, and why it is harder than it looks</h2>")
    s.append(derive("Load-linked / store-conditional in bus form", [
        ("An exclusive read records a monitor for that address and master.",
         "AXI's ARLOCK exclusive, or the processor's load-linked."),
        ("An exclusive write succeeds only if the monitor is still set.",
         "It returns EXOKAY on success and OKAY on failure &mdash; <b>and OKAY means "
         "the write did not happen</b>, which software must check."),
        ("Any intervening write to the address by anyone clears the monitor.",
         "That is what makes it atomic."),
        ("<b>The monitor is in the slave or the interconnect, not the master.</b>",
         "So an IP block containing memory that must support exclusives has to "
         "implement the monitor &mdash; and the number of simultaneous monitors it "
         "supports is a specification item that is routinely omitted."),
        ("Monitors may be granted at a granularity coarser than one address.",
         "<b>Which causes false failures</b>: two masters using different addresses in "
         "the same granule livelock each other. The granule size must be documented."),
        ("Spurious failure is always permitted, so software must loop.",
         "<b>Hardware is allowed to be conservative; software must not assume "
         "success.</b> A driver that does not loop works on one implementation and "
         "hangs on another."),
    ]))
    s.append("""<div class="ms"><b>Atomics moved from the master to the interconnect, and
    an IP vendor should know which era their customer is in.</b> The load-linked /
    store-conditional model requires a monitor per master and a retry loop, and it scales
    badly with core count because contention causes repeated failures. Newer AMBA
    revisions add <i>far atomics</i>: the master sends the operation (add, swap, compare
    and swap) to the point of coherence and receives the result, so the round trip happens
    once regardless of contention. <b>For a block containing shared state, supporting far
    atomics can be far cheaper than supporting exclusives</b> &mdash; an ALU beside the
    memory rather than a monitor table &mdash; and it performs better under contention.
    Asking the customer which their system uses is a scoping question worth raising
    early.</div>""")
    s.append(prob("Your block's register interface is APB and the customer complains of "
                  "poor configuration throughput. What do you say?",
        "That APB is doing exactly what it is for, and then offer the two real options. "
        "APB is deliberately simple &mdash; no pipelining, no outstanding transactions, "
        "two cycles per access minimum &mdash; because a configuration bus should be "
        "trivial to implement and verify, and configuration is not a throughput problem. "
        "If the customer is writing thousands of registers at boot and it matters, the "
        "causes are usually not the bus: a slow bridge clock ratio, a synchroniser per "
        "access, or software doing read-modify-write where a write would do. <b>Measure "
        "before changing the interface.</b> If it genuinely is the bus, the options are "
        "to <b>add a small DMA or descriptor engine</b> that replays a register image "
        "from memory &mdash; which is what blocks with large coefficient tables do, and "
        "it moves the traffic to AXI where it belongs &mdash; or to <b>provide an "
        "AXI-Lite alternative</b> for the register file. <b>Adding coefficient memory "
        "behind a streaming interface, rather than behind the register bus, is the "
        "structural fix</b>, and it is worth designing in from the start for any block "
        "whose configuration is more than a few hundred words."))
    return "\n".join(s)
