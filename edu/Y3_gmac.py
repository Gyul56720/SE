# -*- coding: utf-8 -*-
"""Volume III, Part Y3 -- The Ethernet MAC and its transceiver, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E, lines, find
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_gmac2():
    s = ['<h1 id="y3">Y3. The Ethernet MAC and Its Transceiver, Worked</h1>']
    s.append("""<p>The Gigabit MAC is the most-integrated communications block in
    existence and a good vehicle for the whole of this book: it has a datapath with hard
    real-time constraints, a protocol with a long tail of options, a clock-domain problem
    at its centre, and an interface stack whose names (GMII, RGMII, SGMII, QSGMII) encode
    a series of commercial compromises worth understanding.</p>""")

    s.append("<h2>Y3.1 Frame timing: the arithmetic that sets every buffer</h2>")
    rows = []
    for rate, name in ((10e6, "10BASE-T"), (100e6, "100BASE-TX"), (1e9, "1000BASE-T"),
                       (2.5e9, "2.5GBASE-T"), (10e9, "10GBASE-R"), (25e9, "25GBASE-R")):
        for size in (64, 1518):
            pass
        t64 = (64 + 8 + 12) * 8 / rate
        t1518 = (1518 + 8 + 12) * 8 / rate
        pps = 1 / t64
        rows.append([name, num(rate / 1e6, 5), num(t64 * 1e9, 4), num(t1518 * 1e6, 4),
                     num(pps / 1e6, 4), num(12 * 8 / rate * 1e9, 4)])
    s.append(sweep("Frame times, packet rates and the inter-packet gap",
        ["Rate", "Mbit/s", "Min frame + preamble + IPG (ns)",
         "Max frame + overhead (&micro;s)", "Max frames/s (M)", "IPG (ns)"], rows,
        "Computed from 8 bytes of preamble and start delimiter, 12 bytes of "
        "inter-packet gap, and the frame itself. <b>The fifth column is the number that "
        "sizes the control path</b>: at 25&nbsp;Gbit/s a new frame can start every "
        "33&nbsp;ns, so any per-frame decision &mdash; a lookup, a filter, a statistics "
        "update &mdash; must complete in that time or be pipelined."))
    s.append(ex("Why a MAC at 10&nbsp;Gbit/s cannot process one byte per cycle",
        "10&nbsp;Gbit/s line rate. The digital logic runs at 156.25&nbsp;MHz, which is "
        "the standard XGMII clock.",
        "Divide the bit rate by the clock to find the datapath width, then check what "
        "that width does to frame alignment.",
        [("Bits per clock", num(10e9 / 156.25e6, 4)),
         ("Datapath width", num(64) + " bits = 8 bytes"),
         ("Bytes per clock", num(8)),
         ("Minimum frame (64&nbsp;B) in clocks", num(64 / 8, 3)),
         ("Can a frame start mid-word?", "<b>yes &mdash; the IPG is 12 bytes, not a "
          "multiple of 8</b>"),
         ("Alignment cases the datapath must handle", num(8)),
         ("At 25&nbsp;Gbit/s on the same clock: width", num(25e9 / 156.25e6, 4)
          + " bits")],
        "<b>By designing the datapath for aligned frames.</b> Because the inter-packet "
        "gap is 12 bytes and the datapath is 8 wide, successive frames start at different "
        "byte lanes, so every parser, every CRC engine and every filter must handle all "
        "eight alignments. This is the single largest source of complexity in a wide "
        "Ethernet MAC and it is invisible in a specification that describes the protocol "
        "in bytes. <b>A block that assumes alignment will pass a test bench that sends "
        "one frame at a time and fail on back-to-back traffic at line rate</b> &mdash; "
        "which is the only traffic that matters."))

    s.append("<h2>Y3.2 The interface zoo, and what each trade is</h2>")
    rows = []
    for name, data_w, clk, rate, pins in (
            ("MII", 4, "25 MHz", "100 Mbit/s", 16),
            ("GMII", 8, "125 MHz", "1 Gbit/s", 24),
            ("RGMII", 4, "125 MHz DDR", "1 Gbit/s", 12),
            ("SGMII", 1, "625 MHz DDR serial", "1 Gbit/s", 4),
            ("QSGMII", 1, "5 Gbit/s serial", "4 &times; 1 Gbit/s", 4),
            ("XGMII", 32, "156.25 MHz DDR", "10 Gbit/s", 72),
            ("XFI / SFI", 1, "10.3125 Gbit/s", "10 Gbit/s", 4),
            ("USXGMII", 1, "10.3125 Gbit/s", "up to 10 Gbit/s, multi-port", 4)):
        rows.append([f"<b>{name}</b>", num(data_w), clk, rate, num(pins)])
    s.append(sweep("MAC-to-PHY interfaces: the same function, very different pin counts",
        ["Interface", "Data bits each way", "Clocking", "Carries", "Approx. pins"],
        rows,
        "The progression is one long trade of pins against signalling difficulty. "
        "<b>RGMII halves GMII's pins by clocking on both edges and pays with a "
        "notorious source-synchronous timing problem</b>: the specification's delay "
        "requirement is met either by the board, by the PHY or by the MAC, and "
        "mismatched assumptions between the three are the most common Gigabit Ethernet "
        "bring-up failure in existence."))
    s.append("""<div class="warn"><b>The RGMII delay question, stated once so it can be
    checked.</b> RGMII requires the clock to be delayed relative to the data by roughly
    1.5&ndash;2&nbsp;ns at the receiver. That delay may be provided by a long clock trace
    on the board, by the PHY's internal delay (enabled by strap or register), or by the
    MAC's output delay. <b>Exactly one of the three must provide it.</b> Zero gives a
    link that does not pass traffic or passes it only at 10&nbsp;Mbit/s; two gives the
    same symptom for the opposite reason. Because each is configured by a different party
    &mdash; layout, PHY firmware, RTL &mdash; nobody owns the question, and it is worth
    writing the answer into the integration guide of any MAC a design house ships, along
    with the register bits that set it.</div>""")

    s.append("<h2>Y3.3 64b/66b and the PCS: what the transcoding buys</h2>")
    s.append(derive("Why 64b/66b replaced 8b/10b", [
        ("8b/10b maps each byte to a 10-bit symbol chosen for DC balance and transition "
         "density.", "Original Gigabit encoding."),
        ("Overhead is 25&nbsp;%: a 1.25&nbsp;GBd line carries 1&nbsp;Gbit/s.",
         "10/8. <b>At 10&nbsp;Gbit/s that would demand 12.5&nbsp;GBd</b>, which the "
         "channel of the day could not support."),
        ("64b/66b prefixes two bits of sync header to 64 bits of scrambled payload.",
         "Overhead 3.1&nbsp;%."),
        ("Transition density comes from a self-synchronous scrambler "
         "(<i>x</i><sup>58</sup>+<i>x</i><sup>39</sup>+1), not from the code.",
         "<b>The sync header is the only guaranteed transition</b>, which is enough for "
         "a CDR with a long time constant and would not have been enough for the "
         "receivers of 1998."),
        ("The scrambler is self-synchronising, so a single bit error produces <b>three</b> "
         "errors at the descrambler.",
         "The error is fed back at the two tap positions. <b>This multiplication is the "
         "reason the FEC above it is symbol-oriented</b>, and it is a fact a link budget "
         "must account for."),
    ]))
    rows = []
    for enc, ov, rate in (("8b/10b", 10 / 8, 1e9), ("64b/66b", 66 / 64, 10e9),
                          ("64b/66b", 66 / 64, 25e9),
                          ("256b/257b + RS-FEC", 257 / 256 * 544 / 514, 50e9),
                          ("256b/257b + RS-FEC", 257 / 256 * 544 / 514, 100e9)):
        rows.append([enc, num(ov, 5), num(rate / 1e9, 4), num(rate * ov / 1e9, 5),
                     num((ov - 1) * 100, 3)])
    s.append(sweep("Line-rate consequences of the encoding choice",
        ["Encoding", "Expansion", "Payload Gbit/s", "Line GBd (NRZ)", "Overhead (%)"],
        rows,
        "The last two rows include the RS(544,514) FEC expansion, which is why "
        "100&nbsp;Gbit/s per lane runs at about 53.125&nbsp;GBd &mdash; the number "
        "Part&nbsp;X4's link budget used."))
    s.append("""<div class="ms"><b>Where the design-house opportunity is in this
    stack.</b> The PMA &mdash; serialiser, CDR, equaliser &mdash; is a hard macro and is
    not available to a soft-IP vendor. The MAC is a commodity: dozens of implementations
    exist, several of them open, and margins are thin. <b>The PCS and FEC sublayer between
    them is soft RTL, is algorithmically demanding, changes with every new standard, and
    has far fewer credible suppliers.</b> That combination &mdash; soft, hard, and
    changing &mdash; is the profile of a good product for a small house, and it is the
    reason this book's prior-art survey chose it. The specific opening at the time of
    writing is IEEE&nbsp;802.3dj's concatenated FEC, where the outer RS-KP4 is well
    understood and the inner code and its interleaving are new.</div>""")
    try:
        n = lines("ip", "verilog-ethernet")
        fls = [f for f in find("ip", "verilog-ethernet")
               if "baser" in f["경로"].lower() or "phy" in f["경로"].lower()]
        tot = sum(f["줄"] for f in fls)
        s.append(f"""<p>The code appendix contains <b>{n:,} lines</b> of an
        open-source Ethernet family, of which <b>{tot:,} lines</b> in {len(fls)} files
        are the BASE-R PCS itself &mdash; the 64b/66b encoder and decoder, the scrambler,
        the block synchroniser and the gearbox. Reading those files against the
        derivation above is the fastest way to see how a standard's prose becomes
        RTL.</p>""")
    except Exception as e:
        s.append(f'<div class="warn">verilog-ethernet not indexed: {E(str(e))}</div>')

    s.append("<h2>Y3.4 Flow control, buffering and the numbers a customer checks</h2>")
    rows = []
    for rate in (1e9, 10e9, 25e9, 100e9):
        for cable_m in (100,):
            prop = cable_m / 2e8
        rtt = 2 * prop
        bdp = rate * rtt / 8
        rows.append([num(rate / 1e9, 4), num(prop * 1e6, 3), num(rtt * 1e6, 3),
                     num(bdp / 1024, 4), num(math.ceil(bdp / 1518), 3)])
    s.append(sweep("Buffer needed to stop a sender in time, 100&nbsp;m of copper",
        ["Rate (Gbit/s)", "One-way propagation (&micro;s)", "Round trip (&micro;s)",
         "Bandwidth&ndash;delay product (kB)", "Max-size frames in flight"], rows,
        "This is the buffer a receiver must have <i>after</i> it decides to send a PAUSE "
        "frame, because frames already in flight will arrive regardless. Add the PAUSE "
        "frame's own transmission and the partner's reaction time and the requirement "
        "grows further. <b>The bandwidth&ndash;delay product appears for the third time "
        "in this book</b>, in its third guise; it is the same formula that sized the "
        "credit buffer and the PCIe completion buffer."))
    s.append(prob("A customer reports frame loss under burst traffic although your MAC "
                  "reports no errors and the link is not saturated on average. Where do "
                  "you look?",
        "&lsquo;Not saturated on average&rsquo; is the clue: averages hide bursts, and "
        "Ethernet traffic is bursty at every timescale. The sequence is: <b>read the "
        "drop counters and find out which stage dropped</b> &mdash; a MAC that cannot say "
        "whether a frame was dropped at the PHY interface, in the receive FIFO, or by the "
        "filter is much harder to defend, so this instrumentation is worth building. "
        "Then <b>check the receive FIFO's depth against the consumer's worst-case stall</b>, "
        "not its average service rate; if the consumer is a bus master, the stall is the "
        "interconnect's worst-case arbitration latency from Part&nbsp;X11, which is "
        "usually far longer than anyone estimated. Then <b>check whether flow control is "
        "enabled at both ends</b>, since PAUSE is negotiated and frequently disabled by "
        "default. Finally, <b>check the clock-rate mismatch</b>: two ends nominally at "
        "the same rate differ by up to 200&nbsp;ppm, so a receiver without rate "
        "adaptation slowly falls behind and drops a frame every few seconds &mdash; "
        "a distinctive signature worth recognising, because the loss rate is remarkably "
        "constant."))
    s.append(prob("Why does a MAC need an idle-insertion and idle-deletion mechanism at "
                  "all, given that both ends are specified at the same rate?",
        "Because &lsquo;the same rate&rsquo; means the same nominal rate within a "
        "tolerance, typically &plusmn;100&nbsp;ppm each, so the two can differ by "
        "200&nbsp;ppm &mdash; one part in five thousand. Over a continuous stream that is "
        "one extra or missing byte every 5000, which accumulates without bound. The "
        "mechanism uses the inter-packet gap as elastic: if the local clock is slower, "
        "delete an idle byte from the gap; if faster, insert one. The gap can be "
        "shortened to a floor (five bytes in the 10&nbsp;Gbit/s specifications, from "
        "twelve) which is what limits how much rate difference can be absorbed. "
        "<b>The consequence for a design is that the IPG a MAC sees on receive is not the "
        "IPG the far end transmitted</b>, so any logic that assumes twelve bytes is "
        "wrong, and any logic that uses IPG timing to infer anything about the far end is "
        "wrong twice. This elasticity, and its floor, is also why the FEC and PCS layers "
        "above must tolerate the alignment markers that periodically consume the same "
        "budget."))
    return "\n".join(s)
