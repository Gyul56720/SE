# -*- coding: utf-8 -*-
"""Volume I, Part X21 -- Feedback and control inside digital blocks."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_control2():
    s = ['<h1 id="x21">X21. Feedback and Control Inside Digital Blocks</h1>']
    s.append("""<p>Loops appear in more digital blocks than their designers usually
    realise: clock and data recovery, equaliser adaptation, gain control, rate matching,
    thermal throttling, voltage regulation and every calibration engine. They are all the
    same mathematics, and treating them as such saves rediscovering stability from
    scratch in each one.</p>""")

    s.append("<h2>X21.1 The digital loop and where its delay comes from</h2>")
    s.append(derive("Why loop delay, not loop gain, usually sets the limit", [
        ("A first-order digital loop is "
         "<i>x</i>[<i>n</i>+1] = <i>x</i>[<i>n</i>] + &mu;<i>e</i>[<i>n</i>&minus;<i>d</i>], "
         "with <i>d</i> the delay in the feedback path.",
         "Accumulator plus a delayed error. Every adaptation engine in this book has "
         "this form."),
        ("With <i>d</i> = 0 it is stable for 0 &lt; &mu; &lt; 2 (for unit "
         "error gain).", "Standard result for the integrator."),
        ("Each unit of delay adds phase lag &omega;<i>d</i> at frequency &omega;.",
         "A pure delay is all phase and no magnitude &mdash; <b>which is what makes it "
         "so destructive</b>: it costs stability margin without showing up in a gain "
         "plot."),
        ("Stability requires the loop gain to have fallen below one before the phase "
         "reaches 180&deg;.",
         "Nyquist. With delay <i>d</i>, that caps the bandwidth at roughly "
         "&pi;/(2<i>d</i>)."),
        ("<b>So &mu; must be reduced roughly in proportion to 1/<i>d</i></b>, and the "
         "loop's settling time grows with <i>d</i> twice over.",
         "Once because each correction is smaller, once because corrections arrive "
         "later. <b>Pipelining an adaptation loop is not free even though it meets "
         "timing.</b>"),
    ]))
    rows = []
    for d in (0, 1, 2, 4, 8, 16):
        mu_max = 2.0 / (1 + 2 * d) if d else 2.0
        bw = 1.0 / (2 * (d + 1))
        # simulate settling
        mu = mu_max * 0.5
        x = 0.0
        hist = [0.0] * (d + 1)
        n_settle = None
        for n in range(4000):
            e = 1.0 - x
            hist.append(e)
            x = x + mu * hist[-(d + 1)]
            if n_settle is None and abs(1.0 - x) < 0.02:
                n_settle = n
        rows.append([num(d), num(mu_max, 4), num(mu, 4),
                     num(n_settle if n_settle is not None else -1),
                     num(bw, 4)])
    s.append(sweep("Measured settling of a first-order loop as feedback delay grows "
                   "(step response to within 2&nbsp;%, &mu; set to half the stable "
                   "maximum)",
        ["Delay <i>d</i> (cycles)", "Approx. stable &mu; limit", "&mu; used",
         "Cycles to settle", "Normalised bandwidth"], rows,
        "Simulated directly. <b>The settling column is the cost of pipelining</b>: the "
        "loop still works at every delay, and it takes an order of magnitude longer at "
        "the bottom of the table than at the top."))
    s.append(plot([0, 1, 2, 4, 8, 16],
                  [("cycles to settle", [float(r[3].replace(",", "")) for r in rows])],
                  "feedback delay (cycles)", "cycles to 2 % settling",
                  "Settling time against loop delay, measured. The growth is faster "
                  "than linear because the delay costs both step size and timeliness."))
    s.append(ex("Where the delay in a real adaptation loop comes from",
        "A SerDes equaliser adaptation loop at 53&nbsp;GBd, with the datapath "
        "de-serialised 64:1 so the digital logic runs at 830&nbsp;MHz.",
        "Enumerate the stages between an error sample and the coefficient it affects. "
        "Each is a pipeline register somebody added to meet timing.",
        [("Error slicer to error sample register", num(1) + " cycle"),
         ("Error accumulation across the 64 parallel lanes", num(3) + " cycles"),
         ("Correlation with the data pattern", num(2) + " cycles"),
         ("Leaky accumulator update", num(1) + " cycle"),
         ("Coefficient register to the analogue DAC", num(2) + " cycles"),
         ("DAC settling", num(4) + " cycles"),
         ("Total loop delay", num(13) + " cycles"),
         ("At 830&nbsp;MHz", num(13 / 830e6 * 1e9, 4, "ns")),
         ("Symbols elapsed", num(int(13 / 830e6 * 53.125e9)))],
        "<b>By budgeting only the digital pipeline.</b> The DAC settling is a third of "
        "the loop here and is invisible in an RTL-only analysis; a loop tuned in "
        "simulation without it will be under-damped in silicon. <b>Any mixed-signal loop "
        "must be analysed across the boundary</b>, which in practice means the digital "
        "designer needs a number from the analogue designer and must ask for it "
        "explicitly &mdash; it will not arrive otherwise."))

    s.append("<h2>X21.2 The loops in a typical block, and what each is for</h2>")
    s.append(tab("Digital control loops and their characteristic time constants",
        ["Loop", "Controls", "Time constant", "Failure if too fast", "Failure if too "
         "slow"],
        [["<b>CDR</b>", "Sampling phase", "10<sup>3</sup>&ndash;10<sup>5</sup> UI",
          "Tracks jitter into the eye; fails jitter transfer",
          "<b>Fails jitter tolerance</b> &mdash; cannot follow real wander"],
         ["Equaliser adaptation", "Tap coefficients",
          "10<sup>4</sup>&ndash;10<sup>6</sup> symbols",
          "Noisy coefficients; the taps chase noise", "Cannot follow temperature drift"],
         ["AGC", "Analogue gain", "10<sup>3</sup>&ndash;10<sup>4</sup> symbols",
          "Modulates the signal it is measuring", "Clips on a level change"],
         ["Offset cancellation", "Slicer threshold", "Slow",
          "Interacts with the data pattern", "Residual offset eats the eye"],
         ["Thermal throttle", "Clock frequency", "Milliseconds to seconds",
          "Oscillates audibly in performance", "Overheats"],
         ["Rate matching / elastic buffer", "Idle insertion and deletion",
          "Per packet", "&mdash;", "Overflow or underflow"]]))
    s.append("""<div class="warn"><b>Loops that share a plant interact, and the
    interaction is usually discovered in silicon.</b> An AGC and an offset-cancellation
    loop both observe the same slicer; an equaliser adaptation and a CDR both depend on
    the sampling phase. Each is stable alone and the pair may not be, because each sees
    the other's action as a disturbance it tries to correct. The standard engineering
    answer is <b>time-scale separation</b>: make one loop at least ten times slower than
    the other so the fast loop sees the slow one as constant and the slow one sees the
    fast one as settled. <b>This separation must be stated in the specification</b>,
    because a later optimisation that speeds up one loop &mdash; an entirely reasonable
    thing to do for lock time &mdash; destroys it, and nothing in the RTL records why the
    original number was chosen.</div>""")
    s.append(prob("A calibration loop converges in the lab and oscillates in a customer's "
                  "system. What changed?",
        "Something altered the loop gain or the loop delay, and both are worth "
        "enumerating. <b>Gain</b>: the plant's sensitivity may differ &mdash; a different "
        "supply voltage, a different temperature, a different process corner all change "
        "how much the controlled quantity moves per code, and a loop tuned at one corner "
        "can be over-damped at another and unstable at a third. <b>Delay</b>: a different "
        "clock ratio changes how many cycles the loop takes in real time; if the customer "
        "runs the digital logic slower, every cycle of pipeline is longer. <b>Or the "
        "disturbance changed</b>: a loop that is stable against slow drift can oscillate "
        "when the input contains energy near its bandwidth, which a noisier supply or a "
        "neighbouring switching regulator can supply. <b>The measurement that "
        "discriminates is to reduce the gain and see whether it stops</b>; if it does, "
        "the problem is margin and the fix is a gain that adapts or a specified "
        "operating range. If it does not, look for an interacting second loop &mdash; "
        "and note that the customer's system has loops yours does not know about."))
    return "\n".join(s)
