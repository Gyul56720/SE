# -*- coding: utf-8 -*-
"""Volume I, Part X39 -- Clock generation, distribution and time synchronisation."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_clocking2():
    s = ['<h1 id="x39">X39. Clock Generation, Distribution and Time '
         'Synchronisation</h1>']
    s.append("""<p>Clocking is the one subsystem every block depends on and few
    specifications describe adequately. This part covers the three parts an IP designer
    must be able to reason about: how the clock is made, how it is delivered, and how time
    is agreed between chips.</p>""")

    s.append("<h2>X39.1 Spread spectrum: trading a specification for a specification</h2>")
    s.append(derive("Why modulating the clock reduces measured emissions", [
        ("Radiated emission is measured in a receiver with a defined resolution "
         "bandwidth &mdash; 120&nbsp;kHz for CISPR above 30&nbsp;MHz.",
         "The regulation specifies the measurement, not the physics."),
        ("An unmodulated clock puts all its harmonic energy in one line, far narrower "
         "than that bandwidth.",
         "So the receiver sees the whole harmonic."),
        ("Modulating the frequency by &plusmn;0.5&nbsp;% spreads each harmonic over "
         "&plusmn;0.5&nbsp;% of its frequency.",
         "The <i>n</i>th harmonic spreads <i>n</i> times as far, so higher harmonics "
         "benefit more."),
        ("<b>The receiver now sees only the fraction of the energy inside its "
         "bandwidth</b>, so the reading falls by roughly "
         "10&nbsp;log<sub>10</sub>(spread/RBW) dB.",
         "<b>The total radiated energy is unchanged.</b> The compliance number "
         "improves; the physics does not."),
        ("Cost: the clock period now varies, so every synchronous budget must hold at "
         "the fastest excursion, and any PLL downstream must track the modulation.",
         "<b>Which is why a SerDes reference clock's spread must be negotiated</b> "
         "&mdash; the CDR's loop bandwidth must exceed the modulation rate or it "
         "cannot follow."),
    ]))
    rows = []
    rbw = 120e3
    for f0, spread in ((100e6, 0.005), (100e6, 0.01), (1e9, 0.005), (1e9, 0.01),
                       (5e9, 0.005)):
        for h in (1, 5, 10):
            bwsp = f0 * h * spread * 2
            red = 10 * math.log10(max(bwsp / rbw, 1.0))
            rows.append([num(f0 / 1e6, 5), num(spread * 100, 3), num(h),
                         num(bwsp / 1e6, 5), num(red, 4)])
    s.append(sweep("Spread-spectrum reduction in a 120&nbsp;kHz measurement bandwidth",
        ["Clock (MHz)", "Spread (&plusmn;%)", "Harmonic", "Spread width (MHz)",
         "Reading reduced by (dB)"], rows,
        "Computed from the ratio of spread width to resolution bandwidth. <b>The "
        "fundamental barely benefits and the tenth harmonic benefits a lot</b>, which "
        "matches measured practice and is why spread spectrum is judged on the "
        "harmonics that actually fail the mask."))
    s.append("""<div class="warn"><b>Spread spectrum and a synchronous interface are
    frequently incompatible, and the incompatibility is found late.</b> Any interface
    whose two ends derive their clocks from different sources must absorb the frequency
    difference; spreading one side makes that difference time-varying at the modulation
    rate, typically 30&ndash;33&nbsp;kHz. An elastic buffer sized for a static 200&nbsp;ppm
    offset (Part&nbsp;Y3) will underflow or overflow when the offset swings by
    &plusmn;5000&nbsp;ppm at 33&nbsp;kHz. <b>The remedies are to spread both ends from
    the same source, to size the elastic buffer for the modulation, or to forbid spreading
    on that interface</b> &mdash; and which one applies is a system decision that must be
    recorded in the IP's integration guide, because the block cannot detect the
    problem.</div>""")

    s.append("<h2>X39.2 The clock tree, and what it costs</h2>")
    rows = []
    for flops in (1e4, 1e5, 1e6, 1e7):
        levels = math.ceil(math.log(flops, 4))
        buffers = flops / 3
        cap = flops * 5e-15 + buffers * 3e-15
        pwr = cap * 0.8 ** 2 * 1e9
        rows.append([num(int(flops)), num(levels), num(int(buffers)),
                     num(cap * 1e12, 5), num(pwr, 4), num(levels * 30, 4)])
    s.append(sweep("Clock tree cost at 1&nbsp;GHz, 0.8&nbsp;V (indicative 5&nbsp;fF per "
                   "flop clock pin, fanout 4)",
        ["Flops", "Buffer levels", "Buffers", "Total clock capacitance (pF)",
         "Clock power (W)", "Insertion delay (ps)"], rows,
        "<b>Indicative constants.</b> The shape is what matters: clock power is a large "
        "fraction of total dynamic power (Part&nbsp;X7 measured two thirds on a small "
        "block), and insertion delay grows logarithmically &mdash; which is harmless for "
        "setup and hold, since only skew matters (Part&nbsp;X2), and very harmful for "
        "anything that compares clock phase across a boundary."))
    s.append(tab("Clock distribution styles",
        ["Style", "Skew", "Power", "Where"],
        [["Balanced H-tree", "Low by construction", "High &mdash; long wires",
          "Top-level distribution in large chips"],
         ["<b>Buffered tree from CTS</b>", "Tool-balanced, a few tens of ps",
          "<b>Moderate</b>", "<b>The default for a block</b>"],
         ["Mesh / grid", "<b>Very low</b>", "<b>Highest &mdash; the whole grid "
          "switches</b>", "High-performance processors"],
         ["Clock gating (integrated cell)", "Adds a level",
          "<b>Saves 20&ndash;40&nbsp;%</b>", "<b>Everywhere &mdash; Part&nbsp;X7</b>"],
         ["Resonant / rotary", "Low", "Potentially much lower", "Research and a few "
          "products; needs inductors"]]))
    s.append("""<div class="bs"><b>Why a block should provide one clock input and do its
    own gating, rather than accepting several clocks.</b> Every additional clock at an IP
    boundary is a domain crossing the integrator must analyse, constrain and verify, and
    the constraints must be written by someone who understands both sides &mdash; which
    at integration time is nobody. A block that takes one clock and derives its internal
    enables is far easier to integrate, and the power saving from gating is identical.
    <b>Where a second clock is genuinely required</b> &mdash; a slower configuration
    domain, a recovered receive clock &mdash; <b>the crossing belongs inside the block,
    documented, with its constraints shipped</b>. That is a concrete piece of value a
    vendor adds, and its absence is a concrete integration cost.</div>""")

    s.append("<h2>X39.3 Agreeing on time: IEEE&nbsp;1588 and the hardware it needs</h2>")
    s.append(derive("Why timestamping must be in the PHY", [
        ("Two nodes exchange timestamped messages; the offset is "
         "((<i>t</i><sub>2</sub>&minus;<i>t</i><sub>1</sub>) &minus; "
         "(<i>t</i><sub>4</sub>&minus;<i>t</i><sub>3</sub>))/2.",
         "The standard two-way exchange."),
        ("This assumes the <b>path is symmetric</b>.",
         "<b>Any asymmetry appears directly as half of it in the offset</b> &mdash; an "
         "error no amount of averaging removes."),
        ("Every variable delay between the timestamp point and the wire is "
         "asymmetry.",
         "Software stacks, driver queues, interconnect arbitration, and even FIFO "
         "occupancy in the MAC."),
        ("<b>So the timestamp must be taken as close to the wire as possible</b>, in "
         "hardware, at a defined reference plane.",
         "Typically the start-of-frame delimiter crossing the MII interface, which is "
         "why PTP support is a PHY and MAC feature rather than a software one."),
        ("Residual asymmetry (different cable lengths, different PHY latencies for TX "
         "and RX) must be <i>calibrated</i> and subtracted.",
         "<b>Which means the block must expose a programmable correction</b>, and a "
         "datasheet must state the TX and RX latency and its variation &mdash; a number "
         "customers doing PTP will ask for and many datasheets omit."),
    ]))
    rows = []
    for name, jit in (("Software timestamp", 100e-6), ("Driver, kernel", 10e-6),
                      ("MAC, hardware", 100e-9), ("MII reference plane", 8e-9),
                      ("PHY, sub-ns aware", 1e-9)):
        rows.append([name, num(jit * 1e9, 5), num(jit / 2 * 1e9, 5),
                     num(3e8 * jit / 2, 5)])
    s.append(sweep("Where the timestamp is taken decides the achievable accuracy",
        ["Timestamp point", "Delay variation (ns)", "Offset error contribution (ns)",
         "Equivalent distance error (m)"], rows,
        "Indicative figures for each point in the stack. <b>The jump from software to "
        "hardware timestamping is three orders of magnitude</b>, which is why "
        "sub-microsecond synchronisation is a hardware feature and not a protocol "
        "choice."))
    s.append(prob("Your block must generate a clock that is frequency-locked to a "
                  "recovered network clock. What are the options?",
        "Three, and they differ in what they require from the system rather than in "
        "accuracy. <b>An analogue PLL locked to the recovered clock</b> is the classic "
        "answer: lowest jitter, and it needs an analogue block and a recovered clock "
        "brought out as a real clock signal, which constrains the floorplan and the "
        "package. <b>A digitally controlled oscillator driven by a digital PLL</b> "
        "&mdash; measure the phase error in digital logic, filter it, and steer a "
        "fractional-N synthesiser &mdash; keeps the loop in synthesisable logic, is "
        "portable between processes, and has more jitter; it is what most modern "
        "implementations do, and the loop design is Part&nbsp;X21's arithmetic. <b>Or "
        "adjust time rather than frequency</b>: run the local clock free and maintain a "
        "software-visible time base that is rate-corrected, which needs no clock hardware "
        "at all and is sufficient whenever the requirement is on <i>timestamps</i> rather "
        "than on a physical output clock. <b>The third is far cheaper and is frequently "
        "the right answer</b>, so the scoping question is whether the customer needs a "
        "synchronised clock pin or synchronised time, and those are very different "
        "products."))
    return "\n".join(s)
