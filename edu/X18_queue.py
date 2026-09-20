# -*- coding: utf-8 -*-
"""Volume I, Part X18 -- Performance modelling: queues, bursts and tails."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_perf2():
    s = ['<h1 id="x18">X18. Performance Modelling: Queues, Bursts and Tails</h1>']
    s.append("""<p>Most hardware performance questions are queueing questions in
    disguise: how deep must this FIFO be, how long will this request wait, what happens
    when two masters are busy at once. The answers are available in closed form for the
    simple cases and by simulation for the rest, and having both is what lets a designer
    say &lsquo;sixteen entries&rsquo; with a reason attached.</p>""")

    s.append("<h2>X18.1 Little's law, which is almost too simple to be useful and is not</h2>")
    s.append(derive("Little's law and its three uses", [
        ("In any stable system, <i>L</i> = &lambda;<i>W</i>: average number in the "
         "system equals arrival rate times average time in the system.",
         "It requires only stability &mdash; no distributional assumption whatever, "
         "which is why it is the most portable result in the subject."),
        ("Use 1: from occupancy and rate, get latency.",
         "Measure the average FIFO occupancy and the throughput, and the latency comes "
         "out without instrumenting it."),
        ("Use 2: from rate and latency, get the buffer needed.",
         "<b>This is the bandwidth&ndash;delay product</b>, which Parts X11, Y2 and Y3 "
         "each derived separately. They are the same theorem."),
        ("Use 3: as a consistency check on a simulation.",
         "If measured <i>L</i>, &lambda; and <i>W</i> do not satisfy it, the measurement "
         "is wrong &mdash; <b>an independent cross-check of exactly the kind "
         "Part&nbsp;Y6 insists on</b>, available free."),
    ]))
    s.append("<h2>X18.2 Utilisation and the tail</h2>")
    rows = []
    for rho in (0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
        mm1 = rho / (1 - rho)
        md1 = rho * rho / (2 * (1 - rho))
        rows.append([num(rho, 3), num(mm1, 4), num(md1, 4), num(1 / (1 - rho), 4),
                     num(math.ceil(-math.log(0.01) / max(-math.log(rho), 1e-9)), 3)])
    s.append(sweep("Queue length against utilisation: exponential service (M/M/1) and "
                   "deterministic service (M/D/1)",
        ["Utilisation &rho;", "Mean queue, M/M/1", "Mean queue, M/D/1",
         "Mean time in system (service units)",
         "Depth for 1&nbsp;% overflow, M/M/1"], rows,
        "Deterministic service halves the queue, which is the quantitative reason "
        "fixed-size flits and fixed-latency pipelines are preferred in hardware: "
        "<b>removing service-time variance is worth as much as halving the load.</b>"))
    s.append(plot([0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99],
                  [("M/M/1", [r / (1 - r) for r in (0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99)]),
                   ("M/D/1", [r * r / (2 * (1 - r))
                              for r in (0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99)])],
                  "utilisation", "mean queue length",
                  "Both curves have a pole at rho = 1. A design that targets 90 % "
                  "utilisation is targeting the steep part, and small errors in the "
                  "load estimate become large errors in the buffer requirement."))
    s.append("""<div class="ms"><b>Why hardware designers can be more aggressive about
    utilisation than the curve suggests, and where that reasoning fails.</b> The classical
    curves assume Poisson arrivals, which model independent users. On-chip traffic is
    frequently <i>self-limited</i>: a master with four outstanding transactions cannot
    offer more than four, so the arrival process is closed rather than open and the queue
    cannot blow up &mdash; the right model is a closed network, and utilisation near one
    is achievable. The reasoning fails exactly when the traffic becomes open: a DMA engine
    with deep outstanding support, several masters that do not coordinate, or a packet
    interface fed from outside the chip. <b>Ask whether the source can be throttled by the
    queue itself</b>; if it can, be aggressive, and if it cannot, respect the
    pole.</div>""")
    rng = np.random.default_rng(37)
    rows = []
    T = 200000
    # 8-cycle bursts arriving at one item per cycle; service one item every 2 cycles.
    # The service rate is deliberately below the *burst* rate and above the *average*
    # rate -- which is the only configuration in which the question "how deep?" has a
    # non-trivial answer.  A model whose service keeps up with the burst never queues,
    # and a table of zeros would say nothing.
    start = rng.random(T // 8) < 0.20
    burst = np.repeat(start, 8)[:T]
    for depth in (1, 2, 4, 8, 16, 32):
        occ = 0
        drops = 0
        arrivals = 0
        peak = 0
        for k in range(T):
            if burst[k]:
                arrivals += 1
                if occ < depth:
                    occ += 1
                    peak = max(peak, occ)
                else:
                    drops += 1
            if (k % 2 == 0) and occ:
                occ -= 1
        rows.append([num(depth), num(arrivals), num(drops),
                     num(drops / max(arrivals, 1), 3), num(peak)])
    s.append(sweep("Measured drop rate of a FIFO against depth, bursty arrivals "
                   "(8-cycle bursts at 1/cycle, 20&nbsp;% of slots start a burst, "
                   "service one every 2 cycles)",
        ["Depth", "Arrivals", "Drops", "Drop fraction", "Peak occupancy reached"], rows,
        "Simulated with seed 37. The <i>same</i> arrival trace is replayed at "
        "every depth, so the arrivals column is identical by construction &mdash; only "
        "the buffer changes. The average offered load is "
        + num(float(np.mean(burst)), 3) + " items per cycle against a service rate of "
        "0.5, so the system is <b>stable on average and still drops at small depths</b> "
        "&mdash; because the burst arrives faster than the service can drain it. "
        "The depth at which drops stop is set by the burst, not by the average."))
    s.append(ex("Sizing a FIFO from a burst specification rather than an average",
        "A source delivers a 64-byte burst at one byte per cycle, then idles for at "
        "least 192 cycles. The consumer drains at one byte every 2 cycles.",
        "Compute the accumulation during the burst and the drain afterwards; the peak "
        "occupancy is the answer, and it depends only on the burst, not on the average.",
        [("Burst length", num(64) + " cycles"),
         ("Arrival during burst", num(64) + " bytes"),
         ("Drain during burst", num(32) + " bytes"),
         ("Peak occupancy", num(32) + " bytes"),
         ("Average arrival rate", num(64 / 256, 4) + " B/cycle"),
         ("Average service rate", num(0.5, 3) + " B/cycle"),
         ("Utilisation", num(64 / 256 / 0.5, 4)),
         ("Depth an average-based calculation would suggest",
          "<b>small &mdash; and wrong</b>")],
        "<b>By computing the utilisation, seeing 0.5, and choosing a shallow FIFO.</b> "
        "The system is only half loaded on average and still needs 32 bytes of storage, "
        "because the buffer's job is to absorb the <i>difference between the arrival and "
        "service patterns</i>, not to absorb the average. <b>The general procedure is to "
        "integrate the difference between cumulative arrivals and cumulative service and "
        "take the maximum</b> &mdash; a construction that generalises to any traffic "
        "pattern you can describe, and that is the basis of the network-calculus bounds "
        "used where a hard guarantee is required rather than an average."))
    s.append(prob("Your interconnect meets its bandwidth requirement in simulation but "
                  "a customer reports missed real-time deadlines. What is the likely "
                  "disagreement?",
        "You measured throughput and they need <b>bounded latency</b>, and the two are "
        "almost unrelated once utilisation is high. An arbiter that delivers full "
        "bandwidth can make one requester wait arbitrarily long &mdash; fixed priority "
        "does this by construction, as Part&nbsp;X11's measurement showed. The resolution "
        "has three parts. <b>Establish which requester has the deadline and what it is</b>, "
        "because a real-time requirement is a per-requester property and an aggregate "
        "number cannot express it. <b>Measure the latency distribution, not the mean</b>: "
        "report the 99.9th percentile and the maximum observed, since a deadline is "
        "violated by the tail. <b>Then change the mechanism, not the tuning</b>: a "
        "bandwidth regulator plus a priority class, or a reserved slot, gives a bound; "
        "adjusting weights gives an average. <b>No amount of throughput tuning produces "
        "a latency guarantee</b>, and recognising that these are different requirements "
        "early saves a redesign late."))
    return "\n".join(s)
