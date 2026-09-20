# -*- coding: utf-8 -*-
"""Volume I, Part L -- Semiconductor physics, power, thermal, packaging, control."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def _f_band():
    b = []
    for x0, lab in ((40, "Insulator"), (200, "Semiconductor"), (370, "Metal")):
        b.append(f'<rect x="{x0}" y="30" width="96" height="30" fill="#bcd" stroke="#000" stroke-width="0.9"/>')
        b.append(txt(x0+48, 50, "conduction", 8, "middle"))
        gap = {40: 100, 200: 52, 370: 0}[x0]
        b.append(f'<rect x="{x0}" y="{60+gap}" width="96" height="30" fill="#dcb" stroke="#000" stroke-width="0.9"/>')
        b.append(txt(x0+48, 80+gap, "valence", 8, "middle"))
        if gap:
            b.append(line(x0+48, 60, x0+48, 60+gap, "3,3"))
            b.append(txt(x0+54, 60+gap/2, f"E_g", 8))
        b.append(txt(x0+48, 205, lab, 9, "middle"))
        b.append(txt(x0+48, 222, {40:"E_g > 4 eV", 200:"E_g ≈ 1.1 eV (Si)", 370:"bands overlap"}[x0],
                     8, "middle"))
    b.append(txt(255, 252, "Doping moves the Fermi level; the band gap sets the intrinsic carrier density",
                 9, "middle", 'font-style="italic"'))
    return svg(520, 264, "".join(b))


def ch_semi():
    s = ['<h1 id="l1">L1. Semiconductor Physics: What Survives into Design</h1>']
    s.append(fig(_f_band(), "Band structure. The gap determines whether a material "
                            "conducts, and silicon's 1.1 eV gap is what makes it useful."))
    s.append(tab("Physical quantities and where a designer meets them",
        ["Quantity", "Symbol / value", "Design consequence"],
        [["Band gap of Si", "1.12 eV at 300 K",
          "Falls with temperature &rarr; leakage rises, <i>V<sub>TH</sub></i> falls"],
         ["Intrinsic carrier density", "<i>n<sub>i</sub></i> &asymp; 10<sup>10</sup> cm<sup>&minus;3</sup>",
          "Doubles roughly every 8 K &rarr; junction leakage doubles with it"],
         ["Thermal voltage", "<i>kT</i>/<i>q</i> = 25.9 mV at 300 K",
          "<b>Sets the subthreshold slope</b>: 60 mV/decade minimum"],
         ["Mobility &mu;", "&asymp;1400 (e), 450 (h) cm<sup>2</sup>/Vs",
          "Why PMOS is sized ~2&ndash;3&times; wider than NMOS"],
         ["Saturation velocity", "&asymp;10<sup>7</sup> cm/s",
          "<b>Short-channel current becomes linear in overdrive</b>"],
         ["Oxide capacitance", "<i>C</i><sub>ox</sub> = &epsilon;<sub>ox</sub>/<i>t</i><sub>ox</sub>",
          "Thinner oxide &rarr; more drive and more gate leakage"],
         ["Depletion width", "&prop; &radic;(<i>V</i>/<i>N</i>)",
          "Short-channel effects; junction capacitance"]]))
    s.append("""<div class="ms"><b>The 60 mV/decade subthreshold slope is a hard physical
    limit and it ended Dennard scaling.</b> Below threshold, drain current depends
    exponentially on gate voltage with a slope of at best
    (<i>kT</i>/<i>q</i>)&nbsp;ln10 &asymp; 60&nbsp;mV per decade at room temperature,
    because the mechanism is thermal emission over a barrier. To keep leakage constant
    while lowering the supply, the threshold must fall by the same amount &mdash; but each
    100&nbsp;mV of threshold reduction multiplies leakage by about fifty. <b>This is why
    supply voltage stopped scaling near 0.8&nbsp;V and why power density rose</b>, which
    in turn is why the industry turned to specialised accelerators and therefore why the
    IP market grew. A thermodynamic constant is visible in a business model.</div>""")
    s.append(tab("Devices beyond the planar MOSFET",
        ["Device", "Principle", "Motivation"],
        [["FinFET", "Gate wraps a vertical fin on three sides",
          "Better electrostatic control &rarr; less DIBL and leakage"],
         ["<b>GAA / nanosheet</b>", "Gate surrounds the channel completely",
          "Further control; width quantised by sheet count"],
         ["FD-SOI", "Thin body on buried oxide",
          "Low leakage; <b>body bias as a live tuning knob</b>"],
         ["Tunnel FET", "Band-to-band tunnelling",
          "<b>Can beat 60 mV/decade</b>; low on-current so far"],
         ["Negative-capacitance FET", "Ferroelectric gate stack",
          "Internal voltage amplification; reliability unproven"],
         ["2D materials", "MoS<sub>2</sub> and similar", "Ultra-thin body; research stage"]]))
    return "\n".join(s)


def ch_power():
    s = ['<h1 id="l2">L2. Power Delivery and Conversion</h1>']
    s.append(tab("Voltage regulator types",
        ["Type", "Efficiency", "Ripple", "Response", "Where"],
        [["<b>LDO</b>", "<i>V</i><sub>out</sub>/<i>V</i><sub>in</sub> &mdash; poor if the drop is large",
          "Very low", "Fast", "Sensitive analogue, small currents"],
         ["<b>Buck (switching)</b>", "85&ndash;95%", "Higher (switching ripple)", "Slower",
          "Digital cores, large currents"],
         ["Boost", "&mdash;", "&mdash;", "&mdash;", "Raising a voltage"],
         ["Charge pump", "Moderate", "&mdash;", "&mdash;", "Small currents, no inductor"],
         ["<b>Integrated voltage regulator</b>", "&mdash;", "&mdash;", "<b>Very fast</b>",
          "Per-domain DVFS on die"],
         ["<b>Switched-capacitor</b>", "Good at fixed ratios", "&mdash;", "&mdash;",
          "On-die, no inductor needed"]]))
    s.append("""<div class="ms"><b>Regulator response time is a digital design constraint.</b>
    When a large synchronous block starts, it draws a current step; the regulator takes
    time to respond, and during that time the supply droops. The droop reduces gate drive
    and therefore increases delay, which can violate timing. Designers respond with
    <b>di/dt management</b> &mdash; staggering the release of clock gates so a block wakes
    in stages rather than all at once. <b>This is a purely digital technique introduced to
    solve an analogue problem, and it must be specified</b>: an IP that draws its full
    current in one cycle after an enable is harder to integrate than one that ramps.</div>""")
    s.append(tab("Decoupling hierarchy",
        ["Level", "Capacitance", "Effective range", "Limit"],
        [["On-die (MOS, MIM)", "nF", "&gt;100 MHz", "Area"],
         ["Package", "&mu;F", "10&ndash;100 MHz", "Package inductance"],
         ["Board ceramic", "&mu;F", "1&ndash;10 MHz", "ESL"],
         ["Bulk electrolytic", "100&nbsp;&mu;F+", "&lt;1 MHz", "&mdash;"],
         ["<b>Anti-resonance</b>", "&mdash;", "<b>50&ndash;200 MHz typically</b>",
          "<b>Where package L resonates with die C</b> &mdash; must be damped"]]))
    s.append("""<div class="warn"><b>The anti-resonance peak is a common cause of
    otherwise inexplicable failures.</b> Package inductance and on-die capacitance form a
    parallel resonance at which the power delivery network's impedance is much higher than
    at neighbouring frequencies. A workload whose current draw happens to contain energy at
    that frequency &mdash; a loop running at the resonant rate, a burst-mode accelerator
    &mdash; produces supply noise far larger than the average current would suggest. The
    symptom is a design that passes all tests but fails on one specific piece of
    software. <b>A digital block's current <i>spectrum</i>, not only its average power,
    is a system-level property.</b></div>""")
    return "\n".join(s)


def ch_thermal():
    s = ['<h1 id="l3">L3. Thermal and Packaging</h1>']
    s.append("""<div class="math">T<sub>junction</sub> = T<sub>ambient</sub> +
    P &middot; &theta;<sub>JA</sub></div>""")
    s.append(tab("Thermal resistance path",
        ["Segment", "Symbol", "Typical", "Improved by"],
        [["Junction to case", "&theta;<sub>JC</sub>", "0.1&ndash;1 K/W",
          "Die attach, lid material"],
         ["Case to heatsink", "&mdash;", "0.1&ndash;0.5 K/W", "Thermal interface material"],
         ["Heatsink to ambient", "&theta;<sub>SA</sub>", "0.5&ndash;10 K/W", "Fin area, airflow"],
         ["<b>Total</b>", "&theta;<sub>JA</sub>", "&mdash;", "&mdash;"],
         ["Hot spot", "&mdash;", "&mdash;",
          "<b>Local power density, not average</b> &mdash; floorplanning matters"]]))
    s.append("""<div class="ms"><b>Hot spots are a floorplanning problem, and they couple
    back into timing.</b> Average die temperature may be comfortable while a dense
    arithmetic block runs 20&nbsp;K hotter than its surroundings. Since delay and leakage
    both depend on temperature, that block is slower and leakier than the sign-off corner
    assumed, and its leakage raises its temperature further &mdash; a positive feedback
    known as thermal runaway in the extreme. The design responses are spreading high-activity
    logic, inserting thermal sensors and throttling, and accounting for the gradient in
    timing analysis. <b>For an IP vendor, a block with very high local power density
    should say so</b>, because the customer's floorplanner needs to know.</div>""")
    s.append(tab("Package types",
        ["Package", "Density", "Thermal", "Use"],
        [["Wire-bond QFN/BGA", "Low", "Moderate", "Cost-sensitive"],
         ["Flip-chip BGA", "High", "Good (heat exits through the lid)", "High performance"],
         ["<b>Silicon interposer (2.5D)</b>", "Very high", "Good", "HBM integration"],
         ["<b>3D stacking</b>", "Highest", "<b>Difficult &mdash; heat is trapped</b>",
          "Memory on logic"],
         ["Fan-out wafer level", "High", "Moderate", "Mobile"],
         ["Chiplet in package", "High", "Manageable", "Disaggregated designs"]]))
    s.append("""<div class="ms"><b>Thermal constraints are what limit 3D integration,
    not manufacturing.</b> Stacking a logic die under another die places its heat behind a
    thermal barrier, so the achievable power density falls sharply. This is why current 3D
    products stack memory (low power) on logic rather than logic on logic, and why thermal
    modelling now appears early in architecture rather than at the end. <b>The physical
    constraint determines the partitioning, which determines which interfaces are needed,
    which determines which IP is valuable.</b></div>""")
    return "\n".join(s)


def ch_control():
    s = ['<h1 id="l4">L4. Feedback and Control</h1>']
    s.append("""<p>Feedback loops appear throughout an IP portfolio: PLLs, CDRs, adaptive
    equalisers, AGC, DVFS controllers, thermal throttling, and the convergence of iterative
    decoders. The same small set of concepts governs all of them.</p>""")
    s.append(tab("Control concepts and their hardware instances",
        ["Concept", "Meaning", "Instance"],
        [["Open-loop gain", "Gain around the loop", "PLL <i>K</i><sub>PD</sub><i>K</i><sub>VCO</sub>"],
         ["<b>Loop bandwidth</b>", "Where gain crosses unity",
          "<b>The central design parameter of every loop</b>"],
         ["<b>Phase margin</b>", "Phase at crossover, relative to &minus;180&deg;",
          "&lt;45&deg; gives peaking and ringing"],
         ["Type / order", "Number of integrators / poles",
          "Type-2 PLL tracks a frequency step with zero error"],
         ["Damping &zeta;", "&mdash;", "&zeta;&asymp;0.707 is the usual target"],
         ["Steady-state error", "&mdash;", "Determines whether an offset persists"],
         ["Settling time", "&mdash;", "Lock time; adaptation time"],
         ["Discrete-time effects", "Sampling and delay in the loop",
          "<b>Digital loops must include their own latency</b>"]]))
    s.append("""<div class="warn"><b>Latency inside a digital loop is a stability problem,
    not merely a performance one.</b> A digital adaptation loop that computes an error,
    pipelines it through several stages, and then applies a correction has inserted pure
    delay, which subtracts phase without reducing gain &mdash; exactly what destroys phase
    margin. The loop can oscillate even though every block in it is correct. The standard
    remedies are to reduce the loop gain (slower adaptation), to shorten the loop, or to
    compensate explicitly. <b>A model that applies the correction instantaneously will not
    show the instability</b>, so the pipeline delay must be in the model. This is one of
    the most common gaps between a working model and non-working hardware.</div>""")
    s.append(tab("Adaptation loops in a receiver and their interactions",
        ["Loop", "Controls", "Typical bandwidth", "Interacts with"],
        [["AGC", "Input amplitude", "Fast", "Everything downstream"],
         ["CDR", "Sampling phase", "Moderate", "<b>Equaliser &mdash; MM lock point depends on it</b>"],
         ["CTLE adaptation", "Analogue peaking", "Slow", "FFE"],
         ["FFE/DFE adaptation", "Tap weights", "Slow", "CDR"],
         ["Offset calibration", "Comparator offsets", "Very slow", "Slicer thresholds"],
         ["Interleaving calibration", "ADC mismatch", "Very slow", "All of the above"]]))
    s.append("""<div class="ms"><b>Six loops sharing one signal is the hardest part of a
    modern receiver, and it is a systems problem rather than a circuit one.</b> Each loop
    is stable alone; together they can hunt, lock to a wrong point, or fail to converge
    from certain initial conditions. The standard engineering response is <b>bandwidth
    separation</b> &mdash; giving each loop a rate an order of magnitude apart so that
    faster loops appear instantaneous to slower ones and slower loops appear constant to
    faster ones &mdash; plus a defined start-up sequence. <b>Both the separation and the
    sequence belong in the specification</b>, and verifying convergence from adverse
    initial conditions is a system-model task that no block-level testbench will
    perform.</div>""")
    return "\n".join(s)
