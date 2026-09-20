# -*- coding: utf-8 -*-
"""Volume III -- Interface IP in practice: MIPI CSI/DSI, PCIe, GMAC."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line, poly


def _f_mipi():
    b = []
    lay = [("Application", 40, "pixel / command source"),
           ("CSI-2 / DSI protocol", 96, "packets, ECC, CRC, virtual channels"),
           ("Lane management", 152, "distribution, merge, skew"),
           ("PPI", 208, "PHY–Protocol Interface"),
           ("D-PHY / C-PHY", 252, "HS + LP signalling (hard macro)")]
    for n, y, sub in lay:
        fill = "#fbeaea" if "PHY" in n and "PPI" not in n else "#eef2f7"
        b.append(box(60, y, 300, 40, n, sub, 9, fill))
        if y > 40:
            b.append(arr(210, y - 16, 210, y))
    b.append(txt(390, 120, "Everything above the PPI", 9))
    b.append(txt(390, 138, "is synthesisable RTL —", 9))
    b.append(txt(390, 156, "the sellable boundary.", 9, "start", 'font-weight="bold"'))
    b.append(txt(390, 262, "The PHY is a hard macro", 9))
    b.append(txt(390, 280, "tied to the process.", 9))
    return svg(600, 310, "".join(b))


def _f_pcie():
    b = []
    lay = [("Software / application", 34, ""),
           ("Transaction layer (TLP)", 84, "ordering, credits, TLP assembly"),
           ("Data link layer (DLLP)", 134, "sequence numbers, ACK/NAK, replay"),
           ("Physical logical", 184, "encoding, scrambling, lane management, LTSSM"),
           ("Physical electrical (SerDes)", 234, "hard macro")]
    for n, y, sub in lay:
        fill = "#fbeaea" if "electrical" in n else "#eef2f7"
        b.append(box(45, y, 330, 40, n, sub, 9, fill))
        if y > 34:
            b.append(arr(210, y - 10, 210, y))
    b.append(txt(400, 150, "Gen3–5: 128b/130b", 9))
    b.append(txt(400, 168, "Gen6: PAM4 + FLIT + FEC", 9, "start", 'font-weight="bold"'))
    b.append(txt(400, 200, "The LTSSM is the", 9))
    b.append(txt(400, 218, "largest state machine", 9))
    b.append(txt(400, 236, "in the whole block.", 9))
    return svg(610, 290, "".join(b))


def ch_mipi():
    s = ['<h1 id="p1">P1. MIPI CSI-2 and DSI &mdash; Camera and Display Interfaces</h1>']
    s.append("""<div class="kvbar"><b>Domain</b> mobile, automotive, industrial imaging
    &nbsp;&bull;&nbsp; <b>Layers</b> application / protocol / lane management / PPI / PHY
    &nbsp;&bull;&nbsp; <b>Sellable part</b> everything above the PPI</div>""")
    s.append(fig(_f_mipi(), "MIPI CSI-2 / DSI layering. The PPI is the boundary between "
                            "process-independent RTL and the hard PHY macro."))

    s.append("<h2>P1.1 What the two specifications are</h2>")
    s.append(tab("CSI-2 and DSI compared",
        ["", "CSI-2 (camera)", "DSI / DSI-2 (display)"],
        [["Direction", "Sensor &rarr; host (mostly unidirectional)",
          "Host &rarr; panel, with a low-speed return path"],
         ["Payload", "Pixel data packets", "Pixel data <b>and</b> command packets (DCS)"],
         ["Modes", "Continuous or non-continuous clock",
          "<b>Video mode</b> (streaming) and <b>command mode</b> (panel with own memory)"],
         ["Framing", "Frame Start/End, Line Start/End short packets",
          "Similar, plus timing packets (HSA/HBP/HFP)"],
         ["Typical lanes", "1&ndash;4 (D-PHY), 1&ndash;3 trios (C-PHY)", "1&ndash;4"],
         ["Error handling", "ECC on the header, CRC on the payload", "Same"],
         ["Virtual channels", "Up to 4 (16 in later versions)", "Up to 4"]]))
    s.append("""<div class="ms"><b>The single most useful structural fact is that the
    packet header carries a Hamming ECC and the payload carries a CRC, and they do
    different jobs.</b> The header ECC corrects one bit and detects two, because a
    corrupted header would mis-frame the entire packet and lose synchronisation &mdash;
    a catastrophic, self-propagating failure. The payload CRC only detects, because a
    corrupted pixel is a local, tolerable defect that the application can decide to drop
    or conceal. <b>The protection strength is matched to the consequence of failure</b>,
    which is a design principle worth carrying to other protocols: ask what a corruption
    of each field actually costs before choosing how to protect it.</div>""")

    s.append("<h2>P1.2 D-PHY and C-PHY, and what they force on the digital side</h2>")
    s.append(tab("PHY options",
        ["", "D-PHY", "C-PHY"],
        [["Signalling", "Differential pairs; separate clock lane",
          "<b>Three-wire trios</b>, embedded clock"],
         ["Symbol", "1 bit per lane per UI", "<b>2.28 bits per symbol per trio</b>"],
         ["Wires for a given throughput", "More", "Fewer"],
         ["Low-power mode", "<b>LP single-ended signalling</b> on the same wires",
          "Same concept"],
         ["Digital consequence", "Straightforward byte alignment",
          "<b>Symbol-to-bit mapping and 7-to-16 conversion in the RTL</b>"],
         ["Deskew", "Per-lane, against the clock lane", "Per-trio"]]))
    s.append("""<div class="warn"><b>The high-speed / low-power mode transition is where
    most MIPI bring-up problems occur.</b> The same physical wires carry differential
    high-speed data and single-ended low-power signalling, and the link alternates between
    them constantly &mdash; LP-11 idle, an LP-01/LP-00 request sequence, then HS burst,
    then back. The digital side must drive and observe the PPI handshake with exact
    timing, and the timing parameters (T<sub>LPX</sub>, T<sub>HS-PREPARE</sub>,
    T<sub>HS-ZERO</sub>, T<sub>HS-TRAIL</sub>, T<sub>EOT</sub>) are specified as ranges
    that depend on the bit rate. <b>An implementation that hard-codes these for one rate
    will fail at another</b>, so they must be parameters computed from the configured
    rate, and the verification plan must sweep them.</div>""")

    s.append("<h2>P1.3 What to build, block by block</h2>")
    s.append(tab("CSI-2 receiver: the blocks and what each must do",
        ["Block", "Function", "Design notes"],
        [["PPI interface", "Byte-aligned data and valid per lane from the PHY",
          "Clocked by the PHY byte clock; first CDC boundary"],
         ["<b>Lane aligner / deskew</b>", "Align lanes to a common byte boundary",
          "<b>Uses the sync sequence (0xB8)</b>; must tolerate inter-lane skew"],
         ["Lane merger", "Interleave <i>N</i> lanes into one byte stream",
          "Byte <i>n</i> of the stream came from lane <i>n</i> mod <i>N</i>"],
         ["Packet parser", "Separate short and long packets, extract data type and VC",
          "Short packets carry framing; long packets carry pixels"],
         ["<b>Header ECC</b>", "Correct one bit in the 24-bit header",
          "Hamming; <b>the correction must actually be applied, not just flagged</b>"],
         ["<b>Payload CRC-16</b>", "Detect payload corruption",
          "Polynomial 0x1021, specified initial value &mdash; check against the spec"],
         ["Pixel unpacker", "RAW8/10/12/14, RGB888/565, YUV422 &rarr; aligned pixels",
          "<b>Bit-packing is the fiddliest part</b>; RAW10 packs 4 pixels in 5 bytes"],
         ["Line buffer / output", "Present pixels on a system interface",
          "Usually AXI-Stream with a side channel for VC, data type, line/frame markers"],
         ["Error reporting", "ECC corrected/uncorrected, CRC fail, framing errors",
          "Sticky status registers with defined clearing"],
         ["Register file", "Configuration and status", "Generated from one source"]]))
    s.append("""<div class="ms"><b>The pixel unpacker is where most of the verification
    effort actually goes, and it is worth planning for.</b> RAW10, for example, packs four
    10-bit pixels into five bytes: four bytes of most-significant bits followed by one
    byte containing the four pairs of least-significant bits. RAW12 packs two pixels in
    three bytes. Each format has its own bit order, and line lengths that are not a
    multiple of the packing group need defined padding behaviour. <b>The combinations
    (format &times; lane count &times; line length modulo the group size) multiply
    quickly</b>, which makes this an ideal target for constrained-random verification
    against a golden model &mdash; and a poor one for directed tests.</div>""")

    s.append("<h2>P1.4 Parameters, verification and deliverables</h2>")
    s.append(tab("Parameters an integrator will ask for",
        ["Parameter", "Typical range", "Constraint"],
        [["Number of lanes", "1, 2, 4 (D-PHY)", "Must not exceed the PHY's lanes"],
         ["Bit rate per lane", "80 Mb/s &ndash; 4.5 Gb/s (D-PHY 2.x)",
          "<b>Sets the LP/HS timing parameters</b>"],
         ["Supported data types", "RAW8/10/12/14, RGB, YUV, user-defined",
          "Each adds unpacker logic"],
         ["Virtual channels", "1&ndash;4 or 1&ndash;16", "Affects buffering and routing"],
         ["Output width", "Pixels per clock", "Must divide the packing group cleanly"],
         ["Line buffer depth", "&mdash;", "System back-pressure tolerance"],
         ["Clock mode", "Continuous / non-continuous", "Affects the PPI state machine"]]))
    s.append(tab("Verification plan for a CSI-2 receiver",
        ["Area", "Method", "Oracle"],
        [["Packet framing", "Directed + random packet sequences", "Golden model"],
         ["<b>ECC correction</b>", "<b>Inject one- and two-bit header errors</b>",
          "Corrected / detected / mis-corrected must be counted separately"],
         ["CRC", "Inject payload errors", "Detection rate"],
         ["Unpacking", "Random formats, widths, line lengths", "<b>Golden model, bit-exact</b>"],
         ["Lane skew", "Sweep skew up to the specification limit", "Correct alignment"],
         ["LP/HS transitions", "Sweep bit rates and timing corners", "PPI protocol checker"],
         ["Back-pressure", "Randomised downstream stalls", "No data loss, no deadlock"],
         ["Error injection", "Truncated packets, illegal data types", "Defined error reporting"]]))
    s.append("""<div class="note"><b>Deliverable note.</b> Because the PHY is a third-party
    hard macro, the example design must show the connection at the PPI and state the
    required PHY configuration explicitly. Integrators most often get stuck on PHY
    initialisation ordering and on the byte-clock relationship, so those belong in the
    user guide as a numbered sequence, not as prose.</div>""")
    return "\n".join(s)


def ch_pcie():
    s = ['<h1 id="p2">P2. PCI Express, Generations 3 to 6</h1>']
    s.append("""<div class="kvbar"><b>Domain</b> everything from SSDs to accelerators
    &nbsp;&bull;&nbsp; <b>Layers</b> transaction / data link / physical logical / physical
    electrical &nbsp;&bull;&nbsp; <b>Sellable part</b> controller and physical-logical
    layer; the SerDes is a hard macro</div>""")
    s.append(fig(_f_pcie(), "PCIe layering. Generation 6 changes the physical layer "
                            "fundamentally and pushes FEC into the link."))

    s.append("<h2>P2.1 What changes between generations</h2>")
    s.append(tab("PCIe generations",
        ["Gen", "Rate per lane", "Encoding", "Key addition", "Digital consequence"],
        [["1.0", "2.5 GT/s", "8b/10b", "&mdash;", "20% encoding overhead"],
         ["2.0", "5.0 GT/s", "8b/10b", "&mdash;", "&mdash;"],
         ["<b>3.0</b>", "8.0 GT/s", "<b>128b/130b</b> + scrambling",
          "Equalisation negotiation", "<b>Overhead drops to 1.5%</b>; link training grows"],
         ["4.0", "16.0 GT/s", "128b/130b", "Tighter channel budget",
          "Retimers become common"],
         ["5.0", "32.0 GT/s", "128b/130b", "&mdash;",
          "Equalisation and margining become critical"],
         ["<b>6.0</b>", "64.0 GT/s", "<b>PAM4</b>, FLIT mode",
          "<b>Mandatory lightweight FEC + CRC</b>",
          "<b>Fixed-size FLITs replace variable TLP framing; FEC in the datapath</b>"],
         ["7.0", "128 GT/s", "PAM4", "&mdash;", "Further channel and FEC work"]]))
    s.append("""<div class="ms"><b>Generation 6 is the discontinuity, and it changes the
    controller, not only the PHY.</b> PAM4 raises the raw error rate to a level where an
    uncorrected link would not meet the reliability target, so FEC becomes mandatory.
    Because FEC operates on fixed-size blocks, the variable-length TLP framing of earlier
    generations no longer fits, and the link moves to fixed 256-byte <b>FLITs</b> carrying
    TLPs, DLLPs, CRC and FEC parity. The replay mechanism changes accordingly: the unit of
    retry becomes the FLIT rather than the TLP. <b>An existing Gen5 controller cannot be
    rate-scaled into a Gen6 one</b> &mdash; the data link layer is structurally different,
    which is precisely why it represented a large IP opportunity.</div>""")

    s.append("<h2>P2.2 The layers in implementation terms</h2>")
    s.append(tab("What each layer must implement",
        ["Layer", "Responsibilities", "Hardest part"],
        [["<b>Transaction</b>",
          "TLP assembly and decode; address routing; <b>ordering rules</b>; "
          "credit-based flow control; completion tracking; tag management",
          "<b>The ordering rules</b> (posted / non-posted / completion) and their "
          "interaction with relaxed ordering and ID-based ordering"],
         ["<b>Data link</b>",
          "Sequence numbers; LCRC; ACK/NAK; <b>replay buffer</b>; DLLP generation; "
          "flow-control credit initialisation",
          "Replay buffer sizing versus round-trip latency; credit accounting"],
         ["<b>Physical logical</b>",
          "Scrambling; 128b/130b (or FLIT) framing; lane-to-lane deskew; lane reversal "
          "and polarity inversion; <b>LTSSM</b>; equalisation negotiation; margining",
          "<b>The LTSSM</b> &mdash; a large hierarchical state machine with many "
          "timeouts and substates"],
         ["Physical electrical", "SerDes", "Hard macro &mdash; not RTL"]]))
    s.append("""<div class="warn"><b>Ordering rules are the classic source of subtle PCIe
    bugs, and they cannot be inferred from waveforms.</b> A posted write must not pass a
    previous posted write; a completion must not pass a posted write; a read may be
    reordered relative to another read. Violations do not produce obviously wrong data
    &mdash; they produce a coherence failure at the software level, days later, under
    load. <b>The only reliable approach is to encode the rules as assertions and check
    them continuously</b>, and to build the scoreboard with per-category queues in the way
    described in Chapter H1.4. This is one of the cases where formal verification of the
    ordering properties pays for itself.</div>""")

    s.append("<h2>P2.3 The LTSSM</h2>")
    s.append(tab("Link Training and Status State Machine &mdash; principal states",
        ["State", "Purpose", "Implementation note"],
        [["Detect", "Detect a receiver on the lanes", "Uses electrical idle detection"],
         ["Polling", "Establish bit and symbol lock; exchange TS1/TS2 ordered sets",
          "Lane polarity and reversal are resolved here"],
         ["<b>Configuration</b>", "Link and lane numbering; width negotiation; deskew",
          "<b>Where multi-lane bring-up problems appear</b>"],
         ["L0", "Normal operation", "&mdash;"],
         ["<b>Recovery</b>", "Re-train after an error or a speed change",
          "<b>Equalisation for Gen3+ happens here</b>; substates are numerous"],
         ["L0s / L1 / L2", "Low-power states", "Entry and exit latency budgets"],
         ["Disabled / Loopback / Hot Reset", "Test and control", "Required for compliance"]]))
    s.append("""<div class="ms"><b>The LTSSM is the best formal-verification target in the
    whole block.</b> It is control-dominated, has a bounded state space, and its required
    properties are stated in the specification as reachability and timeout conditions:
    every state must be reachable, no state may be entered from an illegal predecessor,
    every timeout must be able to fire, and the machine must always return to a defined
    state after an error. Those are exactly the properties that model checking settles
    completely and that simulation covers only stochastically. <b>A supplier who can show
    formal proofs of LTSSM properties has a concrete, checkable differentiator.</b></div>""")

    s.append("<h2>P2.4 Parameters, compliance and deliverables</h2>")
    s.append(tab("Controller parameters",
        ["Parameter", "Range", "Effect"],
        [["Link width", "x1, x2, x4, x8, x16", "Datapath width and deskew logic"],
         ["Maximum speed", "Gen1&ndash;Gen6", "PHY choice; equalisation and FEC logic"],
         ["Datapath width", "64/128/256/512 bit", "<b>Width &times; clock must exceed the line rate</b>"],
         ["Max payload size", "128&ndash;4096 B", "Buffer sizing"],
         ["Number of tags / outstanding reads", "&mdash;", "<b>Throughput at high latency</b>"],
         ["Replay buffer depth", "&mdash;", "Must cover the worst-case round trip"],
         ["Virtual channels", "1&ndash;8", "QoS; arbitration complexity"],
         ["Functions / SR-IOV", "&mdash;", "Configuration space replication"]]))
    s.append("""<div class="ms"><b>Outstanding-read capacity, not link width, usually
    determines achieved throughput.</b> With a round-trip latency <i>T</i> and a maximum
    of <i>N</i> outstanding reads of size <i>S</i>, the read bandwidth is bounded by
    <i>NS</i>/<i>T</i> regardless of the link rate. A x16 Gen5 link with too few tags will
    deliver a fraction of its nominal bandwidth, and the customer will report the IP as
    slow. <b>Publishing the bandwidth-versus-latency curve rather than a single peak
    number is both more honest and more useful</b>, and it pre-empts the most common
    performance complaint.</div>""")
    s.append(tab("Compliance and interoperability",
        ["Activity", "What it establishes", "Note"],
        [["PCI-SIG compliance testing", "Conformance to the specification",
          "Required for the logo; a defined test suite"],
         ["Interop testing", "Works with real partners", "<b>Distinct from compliance</b>"],
         ["Lane margining", "Receiver margin reporting", "Mandatory from Gen4"],
         ["Equalisation preset sweep", "Link robustness", "Gen3+"],
         ["Error injection", "Recovery behaviour", "Replay, retrain, surprise removal"]]))
    s.append("""<div class="note"><b>Compliance and interoperability are not the same
    claim, and a datasheet should distinguish them.</b> A block can pass the compliance
    suite and still fail against a particular partner because of a marginal channel, an
    unusual equalisation preset, or a timing corner the suite does not exercise. Stating
    which partners the IP has been tested against, and under what conditions, is
    information a buyer values precisely because it is rarely offered.</div>""")
    return "\n".join(s)


def ch_gmac():
    s = ['<h1 id="p3">P3. The Gigabit Ethernet MAC and Its Transceiver Interfaces</h1>']
    s.append("""<div class="kvbar"><b>Domain</b> networking, automotive, industrial,
    embedded SoC &nbsp;&bull;&nbsp; <b>Standard</b> IEEE 802.3 Clauses 4, 22, 35, 46, 35
    &nbsp;&bull;&nbsp; <b>Sellable part</b> the MAC and the media-independent interface
    logic; the PHY is external or a hard macro</div>""")

    s.append("<h2>P3.1 What a MAC does</h2>")
    s.append(tab("GMAC functional blocks",
        ["Block", "Function", "Notes"],
        [["<b>Transmit framer</b>",
          "Preamble/SFD insertion, padding to 64 B, FCS append, inter-frame gap",
          "<b>The IFG is 96 bit times</b> and must be maintained exactly"],
         ["<b>Receive framer</b>", "Preamble detect, SFD align, FCS check, length check",
          "Must distinguish a runt, a jabber and a valid short frame"],
         ["<b>CRC-32</b>", "Frame check sequence, polynomial 0x04C11DB7",
          "Reflected input and output, initial value 0xFFFFFFFF, final XOR &mdash; "
          "<b>all four conventions must match the standard</b>"],
         ["Address filter", "Unicast, multicast hash, broadcast, promiscuous",
          "Hash table sizing is a parameter"],
         ["Flow control", "PAUSE frames (802.3x), priority PAUSE (802.1Qbb)",
          "Requires watermark logic on the RX FIFO"],
         ["<b>FIFOs and CDC</b>", "Bridge the system clock and the interface clock",
          "<b>Two clock domains; rate adaptation</b>"],
         ["DMA / descriptors", "Move frames to and from memory",
          "Descriptor ring design dominates throughput"],
         ["Statistics (RMON/MIB)", "Counters for frames, errors, sizes",
          "Numerous; generate them from a table"],
         ["MDIO master", "Manage the external PHY", "Clause 22 and Clause 45 addressing"],
         ["Timestamping", "IEEE 1588 / 802.1AS", "<b>Capture point accuracy is the spec</b>"]]))
    s.append("""<div class="ms"><b>The CRC-32 conventions are a classic interoperability
    trap and deserve explicit treatment.</b> Ethernet's FCS uses the polynomial
    0x04C11DB7 with an initial value of all ones, bit-reflected input and output, and a
    final inversion. An implementation that gets the polynomial right but the reflection
    wrong produces a CRC that is self-consistent &mdash; it will pass its own loopback
    test &mdash; and is rejected by every other device on the network. <b>This is the
    canonical example of why a standard's test vectors, not self-consistency, are the
    oracle</b>, and why the reference model must be checked against known frames from the
    specification rather than against the RTL.</div>""")

    s.append("<h2>P3.2 Media-independent interfaces</h2>")
    s.append(tab("The MII family",
        ["Interface", "Speeds", "Signals", "Clocking", "Where used"],
        [["MII", "10/100", "4-bit each direction", "25 MHz from the PHY", "Legacy"],
         ["RMII", "10/100", "2-bit", "50 MHz shared", "Pin reduction"],
         ["<b>GMII</b>", "1000", "8-bit each direction", "125 MHz",
          "<b>Classic gigabit interface</b>"],
         ["<b>RGMII</b>", "10/100/1000", "4-bit <b>DDR</b>", "125 MHz DDR",
          "<b>Halves the pins; introduces a clock-skew requirement</b>"],
         ["SGMII", "10/100/1000", "1 serial lane", "625 MHz DDR / SerDes",
          "Serial; needs a SerDes"],
         ["XGMII / XLGMII", "10G / 40G", "32/64-bit", "&mdash;", "Higher speeds"],
         ["<b>1000BASE-X PCS</b>", "1000", "&mdash;", "&mdash;",
          "<b>8b/10b + auto-negotiation, Clause 36/37</b>"]]))
    s.append("""<div class="warn"><b>RGMII's clock-to-data relationship is the single most
    common Gigabit Ethernet bring-up failure.</b> The interface uses DDR signalling and the
    original specification expects the clock edge aligned with the data, requiring an
    external trace-length delay; version 2.0 added an internal-delay option that the PHY
    may or may not implement, and that is often configured by strapping or by an MDIO
    register. The result is four plausible combinations of delay on each side, only some
    of which work. <b>An IP that exposes a configurable transmit and receive clock delay,
    and documents the required PHY configuration for each, converts a multi-day board
    debug into a register write.</b> This is a small feature with a very large support
    value.</div>""")

    s.append("<h2>P3.3 Design decisions that matter</h2>")
    s.append(tab("GMAC architecture choices",
        ["Decision", "Options", "Consequence"],
        [["Store-and-forward vs cut-through", "&mdash;",
          "<b>Store-and-forward can drop bad frames before transmitting</b>; "
          "cut-through has lower latency but forwards errors"],
         ["FIFO depth", "&mdash;",
          "Must absorb the maximum frame plus system latency; underrun mid-frame is fatal"],
         ["Datapath width", "8 / 32 / 64 bit",
          "Width &times; clock must exceed 1 Gb/s with margin for IFG and preamble"],
         ["Descriptor format", "Ring vs list; scatter-gather", "Throughput under small frames"],
         ["Checksum offload", "IPv4/TCP/UDP", "<b>Reduces host CPU load substantially</b>"],
         ["TSO / LRO", "Segmentation offload", "Large benefit; significant complexity"],
         ["VLAN handling", "Insert/strip/filter", "Standard expectation"],
         ["Jumbo frames", "up to 9 kB", "FIFO and descriptor sizing"],
         ["<b>1588 timestamping</b>", "&mdash;",
          "<b>The capture point must be at a defined layer boundary</b>"]]))
    s.append("""<div class="ms"><b>Transmit underrun is the failure mode that defines FIFO
    sizing.</b> Once transmission starts, the MAC must supply a byte every clock until the
    frame ends; if the DMA cannot keep up because of bus contention, the frame is
    truncated and transmitted with a bad CRC, which the link partner discards. The
    system-level fix is store-and-forward &mdash; do not begin transmitting until the whole
    frame is buffered &mdash; at the cost of latency and FIFO area. <b>A configurable
    start-threshold, from cut-through to full store-and-forward, lets the integrator
    choose their own point on that trade</b>, and it is a parameter worth exposing.</div>""")
    s.append("""<div class="ms"><b>IEEE 1588 timestamping accuracy is determined by where
    the timestamp is taken, not by the counter's resolution.</b> A timestamp captured in
    software has microseconds of jitter; captured at the MAC it has the variability of the
    PHY latency; captured at the PHY's serial boundary it can be sub-nanosecond. Since the
    PHY delay is not constant across speeds and link states, a MAC-level implementation
    must expose calibration registers for the ingress and egress delays. <b>Specify the
    capture point and the residual uncertainty</b>; an accuracy figure without a capture
    point is meaningless.</div>""")

    s.append("<h2>P3.4 Verification and deliverables</h2>")
    s.append(tab("GMAC verification plan",
        ["Area", "Stimulus", "Oracle"],
        [["Frame sizes", "64 (minimum) to 1518 and jumbo, plus every boundary",
          "Golden model; <b>runt, oversize and pad cases explicitly</b>"],
         ["<b>CRC</b>", "Known frames from the standard",
          "<b>Standard vectors, not self-consistency</b>"],
         ["IFG and preamble", "Back-to-back frames at line rate", "Protocol checker"],
         ["Address filtering", "Unicast, multicast, hash collisions, broadcast", "Model"],
         ["Flow control", "Trigger watermarks; receive PAUSE", "Correct pause duration"],
         ["Error injection", "Bad CRC, truncated, symbol errors", "Correct counters and discard"],
         ["Underrun / overrun", "Starve or stall the DMA", "Defined behaviour, no lockup"],
         ["Speed changes", "10/100/1000 transitions", "Clean reconfiguration"],
         ["<b>MDIO</b>", "Clause 22 and 45 transactions", "Timing and turnaround"],
         ["Timestamping", "Known packet timing", "Accuracy within the stated bound"],
         ["<b>Interoperability</b>", "Against a real PHY on a board",
          "<b>The only test that finds RGMII delay problems</b>"]]))
    s.append("""<div class="note"><b>Deliverable note for all three interface blocks in
    this chapter.</b> MIPI, PCIe and Ethernet share a structure: a process-independent
    digital controller above a process-dependent PHY. In every case the integrator's
    difficulties concentrate at that boundary &mdash; PPI timing for MIPI, PIPE and
    equalisation for PCIe, RGMII delay and MDIO configuration for Ethernet. <b>The user
    guide's most valuable section is therefore the numbered PHY bring-up sequence</b>, and
    the example design's most valuable property is that it drives a real PHY. An IP that
    has only ever been simulated against a PHY model will meet these problems at the
    customer's site rather than the vendor's.</div>""")
    return "\n".join(s)
