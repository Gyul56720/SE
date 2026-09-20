# -*- coding: utf-8 -*-
"""Volume III, Part Y2 -- PCI Express generations 3 to 6, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E, lines, find
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


GEN = [(1, 2.5, "8b/10b", 0.8, False), (2, 5.0, "8b/10b", 0.8, False),
       (3, 8.0, "128b/130b", 128 / 130, False), (4, 16.0, "128b/130b", 128 / 130, False),
       (5, 32.0, "128b/130b", 128 / 130, False), (6, 64.0, "242B FLIT / PAM4", 242 / 256, True)]


def ch_pcie2():
    s = ['<h1 id="y2">Y2. PCI Express, Generations 3 to 6, Worked</h1>']
    s.append("""<p>PCIe is the interface a design house is most likely to be asked for and
    least likely to build from scratch, because the controller is enormous and the
    compliance burden is severe. It is nevertheless worth understanding in detail, because
    almost every block a design house sells will sit behind one, and the properties of
    that link &mdash; its latency, its credit behaviour, its error model &mdash; propagate
    into the specification of whatever is attached.</p>""")

    s.append("<h2>Y2.1 The rate table, computed rather than remembered</h2>")
    rows = []
    for g, gt, enc, eff, pam in GEN:
        per_lane = gt * eff
        rows.append([f"Gen{g}", num(gt, 3), enc, num(eff, 4),
                     num(per_lane / 8, 4), num(per_lane * 16 / 8, 4),
                     "PAM4" if pam else "NRZ"])
    s.append(sweep("PCIe generations: raw rate, encoding and usable bandwidth",
        ["Generation", "GT/s per lane", "Encoding", "Encoding efficiency",
         "GB/s per lane (one direction)", "GB/s at x16", "Modulation"], rows,
        "Computed from the transfer rate and the encoding efficiency alone; protocol "
        "overheads (TLP headers, DLLPs, ordered sets) are additional and Y2.3 computes "
        "them. <b>The 8b/10b to 128b/130b change at Gen3 is why Gen3 is more than "
        "1.6&times; Gen2 despite the rate being only 1.6&times;.</b>"))
    s.append(ex("Why Gen6 went to PAM4 and what it cost",
        "Gen5 runs 32&nbsp;GT/s NRZ; Gen6 runs 64&nbsp;GT/s. The channel budget is "
        "roughly unchanged, because the connectors and boards are the same.",
        "Compare the Nyquist frequency each modulation requires and the eye each "
        "produces, then note what follows.",
        [("Gen5 NRZ Nyquist", num(32 / 2, 3, "GHz")),
         ("Gen6 at 64&nbsp;GT/s with NRZ would need", num(64 / 2, 3, "GHz")),
         ("Gen6 PAM4 symbol rate", num(32, 3, "GBd")),
         ("Gen6 PAM4 Nyquist", num(16, 3, "GHz")),
         ("PAM4 levels", num(4)),
         ("Eye height relative to NRZ at equal amplitude", num(1 / 3, 3)),
         ("SNR penalty", num(20 * math.log10(3), 4, "dB")),
         ("Consequence", "<b>a raw BER near 10<sup>&minus;6</sup>, so FEC becomes "
          "mandatory</b>")],
        "<b>By reading PAM4 as free bandwidth.</b> It keeps the Nyquist frequency &mdash; "
        "and therefore the channel loss &mdash; unchanged, which is the whole point, and "
        "it pays 9.5&nbsp;dB of eye for it. That payment forces three things into the "
        "specification at once: <b>forward error correction</b>, which adds latency; "
        "a <b>flit-based protocol</b>, because FEC needs fixed-size blocks and the old "
        "variable-length TLP framing does not provide them; and <b>retry at the flit "
        "level</b> rather than the packet level. Gen6 is therefore not an incremental "
        "speed bump but a protocol change, and any IP behind it sees different latency "
        "statistics."))

    s.append("<h2>Y2.2 Link training: the LTSSM as a bring-up tool</h2>")
    s.append(tab("LTSSM states a bring-up engineer actually watches",
        ["State", "What it establishes", "Stuck here means"],
        [["Detect", "A receiver is present on the far end",
          "<b>No far end, or AC coupling caps missing / wrong value</b>"],
         ["Polling", "Bit lock and symbol lock at 2.5&nbsp;GT/s",
          "Reference clock, PHY configuration, or gross signal integrity"],
         ["Configuration", "Lane numbering, link width, lane reversal, polarity "
          "inversion", "Lane mapping error in the board or the controller"],
         ["<b>Recovery</b>", "Speed change and equalisation",
          "<b>The commonest stall: the link comes up at Gen1 and will not train "
          "higher</b>"],
         ["L0", "Normal operation", "&mdash;"],
         ["L0s / L1 / L2", "Power states", "Exit latency violations, or a partner "
          "that does not support the state"],
         ["Hot Reset / Disabled", "Explicit teardown", "Software"]]))
    s.append("""<div class="ms"><b>&lsquo;Trains at Gen1, fails at Gen3&rsquo; is a
    diagnosis, not a symptom, and it is worth knowing why.</b> Every PCIe link starts at
    2.5&nbsp;GT/s with no equalisation, because both ends must be able to talk before they
    can negotiate. The move to Gen3 and beyond runs a four-phase equalisation procedure in
    Recovery in which each end requests transmitter coefficient settings from the other
    and evaluates the result. A link that trains at Gen1 and fails above it has working
    wires and a failing equalisation: the channel is worse than the preset assumes, the
    far end's coefficient requests are being ignored or mishandled, or the receiver's
    evaluation is reporting success when the eye is marginal. <b>The debug sequence is
    therefore: read the link status registers for the actual speed and width; read the
    lane error status; capture the equalisation phase the link fails in; and only then
    look at the board.</b> Controllers that expose per-phase equalisation status are much
    faster to bring up, and this is a feature worth asking a vendor for.</div>""")
    rows = []
    for g, gt, enc, eff, pam in GEN[2:]:
        ui = 1 / (gt * 1e9) * 1e12
        rows.append([f"Gen{g}", num(gt, 3), num(ui, 4),
                     num(ui * 0.3, 3), num(ui * 0.1, 3),
                     num(20 if g < 5 else (28 if g == 5 else 32), 3)])
    s.append(sweep("Unit intervals and the budgets they imply",
        ["Generation", "GT/s", "UI (ps)", "30&nbsp;% of UI (ps)", "10&nbsp;% of UI (ps)",
         "Typical channel loss budget (dB)"], rows,
        "The loss budgets are the figures commonly cited for the base specification's "
        "channel; <b>they have not been checked against the current specification text "
        "in this repository</b>, which is a paid document. The UI column is exact "
        "arithmetic."))

    s.append("<h2>Y2.3 Protocol overhead: from GB/s on the box to GB/s in the driver</h2>")
    rows = []
    for payload in (64, 128, 256, 512, 4096):
        hdr = 12 + 4 + 2 + 4 + 2    # TLP header + ECRC? + seq + LCRC + framing (approx)
        raw = payload + hdr
        eff = payload / raw
        rows.append([num(payload), num(hdr), num(raw), num(eff, 4),
                     num(eff * 128 / 130, 4),
                     num(eff * 128 / 130 * 32 * 16 / 8, 4)])
    s.append(sweep("TLP efficiency against maximum payload size, Gen5 x16",
        ["Max payload (B)", "Overhead bytes", "Total bytes", "TLP efficiency",
         "&times; encoding efficiency", "Usable GB/s"], rows,
        "The overhead figure counts a 12-byte header, sequence number, LCRC and framing; "
        "it ignores DLLP acknowledgements and flow-control updates, which consume a "
        "further few per cent. <b>The lesson is the first column: a device restricted to "
        "128-byte payloads gets roughly three quarters of the bandwidth of one that "
        "negotiates 512</b>, and maximum payload size is negotiated to the minimum of "
        "the whole path, so one old switch in the chain sets it for everybody."))
    s.append(ex("Why a DMA engine behind PCIe needs deep outstanding-read support",
        "A Gen4 x8 link, 4&nbsp;&micro;s round-trip read latency to host memory, "
        "requesting 512-byte reads. The engine must sustain 12&nbsp;GB/s.",
        "Bandwidth&ndash;delay product again, exactly as in Part X11 &mdash; the formula "
        "does not care that the wire is now a PCIe link.",
        [("Gen4 x8 usable bandwidth",
          num(16 * 128 / 130 * 8 / 8, 4, "GB/s")),
         ("Required bandwidth", num(12, 3, "GB/s")),
         ("Bytes in flight needed", num(12e9 * 4e-6 / 1024, 4, "kB")),
         ("512-byte reads outstanding", num(math.ceil(12e9 * 4e-6 / 512))),
         ("Tag space needed (10-bit tags allow 768)",
          num(math.ceil(12e9 * 4e-6 / 512)) + " of 768"),
         ("Completion buffer required", num(12e9 * 4e-6 / 1024, 4, "kB"))],
        "<b>By sizing from the link rate and ignoring the latency.</b> A device with "
        "32 outstanding reads on this link achieves 512&nbsp;&times;&nbsp;32&nbsp;/&nbsp;"
        "4&nbsp;&micro;s = 4&nbsp;GB/s regardless of the link being capable of 15. "
        "The second trap is the completion buffer: those bytes in flight must land "
        "somewhere, so the buffer is not optional and it is tens of kilobytes. "
        "<b>Outstanding-transaction capability and completion-buffer size are the two "
        "numbers that decide whether a PCIe device performs</b>, and they belong on the "
        "first page of its datasheet, not in an appendix."))

    s.append("<h2>Y2.4 What the corpus contains, and what it does not</h2>")
    try:
        n = lines("ip", "verilog-pcie")
        s.append(f"""<p>This book's code appendix includes <b>{n:,} lines</b> of a
        working open-source PCIe datapath: DMA engines, TLP generation and parsing, and
        AXI bridging. It is genuinely useful and it is worth being precise about what it
        is. <b>It is the transaction and data-link layer above a vendor hard macro</b>
        &mdash; the PHY, the LTSSM, the equalisation procedure and the serialiser are not
        in it and cannot be, because they are analogue and foundry-specific.</p>""")
    except Exception as e:
        s.append(f'<div class="warn">verilog-pcie not indexed: {E(str(e))}</div>')
    s.append(tab("Where PCIe functionality actually comes from, and who can sell it",
        ["Layer", "Implemented as", "Who supplies it", "Can a small design house sell "
         "this?"],
        [["Serialiser, CDR, equaliser", "Hard macro in a specific process",
          "PHY vendor or foundry", "<b>No</b> &mdash; requires analogue design and "
          "process access"],
         ["PIPE interface", "Defined digital interface",
          "Boundary between the two", "&mdash;"],
         ["LTSSM, lane management", "RTL",
          "Controller vendor", "In principle; <b>compliance is the barrier</b>"],
         ["Data link layer: ack/nak, flow control", "RTL", "Controller vendor",
          "Yes, with effort"],
         ["Transaction layer, config space", "RTL", "Controller vendor", "Yes"],
         ["<b>Application logic behind the controller</b>", "<b>RTL</b>",
          "<b>Anyone</b>",
          "<b>Yes &mdash; and this is where a design house should be</b>"]]))
    s.append("""<div class="warn"><b>Compliance is the commercial fact about PCIe.</b>
    A controller that works is not a controller that can be sold: the PCI-SIG compliance
    programme, its test fixtures, its interoperability workshops and the membership that
    permits them are a substantial and recurring cost, and a customer buying a PCIe
    controller is buying that compliance as much as the RTL. <b>For a one-person design
    house the rational position is above the controller, not inside it</b> &mdash; build
    the accelerator, the DMA engine, the protocol offload that sits behind a licensed
    controller, and let the customer bring the controller they have already
    qualified.</div>""")
    s.append(prob("A customer asks you to quote for &lsquo;a PCIe Gen4 endpoint with a "
                  "custom accelerator&rsquo;. How do you structure the quote?",
        "Split it explicitly, and say why in the quote itself. <b>Item one: the "
        "accelerator</b> &mdash; your design, your verification, your price. <b>Item two: "
        "integration with a controller the customer licenses</b>, quoted as integration "
        "effort with the controller named, because the effort depends heavily on which "
        "one; a controller with a clean AXI-Stream application interface is a fortnight "
        "and one with an idiosyncratic interface is two months. <b>Item three: what you "
        "are not supplying</b> &mdash; the controller licence, the PHY, the compliance "
        "testing, and the driver, each listed with who you expect to provide it. A quote "
        "that silently includes the controller either loses on price to competitors who "
        "excluded it, or wins and then discovers the licence costs more than the project. "
        "<b>Being explicit about scope is not a weakness in a proposal; it is the "
        "clearest signal that the quoter has done this before</b>, and experienced buyers "
        "read it that way."))
    s.append(prob("Gen6 introduced FEC. What does that do to the latency your block sees, "
                  "and why can the FEC not simply be made stronger to allow a cheaper "
                  "channel?",
        "FEC operates on fixed-size flits, so the receiver must collect a whole flit "
        "before it can correct it, and the correction itself takes time. The added "
        "latency is small in absolute terms &mdash; tens of nanoseconds &mdash; but it is "
        "<b>added to every transaction</b>, and for a latency-sensitive accelerator "
        "performing fine-grained host synchronisation it can matter more than the doubled "
        "bandwidth helps. It also changes the <i>distribution</i>: retries now happen at "
        "flit granularity with a different tail than Gen5's packet-level replay. "
        "Stronger FEC is not the answer to a worse channel because latency is the "
        "constraint that a stronger code violates first: a longer code corrects more and "
        "waits longer, and PCIe's entire value proposition rests on being a low-latency "
        "load/store fabric rather than a network. <b>The design point was chosen to "
        "bound added latency, and the code strength followed from that bound</b> &mdash; "
        "not the other way round, which is the usual direction in communications and the "
        "reason PCIe's FEC looks weak to someone arriving from Ethernet."))
    return "\n".join(s)
