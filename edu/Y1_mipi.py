# -*- coding: utf-8 -*-
"""Volume III, Part Y1 -- MIPI CSI-2 and DSI, worked as a deliverable."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E, find, lines
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_stack():
    b = []
    layers = [("Application / pixel source", "#eef2f7"),
              ("CSI-2 protocol: packets, ECC, CRC, virtual channels", "#fff"),
              ("Lane management: distribute / merge across N lanes", "#fff"),
              ("PHY protocol interface (PPI)", "#f7f4ee"),
              ("D-PHY or C-PHY: HS / LP states, clock", "#eef7f2")]
    y = 14
    for nm, c in layers:
        b.append(box(24, y, 330, 30, nm, None, 9, fill=c))
        y += 36
    b.append(txt(370, 32, "digital IP", 8))
    b.append(txt(370, 176, "analogue", 8))
    b.append(line(360, 14, 360, 122, w=1.2))
    b.append(line(360, 158, 360, 194, w=1.2, dash="4,3"))
    b.append(txt(189, 214, "The commercial boundary is the PPI: above it is soft RTL a "
                           "design house can sell,", 9, "middle"))
    b.append(txt(189, 228, "below it is a hard macro tied to one foundry process.",
                 9, "middle", 'font-style="italic"'))
    return svg(420, 236, "".join(b))


def ch_mipi2():
    s = ['<h1 id="y1">Y1. MIPI CSI-2 and DSI, Worked as a Deliverable</h1>']
    s.append("""<p>Every phone camera, most automotive cameras and a large fraction of
    embedded vision sensors speak CSI-2; every phone display and most embedded panels
    speak DSI. The two share a PHY and a packet structure, which is why a design house
    that builds one has most of the other. This part works the numbers a customer will
    ask for, and states where the answers come from.</p>""")
    s.append(fig(_f_stack(), "The CSI-2 / DSI stack, with the boundary that determines "
                             "what a soft-IP vendor can actually sell."))

    s.append("<h2>Y1.1 Bandwidth: from a sensor specification to a lane count</h2>")
    s.append("""<p>This is the first calculation a customer will do with your datasheet,
    so it must be the first one in it. It is also the calculation that decides whether
    your block is in the design at all.</p>""")
    rows = []
    for name, w, h, fps, bpp in (("1080p30", 1920, 1080, 30, 12),
                                 ("1080p60", 1920, 1080, 60, 12),
                                 ("4K30", 3840, 2160, 30, 12),
                                 ("4K60", 3840, 2160, 60, 12),
                                 ("8MP automotive 30", 3840, 2160, 30, 16),
                                 ("12MP still burst", 4000, 3000, 30, 14)):
        px = w * h * fps
        bits = px * bpp
        blank = 1.15                       # 15 % for blanking and packet overhead
        need = bits * blank
        for lanes in (2, 4):
            pass
        rows.append([name, num(px / 1e6, 4), num(bpp), num(bits / 1e9, 4),
                     num(need / 1e9, 4),
                     num(math.ceil(need / 4 / 2.5e9), 3),
                     num(math.ceil(need / 2.5e9), 3)])
    s.append(sweep("Required D-PHY bandwidth and lane count at 2.5&nbsp;Gbps per lane",
        ["Mode", "Mpixel/s", "bits/pixel", "Payload (Gbps)",
         "With 15&nbsp;% overhead (Gbps)", "Lanes at 4 Gbps/lane",
         "Lanes at 2.5 Gbps/lane"], rows,
        "The 15&nbsp;% allowance covers line blanking, packet headers and footers, and "
        "the low-power intervals between bursts. <b>It is an assumption and it belongs "
        "in the datasheet beside the number it produced</b>; a customer with a different "
        "blanking ratio will get a different lane count and should be able to see why."))
    s.append(ex("Why the overhead is not a fixed percentage",
        "A 1920&times;1080 frame, 12 bits per pixel, RAW12 packing. Each line is one "
        "long packet: 4 bytes of header, the payload, and 2 bytes of footer. Between "
        "lines the link may drop to low-power state and return, costing "
        "<i>T</i><sub>LPX</sub>&nbsp;+&nbsp;<i>T</i><sub>HS-PREPARE</sub>&nbsp;+&nbsp;"
        "<i>T</i><sub>HS-ZERO</sub>&nbsp;+&nbsp;sync, taken here as 300&nbsp;ns.",
        "Compute the per-line overhead in bytes and in time, then express it as a "
        "fraction. The fraction depends on the line length, which is why a single "
        "percentage cannot be right for every mode.",
        [("Payload bytes per line", num(int(1920 * 12 / 8))),
         ("Packet header + footer", num(6) + "&nbsp;bytes"),
         ("Packet overhead", num(6 / (1920 * 12 / 8) * 100, 3, "%")),
         ("Line payload time at 4 lanes &times; 2.5&nbsp;Gbps",
          num(1920 * 12 / (4 * 2.5e9) * 1e6, 4, "&micro;s")),
         ("LP transition cost per line", num(0.3, 3, "&micro;s")),
         ("Transition overhead",
          num(0.3 / (1920 * 12 / (4 * 2.5e9) * 1e6) * 100, 3, "%")),
         ("Total overhead for this mode",
          num((6 / (1920 * 12 / 8) + 0.3 / (1920 * 12 / (4 * 2.5e9) * 1e6)) * 100, 3, "%")),
         ("Same for a 320-pixel-wide line",
          num((6 / (320 * 12 / 8) + 0.3 / (320 * 12 / (4 * 2.5e9) * 1e6)) * 100, 3, "%"))],
        "<b>By quoting one efficiency figure for the whole product.</b> The overhead is "
        "dominated by a per-line <i>constant</i>, so efficiency collapses for short "
        "lines: a narrow region-of-interest readout &mdash; exactly what a machine-vision "
        "customer does &mdash; can spend more time in transitions than in data. The "
        "design response is to <b>stay in high-speed state across lines</b> when the "
        "blanking interval is short, which the specification permits and which many "
        "controllers do not implement. That feature is worth naming in a datasheet "
        "because a competitor's block that lacks it will lose the ROI benchmark."))

    s.append("<h2>Y1.2 The D-PHY state machine and its timing parameters</h2>")
    s.append(tab("D-PHY lane states and what each costs",
        ["State", "Electrical", "Purpose", "Entry cost"],
        [["LP-11 (Stop)", "Both lines high, 1.2&nbsp;V single-ended", "Idle",
          "&mdash;"],
         ["LP-01 / LP-00", "Low-power signalling", "Request and bridge states",
          "<i>T</i><sub>LPX</sub> per transition, min 50&nbsp;ns"],
         ["<b>HS-0 / HS-1</b>", "<b>200&nbsp;mV differential about a 200&nbsp;mV "
          "common mode</b>", "Data burst", "<i>T</i><sub>HS-PREPARE</sub> + "
          "<i>T</i><sub>HS-ZERO</sub> + sync, 150&ndash;300&nbsp;ns"],
         ["ULPS", "LP-00 held", "Ultra-low power; clock may stop",
          "<b><i>T</i><sub>WAKEUP</sub> &ge; 1&nbsp;ms</b> &mdash; a millisecond, not a "
          "microsecond"],
         ["Escape mode", "LP pulse-coded", "Trigger, LPDT side-channel",
          "Slow by design"]]))
    s.append("""<div class="warn"><b>The 1&nbsp;ms ULPS wake-up is a system-level number
    that routinely surprises integrators.</b> A design that powers the link down between
    frames to save energy cannot wake it in a line blanking interval; it can only wake it
    in a frame interval, and only if the frame rate leaves a millisecond spare.
    30&nbsp;fps gives 33&nbsp;ms per frame, so it fits; a 240&nbsp;fps burst mode does
    not. <b>Power state transitions have latencies that are three to five orders of
    magnitude apart</b> &mdash; 50&nbsp;ns for LPX, 1&nbsp;ms for ULPS &mdash; and a power
    management policy that treats them as interchangeable will either waste energy or
    drop frames.</div>""")
    ui = 1 / 2.5e9
    rows = []
    for tname, spec, unit in (("T_LPX", "&ge; 50", "ns"),
                              ("T_HS-PREPARE", "40 + 4&times;UI &hellip; 85 + 6&times;UI", "ns"),
                              ("T_HS-ZERO", "&ge; 145 + 10&times;UI", "ns"),
                              ("T_HS-TRAIL", "&ge; max(8&times;UI, 60 + 4&times;UI)", "ns"),
                              ("T_HS-EXIT", "&ge; 100", "ns"),
                              ("T_CLK-PRE", "&ge; 8&times;UI", "ns"),
                              ("T_CLK-POST", "&ge; 60 + 52&times;UI", "ns")):
        def ev(x):
            return x
        vals = []
        for br in (1.0e9, 1.5e9, 2.5e9):
            u = 1 / br * 1e9
            if tname == "T_LPX": v = 50
            elif tname == "T_HS-PREPARE": v = 40 + 4 * u
            elif tname == "T_HS-ZERO": v = 145 + 10 * u
            elif tname == "T_HS-TRAIL": v = max(8 * u, 60 + 4 * u)
            elif tname == "T_HS-EXIT": v = 100
            elif tname == "T_CLK-PRE": v = 8 * u
            else: v = 60 + 52 * u
            vals.append(num(v, 4))
        rows.append([f"<code>{tname}</code>", spec] + vals)
    s.append(sweep("D-PHY timing parameters evaluated at three lane rates (ns)",
        ["Parameter", "Specified as", "at 1.0&nbsp;Gbps", "at 1.5&nbsp;Gbps",
         "at 2.5&nbsp;Gbps"], rows,
        "<b>These values are computed from the formulae as written here and have not "
        "been checked against a current copy of the MIPI D-PHY specification</b>, which "
        "is a paid document this repository has not obtained. Treat the shape as correct "
        "and the constants as requiring confirmation before they enter an "
        "implementation."))
    s.append("""<div class="note"><b>On quoting a specification you have not read.</b>
    The table above is deliberately marked. A design house that builds a MIPI controller
    buys the specification; there is no substitute and no legitimate way around it.
    Writing formulae from secondary sources into RTL is how a block comes to fail
    interoperability at a plugfest, and the failure is expensive precisely because it is
    found late and in public. <b>The correct entry in a project plan is a line item for
    the specification and for membership, not an assumption that the numbers can be
    inferred.</b></div>""")

    s.append("<h2>Y1.3 Packet structure, ECC and CRC &mdash; and why both exist</h2>")
    s.append(derive("Why the header has ECC and the payload has CRC", [
        ("The short packet header is 4 bytes: data identifier, two word-count bytes, "
         "and one ECC byte.",
         "CSI-2 packet structure."),
        ("The ECC is a Hamming code over the preceding 24 bits, giving single-error "
         "correction and double-error detection.",
         "From Part X10's bound: 24 data bits need <i>r</i> = 5 for correction, plus one "
         "overall parity, which fits in the byte with two bits spare."),
        ("<b>A corrupted header is unrecoverable at any higher layer</b>, because the "
         "word count tells the receiver where the packet ends.",
         "A wrong length desynchronises the stream for the remainder of the frame. "
         "Correction, not detection, is therefore required here."),
        ("The payload carries a 16-bit CRC and <b>no correction</b>.",
         "A corrupted pixel is one bad pixel; the frame continues. Detection lets the "
         "application decide, and correction would cost far more for far less."),
        ("<b>The asymmetry is a design principle, not a quirk of this standard.</b>",
         "Spend correction where a failure is structural and detection where it is "
         "local. The same reasoning produced the parity-plus-reload answer for "
         "configuration memory in Part X10."),
    ]))
    s.append(prob("A customer reports occasional frame corruption that disappears when "
                  "they reduce the lane rate. Your ECC error counter is zero and your "
                  "CRC counter is non-zero. What does that tell you, and what would the "
                  "opposite pattern tell you?",
        "CRC errors without ECC errors mean the <i>payload</i> is being corrupted while "
        "the headers survive. That is a strong hint, because headers and payload travel "
        "the same wires but not the same way: headers occur at the start of a burst, just "
        "after the HS settle time, and are short; payload is long and continuous. "
        "Corruption that spares the header and hits the payload points at something that "
        "accumulates over a burst &mdash; <b>clock drift or an under-specified "
        "<i>T</i><sub>HS-SETTLE</sub> window that is fine for the first bytes and drifts "
        "later</b>, or an SSC/jitter interaction, or simply insufficient eye at the "
        "sampling point for long runs. The opposite pattern, ECC errors without CRC "
        "errors, would point at the <i>transition</i>: the receiver is mis-sampling the "
        "first bytes after leaving low-power state, which is the classic symptom of an "
        "incorrect settle-time programming or of a PHY that reports ready too early. "
        "<b>The instrumentation that makes this diagnosis possible &mdash; separate, "
        "readable counters for header and payload errors, with the ability to capture "
        "the first failing packet &mdash; is a feature to design in, not a debug hack; "
        "it is also a strong differentiator in a datasheet.</b>"))

    s.append("<h2>Y1.4 What the repository's real CSI-2 source shows</h2>")
    try:
        n1 = lines("ip", "circuitvalley")
        files = find("ip", "circuitvalley")
        s.append(f"""<p>The code appendix of this book reproduces
        <b>{n1:,} lines</b> across {len(files)} files of a working MIPI CSI-2 receiver
        written for FPGA fabric. It is worth reading for one reason above all: it shows
        how much of the block is <i>not</i> the protocol. Word alignment, lane
        de-skew, the byte-to-pixel unpacker and the clock-domain crossing to the pixel
        clock take more code than the packet decoder.</p>""")
        rows = []
        for f in sorted(files, key=lambda x: -x["줄"])[:12]:
            rows.append([f"<code>{E(f['경로'].split('/')[-1])}</code>", num(f["줄"])])
        s.append(sweep("The twelve largest files of the CSI-2 receiver in the corpus",
            ["File", "Lines"], rows,
            "Counted from the indexed corpus at build time."))
    except Exception as e:
        s.append(f'<div class="warn">CSI-2 source not found in the corpus index: '
                 f'{E(str(e))}</div>')
    s.append("""<div class="ms"><b>What a design house adds on top of an open-source
    receiver like this one.</b> The open block demonstrates the datapath. What it does not
    contain is what a customer pays for: a register map with a defined reset state and an
    IP-XACT description; error counters and an interrupt controller; support for more than
    one virtual channel and for the data types the customer's sensor actually emits;
    a verification environment with the protocol checkers and a compliance test list;
    synthesis and timing closure at a specified frequency in a named process with reports;
    lint and CDC sign-off; and documentation that lets an integrator finish without
    calling. <b>Each of those is weeks of work, and together they are the product.</b>
    A design house that believes the RTL is the product will price the work at a fraction
    of its cost and deliver something a customer cannot integrate.</div>""")
    rows = []
    for item, weeks in (("Specification study and register map", 3),
                        ("RTL: protocol layer", 4),
                        ("RTL: lane management and de-skew", 3),
                        ("RTL: PPI adaptation and CDC", 3),
                        ("C reference model for the packet layer", 2),
                        ("Verification environment and checkers", 6),
                        ("Directed and random test suites", 5),
                        ("Lint, CDC and synthesis sign-off", 3),
                        ("Timing closure at target frequency", 2),
                        ("IP-XACT packaging and integration guide", 2),
                        ("Documentation and datasheet", 3),
                        ("Customer support allowance, first year", 6)):
        rows.append([item, num(weeks), num(weeks / 52 * 100, 3)])
    tot = 3+4+3+3+2+6+5+3+2+2+3+6
    s.append(sweep("An honest effort estimate for a sellable CSI-2 receiver, one engineer",
        ["Activity", "Weeks", "Share of a person-year (%)"], rows,
        f"Total {tot} weeks &mdash; about {tot/52:.1f} person-years. "
        "<b>Verification and everything downstream of RTL is {0:.0f}&nbsp;% of it.</b> "
        "An estimate that counts only the RTL rows produces {1} weeks and is the reason "
        "first-time IP vendors run out of money.".format(
            (6+5+3+2+2+3+6)/tot*100, 4+3+3)))
    return "\n".join(s)
