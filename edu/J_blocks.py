# -*- coding: utf-8 -*-
"""Volume I, Part J -- Memory, accelerators, interconnect, codecs."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line


def _f_systolic():
    b = []
    for r in range(3):
        for c in range(4):
            b.append(box(120+c*74, 40+r*56, 58, 40, "PE", None, 9))
            if c: b.append(arr(120+c*74-16, 60+r*56, 120+c*74, 60+r*56))
            if r: b.append(arr(149+c*74, 40+r*56-16, 149+c*74, 40+r*56))
    for r in range(3):
        b.append(arr(78, 60+r*56, 120, 60+r*56))
        b.append(txt(74, 54+r*56, f"a{r}", 9, "end"))
    for c in range(4):
        b.append(arr(149+c*74, 14, 149+c*74, 40))
        b.append(txt(149+c*74, 10, f"b{c}", 9, "middle"))
    b.append(txt(240, 232, "Each datum is read from memory once and reused across the array",
                 9, "middle", 'font-style="italic"'))
    b.append(txt(240, 249, "Arithmetic intensity rises with array size — that is the whole point",
                 9, "middle", 'font-style="italic"'))
    return svg(470, 262, "".join(b))


def _f_roofline():
    b = []
    b += [line(50, 190, 400, 190), line(50, 190, 50, 30)]
    b.append('<path d="M50,190 L205,60" stroke="#123f6d" stroke-width="2" fill="none"/>')
    b.append('<path d="M205,60 L395,60" stroke="#123f6d" stroke-width="2" fill="none"/>')
    b += [txt(110, 110, "memory bound", 9, "start", 'font-style="italic"'),
          txt(280, 50, "compute bound", 9, "start", 'font-style="italic"'),
          txt(205, 205, "ridge point", 9, "middle"),
          line(205, 60, 205, 190, "3,3"),
          txt(40, 30, "GFLOP/s", 9, "end"),
          txt(400, 208, "arithmetic intensity (FLOP/byte)", 9, "end")]
    b.append(txt(225, 236, "Left of the ridge, adding compute units buys nothing",
                 9, "middle", 'font-style="italic"'))
    return svg(420, 248, "".join(b))


def ch_memory_design():
    s = ['<h1 id="j1">J1. On-Chip Memory</h1>']
    s.append(tab("Memory types available to an IP block",
        ["Type", "Bit cell", "Density", "Notes"],
        [["<b>6T SRAM</b>", "6 transistors", "High", "Standard; compiled by the foundry"],
         ["8T / 10T SRAM", "8&ndash;10 T", "Lower", "Better read stability, low-voltage operation"],
         ["Register file", "Latch or flop array", "Low", "Multi-port, fast, expensive"],
         ["<b>Flip-flop array</b>", "&mdash;", "Lowest",
          "<b>Synthesisable</b> &mdash; the only portable option for small storage"],
         ["Dual-port SRAM", "8T", "Lower", "True dual port costs ~30&ndash;40% more area"],
         ["Pseudo dual port", "6T, time-multiplexed", "High", "Half the bandwidth"],
         ["ROM", "&mdash;", "Very high", "Constants, microcode, S-boxes"],
         ["eDRAM / MRAM / RRAM", "&mdash;", "Very high", "Process-specific; limited availability"]]))
    s.append("""<div class="ms"><b>For an IP vendor the portability question dominates the
    density question.</b> A compiled SRAM is smaller and faster than a flip-flop array,
    but it is a foundry-specific macro: shipping RTL that instantiates one ties the
    customer to a particular process and library. The standard resolution is a
    <b>memory wrapper</b> &mdash; the IP instantiates a thin module with a defined
    interface, and the customer maps it to their compiler's output or to a behavioural
    model. A well-built IP ships the wrapper, a synthesisable fallback, and a document
    specifying the required timing (read latency, write behaviour on a read&ndash;write
    collision). <b>Omitting the collision behaviour is a frequent and expensive
    omission</b>, because different compilers do different things and the block's
    correctness may depend on which.</div>""")
    s.append(tab("Memory design considerations",
        ["Issue", "Consequence", "Handling"],
        [["Read/write collision", "Behaviour is compiler-dependent",
          "<b>Specify it</b>; forbid it in the design if possible"],
         ["Banking", "Enables parallel access", "Address mapping becomes a design choice"],
         ["Wide words vs many banks", "Power and area trade", "Follow the access pattern"],
         ["<b>ECC</b>", "Soft-error protection", "Adds a cycle of latency and ~12&ndash;25% bits"],
         ["Scrubbing", "Corrects accumulated errors", "Background read&ndash;correct&ndash;write"],
         ["Redundancy and repair", "Yield", "Foundry feature; needs BIST/BIRA"],
         ["Retention voltage", "Low-power state", "Below it, data is lost"]]))
    s.append("""<div class="ms"><b>ECC on memory is a reliability calculation, not a
    preference.</b> Soft-error rate is quoted in FIT per megabit (failures in
    10<sup>9</sup> device-hours), typically a few hundred FIT/Mb at sea level for SRAM.
    A 10&nbsp;Mb on-chip memory at 300&nbsp;FIT/Mb gives 3000 FIT, or roughly one upset
    per 38 years per device &mdash; negligible for a phone, unacceptable for a fleet of
    a million servers, where it means an upset every twenty minutes somewhere in the
    fleet. <b>The same silicon needs ECC in one market and not in another</b>, which is
    why it must be a parameter rather than a fixed design choice, and why the datasheet
    must state the FIT contribution with and without it.</div>""")
    return "\n".join(s)


def ch_accel():
    s = ['<h1 id="j2">J2. Accelerators: Systolic Arrays and the Roofline</h1>']
    s.append(fig(_f_roofline(), "The roofline model. A kernel's arithmetic intensity "
                                "determines whether more compute or more bandwidth helps."))
    s.append("""<div class="math">Attainable performance =
    min(Peak compute, Bandwidth &times; Arithmetic intensity)</div>""")
    s.append("""<div class="ms"><b>The roofline is the first slide of any accelerator
    proposal, and it decides the architecture.</b> Arithmetic intensity &mdash; useful
    operations per byte moved from memory &mdash; is a property of the algorithm and its
    dataflow, not of the hardware. A naive matrix multiply that re-reads operands has low
    intensity and is memory-bound: adding multipliers achieves nothing. Tiling the
    computation so that each loaded element is reused <i>n</i> times multiplies the
    intensity by <i>n</i> and moves the kernel rightward past the ridge, at which point
    additional compute finally pays. <b>Every accelerator architecture is, at bottom, a
    scheme for raising arithmetic intensity.</b></div>""")
    s.append(fig(_f_systolic(), "A systolic array. Operands flow through the array and "
                                "are reused by every processing element they pass."))
    s.append(tab("Accelerator dataflow taxonomy",
        ["Dataflow", "What stays resident", "Best when"],
        [["<b>Weight stationary</b>", "Weights in the PE",
          "Weights are reused across many activations (CNN inference)"],
         ["<b>Output stationary</b>", "Partial sums in the PE",
          "Long reduction chains; minimises partial-sum movement"],
         ["<b>Row stationary</b>", "A row of the convolution", "Balances all three reuse types"],
         ["No local reuse", "Nothing", "Simple, memory-bound"]]))
    s.append(tab("Precision in inference accelerators",
        ["Format", "Bits", "Effect", "Hardware cost"],
        [["FP32", "32", "Baseline", "Reference"],
         ["<b>BF16</b>", "16", "Same exponent range as FP32, fewer mantissa bits",
          "~1/2 multiplier area; <b>drop-in for training</b>"],
         ["FP16", "16", "Smaller range &mdash; needs loss scaling", "~1/2"],
         ["<b>INT8</b>", "8", "Requires calibration or QAT",
          "<b>~1/4 area, ~1/4 energy</b> of FP32"],
         ["INT4 / INT2", "4/2", "Significant accuracy loss without care", "Smaller still"],
         ["Binary / ternary", "1&ndash;2", "XNOR&ndash;popcount replaces multiply",
          "<b>No multipliers at all</b>"],
         ["Mixed / per-channel scale", "&mdash;", "Recovers most INT8 accuracy",
          "Per-channel scaling logic"]]))
    s.append("""<div class="ms"><b>Binary networks replace arithmetic with logic, which
    changes the whole cost structure.</b> When weights and activations are &plusmn;1, a
    multiply becomes an XNOR and the accumulation becomes a population count. A 256-input
    dot product is then 256 XNOR gates and a popcount tree &mdash; a few hundred gates
    instead of 256 multipliers. The trade is accuracy, recovered partially by keeping the
    first and last layers at higher precision and by batch normalisation folded into a
    threshold comparison. <b>For an IP house this is attractive because the resulting
    block is small, fully synthesisable, and has no dependence on DSP hard macros</b>,
    which makes it portable across FPGA and ASIC targets.</div>""")
    s.append(tab("Accelerator interface decisions",
        ["Decision", "Options", "Consequence"],
        [["Weight delivery", "Resident in the bitstream vs streamed at run time",
          "<b>Dominates the system architecture</b>: bandwidth vs flexibility"],
         ["Granularity", "Layer-at-a-time vs fused layers",
          "Fusion removes intermediate memory traffic"],
         ["Control", "Fixed sequence vs programmable", "Flexibility vs area"],
         ["Memory", "Scratchpad vs cache",
          "<b>Scratchpad is deterministic</b>; cache is easier to program"],
         ["Sparsity", "Dense vs structured vs unstructured",
          "Unstructured sparsity rarely pays in hardware"]]))
    return "\n".join(s)


def ch_noc():
    s = ['<h1 id="j3">J3. On-Chip Interconnect and Networks</h1>']
    s.append(tab("Interconnect topologies",
        ["Topology", "Scaling", "Latency", "Use"],
        [["Shared bus", "Poor beyond ~8 masters", "Low", "Small SoC"],
         ["Crossbar", "<i>O</i>(<i>N</i><sup>2</sup>) area", "Low", "Moderate port counts"],
         ["<b>Mesh NoC</b>", "Good", "<i>O</i>(&radic;<i>N</i>) hops", "Many-core"],
         ["Torus", "Good", "Lower diameter", "&mdash;"],
         ["Ring", "Simple", "<i>O</i>(<i>N</i>)", "Moderate core counts"],
         ["Tree / fat tree", "Good for hierarchical traffic", "&mdash;", "Cache hierarchies"],
         ["Butterfly / Clos", "Good", "Uniform", "Switches"]]))
    s.append(tab("NoC design issues",
        ["Issue", "Cause", "Solution"],
        [["<b>Deadlock</b>", "Cyclic dependency among buffers",
          "Virtual channels, turn-model routing (e.g. dimension-order)"],
         ["Livelock", "Packets circulate without progress", "Bounded misrouting, ageing"],
         ["Head-of-line blocking", "One blocked packet stalls the queue", "Virtual channels"],
         ["Fairness", "Some sources starve", "Arbitration policy"],
         ["QoS", "Mixed traffic classes", "Priority virtual channels, rate limiting"],
         ["Flow control", "Buffer overflow", "Credit-based"]]))
    s.append("""<div class="ms"><b>Deadlock freedom is a structural property and should be
    established structurally, not tested.</b> Dimension-order routing (traverse X fully,
    then Y) makes cyclic buffer dependencies impossible in a mesh, and the argument is a
    short proof rather than a simulation campaign. Adaptive routing performs better under
    load but reintroduces the possibility, which is then removed by reserving an escape
    virtual channel that uses dimension-order. <b>This is an unusually clean example of
    the general principle that architecture should make undesirable states unreachable
    rather than merely unlikely</b> &mdash; the same principle behind sparse FSM encodings
    and Gray-coded FIFO pointers.</div>""")
    s.append(tab("Chip-to-chip and chiplet interfaces",
        ["Standard", "Scope", "Note"],
        [["PCIe", "Board-level, packetised", "Gen6 uses PAM4 and FLIT mode"],
         ["CXL", "Cache-coherent over PCIe PHY", "Memory expansion and pooling"],
         ["<b>UCIe</b>", "Die-to-die in a package",
          "<b>Very short reach &rarr; very low energy per bit</b>"],
         ["BoW / AIB", "Die-to-die", "Open alternatives"],
         ["HBM", "Memory via silicon interposer", "Very wide, moderate rate"],
         ["Ethernet", "Rack and beyond", "&mdash;"]]))
    s.append("""<div class="ms"><b>Chiplets change the economics that an IP business
    operates in.</b> When a system is partitioned across dies, the interface between them
    becomes a standardised product boundary, and a company can sell an entire die rather
    than an RTL block. Energy per bit is the defining metric: on-chip wires are
    ~0.1&nbsp;pJ/bit, UCIe die-to-die ~0.5&nbsp;pJ/bit, and long-reach SerDes
    ~5&ndash;10&nbsp;pJ/bit. <b>That two-order-of-magnitude spread is why partitioning
    decisions are made at the package level and why die-to-die PHY IP became valuable so
    quickly.</b> A digital design house cannot build the PHY, but the link layer,
    the retry and CRC logic, and the protocol adapters above it are all synthesisable
    &mdash; the familiar pattern of a sellable digital block adjacent to an unreachable
    analogue one.</div>""")
    return "\n".join(s)


def ch_codec():
    s = ['<h1 id="j4">J4. Image and Video Coding</h1>']
    s.append(tab("Codec pipeline stages",
        ["Stage", "Purpose", "Hardware character"],
        [["Prediction (intra)", "Exploit spatial correlation",
          "Many modes &rarr; mode decision is a search"],
         ["<b>Prediction (inter / motion)</b>", "Exploit temporal correlation",
          "<b>Motion estimation dominates encoder cost</b>"],
         ["Transform", "Energy compaction (integer DCT)",
          "Multiplier-free integer approximations"],
         ["Quantisation", "Lossy step &mdash; rate control lives here", "Divide by a table value"],
         ["<b>Entropy coding</b>", "Remove remaining redundancy (CABAC)",
          "<b>Serial bottleneck</b>"],
         ["Loop filter (deblocking, SAO, ALF)", "Remove artefacts",
          "In the reconstruction loop &mdash; must be bit-exact"],
         ["Reference frame store", "&mdash;", "<b>DRAM bandwidth dominates</b>"]]))
    s.append("""<div class="ms"><b>Encoder and decoder are asymmetric by design.</b> The
    standard specifies only the decoder; the encoder may choose modes however it likes,
    provided the bitstream is conformant. This means <b>encoder quality is a product
    differentiator while decoder correctness is a conformance requirement</b>, and the two
    have completely different verification strategies: a decoder is verified against
    conformance bitstreams with bit-exact expected output, whereas an encoder is evaluated
    on rate&ndash;distortion curves and must only produce decodable output. A design house
    entering video should know which side it is selling into, because the effort profiles
    differ by an order of magnitude.</div>""")
    s.append(tab("Standards and their distinguishing features",
        ["Codec", "Year", "Key additions", "Hardware impact"],
        [["JPEG", "1992", "8&times;8 DCT, Huffman", "Simple, still ubiquitous"],
         ["H.264/AVC", "2003", "Integer transform, CABAC, variable block size",
          "<b>Integer transform removes encoder/decoder drift</b>"],
         ["HEVC/H.265", "2013", "CTU up to 64&times;64, 35 intra modes, SAO",
          "Much larger mode search"],
         ["VP9 / AV1", "2013/2018", "Royalty-free, ANS coding, many partitions",
          "Very large encoder search space"],
         ["VVC/H.266", "2020", "More partitions, ALF, affine motion", "Further complexity"],
         ["JPEG XS / lightweight", "&mdash;", "Low latency, visually lossless",
          "<b>Line-based, small buffers</b> &mdash; a good niche for a small IP house"]]))
    s.append("""<div class="warn"><b>Bit-exactness inside the reconstruction loop is
    non-negotiable.</b> The decoder's output feeds the encoder's prediction, so any
    arithmetic difference accumulates frame after frame &mdash; drift. This is why every
    in-loop operation (transform, quantisation, interpolation filters, deblocking) is
    specified as exact integer arithmetic with defined rounding, and why a reference model
    for a codec must reproduce those operations bit for bit rather than
    mathematically. <b>A floating-point reference model of a video codec is not a
    reference model.</b></div>""")
    return "\n".join(s)
