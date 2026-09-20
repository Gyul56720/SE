# -*- coding: utf-8 -*-
"""Volume I, Part X10 -- Memory: the block that decides the floorplan."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_mem2():
    s = ['<h1 id="x10">X10. Memory: The Block That Decides the Floorplan</h1>']
    s.append("""<p>In most IP blocks the memory is the largest single object, the slowest
    path, and the thing that cannot be changed late. It is also the part of a design that
    RTL hides most completely: a two-dimensional array in SystemVerilog becomes, in
    silicon, a compiled macro with a fixed aspect ratio, a fixed number of ports and its
    own timing model. This part computes what that substitution costs.</p>""")

    s.append("<h2>X10.1 The bit cell and what follows from it</h2>")
    s.append(tab("Storage cells compared",
        ["Cell", "Transistors / bit", "Relative area", "Volatile", "Read", "Used for"],
        [["6T SRAM", "6", "1", "Yes", "Non-destructive", "Caches, buffers, everything "
          "on-chip"],
         ["8T SRAM", "8", "~1.3", "Yes", "Separate read port",
          "<b>Low-voltage operation</b> &mdash; decouples read and write stability"],
         ["Dual-port (2RW)", "8&ndash;10", "~1.8&ndash;2", "Yes", "Two ports",
          "FIFOs across clock domains"],
         ["Register file cell", "~8&ndash;12", "1.5&ndash;3", "Yes", "Many ports",
          "Small, highly ported storage"],
         ["1T-1C DRAM", "1 + capacitor", "~0.15", "Yes, <b>needs refresh</b>",
          "<b>Destructive &mdash; must write back</b>", "Main memory, eDRAM"],
         ["ROM (via / contact)", "1 or 0", "~0.1", "No", "Non-destructive",
          "Twiddles, microcode, constants"],
         ["Flip-flop", "~20&ndash;24", "4&ndash;5", "Yes", "&mdash;",
          "<b>What synthesis gives you if you do not instantiate a macro</b>"]]))
    s.append(ex("The cost of forgetting to instantiate a RAM",
        "A 4&nbsp;kB buffer, 32&nbsp;768 bits. The 6T cell is 0.03&nbsp;&micro;m&sup2;; "
        "a flip-flop with its multiplexer occupies roughly 150&times; a bit cell once "
        "the write-enable logic is counted.",
        "Compute both areas and the array overhead. SRAM macros carry decoders, sense "
        "amplifiers and control that a small array cannot amortise; assume 40&nbsp;% "
        "overhead at this size.",
        [("Bit-cell area", num(32768 * 0.03, 4) + "&nbsp;&micro;m&sup2;"),
         ("Compiled macro with 40&nbsp;% overhead",
          num(32768 * 0.03 * 1.4, 4) + "&nbsp;&micro;m&sup2;"),
         ("Same storage in flip-flops",
          num(32768 * 0.03 * 150, 4) + "&nbsp;&micro;m&sup2;"),
         ("Ratio", num(150 / 1.4, 3) + "&times;"),
         ("Flip-flop clock power penalty (all bits clocked every cycle)",
          "<b>very large &mdash; every bit is on the clock tree</b>")],
        "<b>By writing an array in RTL and letting synthesis decide.</b> Synthesis will "
        "infer flip-flops unless the coding style matches the inference template exactly "
        "&mdash; and the template differs between tools and between memory compilers. "
        "The failure is quiet: the design works, meets timing, and is a hundred times too "
        "large. <b>Always check the synthesis report for inferred registers against your "
        "expected memory instances</b>, and prefer explicit instantiation with a wrapper "
        "for anything above a few hundred bits."))

    s.append("<h2>X10.2 Aspect ratio, banking and the access-energy curve</h2>")
    rows = []
    total = 32768
    for words in (128, 256, 512, 1024, 2048, 4096):
        w = total // words
        if w < 8:
            continue
        # crude but monotone models: bitline length ~ words, wordline ~ width
        bl = words
        wl = w
        energy = bl * 1.0 + wl * 0.4
        delay = math.sqrt(bl) * 1.0 + math.log2(max(words, 2)) * 0.5
        rows.append([num(words), num(w), num(bl), num(wl),
                     num(energy / 1000, 3), num(delay, 3)])
    s.append(sweep("Same 32&#8239;768 bits, six aspect ratios (relative units)",
        ["Words (depth)", "Bits per word", "Bit-line length", "Word-line length",
         "Relative access energy", "Relative access delay"], rows,
        "A tall narrow array has long bit lines, which cost energy and delay; a short "
        "wide one has long word lines and wastes energy activating bits it will not "
        "return. <b>The optimum is in the middle and memory compilers know it</b>, which "
        "is why a compiler refuses extreme aspect ratios and folds internally instead."))
    s.append("""<div class="ms"><b>Sub-banking is why a 1&nbsp;MB cache does not cost
    32&times; the energy of a 32&nbsp;kB one.</b> A large array is built as many small
    arrays with a hierarchical decoder, and an access activates one of them. Energy per
    access therefore grows roughly with the <i>square root</i> of capacity rather than
    linearly, and the same structure bounds the delay growth. This is the reason
    capacity-versus-energy intuitions borrowed from a small block do not transfer, and the
    reason a cache model that charges energy proportional to size will mispredict a
    memory-bound design badly. <b>When you need real numbers, use a memory compiler's
    datasheet or a model such as CACTI</b> &mdash; and state which, because the two
    disagree.</div>""")

    s.append("<h2>X10.3 Multi-port memory: three ways, all of them compromises</h2>")
    s.append(tab("Getting more ports than the compiler offers",
        ["Technique", "Ports obtained", "Area cost", "Restriction"],
        [["True multi-port cell", "<i>n</i>R<i>m</i>W",
          "<b>Grows as (<i>n</i>+<i>m</i>)&sup2;</b> &mdash; wires per cell",
          "Only 1RW and 2RW are usually in the compiler library"],
         ["Banking by address", "<i>n</i> accesses if to different banks",
          "Decode and crossbar", "<b>Conflicts stall</b> &mdash; needs arbitration and "
          "back-pressure"],
         ["Replication (one copy per reader)", "<i>n</i>R1W",
          "<i>n</i>&times; the array", "Writes must go to every copy"],
         ["Double clocking", "2 accesses per functional cycle", "None in area",
          "<b>Halves the frequency budget</b>; needs a clean 2&times; clock"],
         ["XOR / LVT multi-port", "<i>n</i>R<i>m</i>W from 1RW banks",
          "<i>m</i>(<i>n</i>+<i>m</i>) banks plus a live-value table",
          "Complexity; well suited to FPGA, rarely worth it in ASIC"]]))
    s.append(ex("A register file's port count is a quadratic cost",
        "A 32-entry &times; 64-bit register file for a 2-wide machine: 4 read ports and "
        "2 write ports.",
        "Model the cell area as growing with the square of the total port count, which "
        "is the standard first-order model because each port adds a bit line and a word "
        "line to every cell.",
        [("Ports", num(6)),
         ("Area relative to a 1R1W cell", num((6 / 2) ** 2, 3) + "&times;"),
         ("Bits", num(32 * 64)),
         ("If widened to 4-wide (8R4W): ports", num(12)),
         ("Area relative to 1R1W", num((12 / 2) ** 2, 3) + "&times;"),
         ("Area penalty of doubling issue width", num((12 / 6) ** 2, 3) + "&times;")],
        "<b>By treating issue width as a free architectural parameter.</b> Doubling it "
        "quadruples the register-file area and lengthens its access, which is one of the "
        "two reasons superscalar width stopped growing (the other is the scheduler's own "
        "quadratic wake-up logic). The architectural responses are all about avoiding the "
        "quadratic: clustering the register file and accepting a cross-cluster penalty, "
        "banking it by register number, or moving to a structure where most operands "
        "never enter the file at all. <b>A cost model that is quadratic in a parameter is "
        "a signal to change the structure, not to tune the parameter.</b>"))

    s.append("<h2>X10.4 ECC: the arithmetic of protecting a memory</h2>")
    s.append(derive("Why SECDED needs exactly the bits it needs", [
        ("To correct a single error among <i>k</i> data bits, the syndrome must name one "
         "of <i>k</i>+<i>r</i> positions or say &lsquo;no error&rsquo;.",
         "Every correctable case needs its own syndrome value."),
        ("So 2<sup><i>r</i></sup> &ge; <i>k</i> + <i>r</i> + 1.",
         "The Hamming bound for single-error correction."),
        ("Detecting double errors as well costs one more bit: an overall parity.",
         "With it, a double error gives a non-zero syndrome and <i>even</i> overall "
         "parity, which single errors never do."),
        ("<b>SECDED overhead is <i>r</i>+1 bits for <i>k</i> data bits.</b>",
         "And because <i>r</i> grows logarithmically, <b>wide words are far cheaper to "
         "protect than narrow ones</b> &mdash; the single most useful consequence."),
    ]))
    rows = []
    for k in (8, 16, 32, 64, 128, 256, 512):
        r = 1
        while 2 ** r < k + r + 1:
            r += 1
        rows.append([num(k), num(r), num(r + 1), num((r + 1) / k * 100, 3),
                     num(k + r + 1)])
    s.append(sweep("SECDED overhead against word width",
        ["Data bits <i>k</i>", "Hamming bits <i>r</i>", "SECDED bits",
         "Overhead (%)", "Total stored bits"], rows,
        "Protecting a 64-bit word costs 12.5&nbsp;%; protecting a 512-bit line costs "
        "2&nbsp;%. <b>This is why ECC is applied to cache lines and DRAM bursts rather "
        "than to bytes</b>, and why a design that must protect narrow fields should "
        "consider grouping them first."))
    s.append("""<div class="warn"><b>ECC changes the timing path and the failure modes,
    not only the area.</b> The syndrome must be computed and the correction applied before
    the data is used, which inserts an XOR tree &mdash; typically 3 to 5 gate levels for a
    64-bit word &mdash; into the read path. At high frequency this forces the correction
    into a later pipeline stage, which means <b>the consumer must be able to tolerate a
    late correction or be stalled</b>, and that is an architectural decision, not an
    implementation detail. There is a second trap: a memory with ECC that is never
    scrubbed accumulates single-bit errors until two coincide in one word, at which point
    a correctable fault population becomes an uncorrectable event. <b>Scrubbing is part of
    the ECC design, not an optional extra</b>, and its period follows from the soft-error
    rate and the word count.</div>""")
    rows = []
    fit = 1000.0   # FIT per Mbit
    for mbit in (1, 4, 16, 64, 256):
        rate = fit * mbit / 1e9        # errors per hour
        rows.append([num(mbit), num(rate, 3), num(1 / rate / 24 / 365.25, 3),
                     num(rate * 24 * 365.25, 3),
                     num(rate * 24 * 365.25 * 1e6, 3)])
    s.append(sweep("Soft-error arithmetic at 1000 FIT/Mbit (one failure per "
                   "10<sup>9</sup> device-hours per Mbit)",
        ["Memory (Mbit)", "Errors per hour", "MTBF (years, one device)",
         "Errors per device-year", "Errors per year across a million units"], rows,
        "The last column is the one a product manager needs. <b>A part that sees one "
        "upset per device-century produces thousands of field events per year across a "
        "large deployment</b>, which is why ECC appears in consumer parts and not only in "
        "servers. The FIT figure itself depends on altitude, process and cell design and "
        "must come from the foundry."))
    s.append(prob("Your block has a 2&nbsp;kB configuration RAM written once at boot and "
                  "read every cycle thereafter. Does it need ECC, and of what kind?",
        "It needs protection more than a data buffer does, for a reason that has nothing "
        "to do with its size: <b>a corrupted configuration bit is permanent and "
        "systematic</b>, where a corrupted data word is transient. An upset in a filter "
        "coefficient degrades every subsequent output, silently, until the next reboot, "
        "and there is no downstream check that will catch it. The economical answer is "
        "usually <b>parity plus a reload path</b> rather than full SECDED: since the "
        "contents are known and re-writable, detection is enough &mdash; flag the error, "
        "interrupt, and have software rewrite the block. That costs one bit per word "
        "instead of eight and needs no correction logic in the read path, so it does not "
        "disturb the timing at all. <b>Choose detection over correction whenever a "
        "recovery path exists</b>; the recovery path is usually cheaper than the "
        "correction hardware, and it also covers failures the ECC cannot, such as a "
        "corrupted address."))
    s.append(prob("Why does a FIFO built from a dual-port SRAM need its pointers in "
                  "flip-flops rather than in the same memory?",
        "Because the pointers must be readable in the same cycle they are compared, and "
        "a synchronous SRAM read has a cycle of latency. The full and empty conditions "
        "gate the write and read enables of the current cycle, so a pointer that arrives "
        "a cycle late produces a FIFO that overflows by one entry under back-to-back "
        "traffic &mdash; a bug that appears only at full rate, which is to say only in "
        "the system and never in the unit test that writes one word at a time. <b>The "
        "general form of this trap is worth internalising: any state that participates "
        "in this cycle's flow-control decision cannot live behind a synchronous read "
        "port.</b> It is the same reason a cache tag array is read a cycle ahead of the "
        "data array, and the reason credit counters in an interconnect are registers "
        "however large the credit table becomes."))
    return "\n".join(s)
