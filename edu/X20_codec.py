# -*- coding: utf-8 -*-
"""Volume I, Part X20 -- Image and video coding as a hardware block."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_codec2():
    s = ['<h1 id="x20">X20. Image and Video Coding as a Hardware Block</h1>']
    s.append("""<p>A video codec is the largest fixed-function block in most consumer
    SoCs and it exercises nearly everything in this book: transforms, arithmetic coding,
    enormous memory bandwidth, a hard real-time deadline and a standard with a
    compliance regime. It is also the clearest example of a block whose <i>decoder</i> is
    fully specified and whose <i>encoder</i> is not, which has a large commercial
    consequence.</p>""")

    s.append("<h2>X20.1 The asymmetry that defines the business</h2>")
    s.append(tab("Decoder and encoder are different products",
        ["", "Decoder", "Encoder"],
        [["Specified by the standard", "<b>Exactly &mdash; bit-exact output is "
          "required</b>", "Only the bitstream syntax; how to choose it is free"],
         ["Conformance", "Run the conformance streams; output must match bit for bit",
          "Any legal stream is conformant, however bad"],
         ["Where the value is", "Correctness and area", "<b>Rate&ndash;distortion "
          "decisions &mdash; the quality at a given bitrate</b>"],
         ["Differentiation", "Little &mdash; all correct decoders agree",
          "<b>Large and lasting</b>"],
         ["Verification", "Against the reference decoder, bit-exact",
          "Against a quality metric on a corpus, statistically"],
         ["A design house should", "Build it if the volume justifies it",
          "<b>Build it if you have an algorithmic advantage to sell</b>"]]))
    s.append("""<div class="ms"><b>The bit-exactness requirement on decoders is what makes
    them verifiable and therefore commoditisable.</b> Because a conformant decoder's
    output is defined to the bit, a test is unambiguous: run the standard's conformance
    streams, compare to the reference output, and the answer is yes or no. That property
    makes verification tractable and makes every correct decoder equivalent, which drives
    margins to the cost of implementation. The encoder has no such test &mdash; quality is
    measured statistically on a corpus, and two encoders producing different streams can
    both be right &mdash; which is exactly why encoder quality remains a durable
    differentiator and why encoder IP is worth more per gate.</div>""")

    s.append("<h2>X20.2 Bandwidth: the number that sizes the block</h2>")
    rows = []
    for name, w, h, fps, bits in (("1080p60 8-bit 4:2:0", 1920, 1080, 60, 12),
                                  ("4K60 10-bit 4:2:0", 3840, 2160, 60, 15),
                                  ("8K60 10-bit 4:2:0", 7680, 4320, 60, 15),
                                  ("4K120 10-bit 4:2:2", 3840, 2160, 120, 20)):
        frame = w * h * bits / 8
        raw = frame * fps
        # motion estimation reads the reference many times
        for reads in (1,):
            pass
        rows.append([name, num(frame / 1024 / 1024, 4), num(raw / 1e9, 4),
                     num(raw * 3 / 1e9, 4), num(raw * 8 / 1e9, 4)])
    s.append(sweep("Frame store and bandwidth for video coding",
        ["Format", "Frame (MB)", "Raw read once (GB/s)",
         "Decoder: ~3&times; (read ref, write, display)",
         "Encoder: ~8&times; with motion search"], rows,
        "The multipliers are indicative of a straightforward implementation and are the "
        "quantity every architectural trick attacks. <b>8K60 encoding at eight passes "
        "would need more bandwidth than the whole rest of a mobile SoC</b>, which is "
        "why real encoders use hierarchical search, reference compression and "
        "aggressive on-chip tiling."))
    s.append(ex("Why reference-frame compression exists",
        "4K60 10-bit decoding, three passes over the frame store, in a system with "
        "25&nbsp;GB/s of usable DRAM bandwidth shared with everything else.",
        "Compare the requirement with a realistic allocation, then compute what a "
        "lossless 2:1 reference compressor buys.",
        [("Raw bandwidth required", num(3840 * 2160 * 15 / 8 * 60 * 3 / 1e9, 4, "GB/s")),
         ("Plausible allocation to video", num(6, 3, "GB/s")),
         ("Shortfall", num(3840 * 2160 * 15 / 8 * 60 * 3 / 1e9 - 6, 4, "GB/s")),
         ("With 2:1 lossless reference compression",
          num(3840 * 2160 * 15 / 8 * 60 * 3 / 1e9 / 2, 4, "GB/s")),
         ("Still short by",
          num(max(0.0, 3840 * 2160 * 15 / 8 * 60 * 3 / 1e9 / 2 - 6), 4, "GB/s")),
         ("Energy saved at 20&nbsp;pJ/byte",
          num(3840 * 2160 * 15 / 8 * 60 * 3 / 2 * 20e-12, 4, "W"))],
        "<b>By treating compression as a capacity optimisation.</b> Its purpose here is "
        "<i>bandwidth and energy</i>, not storage: DRAM traffic is often the largest "
        "single power term in a video subsystem, so halving it halves that term. Note "
        "the requirement that the compression be <b>lossless</b>: a decoder must produce "
        "bit-exact output, so any loss in the reference frames propagates and the "
        "decoder is no longer conformant. That constraint &mdash; lossless, fixed "
        "compression ratio for random access, and low latency &mdash; is why reference "
        "compressors are their own small design problem rather than an off-the-shelf "
        "codec."))

    s.append("<h2>X20.3 Entropy coding: the serial bottleneck</h2>")
    s.append(derive("Why arithmetic coding resists parallelisation", [
        ("An arithmetic coder maintains an interval and narrows it by one symbol's "
         "probability at a time.",
         "Definition."),
        ("The interval after symbol <i>k</i> depends on every previous symbol.",
         "<b>Strictly serial by construction.</b>"),
        ("Context-adaptive coding makes it worse: the probability model is updated "
         "from the decoded symbols.",
         "So even the model is serial."),
        ("Throughput is therefore bins per cycle, and a high-bitrate stream needs "
         "several.",
         "Where the decoder's frequency wall comes from."),
        ("<b>The architectural answers change the standard, not the hardware.</b>",
         "Slices and tiles create independent partitions; wavefront parallel processing "
         "allows rows to start once the row above is far enough ahead; bypass bins skip "
         "the model. <b>All three are features the standard had to provide</b>, which is "
         "why codec standards are shaped by hardware feasibility."),
    ]))
    rows = []
    for mbps, bins_per_bit in ((50, 1.2), (100, 1.2), (400, 1.2), (1000, 1.2)):
        bins = mbps * 1e6 * bins_per_bit
        for f in (600e6,):
            need = bins / f
        rows.append([num(mbps), num(bins / 1e6, 4), num(need, 4),
                     num(math.ceil(need)), num(need / 4 * 100, 3)])
    s.append(sweep("Entropy-decoding throughput required at 600&nbsp;MHz",
        ["Bitrate (Mbit/s)", "Mbins/s", "Bins per cycle needed",
         "Parallel engines at 1 bin/cycle", "Utilisation of a 4-bin engine (%)"], rows,
        "Assuming 1.2 bins per coded bit. <b>The last row is why 8K and high-bitrate "
        "professional profiles force tiles</b>: no serial engine reaches those rates, "
        "and the only remaining parallelism is across independent partitions the "
        "bitstream must declare."))
    s.append(prob("Why do codec standards define tiles and slices when they cost "
                  "compression efficiency?",
        "Because they are the only mechanism that creates <b>independent</b> work, and "
        "without independence a decoder cannot be parallelised at all. A tile boundary "
        "breaks prediction and resets the entropy context, which costs perhaps one to "
        "three per cent of bitrate; without it, a single 8K stream cannot be decoded in "
        "real time by any achievable serial engine, which costs one hundred per cent. "
        "<b>The standard is therefore making a deliberate efficiency sacrifice to "
        "preserve implementability</b>, and this is a general and under-appreciated fact "
        "about protocol design: the constraints hardware imposes appear in the "
        "specification as features. Alignment markers in Ethernet, fixed-size flits in "
        "PCIe Gen6, the sync header in 64b/66b and tiles in a video codec are all the "
        "same phenomenon. <b>For an engineer reading a standard, asking &lsquo;which "
        "hardware constraint put this here?&rsquo; explains a surprising fraction of "
        "its otherwise arbitrary-looking content.</b>"))
    s.append(prob("A customer asks for an encoder that beats the reference software in "
                  "quality. Is that possible, and what does it cost?",
        "Possible, and the framing matters. Reference software (HM, VTM, and their "
        "equivalents) is written for <i>correctness and experiment</i>, not for speed, "
        "and its default configuration is a compromise; a hardware encoder that searched "
        "the same space would be enormous. What a good hardware encoder does instead is "
        "spend its budget differently: a wider but shallower motion search, "
        "rate&ndash;distortion decisions made with cheaper approximations applied "
        "everywhere rather than exact ones applied rarely, and pre-analysis over the "
        "whole frame that the reference's block-by-block structure does not perform. "
        "The result can beat the reference at equal <i>time</i> while losing at equal "
        "<i>search effort</i> &mdash; and quoting which comparison you mean is the "
        "difference between an honest claim and a misleading one. <b>The cost is that "
        "encoder quality work is empirical</b>: it requires a corpus, a metric the "
        "customer agrees with, and a measurement loop, and that infrastructure is a "
        "larger investment than the RTL."))
    return "\n".join(s)
