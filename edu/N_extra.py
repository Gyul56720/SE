# -*- coding: utf-8 -*-
"""Volume I, Part N -- Asynchronous design, physical design, statistics, photonics."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def ch_async():
    s = ['<h1 id="n1">N1. Asynchronous and Globally Asynchronous Design</h1>']
    s.append("""<p>Synchronous design &mdash; one clock, one timing constraint &mdash; is
    overwhelmingly dominant because it makes timing analysis tractable. Asynchronous
    techniques remain relevant in three specific places, and knowing which is which
    prevents both over-application and blind avoidance.</p>""")
    s.append(tab("Asynchronous styles",
        ["Style", "Timing assumption", "Property", "Practical use"],
        [["Bundled data", "Matched delay line models the logic",
          "Simple, small", "Local handshakes, self-timed SRAM"],
         ["<b>Dual-rail / QDI</b>", "<b>None (delay insensitive)</b>",
          "Robust to any delay; ~2&times; area",
          "Extreme reliability, some security uses"],
         ["Micropipelines", "Bundled", "Elastic pipelines", "&mdash;"],
         ["<b>GALS</b>", "Synchronous islands, async between",
          "<b>Avoids a global clock tree</b>",
          "<b>The practically important case</b> &mdash; multi-domain SoCs"],
         ["Self-timed memory", "Internal", "Hidden from the user", "Nearly all SRAM"]]))
    s.append("""<div class="ms"><b>GALS is what most engineers actually encounter, usually
    without the name.</b> Any SoC with several clock domains connected by asynchronous
    FIFOs is globally asynchronous and locally synchronous. Framing it that way is useful
    because it makes the design rules explicit: each island has its own timing closure,
    and every boundary between islands is a CDC problem requiring one of the techniques of
    Chapter C3. <b>The failure mode of an undisciplined multi-domain design is not a
    timing violation but an intermittent data corruption</b>, which is far harder to
    diagnose &mdash; which is why the boundaries must be enumerated and checked by a
    tool rather than by inspection.</div>""")
    s.append(tab("Where fully asynchronous logic is genuinely used",
        ["Application", "Reason"],
        [["SRAM internal timing", "Self-timed sense amplifier control is faster than a clock"],
         ["Security", "No clock to glitch; power profile is less data-correlated"],
         ["Ultra-low power / energy harvesting", "No clock power when idle"],
         ["Very wide dynamic voltage range", "Works at whatever speed the supply allows"],
         ["Reliability at extremes", "Delay-insensitive circuits tolerate huge variation"]]))
    s.append("""<div class="warn"><b>The barrier to asynchronous design is tooling, not
    theory.</b> Standard synthesis, static timing analysis, scan insertion and equivalence
    checking all assume a clock. An asynchronous block therefore needs custom flows, and
    &mdash; decisively for an IP vendor &mdash; the customer must be able to integrate,
    verify and test it in <i>their</i> flow. <b>An asynchronous block is usually
    unsellable as RTL for this reason alone</b>, regardless of its merits. Where the
    technique is used commercially it is nearly always hidden inside a hard macro with a
    synchronous interface.</div>""")
    return "\n".join(s)


def ch_physdes():
    s = ['<h1 id="n2">N2. Physical Design in More Depth</h1>']
    s.append(tab("Placement and routing concerns",
        ["Concern", "Cause", "Symptom", "Remedy"],
        [["<b>Congestion</b>", "More nets than routing tracks in a region",
          "Routing failures, detours, timing loss",
          "Spread cells, reduce utilisation, restructure logic"],
         ["Timing/congestion conflict", "Timing wants cells close; routing wants them apart",
          "&mdash;", "Iterate; sometimes an architectural change is needed"],
         ["Antenna effect", "Charge accumulation on a long metal segment during etch",
          "Gate oxide damage", "Diode insertion, layer jumping"],
         ["Crosstalk delay and noise", "Coupling between adjacent nets",
          "Timing variation, glitches", "Spacing, shielding, net ordering"],
         ["Electromigration", "Current density", "Long-term failure", "Wire widening, via arrays"],
         ["IR drop", "Grid resistance", "Local slowdown", "Grid strengthening, decap"],
         ["<b>Hold violations after CTS</b>", "Skew changes after the clock tree is built",
          "&mdash;", "Buffer insertion; usually many thousands"]]))
    s.append("""<div class="ms"><b>Utilisation is the number that governs the whole
    back-end schedule.</b> Utilisation &mdash; the fraction of core area occupied by cells
    &mdash; trades area against routability. Below roughly 60% a design routes easily and
    wastes area; above roughly 80% congestion begins to dominate and each iteration
    becomes slower and less predictable. A block delivered with a recommended utilisation
    lets the customer floorplan correctly the first time. <b>Omitting it is one of the
    common causes of "the IP does not meet timing in our flow"</b>, because the customer
    packed it at 85% while the vendor characterised it at 65%.</div>""")
    s.append(tab("Standard cell library concepts",
        ["Concept", "Meaning", "Selection consequence"],
        [["Track height (e.g. 7.5T, 9T)", "Cell height in routing tracks",
          "Taller cells are faster and larger"],
         ["Drive strength (X1, X2, X4&hellip;)", "Transistor width multiplier",
          "Higher drive for larger loads"],
         ["Multi-<i>V<sub>TH</sub></i> (LVT/SVT/HVT)", "Threshold variants",
          "<b>Leakage versus speed, per cell</b>"],
         ["Characterisation corner", "PVT point of the timing data",
          "Must match the sign-off corner"],
         ["NLDM / CCS", "Delay model fidelity", "CCS is needed at advanced nodes"],
         ["Engineering change order cells", "Spare gates scattered in the layout",
          "<b>Enable metal-only fixes after tape-out</b>"]]))
    s.append("""<div class="ms"><b>Spare cells are cheap insurance that is often omitted
    and then badly missed.</b> Scattering a small percentage of unused gates across the
    floorplan allows a post-silicon logic fix to be implemented by changing only the metal
    masks, which costs a fraction of a full mask set and weeks rather than months. The
    area cost is typically one or two percent. <b>The decision is made at floorplan time
    and cannot be revisited</b>, which is why it belongs on the checklist of Chapter
    W1 rather than being left to back-end judgement.</div>""")
    return "\n".join(s)


def ch_stats():
    s = ['<h1 id="n3">N3. Statistics for Silicon</h1>']
    s.append(tab("Variation sources",
        ["Source", "Scale", "Correlation", "Handled by"],
        [["Lot to lot", "Global", "Fully correlated on a die", "Process corners"],
         ["Wafer to wafer", "Global", "Correlated", "Corners"],
         ["Die to die", "Global", "Correlated", "Corners"],
         ["<b>Within die, systematic</b>", "Local", "Position dependent",
          "Layout-dependent effects, proximity rules"],
         ["<b>Within die, random</b>", "Local", "<b>Uncorrelated</b>",
          "<b>OCV / AOCV / POCV derating</b>"],
         ["Random dopant fluctuation", "Per device", "None",
          "&sigma; &prop; 1/&radic;(<i>WL</i>) &mdash; <b>matters most for small devices</b>"]]))
    s.append("""<div class="ms"><b>The distinction between correlated and uncorrelated
    variation is what makes modern timing analysis tractable.</b> If every device on a path
    varied independently, a long path would average out and show <i>less</i> relative
    variation than a short one &mdash; which is exactly what statistical on-chip variation
    (POCV) captures, and why it recovers pessimism that flat derating throws away. Flat OCV
    applies the same percentage to every path regardless of depth, which over-penalises
    long paths and under-penalises short ones (making hold analysis optimistic). <b>The
    statistics are not a refinement; using the wrong model can make a design that signs off
    fail in silicon.</b></div>""")
    s.append(tab("Statistical concepts used in characterisation",
        ["Concept", "Use"],
        [["Mean, &sigma;, &plusmn;3&sigma;", "Basic spread; 3&sigma; &asymp; 99.73%"],
         ["<b>6&sigma; design</b>", "Memory bit cells &mdash; billions of instances require "
          "extreme tails to be safe"],
         ["<b>Importance sampling</b>", "Simulating a 6&sigma; failure directly is infeasible; "
          "bias the sampling and correct"],
         ["Monte Carlo", "General variation analysis"],
         ["Design of experiments", "Efficient exploration of many parameters"],
         ["Regression / response surface", "Build a fast surrogate model"],
         ["Confidence intervals", "<b>A measurement without one is an anecdote</b>"],
         ["Process capability <i>C<sub>pk</sub></i>", "Manufacturing margin"]]))
    s.append("""<div class="ms"><b>Memory bit cells illustrate why tail statistics matter
    so much.</b> A 100&nbsp;Mbit memory contains 10<sup>8</sup> cells; for the chip to
    yield, the per-cell failure probability must be well below 10<sup>&minus;8</sup>,
    which corresponds to roughly 5.7&sigma;. Plain Monte Carlo would need on the order of
    10<sup>9</sup> simulations to see such an event, so importance sampling &mdash;
    deliberately sampling the tail and reweighting &mdash; is mandatory. <b>This is why
    memory design is a specialised discipline</b>, and why memories come from compilers
    rather than being drawn by hand.</div>""")
    return "\n".join(s)


def ch_optics():
    s = ['<h1 id="n4">N4. Optical Links and Photonics</h1>']
    s.append("""<p>Beyond a few metres of copper, electrical links become impractical and
    the industry switches to optics. The digital blocks on either side &mdash; the FEC, the
    PCS, the DSP &mdash; are the same kind of IP discussed throughout this book, which is
    why the domain deserves a chapter.</p>""")
    s.append(tab("Optical link components",
        ["Component", "Function", "Impairment introduced"],
        [["Laser (DFB, VCSEL)", "Source", "RIN, chirp, temperature drift"],
         ["Modulator (direct, EML, MZM)", "Impress data on light",
          "Extinction ratio, chirp, nonlinearity"],
         ["Fibre (SMF, MMF)", "Transport",
          "<b>Chromatic dispersion, modal dispersion, attenuation, nonlinearity</b>"],
         ["Photodiode (PIN, APD)", "Detect", "Shot noise; APD adds excess noise"],
         ["<b>TIA</b>", "Current to voltage", "Noise; bandwidth"],
         ["Coherent receiver", "Recover amplitude and phase",
          "Requires a local oscillator and heavy DSP"]]))
    s.append(tab("Modulation and detection schemes",
        ["Scheme", "Detection", "Reach", "DSP required"],
        [["<b>NRZ / PAM4 IM-DD</b>", "Direct (intensity only)", "&le; 10 km",
          "Equalisation, FEC &mdash; <b>802.3 territory</b>"],
         ["<b>Coherent QPSK / 16-QAM</b>", "Coherent (amplitude and phase)", "Long haul",
          "<b>Very heavy: CD and PMD compensation, carrier recovery</b>"],
         ["Probabilistic shaping", "Coherent", "Long haul", "Shaping encoder/decoder"]]))
    s.append("""<div class="ms"><b>Chromatic dispersion compensation is where photonics
    becomes a large digital problem.</b> Different wavelengths travel at slightly different
    speeds in fibre, so a pulse spreads over distance &mdash; and over hundreds of
    kilometres the spread reaches hundreds of symbol periods. Compensating it optically
    requires dispersion-compensating fibre; compensating it digitally requires a very long
    filter, which is implemented in the frequency domain because a direct FIR of that
    length is uneconomical. <b>The result is that a coherent optical receiver contains one
    of the largest FFT blocks in commercial electronics</b>, and the chapter on multirate
    and transform architectures applies directly. This is an unusually clear case of a
    physical-layer impairment creating a large, well-specified digital IP
    opportunity.</div>""")
    s.append(tab("Co-packaged and silicon photonics",
        ["Development", "Motivation", "Consequence"],
        [["Pluggable optics", "Serviceability", "Electrical link to the module costs power"],
         ["<b>Co-packaged optics</b>", "Remove the electrical link",
          "<b>Large power saving</b>; serviceability and thermal challenges"],
         ["Silicon photonics", "CMOS-compatible fabrication", "Integration density, cost"],
         ["Optical I/O for chiplets", "Bandwidth density", "Research to early product"]]))
    return "\n".join(s)
