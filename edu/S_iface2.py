# -*- coding: utf-8 -*-
"""Volume III -- More interface IP: storage, display, audio, sensors, clocking."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def ch_storage():
    s = ['<h1 id="s1">S1. Storage Interfaces</h1>']
    s.append(tab("Storage interface families",
        ["Interface", "Physical layer", "Protocol", "Where"],
        [["SATA", "1 lane, 1.5/3/6 Gb/s, 8b/10b", "ATA command set", "Legacy HDD/SSD"],
         ["SAS", "Similar", "SCSI", "Enterprise"],
         ["<b>NVMe over PCIe</b>", "<b>PCIe lanes</b>",
          "<b>Queue-pair model in host memory</b>", "<b>Modern SSD &mdash; dominant</b>"],
         ["UFS", "M-PHY (MIPI)", "UniPro + SCSI subset", "Mobile"],
         ["eMMC", "Parallel, up to 200 MB/s", "MMC", "Cost-sensitive embedded"],
         ["SD / SDIO", "Parallel or UHS-II serial", "SD", "Removable"],
         ["CXL memory", "PCIe PHY", "Coherent memory semantics", "Datacentre expansion"]]))
    s.append("""<div class="ms"><b>NVMe's design lesson is that the protocol, not the
    link, was the bottleneck.</b> AHCI (the SATA host interface) supports one command queue
    of 32 entries and requires several register accesses per command, which was adequate
    for a rotating disk whose latency was milliseconds. Flash reduced device latency by
    three orders of magnitude and the host interface became the limit. NVMe replaced it
    with up to 64k queues of 64k entries each, placed in host memory so that submission
    costs one memory write and one doorbell write. <b>A protocol designed around the
    assumptions of one storage medium became the bottleneck when the medium
    changed</b> &mdash; a pattern worth recognising, because the same thing is happening
    now at the memory interface.</div>""")
    s.append(tab("What a storage controller IP contains",
        ["Block", "Function", "Difficulty"],
        [["Host interface", "PCIe/SATA link and protocol", "Standard interface work"],
         ["<b>Command processing</b>", "Fetch, decode, dispatch, complete",
          "Queue management; ordering"],
         ["<b>DMA engine</b>", "Move data between host memory and media buffers",
          "Scatter-gather; alignment"],
         ["<b>Flash translation layer</b>", "Logical to physical mapping, wear levelling, "
          "garbage collection", "<b>Usually firmware &mdash; the real product differentiator</b>"],
         ["<b>ECC (BCH or LDPC)</b>", "Correct raw flash errors",
          "<b>Raw BER rises as the flash wears &mdash; the code must be sized for end of life</b>"],
         ["Buffer manager", "DRAM or SRAM buffering", "Bandwidth"],
         ["Power loss protection", "Flush on power failure", "Capacitor budget and sequencing"]]))
    s.append("""<div class="ms"><b>Flash ECC is sized for the end of the device's life,
    not its beginning.</b> A fresh NAND cell has a raw bit error rate that a modest BCH
    code handles; after thousands of program/erase cycles the rate rises by orders of
    magnitude, and modern controllers use LDPC with soft information obtained by re-reading
    at shifted thresholds. This is why the decoder chapter's material is directly relevant
    to storage: the same min-sum architectures, the same fixed-point traps, and the same
    trade between average latency (few iterations) and worst-case correction (many).
    <b>The controller's ECC strength is what determines the drive's endurance
    rating</b>, which is a marketing number produced by a digital design
    decision.</div>""")
    return "\n".join(s)


def ch_display():
    s = ['<h1 id="s2">S2. Display and Audio Interfaces</h1>']
    s.append(tab("Display interfaces",
        ["Interface", "Layer", "Notes"],
        [["<b>MIPI DSI</b>", "Mobile panel", "Covered in P1; command and video modes"],
         ["<b>eDP / DisplayPort</b>", "Packetised, micro-packet",
          "<b>Lane count and rate negotiated; supports MST</b>"],
         ["HDMI", "TMDS or FRL", "Consumer; HDCP content protection"],
         ["LVDS / FPD-Link", "Parallel serialised", "Automotive, industrial"],
         ["V-by-One", "&mdash;", "Large panels"],
         ["Parallel RGB", "&mdash;", "Simple small panels"]]))
    s.append("""<div class="ms"><b>The recurring structure is the same as everywhere else
    in this volume: a controller above a PHY.</b> For DisplayPort the controller handles
    link training, stream packing into micro-packets, and the AUX channel; for HDMI it
    handles TMDS encoding or FRL framing and the DDC channel. In both cases the PHY is a
    hard macro and the controller is RTL. <b>What differs between display and data
    interfaces is the consequence of error</b>: a corrupted pixel is a momentary visual
    artefact, so retransmission is usually absent and error handling is concealment rather
    than recovery. That asymmetry changes the verification emphasis from data integrity to
    timing and synchronisation.</div>""")
    s.append(tab("Audio interfaces",
        ["Interface", "Character", "Design note"],
        [["I2S", "Simple serial, word clock + bit clock",
          "<b>Clock relationship is the whole protocol</b>"],
         ["TDM", "Multi-channel over one data line", "Slot assignment"],
         ["<b>SoundWire (MIPI)</b>", "Multi-drop, two wires", "Control and data combined"],
         ["S/PDIF", "Self-clocking biphase-mark", "Consumer digital audio"],
         ["PDM", "1-bit oversampled from a MEMS microphone",
          "<b>Needs a decimation filter</b> &mdash; a CIC plus compensation"],
         ["USB Audio", "&mdash;", "Isochronous transfers; clock domain handling"]]))
    s.append("""<div class="ms"><b>A PDM microphone is a sigma-delta modulator without its
    decimator, and that decimator is the sellable block.</b> The microphone outputs a
    1-bit stream at a few megahertz; converting it to 48&nbsp;kHz multi-bit samples
    requires exactly the CIC-plus-compensation chain of Chapter E1, including the
    wrap-around word-growth subtlety. <b>Audio is therefore a low-cost entry point for a
    designer who wants to build and sell a real DSP block</b>: the specification is
    simple, the arithmetic is genuinely interesting, and the quality metric (SNR and THD
    in the audio band) is measurable with open tools.</div>""")
    s.append(tab("Audio-specific signal processing",
        ["Function", "Purpose", "Hardware note"],
        [["Sample rate conversion", "44.1 &harr; 48 kHz and others",
          "<b>Non-integer ratio &rarr; Farrow or polyphase with a long filter</b>"],
         ["Equalisation", "Tone shaping", "Cascaded biquads &mdash; see Chapter E1"],
         ["Dynamic range compression", "Loudness control", "Envelope detection; attack/release"],
         ["Echo cancellation", "Full duplex", "Adaptive filter, often frequency domain"],
         ["Beamforming", "Microphone array", "Delay-and-sum or MVDR"],
         ["Dither and noise shaping", "Requantisation", "<b>See Chapter A3</b>"]]))
    return "\n".join(s)


def ch_clocking():
    s = ['<h1 id="s3">S3. Clock, Reset and Power Architecture of an IP Block</h1>']
    s.append("""<p>These three decisions are made early, are hard to change later, and are
    the ones a customer will question first. They deserve their own chapter in the practice
    volume because they are specification items rather than implementation details.</p>""")
    s.append(tab("Clock architecture decisions",
        ["Decision", "Options", "Consequence for the integrator"],
        [["Number of clock domains", "One, or several",
          "<b>Each additional domain is a CDC verification obligation</b>"],
         ["Clock relationship", "Synchronous ratio, asynchronous, or plesiochronous",
          "Determines which CDC technique is legal"],
         ["Who divides", "Internal divider or external clocks",
          "Internal is easier to use; external is easier to verify"],
         ["Gating", "Internal automatic, external enable, or none",
          "<b>Internal gating must be bypassable for scan</b>"],
         ["Clock enable versus gating", "&mdash;",
          "Enables are simpler; gating saves clock-tree power"],
         ["DFT", "&mdash;", "Test clock must reach every flip-flop"]]))
    s.append("""<div class="ms"><b>Every clock domain you expose is a cost you impose on
    the customer.</b> A block with one clock is integrated by connecting one net; a block
    with three requires the customer to understand their relationship, to run CDC analysis
    across the boundary, and to constrain three trees. If the second and third domains
    exist only because it was convenient internally, the block is harder to sell than it
    needs to be. <b>A useful discipline is to justify each domain in the datasheet</b>:
    if the justification is weak, the domain should probably be removed.</div>""")
    s.append(tab("Reset architecture decisions",
        ["Decision", "Recommendation", "Reason"],
        [["Polarity", "State it; be consistent", "Mixed polarity causes integration errors"],
         ["Synchronous or asynchronous", "<b>Async assert, sync de-assert</b>",
          "Works without a clock; avoids recovery/removal violations"],
         ["One reset or several", "As few as possible", "Ordering between resets is a hazard"],
         ["Minimum assertion width", "<b>Specify in cycles of each clock</b>",
          "Otherwise the customer guesses"],
         ["Reset-less registers", "Only where provably initialised by data",
          "Saves area; creates an X-propagation obligation"],
         ["Soft reset", "Define exactly what it does and does not clear",
          "<b>Almost always under-specified</b>"]]))
    s.append(tab("Power architecture decisions",
        ["Decision", "Options", "Consequence"],
        [["Single or multiple supplies", "&mdash;", "Level shifters; isolation cells"],
         ["Power gating", "Supported or not", "Retention registers; wake sequencing; UPF"],
         ["Retention", "Full, partial, none", "Area versus wake latency"],
         ["DVFS", "Supported or not", "<b>Timing must close at every operating point</b>"],
         ["Clock gating granularity", "Block, module, register",
          "Finer saves more and costs more verification states"],
         ["Idle behaviour", "Defined quiescent state", "Predictable leakage"]]))
    s.append("""<div class="warn"><b>Power gating is the feature that most often turns out
    to cost more than expected.</b> It requires isolation cells on every output crossing
    the boundary, retention flops for whatever state must survive, a power controller with
    a correct sequence, UPF describing all of it, and verification at every combination of
    domain states &mdash; which multiplies the functional state space. For an IP vendor the
    honest positions are either to support it fully, with the UPF and the verification
    evidence, or to state clearly that the block is not power-gateable. <b>The damaging
    middle position is a block that appears gateable and has never been verified in that
    mode.</b></div>""")
    return "\n".join(s)


def ch_ipxact():
    s = ['<h1 id="s4">S4. Packaging an IP for Delivery</h1>']
    s.append(tab("Directory structure a customer expects",
        ["Directory", "Contents", "Note"],
        [["<code>doc/</code>", "Product brief, user guide, release notes, verification report",
          "<b>The first thing opened</b>"],
         ["<code>rtl/</code>", "Synthesisable sources plus a file list",
          "<b>Provide the file list in compile order</b>"],
         ["<code>model/</code>", "Reference model, build instructions", "&mdash;"],
         ["<code>tb/</code>", "Testbench, vectors, run scripts", "Must run out of the box"],
         ["<code>syn/</code>", "Synthesis scripts, SDC, reported results", "Reproducibility"],
         ["<code>example/</code>", "A minimal working system", "Named target"],
         ["<code>sw/</code>", "Headers, driver example", "Generated from the register source"],
         ["<code>ipxact/</code>", "Component description", "Enables automated integration"]]))
    s.append("""<div class="ms"><b>The file list in compile order is a small item that
    saves every customer an hour.</b> SystemVerilog packages must be compiled before their
    users, and a dependency mistake produces errors that look like the IP is broken.
    Providing an explicit ordered list &mdash; and ideally a simple filelist format that
    common tools accept &mdash; removes an entire class of first-hour frustration. The same
    applies to a documented minimum tool version: nothing damages confidence faster than an
    IP that does not compile.</div>""")
    s.append(tab("IP-XACT: what it buys",
        ["Element", "Content", "Enables"],
        [["Component", "Name, version, vendor", "Identification in a catalogue"],
         ["Ports", "Names, widths, directions", "Automated connection"],
         ["Bus interfaces", "AXI/APB mapping of ports", "<b>Automatic bus connection</b>"],
         ["Parameters", "Names, types, ranges, defaults", "Configuration UI"],
         ["<b>Memory maps</b>", "Registers, fields, access, reset values",
          "<b>Generation of RTL, headers, documentation and UVM RAL</b>"],
         ["File sets", "Source files by purpose", "Build automation"]]))
    s.append("""<div class="ms"><b>The memory map element is where the real value sits.</b>
    From one description a tool generates the register block RTL, the C header, the
    documentation table, and the UVM register model &mdash; four artefacts that otherwise
    drift apart. Even a design house that does not ship IP-XACT should adopt the discipline
    internally, because the alternative is maintaining four hand-written copies of the same
    information. <b>A short YAML description and a template engine achieve most of the
    benefit in a day's work</b>, and that generator itself becomes reusable across every
    future project.</div>""")
    s.append(tab("Release checklist",
        ["Item", "Check"],
        [["Clean checkout", "Does everything build and run from a fresh clone?"],
         ["No absolute paths", "Scripts must not reference the vendor's filesystem"],
         ["Tool versions", "Stated and tested"],
         ["Licence headers", "On every file"],
         ["Third-party notices", "Complete bill of materials"],
         ["Version consistency", "Version register, documentation and release note agree"],
         ["Example runs", "On the named target, from clean"],
         ["Known issues", "Listed, with severity and workaround"],
         ["<b>Regression evidence</b>", "<b>Logs included, not just claimed</b>"]]))
    s.append("""<div class="note">The last item is worth a sentence of its own. A
    verification report that states a coverage figure is a claim; one that ships the
    regression logs and the scripts that produced them is evidence. The difference costs
    nothing to provide and is immediately visible to a technical evaluator, who has almost
    certainly received the former from someone else.</div>""")
    return "\n".join(s)
