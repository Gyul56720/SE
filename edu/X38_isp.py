# -*- coding: utf-8 -*-
"""Volume I, Part X38 -- Colour, the ISP pipeline and display processing."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_isp():
    b = []
    st = [("black level", 10), ("lens shading", 74), ("demosaic", 142), ("white bal", 202),
          ("CCM", 258), ("gamma", 306), ("sharpen", 352)]
    for nm, x in st:
        w = 58 if nm != "black level" else 60
        b.append(box(x, 28, w, 26, nm, None, 7.5))
        if x > 10:
            b.append(arr(x - 6, 41, x, 41))
    b.append(arr(412, 41, 434, 41))
    b.append(txt(220, 72, "Bayer domain", 8, "middle"))
    b.append(line(10, 60, 200, 60, w=0.8))
    b.append(line(202, 60, 412, 60, w=0.8, dash="4,3"))
    b.append(txt(310, 72, "RGB domain", 8, "middle"))
    b.append(txt(220, 98, "Demosaic is the boundary: before it one value per pixel, "
                          "after it three.", 9, "middle"))
    b.append(txt(220, 112, "Everything upstream is a third of the data rate &mdash; and "
                           "that is where the fixes belong.", 9, "middle",
                 'font-style="italic"'))
    return svg(450, 122, "".join(b))


def ch_isp2():
    s = ['<h1 id="x38">X38. Colour, the ISP Pipeline and Display Processing</h1>']
    s.append("""<p>Camera and display IP is one of the largest licensing markets, and it
    is unusual in that the correctness criterion is partly perceptual. That does not make
    it unquantifiable &mdash; it makes the quantities colorimetric rather than
    signal-theoretic, and they are just as computable.</p>""")
    s.append(fig(_f_isp(), "A minimal image signal processor. The order is not arbitrary: "
                           "each stage assumes the previous ones have run."))

    s.append("<h2>X38.1 Why the pipeline is in that order</h2>")
    s.append(tab("Each stage, what it corrects, and why it must come where it does",
        ["Stage", "Corrects", "Why here"],
        [["Black level", "Sensor pedestal and dark current",
          "<b>First &mdash; everything downstream assumes zero means zero</b>"],
         ["Defect pixel", "Stuck sensor pixels",
          "Before demosaic, or the defect spreads to neighbours"],
         ["Lens shading", "Vignetting, colour shading",
          "Before white balance, because the shading is colour dependent"],
         ["<b>Demosaic</b>", "One colour per pixel &rarr; three",
          "<b>The data rate triples here</b>; everything possible is done before it"],
         ["White balance", "Illuminant colour",
          "Per-channel gains; conventionally applied on the Bayer data for cost"],
         ["Colour correction matrix", "Sensor spectral response &rarr; a standard "
          "space", "Needs three channels, so after demosaic"],
         ["<b>Gamma / tone</b>", "Perceptual coding",
          "<b>After all linear operations</b> &mdash; averaging gamma-encoded values is "
          "wrong, and doing it is the commonest ISP bug"],
         ["Sharpen, noise reduction", "Perceptual quality",
          "After tone mapping, because the visibility of noise is nonlinear"]]))
    s.append("""<div class="warn"><b>Gamma is the ordering rule that is broken most
    often, and the error is visible.</b> Gamma encoding is a nonlinear map applied so that
    the limited code space is distributed according to human contrast sensitivity. Linear
    operations &mdash; scaling, blending, resizing, demosaicing, averaging &mdash; are
    only correct on <i>linear</i> light. Resizing a gamma-encoded image darkens edges and
    shifts colours; alpha-blending gamma-encoded values produces halos. <b>The fix is to
    keep the pipeline linear until the final encode</b>, and where hardware must operate
    on encoded data, to linearise and re-encode around the operation. This is a real and
    recurring defect in shipped display and camera pipelines, and it is worth an explicit
    statement in an IP block's datasheet about which domain its input and output are
    in.</div>""")
    # measure the gamma-averaging error
    rows = []
    for a, b_ in ((0.0, 1.0), (0.2, 0.8), (0.4, 0.6), (0.0, 0.5), (0.5, 1.0)):
        g = 2.2
        correct = ((a + b_) / 2)
        encoded_avg = (((a ** (1 / g)) + (b_ ** (1 / g))) / 2) ** g
        rows.append([num(a, 3), num(b_, 3), num(correct, 4), num(encoded_avg, 4),
                     num((encoded_avg - correct) / max(correct, 1e-9) * 100, 4)])
    s.append(sweep("Measured error from averaging in the gamma domain "
                   "(&gamma;&nbsp;=&nbsp;2.2), linear light values",
        ["Value A", "Value B", "Correct average (linear)",
         "Average of encoded values, decoded", "Error (%)"], rows,
        "Computed directly. <b>The first row is the worst case and it is a "
        "26&nbsp;% error</b> &mdash; averaging black and white in the encoded domain "
        "gives a result noticeably darker than mid-grey. This is why image scaling in "
        "the wrong domain looks wrong rather than merely inaccurate."))

    s.append("<h2>X38.2 Colour spaces as matrices</h2>")
    s.append(derive("Why colour conversion is a 3&times;3 matrix and when it is not", [
        ("Human colour vision has three cone types, so colour is a three-dimensional "
         "quantity.",
         "Trichromacy. Two spectra that produce the same cone responses look identical "
         "&mdash; metamerism."),
        ("A display's primaries span a triangle in chromaticity space; its gamut is "
         "that triangle.",
         "Any colour inside is reproducible; outside is not."),
        ("Converting between two sets of primaries is a change of basis: a 3&times;3 "
         "matrix on <b>linear</b> tristimulus values.",
         "<b>Linear</b> is load-bearing &mdash; see X38.1."),
        ("<b>So BT.709 to BT.2020, or camera RGB to XYZ, is one matrix multiply per "
         "pixel.</b>",
         "Nine multiplies and six adds &mdash; trivial hardware, which is why colour "
         "conversion is never the bottleneck."),
        ("It stops being a matrix when the gamut does not contain the colour, or when "
         "the transfer function is not a power law.",
         "<b>Gamut mapping is a nonlinear, perceptual and proprietary operation</b>, and "
         "HDR transfer functions (PQ, HLG) are not power laws, so they need a LUT. "
         "<b>Those two are where display IP actually differentiates.</b>"),
    ]))
    rows = []
    for name, R, G, B, W in (
            ("BT.709 / sRGB", (0.640, 0.330), (0.300, 0.600), (0.150, 0.060), "D65"),
            ("DCI-P3", (0.680, 0.320), (0.265, 0.690), (0.150, 0.060), "D65"),
            ("BT.2020", (0.708, 0.292), (0.170, 0.797), (0.131, 0.046), "D65"),
            ("Adobe RGB", (0.640, 0.330), (0.210, 0.710), (0.150, 0.060), "D65")):
        area = abs((G[0] - R[0]) * (B[1] - R[1]) - (B[0] - R[0]) * (G[1] - R[1])) / 2
        rows.append([name, f"{R[0]}, {R[1]}", f"{G[0]}, {G[1]}", f"{B[0]}, {B[1]}",
                     num(area, 4), num(area / 0.1582 * 100, 4)])
    s.append(sweep("Gamut areas in CIE xy, computed from the primaries",
        ["Space", "Red (x,y)", "Green (x,y)", "Blue (x,y)", "Triangle area",
         "Relative to BT.709 (%)"], rows,
        "Areas computed as the triangle area of the primaries in the xy chromaticity "
        "diagram. <b>xy area is a crude perceptual measure</b> &mdash; the diagram is "
        "not perceptually uniform, so these percentages overstate the green region and "
        "understate the blue &mdash; and it is the number most commonly quoted, which is "
        "worth knowing when reading a display specification."))

    s.append("<h2>X38.3 Line buffers: the memory that sets ISP area</h2>")
    s.append(ex("Why an ISP is mostly SRAM",
        "A 4K (3840-wide) pipeline, 12 bits per channel. The stages need vertical "
        "neighbourhoods: demosaic 5 lines, noise reduction 7, sharpening 5, lens "
        "shading 1, scaler 4.",
        "Each stage that looks at neighbouring rows must buffer those rows, because "
        "the sensor delivers one row at a time. Count the lines and the bits.",
        [("Line width", num(3840)),
         ("Bits per pixel (Bayer, pre-demosaic)", num(12)),
         ("Demosaic: 5 lines", num(5 * 3840 * 12 / 8 / 1024, 4, "kB")),
         ("Noise reduction: 7 lines (RGB, 36 bit)",
          num(7 * 3840 * 36 / 8 / 1024, 4, "kB")),
         ("Sharpen: 5 lines (RGB)", num(5 * 3840 * 36 / 8 / 1024, 4, "kB")),
         ("Scaler: 4 lines (RGB)", num(4 * 3840 * 36 / 8 / 1024, 4, "kB")),
         ("Total line buffers",
          num((5 * 12 + (7 + 5 + 4) * 36) * 3840 / 8 / 1024, 4, "kB")),
         ("As a fraction of a typical ISP's area", "<b>the majority</b>")],
        "<b>By counting arithmetic and not lines.</b> The filters are small &mdash; a "
        "5&times;5 convolution is 25 multiplies &mdash; and the line buffers are "
        "hundreds of kilobytes. Two consequences follow and both are architectural. "
        "<b>Process in tiles or stripes</b> rather than full lines where the algorithm "
        "permits, trading a small overlap region for a large memory saving; this is why "
        "many ISPs are tile-based. And <b>fuse stages</b> so one buffer serves several "
        "neighbourhoods rather than each stage buffering separately &mdash; the same "
        "fusion argument as in Part&nbsp;X13's accelerator dataflow, arriving in a "
        "completely different domain."))
    rows = []
    for w in (1920, 3840, 7680):
        for tile in (0, 256, 512):
            if tile == 0:
                mem = (5 * 12 + 16 * 36) * w / 8 / 1024
                ov = 0
            else:
                mem = (5 * 12 + 16 * 36) * tile / 8 / 1024
                ov = 8 / tile * 100
            rows.append([num(w), "full line" if tile == 0 else num(tile),
                         num(mem, 5), num(ov, 3),
                         num(mem / ((5 * 12 + 16 * 36) * w / 8 / 1024) * 100, 4)])
    s.append(sweep("Line-buffer memory against tile width (8-pixel halo)",
        ["Image width", "Tile width", "Line buffer (kB)", "Overlap overhead (%)",
         "Memory vs. full line (%)"], rows,
        "<b>Tiling trades a few per cent of redundant computation for an order of "
        "magnitude of memory</b>, and the trade improves as resolution rises, which is "
        "why 8K pipelines are tiled and 1080p ones often are not."))
    s.append(prob("A customer says your ISP's output does not match their reference "
                  "software. Where do you look?",
        "Almost always at a convention rather than at the arithmetic, and the candidates "
        "are few enough to enumerate. <b>Domain</b>: is the reference operating on linear "
        "or encoded values at the stage that differs? X38.1's error is large and looks "
        "like a gain error. <b>Rounding and clipping</b>: a pipeline that clips "
        "intermediate values to the output range destroys headroom that the reference "
        "keeps, and the difference appears only in highlights. <b>Chroma siting and "
        "subsampling phase</b>: 4:2:0 has several legal sitings and choosing the wrong "
        "one produces a half-pixel colour shift that is invisible on most content and "
        "obvious on a colour edge. <b>Matrix coefficients and range</b>: limited versus "
        "full range, and BT.601 versus BT.709 coefficients, are four combinations and "
        "three of them are wrong. <b>Demosaic algorithm</b>, which is genuinely allowed "
        "to differ and is where a vendor's quality claim lives. <b>Establish which by "
        "bypassing stages one at a time</b> &mdash; which requires the block to have "
        "bypass controls, and that is a design decision worth making early for exactly "
        "this conversation."))
    return "\n".join(s)
