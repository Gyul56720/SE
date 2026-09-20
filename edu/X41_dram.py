# -*- coding: utf-8 -*-
"""Volume I, Part X41 -- DRAM: the timing that shapes every memory controller."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_dram():
    s = ['<h1 id="x41">X41. DRAM: The Timing That Shapes Every Memory Controller</h1>']
    s.append("""<p>Off-chip memory is where most systems spend most of their latency and
    a large part of their power, and its behaviour is not a simple latency number. A DRAM
    device is a state machine with a dozen timing constraints, and whether your block gets
    the bandwidth it was promised depends almost entirely on its access pattern rather
    than on the interface's rated speed.</p>""")

    s.append("<h2>X41.1 The bank, the row and the reason access order matters</h2>")
    s.append(derive("Why a DRAM read is three operations, not one", [
        ("A DRAM array stores each bit as charge on a capacitor, read by dumping it "
         "onto a bit line.",
         "The read is <b>destructive</b> &mdash; the charge is consumed."),
        ("<b>ACTIVATE</b> opens a row: the whole row is sensed into the sense "
         "amplifiers, which form the <i>row buffer</i>.",
         "Thousands of bits at once. This takes <i>t</i><sub>RCD</sub>."),
        ("<b>READ</b> or <b>WRITE</b> then accesses columns within the open row.",
         "Fast &mdash; the data is already in the sense amplifiers. "
         "<b>A second access to the same row is far cheaper than the first.</b>"),
        ("<b>PRECHARGE</b> writes the row back and restores the bit lines.",
         "Takes <i>t</i><sub>RP</sub>. Required before opening a different row in the "
         "same bank."),
        ("<b>So three cases: row hit, row miss (different row, same bank), and bank "
         "hit with a different bank.</b>",
         "<b>Their costs differ by a factor of three or more</b>, which is why access "
         "ordering is the memory controller's main job."),
        ("And the whole array must be refreshed periodically, because the charge "
         "leaks.",
         "Refresh steals bandwidth and blocks access to a bank while it runs."),
    ]))
    rows = []
    tck = 0.625  # ns, DDR4-3200
    trcd, trp, tcl, tras, trc = 22, 22, 22, 52, 74
    for case, cycles in (("Row hit (open row)", tcl),
                         ("Row miss, same bank", trp + trcd + tcl),
                         ("Different bank, row hit", tcl),
                         ("Different bank, row miss", trcd + tcl)):
        rows.append([case, num(cycles), num(cycles * tck, 4),
                     num(cycles / tcl, 4)])
    s.append(sweep("Read latency by case, DDR4-3200 (indicative "
                   "<i>t</i><sub>CL</sub>=<i>t</i><sub>RCD</sub>=<i>t</i><sub>RP</sub>=22)",
        ["Case", "Cycles", "Latency (ns)", "Relative to a row hit"], rows,
        "<b>Indicative JEDEC-speed-bin numbers, not a datasheet.</b> The ratio is the "
        "point: the same DRAM delivers data in 14&nbsp;ns or 41&nbsp;ns depending "
        "entirely on which row was previously open."))
    rng = np.random.default_rng(19)
    rows = []
    for name, gen in (("Sequential", lambda i: i * 64),
                      ("Stride 4&nbsp;kB", lambda i: i * 4096),
                      ("Random", None),
                      ("Two interleaved streams",
                       lambda i: (i // 2) * 64 + (i % 2) * (1 << 22))):
        n = 20000
        banks, bankbits, rowshift = 16, 4, 13
        last_row = [None] * banks
        hits = miss = 0
        for i in range(n):
            a = rng.integers(0, 1 << 30) if gen is None else gen(i)
            bank = (a >> 8) & (banks - 1)
            row = a >> rowshift
            if last_row[bank] == row:
                hits += 1
            else:
                miss += 1
                last_row[bank] = row
        cyc = hits * tcl + miss * (trp + trcd + tcl)
        peak = n * tcl
        rows.append([name, num(hits / n, 4), num(miss / n, 4),
                     num(cyc * tck / 1000, 5), num(peak / cyc * 100, 4)])
    s.append(sweep("Measured row-buffer hit rate and the bandwidth it implies, "
                   "16 banks, 20&#8239;000 accesses",
        ["Access pattern", "Row hit rate", "Row miss rate", "Total time (&micro;s)",
         "Bandwidth as % of the row-hit-only case"], rows,
        "Simulated with a simple address decode (bank bits low, row bits high). "
        "<b>The same device delivers between a third and all of its rated bandwidth</b>, "
        "decided by the access pattern alone. This is why a block's DMA pattern is a "
        "system-level specification item."))

    s.append("<h2>X41.2 What the memory controller does about it</h2>")
    s.append(tab("Controller techniques and what each attacks",
        ["Technique", "Attacks", "Cost"],
        [["<b>Address mapping</b>", "Which bits select bank, row and column",
          "<b>Free, and it decides everything</b> &mdash; interleaving banks on low "
          "bits turns a sequential stream into parallel bank accesses"],
         ["Bank interleaving", "Row-miss latency", "Needs enough banks and enough "
          "outstanding requests"],
         ["<b>Request reordering (FR-FCFS)</b>",
          "<b>Serves row hits before older row misses</b>",
          "A scheduling queue; <b>and it makes latency unfair between requesters</b>"],
         ["Write batching", "Bus turnaround, which costs several cycles",
          "Write buffer; adds read latency when it drains"],
         ["Open-page vs closed-page policy", "Whether to leave a row open",
          "Open wins on locality, closed wins on random traffic &mdash; "
          "<b>a workload decision</b>"],
         ["Refresh scheduling", "Refresh blocking a bank",
          "Per-bank refresh and postponement; <b>the device sets the limits</b>"]]))
    s.append("""<div class="warn"><b>FR-FCFS scheduling makes DRAM latency unfair, and
    that unfairness reaches your block.</b> A scheduler that prioritises row hits gives
    enormous throughput to a requester with good locality and can starve one with poor
    locality almost indefinitely &mdash; a real-time display fetch behind a streaming
    accelerator is the classic case. Systems therefore add per-requester quotas or
    deadline awareness, which is Part&nbsp;X11's arbitration argument arriving at the
    memory controller. <b>For an IP vendor the consequence is concrete</b>: a latency
    figure measured in isolation is not the latency your block will see, and any real-time
    guarantee must be expressed as a requirement on the system's memory scheduler, not
    assumed.</div>""")
    rows = []
    for name, rate, width, ch in (("DDR4-3200", 3200e6, 64, 2), ("DDR5-6400", 6400e6, 64, 2),
                                  ("LPDDR5-6400", 6400e6, 32, 4),
                                  ("HBM2E", 3200e6, 1024, 1),
                                  ("HBM3", 6400e6, 1024, 1)):
        bw = rate * width * ch / 8 / 1e9
        rows.append([name, num(rate / 1e6, 5), num(width), num(ch), num(bw, 5),
                     num(bw / 25.6, 4)])
    s.append(sweep("Peak bandwidth of common memory interfaces",
        ["Interface", "MT/s", "Bits per channel", "Channels", "Peak GB/s",
         "Relative to one DDR4-3200 channel"], rows,
        "Peak, which nothing achieves. <b>HBM's advantage is width, not speed</b> "
        "&mdash; a thousand-bit interface at a modest rate, possible only because it is "
        "stacked on an interposer rather than routed on a board, which is why it costs "
        "what it does."))

    s.append("<h2>X41.3 Refresh, and why it gets worse</h2>")
    s.append(ex("What refresh costs at each density",
        "DDR4 requires all rows refreshed every 64&nbsp;ms (32&nbsp;ms above "
        "85&nbsp;&deg;C). Refresh is issued as 8192 commands per interval, each "
        "occupying the device for <i>t</i><sub>RFC</sub>.",
        "Compute the fraction of time spent refreshing at several densities, where "
        "<i>t</i><sub>RFC</sub> grows with density because more rows are refreshed per "
        "command.",
        [("Refresh interval", num(64, 3, "ms")),
         ("Commands per interval", num(8192)),
         ("<i>t</i><sub>RFC</sub> at 8&nbsp;Gbit", num(350, 4, "ns")),
         ("Time refreshing", num(8192 * 350e-9 / 64e-3 * 100, 4, "%")),
         ("<i>t</i><sub>RFC</sub> at 16&nbsp;Gbit", num(550, 4, "ns")),
         ("Time refreshing", num(8192 * 550e-9 / 64e-3 * 100, 4, "%")),
         ("At 32&nbsp;Gbit and 95&nbsp;&deg;C (32&nbsp;ms interval)",
          num(8192 * 880e-9 / 32e-3 * 100, 4, "%")),
         ("Trend", "<b>refresh overhead grows with density and with temperature</b>")],
        "<b>By assuming refresh is a rounding error.</b> It was, at low density and room "
        "temperature; at high density in a hot enclosure it approaches a quarter of the "
        "device's time, and during a refresh the affected bank is unavailable, so the "
        "<i>latency tail</i> grows faster than the average. <b>Any block with a hard "
        "real-time deadline on a DRAM access must budget for a refresh collision</b>, and "
        "the number to budget is <i>t</i><sub>RFC</sub> at the maximum operating "
        "temperature, which a datasheet should state and a system integrator should be "
        "asked for."))
    s.append(prob("Your accelerator needs 40&nbsp;GB/s and the system has one DDR5 "
                  "channel rated at 51&nbsp;GB/s. Is that enough?",
        "Almost certainly not, and the calculation to show it is short. Start from the "
        "rated figure and subtract, in order: <b>refresh</b>, a few per cent to a quarter "
        "depending on density and temperature; <b>read/write turnaround</b>, several "
        "cycles each time the bus direction changes, which for a mixed read-write stream "
        "costs 10&ndash;20&nbsp;%; <b>row misses</b>, from the measurement in X41.1, "
        "which for anything but a sequential pattern is the largest term; and <b>other "
        "requesters</b>, because the channel is not yours. A realistic efficiency for a "
        "well-behaved streaming pattern sharing a channel is 60&ndash;75&nbsp;%, giving "
        "30&ndash;38&nbsp;GB/s &mdash; below the requirement. <b>The productive response "
        "is not to ask for a faster channel but to reduce the demand</b>: tile the "
        "computation so data is reused on chip (Part&nbsp;X13), compress the traffic "
        "(Part&nbsp;X20's reference compression), or restructure the access pattern for "
        "row locality, which the measurement above shows can be worth a factor of two on "
        "its own. <b>And whatever is decided, the efficiency assumption belongs in the "
        "datasheet</b>, because the customer will measure it."))
    return "\n".join(s)
